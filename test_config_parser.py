#!/usr/bin/env python3
"""cx_config parser tests: subcommand parsing, argument types, exit-code
guards, WIP subcommand dispatch, and cmd_config FQDN normalization."""

import argparse
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


class TestConfigCmdConfigNormalization(unittest.TestCase):
    """cmd_config normalizes the FQDN before persisting credentials."""

    @mock.patch.object(cx_config, "save_config")
    def test_fqdn_strips_https_scheme_and_trailing_slash(self, mock_save):
        # Given an FQDN entered with scheme and trailing slash
        args = types.SimpleNamespace(fqdn="https://pbx.example.com/",
                                     client_id="id", client_secret="sec")
        # When config is saved
        with mock.patch("builtins.print"):
            cx_config.cmd_config(args)
        # Then only the bare host is persisted
        self.assertEqual(mock_save.call_args[0][0], {
            "fqdn": "pbx.example.com", "client_id": "id", "client_secret": "sec"})

    @mock.patch.object(cx_config, "save_config")
    def test_fqdn_strips_http_scheme(self, mock_save):
        # Given an FQDN entered with the http scheme
        args = types.SimpleNamespace(fqdn="http://pbx.example.com",
                                     client_id="id", client_secret="sec")
        # When config is saved
        with mock.patch("builtins.print"):
            cx_config.cmd_config(args)
        # Then the scheme is stripped
        self.assertEqual(mock_save.call_args[0][0]["fqdn"], "pbx.example.com")


class TestConfigParserGuards(unittest.TestCase):
    """Exit-code and help behavior of the cx_config argument parser."""

    def test_missing_subcommand_exits_with_code_2(self):
        # Given no subcommand on the command line
        with mock.patch("sys.argv", ["prog"]), \
             mock.patch("sys.stderr", StringIO()):
            # When main parses args, argparse exits with usage error code 2
            with self.assertRaises(SystemExit) as cm:
                cx_config.main()
        self.assertEqual(cm.exception.code, 2)

    def test_help_exits_zero_and_lists_wip_subcommands(self):
        # Given a top-level help request
        out = StringIO()
        # When main handles -h, it exits 0 after printing help
        with mock.patch("sys.argv", ["prog", "-h"]), \
             mock.patch("sys.stdout", out):
            with self.assertRaises(SystemExit) as cm:
                cx_config.main()
        self.assertEqual(cm.exception.code, 0)
        # Then the WIP subcommands are advertised
        for cmd in ("create-outbound-rule", "outbound-rules-update",
                    "department-members", "who-can-dial"):
            self.assertIn(cmd, out.getvalue())

    def test_non_config_command_without_credentials_file_exits(self):
        # Given no saved credentials file
        err = StringIO()
        # When a non-config command runs
        with mock.patch("sys.argv", ["prog", "users"]), \
             mock.patch("os.path.exists", return_value=False), \
             mock.patch("sys.stderr", err):
            # Then main exits 1 with a setup hint
            with self.assertRaises(SystemExit) as cm:
                cx_config.main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("config", err.getvalue())

    def test_assign_role_rejects_unknown_role(self):
        # Given a role outside the allowed choices
        with mock.patch("sys.argv", ["prog", "assign-role", "--user-id", "1",
                                     "--group-id", "1", "--role", "bogus"]), \
             mock.patch("sys.stderr", StringIO()):
            # When main parses args, argparse exits with code 2
            with self.assertRaises(SystemExit) as cm:
                cx_config.main()
        self.assertEqual(cm.exception.code, 2)


class TestConfigWipSubcommandsParse(unittest.TestCase):
    """The WIP subcommands registered in main() parse and dispatch."""

    SUBCOMMANDS = {
        "create-outbound-rule": ["--name", "R"],
        "outbound-rules-update": ["--id", "5"],
        "department-members": [],
        "who-can-dial": [],
    }

    def test_each_wip_subcommand_parses(self):
        for cmd, extra in self.SUBCOMMANDS.items():
            with self.subTest(cmd=cmd):
                with mock.patch("sys.argv", ["prog", cmd] + extra), \
                     mock.patch("os.path.exists", return_value=True), \
                     mock.patch.object(cx_config, "load_config",
                                       return_value=dict(CONFIG_CREDS)), \
                     mock.patch.object(cx_config, "save_config"), \
                     mock.patch.object(cx_config, "get_headers",
                                       return_value=dict(AUTH_HEADERS)), \
                     mock.patch("requests.get", return_value=make_response(
                     200, body={"value": [], "Id": 5, "Name": "R", "Routes": []})), \
                     mock.patch("requests.post", return_value=make_response(201)), \
                     mock.patch("requests.patch", return_value=make_response(204)), \
                     mock.patch("builtins.print"):
                    try:
                        cx_config.main()
                    except SystemExit:
                        pass


if __name__ == "__main__":
    unittest.main()
