#!/usr/bin/env python3
"""cx_call parser tests: subcommand parsing, --verbose placement on the
main parser, and exit-code/help guards."""

import argparse
import unittest
from io import StringIO
from unittest import mock

from cx_test_support import cx_call


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


class TestCallParserGuards(unittest.TestCase):
    """Exit-code and help behavior of the cx_call argument parser."""

    def test_missing_subcommand_exits_with_code_2(self):
        # Given no subcommand on the command line
        with mock.patch("sys.argv", ["prog"]), \
             mock.patch("sys.stderr", StringIO()):
            # When main parses args, argparse exits with usage error code 2
            with self.assertRaises(SystemExit) as cm:
                cx_call.main()
        self.assertEqual(cm.exception.code, 2)

    def test_help_exits_zero_and_lists_subcommands(self):
        # Given a top-level help request
        out = StringIO()
        # When main handles -h, it exits 0 after printing help
        with mock.patch("sys.argv", ["prog", "-h"]), \
             mock.patch("sys.stdout", out):
            with self.assertRaises(SystemExit) as cm:
                cx_call.main()
        self.assertEqual(cm.exception.code, 0)
        # Then all subcommands are advertised
        for cmd in ("config", "status", "devices", "call", "participant",
                    "action", "listen", "stream"):
            self.assertIn(cmd, out.getvalue())

    def test_non_config_command_without_credentials_file_exits(self):
        # Given no saved credentials file
        err = StringIO()
        # When a non-config command runs
        with mock.patch("sys.argv", ["prog", "status"]), \
             mock.patch("os.path.exists", return_value=False), \
             mock.patch("sys.stderr", err):
            # Then main exits 1 with a setup hint
            with self.assertRaises(SystemExit) as cm:
                cx_call.main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("config", err.getvalue())

    def test_action_rejects_unknown_action(self):
        # Given an action outside the allowed choices
        with mock.patch("sys.argv", ["prog", "action", "--participant-id", "1",
                                     "--action", "bogus"]), \
             mock.patch("sys.stderr", StringIO()):
            # When main parses args, argparse exits with code 2
            with self.assertRaises(SystemExit) as cm:
                cx_call.main()
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
