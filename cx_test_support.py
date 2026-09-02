#!/usr/bin/env python3
"""Shared test support for the 3cx-config / 3cx-call test suite.

Centralizes the extensionless-script import seam, the mock Response
factory, credential fixtures, and the command-invocation helpers used by
the test_config_* / test_call_* modules. Not a test module itself: the
name deliberately does not match the unittest discovery pattern
'test_*.py', so discovery never picks it up as a duplicate test module.
"""

import importlib.machinery
import importlib.util
import json
import os
import sys
import types
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


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cx_config = _import_script("cx_config", os.path.join(BASE_DIR, "3cx-config"))
cx_call = _import_script("cx_call", os.path.join(BASE_DIR, "3cx-call"))


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


# ---------------------------------------------------------------------------
# Shared fixtures/seam helpers for characterization tests
# ---------------------------------------------------------------------------

CONFIG_CREDS = {"fqdn": "pbx.example.com", "client_id": "id", "client_secret": "secret"}
CALL_CREDS = {"fqdn": "pbx.example.com", "api_key": "k", "dn": "100"}
AUTH_HEADERS = {"Authorization": "Bearer t"}
CALL_HEADERS = {"Authorization": "Bearer t", "Content-Type": "application/json"}


def list_args(**overrides):
    """Parsed-args namespace for list-style commands with sensible defaults."""
    base = {"top": 100, "skip": 0, "odata_filter": None}
    base.update(overrides)
    return types.SimpleNamespace(**base)


def invoke_config_cmd(func, args, http_method="get", response=None):
    """Run a cx_config cmd_* with config/auth/HTTP mocked at the requests seam.
    Returns the requests.<method> mock for URL/params/payload assertions."""
    with mock.patch.object(cx_config, "load_config", return_value=dict(CONFIG_CREDS)), \
         mock.patch.object(cx_config, "get_headers", return_value=dict(AUTH_HEADERS)), \
         mock.patch.object(cx_config, "handle_response"), \
         mock.patch("requests." + http_method,
                    return_value=response or make_response(200)) as mock_http:
        func(args)
    return mock_http


def invoke_call_cmd(func, args, http_method="get", response=None):
    """Run a cx_call cmd_* with config/auth/HTTP mocked at the requests seam."""
    with mock.patch.object(cx_call, "load_config", return_value=dict(CALL_CREDS)), \
         mock.patch.object(cx_call, "get_headers", return_value=dict(CALL_HEADERS)), \
         mock.patch.object(cx_call, "handle_response"), \
         mock.patch("requests." + http_method,
                    return_value=response or make_response(200)) as mock_http:
        func(args)
    return mock_http
