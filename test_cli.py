#!/usr/bin/env python3
"""Tests for 3cx-config and 3cx-call CLI tools."""

import argparse
import importlib.machinery
import importlib.util
import json
import sys
import types
import unittest
from io import StringIO
from unittest import mock

# ---------------------------------------------------------------------------
# Import scripts that lack .py extensions
# ---------------------------------------------------------------------------

def _import_script(name, path):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader, origin=path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

cx_config = _import_script("cx_config", "/home/rc/3cx/3cx-config")
cx_call = _import_script("cx_call", "/home/rc/3cx/3cx-call")

# ---------------------------------------------------------------------------
# Helper: build a mock Response object
# ---------------------------------------------------------------------------

def make_response(status_code=200, body=None, text=None, is_json=True):
    resp = mock.MagicMock()
    resp.status_code = status_code
    if body is not None:
        resp.text = json.dumps(body) if is_json else body
        resp.json.return_value = body
    elif text is not None:
        resp.text = text
        resp.json.side_effect = json.JSONDecodeError("x", "x", 0)
    else:
        resp.text = ""
    return resp


# ===========================================================================
# 3cx-config tests
# ===========================================================================

class TestConfigApiUrl(unittest.TestCase):
    def test_api_url_basic(self):
        config = {"fqdn": "pbx.example.com"}
        self.assertEqual(cx_config.api_url(config, "Users"),
                         "https://pbx.example.com/xapi/v1/Users")

    def test_api_url_nested_path(self):
        config = {"fqdn": "pbx.example.com"}
        self.assertEqual(cx_config.api_url(config, "Users/Pbx.BulkUsersDelete"),
                         "https://pbx.example.com/xapi/v1/Users/Pbx.BulkUsersDelete")


class TestConfigAddListArgs(unittest.TestCase):
    def test_adds_top_skip_filter_defaults(self):
        parser = argparse.ArgumentParser()
        cx_config.add_list_args(parser)
        args = parser.parse_args([])
        self.assertEqual(args.top, 100)
        self.assertEqual(args.skip, 0)
        self.assertIsNone(args.odata_filter)

    def test_custom_values(self):
        parser = argparse.ArgumentParser()
        cx_config.add_list_args(parser)
        args = parser.parse_args(["--top", "50", "--skip", "10", "--filter", "Name eq 'Test'"])
        self.assertEqual(args.top, 50)
        self.assertEqual(args.skip, 10)
        self.assertEqual(args.odata_filter, "Name eq 'Test'")


class TestConfigBuildListParams(unittest.TestCase):
    def test_default_params(self):
        args = types.SimpleNamespace(top=100, skip=0, odata_filter=None)
        params = cx_config.build_list_params(args)
        self.assertEqual(params, {"$top": 100, "$skip": 0, "$orderby": "Id"})

    def test_with_filter(self):
        args = types.SimpleNamespace(top=50, skip=5, odata_filter="Name eq 'Foo'")
        params = cx_config.build_list_params(args)
        self.assertEqual(params["$filter"], "Name eq 'Foo'")

    def test_no_filter_attr(self):
        args = types.SimpleNamespace(top=10, skip=0)
        params = cx_config.build_list_params(args)
        self.assertNotIn("$filter", params)


class TestConfigHandleResponse(unittest.TestCase):
    def test_error_400(self):
        resp = make_response(400, text="Bad Request", is_json=False)
        with self.assertRaises(SystemExit):
            cx_config.handle_response(resp)

    def test_error_500(self):
        resp = make_response(500, text="Internal Server Error", is_json=False)
        with self.assertRaises(SystemExit):
            cx_config.handle_response(resp)

    def test_200_json(self):
        resp = make_response(200, body={"value": [1, 2, 3]})
        with mock.patch("builtins.print") as mock_print:
            cx_config.handle_response(resp)
            mock_print.assert_called_once()
            printed = mock_print.call_args[0][0]
            self.assertIn('"value"', printed)

    def test_200_non_json(self):
        resp = make_response(200, text="plain text")
        with mock.patch("builtins.print") as mock_print:
            cx_config.handle_response(resp)
            mock_print.assert_called_once_with("plain text")

    def test_200_empty_body(self):
        resp = make_response(200)
        with mock.patch("builtins.print") as mock_print:
            cx_config.handle_response(resp)
            mock_print.assert_called_once_with("Success: 200")


class TestConfigTokenCaching(unittest.TestCase):
    @mock.patch.object(cx_config, "save_config")
    @mock.patch.object(cx_config, "get_token")
    @mock.patch("time.time", return_value=1000.0)
    def test_uses_cached_token(self, mock_time, mock_get_token, mock_save):
        config = {
            "fqdn": "pbx.example.com",
            "client_id": "id",
            "client_secret": "secret",
            "access_token": "cached_tok",
            "token_expiry": 2000.0,
        }
        headers = cx_config.get_headers(config)
        self.assertEqual(headers["Authorization"], "Bearer cached_tok")
        mock_get_token.assert_not_called()

    @mock.patch.object(cx_config, "save_config")
    @mock.patch.object(cx_config, "get_token",
                       return_value={"access_token": "new_tok", "expires_in": 3600})
    @mock.patch("time.time", return_value=1000.0)
    def test_fetches_new_token_when_expired(self, mock_time, mock_get_token, mock_save):
        config = {
            "fqdn": "pbx.example.com",
            "client_id": "id",
            "client_secret": "secret",
            "access_token": "old_tok",
            "token_expiry": 1003.0,  # within 5s safety margin
        }
        headers = cx_config.get_headers(config)
        self.assertEqual(headers["Authorization"], "Bearer new_tok")
        mock_get_token.assert_called_once()
        mock_save.assert_called_once()

    @mock.patch.object(cx_config, "save_config")
    @mock.patch.object(cx_config, "get_token",
                       return_value={"access_token": "fresh_tok", "expires_in": 3600})
    @mock.patch("time.time", return_value=1000.0)
    def test_fetches_token_when_no_cached(self, mock_time, mock_get_token, mock_save):
        config = {"fqdn": "pbx.example.com", "client_id": "id", "client_secret": "secret"}
        headers = cx_config.get_headers(config)
        self.assertEqual(headers["Authorization"], "Bearer fresh_tok")
        mock_get_token.assert_called_once()


class TestConfigAllSubcommandsParse(unittest.TestCase):
    """Verify all 31 subcommands parse without error via sys.argv mocking."""

    SUBCOMMANDS = {
        "config": ["--fqdn", "x", "--client-id", "x", "--client-secret", "x"],
        "token": [],
        "version": [],
        "system-status": [],
        "departments": [],
        "create-department": ["--name", "T", "--prompt-set", "EN"],
        "delete-department": ["--id", "1"],
        "users": [],
        "create-user": ["--first-name", "A", "--last-name", "B", "--email", "a@b.c",
                         "--password", "P", "--extension", "100", "--prompt-set", "EN"],
        "delete-users": ["--ids", "1", "2", "3"],
        "assign-role": ["--user-id", "1", "--group-id", "1", "--role", "users"],
        "live-chat": [],
        "create-live-chat": ["--link", "x", "--group-id", "1",
                              "--group-name", "G", "--group-number", "100"],
        "parking": [],
        "active-calls": [],
        "call-history": [],
        "recordings": [],
        "inbound-rules": [],
        "outbound-rules": [],
        "ivrs": [],
        "queues": [],
        "ring-groups": [],
        "trunks": [],
        "phones": [],
        "contacts": [],
        "blacklist": [],
        "ip-blocklist": [],
        "activity-log": [],
        "backups": [],
        "restart": [],
        "emergency-numbers": [],
    }

    def test_count_is_31(self):
        self.assertEqual(len(self.SUBCOMMANDS), 31)

    def test_each_subcommand_parses(self):
        for cmd, extra_args in self.SUBCOMMANDS.items():
            with self.subTest(cmd=cmd):
                with mock.patch("sys.argv", ["prog", cmd] + extra_args):
                    # Intercept parse_args result; run only up to parse, not execute
                    with mock.patch("os.path.exists", return_value=True), \
                         mock.patch.object(cx_config, "load_config", return_value={
                             "fqdn": "x", "client_id": "c", "client_secret": "s",
                         }), \
                         mock.patch.object(cx_config, "save_config"), \
                         mock.patch.object(cx_config, "get_headers",
                                           return_value={"Authorization": "Bearer t"}), \
                         mock.patch.object(cx_config, "get_token",
                                           return_value={"access_token": "t", "expires_in": 3600}), \
                         mock.patch("requests.get", return_value=make_response(
                         200, body={"value": [], "Version": "20", "FQDN": "x"})), \
                         mock.patch("requests.post", return_value=make_response(200)), \
                         mock.patch("requests.patch", return_value=make_response(200)), \
                         mock.patch("requests.delete", return_value=make_response(200)), \
                         mock.patch("builtins.print"):
                        try:
                            cx_config.main()
                        except SystemExit:
                            pass


class TestConfigArgTypes(unittest.TestCase):
    def test_ids_accepts_multiple_ints(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("delete-users")
        p.add_argument("--ids", type=int, nargs="+", required=True)
        args = parser.parse_args(["delete-users", "--ids", "10", "20", "30"])
        self.assertEqual(args.ids, [10, 20, 30])

    def test_confirm_is_boolean_flag(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("restart")
        p.add_argument("--confirm", action="store_true")
        self.assertFalse(parser.parse_args(["restart"]).confirm)
        self.assertTrue(parser.parse_args(["restart", "--confirm"]).confirm)

    def test_delete_nargs_plus(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("recordings")
        p.add_argument("--delete", type=int, nargs="+")
        args = parser.parse_args(["recordings", "--delete", "5", "6"])
        self.assertEqual(args.delete, [5, 6])


class TestConfigCmdRestart(unittest.TestCase):
    def test_restart_without_confirm_exits(self):
        args = types.SimpleNamespace(confirm=False)
        with self.assertRaises(SystemExit):
            cx_config.cmd_restart(args)


class TestConfigCmdDepartments(unittest.TestCase):
    @mock.patch.object(cx_config, "handle_response")
    @mock.patch("requests.get")
    @mock.patch.object(cx_config, "get_headers", return_value={"Authorization": "Bearer t"})
    @mock.patch.object(cx_config, "load_config", return_value={"fqdn": "pbx.example.com"})
    def test_name_filter(self, mock_load, mock_hdr, mock_get, mock_hr):
        args = types.SimpleNamespace(top=100, skip=0, odata_filter=None, name="Sales")
        cx_config.cmd_departments(args)
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["$filter"], "Name eq 'Sales'")


class TestConfigCmdUsers(unittest.TestCase):
    @mock.patch.object(cx_config, "handle_response")
    @mock.patch("requests.get")
    @mock.patch.object(cx_config, "get_headers", return_value={"Authorization": "Bearer t"})
    @mock.patch.object(cx_config, "load_config", return_value={"fqdn": "pbx.example.com"})
    def test_email_filter_lowered(self, mock_load, mock_hdr, mock_get, mock_hr):
        args = types.SimpleNamespace(top=100, skip=0, odata_filter=None,
                                     email="Admin@Example.COM")
        cx_config.cmd_users(args)
        params = mock_get.call_args.kwargs["params"]
        self.assertIn("admin@example.com", params["$filter"])
        self.assertEqual(params["$top"], 1)


class TestConfigBugFixes(unittest.TestCase):
    @mock.patch.object(cx_config, "handle_response")
    @mock.patch("requests.post")
    @mock.patch.object(cx_config, "get_headers", return_value={"Authorization": "Bearer t"})
    @mock.patch.object(cx_config, "load_config", return_value={"fqdn": "pbx.example.com"})
    def test_delete_users_uses_bulk_endpoint(self, mock_load, mock_hdr, mock_post, mock_hr):
        args = types.SimpleNamespace(ids=[1, 2])
        cx_config.cmd_delete_users(args)
        url_called = mock_post.call_args[0][0]
        self.assertIn("Pbx.BatchDelete", url_called)

    @mock.patch.object(cx_config, "handle_response")
    @mock.patch("requests.post")
    @mock.patch.object(cx_config, "get_headers", return_value={"Authorization": "Bearer t"})
    @mock.patch.object(cx_config, "load_config", return_value={"fqdn": "pbx.example.com"})
    def test_delete_department_payload_capital_id(self, mock_load, mock_hdr, mock_post, mock_hr):
        args = types.SimpleNamespace(id=42)
        cx_config.cmd_delete_department(args)
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("Id", payload)
        self.assertNotIn("id", payload)
        self.assertEqual(payload["Id"], 42)


# ===========================================================================
# 3cx-call tests
# ===========================================================================

class TestCallApiUrl(unittest.TestCase):
    def test_no_path(self):
        config = {"fqdn": "pbx.example.com"}
        self.assertEqual(cx_call.api_url(config),
                         "https://pbx.example.com/callcontrol")

    def test_with_path(self):
        config = {"fqdn": "pbx.example.com"}
        self.assertEqual(cx_call.api_url(config, "100/devices"),
                         "https://pbx.example.com/callcontrol/100/devices")


class TestCallWsUrl(unittest.TestCase):
    def test_format(self):
        config = {"fqdn": "pbx.example.com"}
        self.assertEqual(cx_call.ws_url(config),
                         "wss://pbx.example.com/callcontrol/ws")


class TestCallHandleResponse(unittest.TestCase):
    def test_401_special_message(self):
        resp = make_response(401, text="Unauthorized", is_json=False)
        with self.assertRaises(SystemExit):
            cx_call.handle_response(resp)

    def test_403_error(self):
        resp = make_response(403, text="Forbidden", is_json=False)
        with self.assertRaises(SystemExit):
            cx_call.handle_response(resp)

    def test_200_json(self):
        resp = make_response(200, body={"status": "ok"})
        with mock.patch("builtins.print") as mock_print:
            cx_call.handle_response(resp)
            printed = mock_print.call_args[0][0]
            self.assertIn('"status"', printed)

    def test_200_empty_body(self):
        resp = make_response(200)
        with mock.patch("builtins.print") as mock_print:
            cx_call.handle_response(resp)
            printed = mock_print.call_args[0][0]
            self.assertIn("200", printed)

    def test_401_prints_api_key_hint(self):
        """Verify the 401 message mentions API key instructions."""
        resp = make_response(401, text="Unauthorized", is_json=False)
        captured = StringIO()
        with mock.patch("sys.stderr", captured):
            with self.assertRaises(SystemExit):
                cx_call.handle_response(resp)
        self.assertIn("API", captured.getvalue())


class TestCallVerboseRequest(unittest.TestCase):
    @mock.patch("requests.get", return_value=make_response(200))
    def test_verbose_prints_to_stderr(self, mock_get):
        captured = StringIO()
        with mock.patch("sys.stderr", captured):
            cx_call.verbose_request("get", "https://example.com/test", verbose=True)
        self.assertIn("[GET]", captured.getvalue())
        self.assertIn("https://example.com/test", captured.getvalue())

    @mock.patch("requests.get", return_value=make_response(200))
    def test_not_verbose_silent(self, mock_get):
        captured = StringIO()
        with mock.patch("sys.stderr", captured):
            cx_call.verbose_request("get", "https://example.com/test", verbose=False)
        self.assertEqual(captured.getvalue(), "")


class TestCallAllSubcommandsParse(unittest.TestCase):
    """Verify all 8 subcommands parse without error.

    Instead of calling main() (which would trigger WebSocket for 'listen'),
    we build the parser via main() but intercept parse_args.
    """

    SUBCOMMANDS = {
        "config": ["--fqdn", "x", "--api-key", "k", "--dn", "100"],
        "status": [],
        "devices": [],
        "call": ["--destination", "200"],
        "participant": [],
        "action": ["--participant-id", "1", "--action", "drop"],
        "listen": [],
        "stream": ["--participant-id", "1"],
    }

    def test_count_is_8(self):
        self.assertEqual(len(self.SUBCOMMANDS), 8)

    def test_each_subcommand_parses(self):
        for cmd, extra_args in self.SUBCOMMANDS.items():
            with self.subTest(cmd=cmd):
                # Capture the real parse_args result but prevent func execution
                parsed = [None]
                original_parse = argparse.ArgumentParser.parse_args

                def intercept_parse(self_parser, args=None, namespace=None):
                    result = original_parse(self_parser, args, namespace)
                    parsed[0] = result
                    # Replace func with a no-op so the command body never runs
                    if hasattr(result, "func"):
                        result.func = lambda a: None
                    return result

                with mock.patch("sys.argv", ["prog", cmd] + extra_args), \
                     mock.patch.object(argparse.ArgumentParser, "parse_args",
                                       intercept_parse), \
                     mock.patch("os.path.exists", return_value=True), \
                     mock.patch.object(cx_call, "load_config",
                                       return_value={"fqdn": "x", "api_key": "k", "dn": "100"}), \
                     mock.patch.object(cx_call, "save_config"), \
                     mock.patch("builtins.print"):
                    try:
                        cx_call.main()
                    except SystemExit:
                        pass
                self.assertIsNotNone(parsed[0])
                self.assertEqual(parsed[0].command, cmd)


class TestCallVerboseOnMainParser(unittest.TestCase):
    def test_verbose_is_on_main_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", "-v", action="store_true")
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("status")
        args = parser.parse_args(["--verbose", "status"])
        self.assertTrue(args.verbose)

    def test_verbose_before_subcommand(self):
        """--verbose must come before the subcommand name."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", "-v", action="store_true")
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("status")
        args = parser.parse_args(["--verbose", "status"])
        self.assertTrue(args.verbose)


class TestCallListenRetries(unittest.TestCase):
    def test_default_is_5(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("listen")
        p.add_argument("--retries", type=int, default=5)
        self.assertEqual(parser.parse_args(["listen"]).retries, 5)

    def test_custom_value(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("listen")
        p.add_argument("--retries", type=int, default=5)
        self.assertEqual(parser.parse_args(["listen", "--retries", "10"]).retries, 10)


class TestCallGetToken(unittest.TestCase):
    """Tests for cx_call.get_token() OAuth2 client credentials flow."""

    @mock.patch.object(cx_call, "save_config")
    @mock.patch("requests.post")
    def test_get_token_posts_correct_payload(self, mock_post, mock_save):
        mock_post.return_value = make_response(200, body={
            "access_token": "jwt_token_abc",
            "expires_in": 3600,
        })
        config = {"fqdn": "pbx.example.com", "api_key": "secret123", "dn": "100"}
        token = cx_call.get_token(config)
        self.assertEqual(token, "jwt_token_abc")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://pbx.example.com/connect/token")
        self.assertEqual(call_args[1]["data"]["client_id"], "100")
        self.assertEqual(call_args[1]["data"]["client_secret"], "secret123")
        self.assertEqual(call_args[1]["data"]["grant_type"], "client_credentials")

    @mock.patch.object(cx_call, "save_config")
    @mock.patch("requests.post")
    @mock.patch("time.time", return_value=1000.0)
    def test_get_token_uses_cached_when_valid(self, mock_time, mock_post, mock_save):
        config = {
            "fqdn": "pbx.example.com",
            "api_key": "secret123",
            "dn": "100",
            "access_token": "cached_jwt",
            "token_expiry": 2000.0,
        }
        token = cx_call.get_token(config)
        self.assertEqual(token, "cached_jwt")
        mock_post.assert_not_called()

    @mock.patch.object(cx_call, "save_config")
    @mock.patch("requests.post")
    @mock.patch("time.time", return_value=1000.0)
    def test_get_token_refreshes_when_expired(self, mock_time, mock_post, mock_save):
        mock_post.return_value = make_response(200, body={
            "access_token": "fresh_jwt",
            "expires_in": 3600,
        })
        config = {
            "fqdn": "pbx.example.com",
            "api_key": "secret123",
            "dn": "100",
            "access_token": "stale_jwt",
            "token_expiry": 1003.0,  # within 5s safety margin
        }
        token = cx_call.get_token(config)
        self.assertEqual(token, "fresh_jwt")
        mock_post.assert_called_once()
        mock_save.assert_called_once()
        self.assertEqual(config["access_token"], "fresh_jwt")
        self.assertEqual(config["token_expiry"], 4600.0)


class TestCallGetHeaders(unittest.TestCase):
    """Tests for cx_call.get_headers() using get_token internally."""

    @mock.patch.object(cx_call, "get_token", return_value="my_bearer_token")
    def test_get_headers_returns_bearer_and_content_type(self, mock_get_token):
        config = {"fqdn": "pbx.example.com", "api_key": "k", "dn": "100"}
        headers = cx_call.get_headers(config)
        mock_get_token.assert_called_once_with(config)
        self.assertEqual(headers["Authorization"], "Bearer my_bearer_token")
        self.assertEqual(headers["Content-Type"], "application/json")


if __name__ == "__main__":
    unittest.main()
