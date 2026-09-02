#!/usr/bin/env python3
"""Core cx_call tests: URL building, response handling, verbose requests,
OAuth2 token flow, headers, listen retries, and cmd_config normalization."""

import argparse
import types
import unittest
from io import StringIO
from unittest import mock

from cx_test_support import cx_call, make_response


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


class TestCallCmdConfigNormalization(unittest.TestCase):
    @mock.patch.object(cx_call, "save_config")
    def test_fqdn_strips_scheme_and_trailing_slash(self, mock_save):
        # Given an FQDN entered with scheme and trailing slash
        args = types.SimpleNamespace(fqdn="https://pbx.example.com/",
                                     api_key="k", dn="100")
        # When config is saved
        with mock.patch("builtins.print"):
            cx_call.cmd_config(args)
        # Then only the bare host is persisted
        self.assertEqual(mock_save.call_args[0][0],
                         {"fqdn": "pbx.example.com", "api_key": "k", "dn": "100"})


if __name__ == "__main__":
    unittest.main()
