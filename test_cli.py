#!/usr/bin/env python3
"""Compatibility entry point for the 3CX CLI test suite.

The suite was split out of this (formerly 2050-line) module into focused
test modules:

- test_config_core          - cx_config URLs, list params, tokens, responses
- test_config_parser        - cx_config subcommand parsing and guards
- test_config_cmd_users     - cx_config departments/users/roles/live-chat
- test_config_cmd_system    - cx_config version/recordings/backups/restart
- test_config_cmd_endpoints - cx_config rule/infra/security endpoint mapping
- test_config_cmd_outbound  - cx_config outbound-rule create/update flows
- test_call_core            - cx_call URLs, tokens, responses, verbose
- test_call_parser          - cx_call subcommand parsing and guards
- test_call_commands        - cx_call status/call/action/stream/listen

Shared helpers (extensionless-script import seam, make_response,
list_args, invoke_*_cmd) live in cx_test_support.py, which deliberately
does not match the discovery pattern 'test_*.py'.

Both entry points run the full 148-test suite exactly once:

- ``python3 -m unittest discover -p 'test_*.py'`` discovers each focused
  module directly; load_tests sees the discovery pattern and yields this
  module's (empty) own test list so nothing runs twice.
- ``python3 -m unittest test_cli.py`` (historical command) has no
  discovery pattern, so load_tests assembles the full suite from the
  focused modules.
"""

import unittest

SUITE_MODULES = (
    "test_config_core",
    "test_config_parser",
    "test_config_cmd_users",
    "test_config_cmd_system",
    "test_config_cmd_endpoints",
    "test_config_cmd_outbound",
    "test_call_core",
    "test_call_parser",
    "test_call_commands",
)


def load_tests(loader, tests, pattern):
    if pattern is not None:
        # Discovery run: the focused modules are discovered on their own,
        # so this module contributes nothing (avoids duplicate execution).
        return tests
    # Direct run (`python3 -m unittest test_cli.py` or `python3 test_cli.py`):
    # assemble the complete suite from the focused modules.
    suite = unittest.TestSuite()
    for name in SUITE_MODULES:
        suite.addTests(loader.loadTestsFromName(name))
    return suite


if __name__ == "__main__":
    unittest.main()
