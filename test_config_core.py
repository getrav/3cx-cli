#!/usr/bin/env python3
"""Core cx_config tests: URL building, list args/params, response handling,
token caching/expiry, config file persistence, and regression bug fixes."""

import argparse
import json
import os
import tempfile
import types
import unittest
from unittest import mock

from cx_test_support import CONFIG_CREDS, cx_config, make_response


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


class TestConfigGetTokenHttp(unittest.TestCase):
    """cx_config.get_token posts OAuth2 client credentials to /connect/token."""

    @mock.patch("requests.post")
    def test_posts_client_credentials_to_token_endpoint(self, mock_post):
        # Given a PBX FQDN and client credentials
        mock_post.return_value = make_response(200, body={"access_token": "tok", "expires_in": 60})
        # When a token is requested
        token = cx_config.get_token("pbx.example.com", "id", "secret")
        # Then the token endpoint receives the client_credentials grant payload
        self.assertEqual(mock_post.call_args[0][0], "https://pbx.example.com/connect/token")
        self.assertEqual(mock_post.call_args.kwargs["data"], {
            "client_id": "id",
            "client_secret": "secret",
            "grant_type": "client_credentials",
        })
        self.assertEqual(token["access_token"], "tok")


class TestConfigTokenExpiryCap(unittest.TestCase):
    """Cached token lifetime is capped at 45s regardless of expires_in."""

    @mock.patch.object(cx_config, "save_config")
    @mock.patch.object(cx_config, "get_token",
                       return_value={"access_token": "tok", "expires_in": 3600})
    @mock.patch("time.time", return_value=1000.0)
    def test_expiry_capped_at_45_seconds(self, mock_time, mock_get_token, mock_save):
        # Given no usable cached token and a generous upstream expires_in
        config = dict(CONFIG_CREDS)
        # When headers are built
        cx_config.get_headers(config)
        # Then the cache expiry is capped 45s out, not the full 3600s
        self.assertEqual(config["token_expiry"], 1045.0)
        mock_save.assert_called_once()

    @mock.patch.object(cx_config, "save_config")
    @mock.patch.object(cx_config, "get_token",
                       return_value={"access_token": "tok", "expires_in": 30})
    @mock.patch("time.time", return_value=1000.0)
    def test_shorter_expires_in_wins(self, mock_time, mock_get_token, mock_save):
        # Given a token whose expires_in is below the 45s cap
        config = dict(CONFIG_CREDS)
        # When headers are built
        cx_config.get_headers(config)
        # Then the shorter upstream lifetime is used
        self.assertEqual(config["token_expiry"], 1030.0)

    @mock.patch("time.time", return_value=1000.0)
    def test_headers_shape_with_cached_token(self, mock_time):
        # Given a still-valid cached token
        config = dict(CONFIG_CREDS, access_token="cached", token_expiry=2000.0)
        # When headers are built
        headers = cx_config.get_headers(config)
        # Then they carry the bearer token and JSON content type
        self.assertEqual(headers, {
            "Authorization": "Bearer cached",
            "Content-Type": "application/json",
        })


class TestConfigFilePersistence(unittest.TestCase):
    """load_config/save_config file contract on ~/.3cx-config.json."""

    def test_load_config_returns_empty_dict_when_file_missing(self):
        # Given a config path that does not exist
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.json")
            with mock.patch.object(cx_config, "CONFIG_FILE", path):
                # When config is loaded, an empty dict comes back
                self.assertEqual(cx_config.load_config(), {})

    def test_save_config_writes_json_with_0600_permissions(self):
        # Given a writable config path
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.json")
            with mock.patch.object(cx_config, "CONFIG_FILE", path):
                # When config is saved
                cx_config.save_config({"fqdn": "pbx.example.com"})
                # Then the file holds the JSON and is owner-only read/write
                with open(path) as f:
                    self.assertEqual(json.load(f), {"fqdn": "pbx.example.com"})
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)


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


if __name__ == "__main__":
    unittest.main()
