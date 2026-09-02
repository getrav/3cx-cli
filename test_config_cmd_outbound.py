#!/usr/bin/env python3
"""cx_config outbound-rule command contracts: the outbound-rules-update
GET/PATCH flow and the create-outbound-rule POST payload."""

import types
import unittest
from io import StringIO
from unittest import mock

from cx_test_support import (
    AUTH_HEADERS,
    CONFIG_CREDS,
    cx_config,
    make_response,
)


class TestConfigCmdOutboundRulesUpdate(unittest.TestCase):
    """outbound-rules-update GET/PATCH flow."""

    RULE = {"Id": 5, "Name": "Old", "GroupIds": [30],
            "Routes": [{"TrunkId": 1, "CallerID": "old", "Prepend": "", "StripDigits": 0}]}

    def _args(self, **overrides):
        base = dict(id=5, groups=None, trunk=None, caller_id=None, prepend=None,
                    strip_digits=None, name=None, prefix=None, priority=None)
        base.update(overrides)
        return types.SimpleNamespace(**base)

    def _run(self, args, get_side_effect=None, patch_response=None):
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get") as mock_get, \
             mock.patch("requests.patch",
                        return_value=patch_response or make_response(204)) as mock_patch, \
             mock.patch("builtins.print"):
            mock_get.side_effect = get_side_effect or [
                make_response(200, body=dict(self.RULE)),
                make_response(200, body=dict(self.RULE)),
            ]
            cx_config.cmd_outbound_rules_update(args)
        return mock_get, mock_patch

    def test_fetches_rule_then_patches_same_entity(self):
        # Given an existing rule and a name update
        mock_get, mock_patch = self._run(self._args(name="New"))
        # Then the rule is fetched first and the same entity is patched
        self.assertEqual(mock_get.call_args_list[0][0][0],
                         "https://pbx.example.com/xapi/v1/OutboundRules(5)")
        self.assertEqual(mock_patch.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/OutboundRules(5)")
        self.assertEqual(mock_patch.call_args.kwargs["json"], {"Name": "New"})

    def test_name_prefix_and_priority_fields(self):
        # Given name, prefix and a zero priority (0 must not be treated as missing)
        _, mock_patch = self._run(self._args(name="N", prefix="00", priority=0))
        # Then all three fields are patched, priority 0 included
        self.assertEqual(mock_patch.call_args.kwargs["json"],
                         {"Name": "N", "Prefix": "00", "Priority": 0})

    def test_groups_parse_comma_separated(self):
        # Given comma-separated group ids with a space
        _, mock_patch = self._run(self._args(groups="30, 34"))
        # Then they parse to an int list
        self.assertEqual(mock_patch.call_args.kwargs["json"], {"GroupIds": [30, 34]})

    def test_trunk_updates_first_route(self):
        # Given a trunk change
        _, mock_patch = self._run(self._args(trunk=9))
        # Then route 0's TrunkId is replaced, other route fields preserved
        self.assertEqual(mock_patch.call_args.kwargs["json"], {
            "Routes": [{"TrunkId": 9, "CallerID": "old", "Prepend": "", "StripDigits": 0}]})

    def test_no_flags_exits_before_patch(self):
        # Given no update flags
        with self.assertRaises(SystemExit):
            mock_get, mock_patch = self._run(self._args())
            mock_patch.assert_not_called()

    def test_fetch_failure_exits_without_patch(self):
        # Given a missing rule
        with self.assertRaises(SystemExit):
            with mock.patch("sys.stderr", StringIO()):
                mock_get, mock_patch = self._run(
                    self._args(name="N"),
                    get_side_effect=[make_response(404, text="no", is_json=False)])
                mock_patch.assert_not_called()


class TestConfigCmdCreateOutboundRule(unittest.TestCase):
    """create-outbound-rule POST payload contract."""

    def _args(self, **overrides):
        base = dict(name="Rule1", prefix=None, priority=None, groups=None,
                    trunk=None, caller_id=None, prepend=None, strip_digits=None)
        base.update(overrides)
        return types.SimpleNamespace(**base)

    def _run(self, args, post_response=None):
        resp = post_response or make_response(201)
        resp.headers = {}  # no Location header -> no follow-up GET
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.post", return_value=resp) as mock_post, \
             mock.patch("builtins.print"):
            cx_config.cmd_create_outbound_rule(args)
        return mock_post

    def test_posts_five_route_payload(self):
        # Given a fully specified rule
        mock_post = self._run(self._args(groups="30,34", trunk=7, caller_id="cid",
                                         prepend="9", strip_digits=1,
                                         prefix="00", priority=3))
        # Then the POST carries 5 routes with route 0 populated
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/OutboundRules")
        payload = call.kwargs["json"]
        self.assertEqual(payload["Name"], "Rule1")
        self.assertEqual(payload["Prefix"], "00")
        self.assertEqual(payload["Priority"], 3)
        self.assertEqual(payload["NumberLengthRanges"], "")
        self.assertEqual(payload["GroupIds"], [30, 34])
        self.assertEqual(payload["DNRanges"], [])
        self.assertEqual(len(payload["Routes"]), 5)
        self.assertEqual(payload["Routes"][0], {
            "Append": "", "CallerID": "cid", "Prepend": "9",
            "StripDigits": 1, "TrunkId": 7})
        empty_route = {"Append": "", "CallerID": "", "Prepend": "",
                       "StripDigits": 0, "TrunkId": -1}
        for route in payload["Routes"][1:]:
            self.assertEqual(route, empty_route)

    def test_defaults_when_optional_flags_missing(self):
        # Given only the required name
        mock_post = self._run(self._args())
        # Then optional fields fall back to empty/zero/-1 defaults
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["Prefix"], "")
        self.assertEqual(payload["Priority"], 0)
        self.assertEqual(payload["GroupIds"], [])
        self.assertEqual(payload["Routes"][0], {
            "Append": "", "CallerID": "", "Prepend": "",
            "StripDigits": 0, "TrunkId": -1})

    def test_error_status_exits(self):
        # Given a server rejection
        resp = make_response(400, text="bad", is_json=False)
        resp.headers = {}
        # When create runs, it exits 1
        with mock.patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self._run(self._args(), post_response=resp)
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
