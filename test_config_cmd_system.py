#!/usr/bin/env python3
"""cx_config system-operation command contracts: version, active calls,
recordings, call history, activity log, backups, restart, emergency
numbers, and the token command."""

import json
import types
import unittest
from io import StringIO
from unittest import mock

from cx_test_support import (
    AUTH_HEADERS,
    CONFIG_CREDS,
    cx_config,
    invoke_config_cmd,
    list_args,
    make_response,
)


class TestConfigCmdVersion(unittest.TestCase):
    def test_prints_only_version_and_fqdn(self):
        # Given a SystemStatus response with extra fields
        resp = make_response(200, body={"Version": "20.0.0.1",
                                        "FQDN": "pbx.example.com", "Extra": "x"})
        # When version runs
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", return_value=resp) as mock_get, \
             mock.patch("builtins.print") as mock_print:
            cx_config.cmd_version(types.SimpleNamespace())
        # Then SystemStatus is fetched and only Version/FQDN are printed
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/SystemStatus")
        printed = json.loads(mock_print.call_args[0][0])
        self.assertEqual(printed, {"Version": "20.0.0.1", "FQDN": "pbx.example.com"})

    def test_error_status_delegates_to_handle_response(self):
        # Given a SystemStatus error with a JSON body
        resp = make_response(500, body={"error": "boom"})
        # When version runs, handle_response exits 1
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", return_value=resp), \
             mock.patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cx_config.cmd_version(types.SimpleNamespace())
        self.assertEqual(cm.exception.code, 1)


class TestConfigCmdActiveCalls(unittest.TestCase):
    def test_drop_posts_to_dropcall_endpoint(self):
        # Given a call drop request
        args = list_args(drop=42)
        # When active-calls --drop runs
        mock_post = invoke_config_cmd(cx_config.cmd_active_calls, args, "post")
        # Then the DropCall action endpoint is posted with no body
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/ActiveCalls(42)/Pbx.DropCall")
        self.assertNotIn("json", call.kwargs)

    def test_list_gets_active_calls(self):
        # Given default list args
        args = list_args(drop=None)
        # When active calls are listed
        mock_get = invoke_config_cmd(cx_config.cmd_active_calls, args)
        # Then ActiveCalls is queried
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/ActiveCalls")


class TestConfigCmdRecordings(unittest.TestCase):
    def test_delete_posts_bulk_delete_with_ids(self):
        # Given recording deletions
        args = list_args(download=None, delete=[123, 456])
        # When recordings --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_recordings, args, "post")
        # Then the bulk delete endpoint receives capital-Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/Recordings/Pbx.BulkRecordingsDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [123, 456]})

    def test_list_gets_recordings(self):
        # Given default list args
        args = list_args(download=None, delete=None)
        # When recordings are listed
        mock_get = invoke_config_cmd(cx_config.cmd_recordings, args)
        # Then Recordings is queried
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Recordings")

    def test_download_writes_wav_file(self):
        # Given a downloadable recording response
        resp = make_response(200)
        resp.content = b"WAVDATA"
        args = list_args(download=7, delete=None)
        m_open = mock.mock_open()
        # When recordings --download runs
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", return_value=resp) as mock_get, \
             mock.patch("builtins.open", m_open), \
             mock.patch("builtins.print"):
            cx_config.cmd_recordings(args)
        # Then the download endpoint is hit and bytes land in recording_<id>.wav
        self.assertEqual(mock_get.call_args[0][0],
            "https://pbx.example.com/xapi/v1/Recordings/Pbx.DownloadRecording(recId=7)")
        m_open.assert_called_once_with("recording_7.wav", "wb")
        m_open().write.assert_called_once_with(b"WAVDATA")

    def test_download_error_exits_without_writing(self):
        # Given a failed download
        resp = make_response(404, text="not found", is_json=False)
        args = list_args(download=7, delete=None)
        m_open = mock.mock_open()
        # When recordings --download runs, it exits 1 and writes nothing
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", return_value=resp), \
             mock.patch("builtins.open", m_open), \
             mock.patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cx_config.cmd_recordings(args)
        self.assertEqual(cm.exception.code, 1)
        m_open.assert_not_called()


class TestConfigCmdCallHistory(unittest.TestCase):
    def test_uses_getcalllogdata_function_with_explicit_range(self):
        # Given an explicit date range
        args = list_args(start="2026-01-01T00:00:00Z", end="2026-01-31T23:59:59Z")
        # When call-history runs
        mock_get = invoke_config_cmd(cx_config.cmd_call_history, args)
        # Then the OData function URL embeds the range and drops $orderby
        url = mock_get.call_args[0][0]
        self.assertIn("ReportCallLogData/Pbx.GetCallLogData(", url)
        self.assertIn("periodFrom=2026-01-01T00:00:00Z", url)
        self.assertIn("periodTo=2026-01-31T23:59:59Z", url)
        params = mock_get.call_args.kwargs["params"]
        self.assertNotIn("$orderby", params)
        self.assertEqual(params["$top"], 100)

    def test_default_range_is_populated(self):
        # Given no explicit date range
        args = list_args(start=None, end=None)
        # When call-history runs
        mock_get = invoke_config_cmd(cx_config.cmd_call_history, args)
        # Then default period bounds are still present in the URL
        url = mock_get.call_args[0][0]
        self.assertIn("periodFrom=", url)
        self.assertIn("periodTo=", url)


class TestConfigCmdActivityLog(unittest.TestCase):
    def test_purge_posts_purgelogs(self):
        # Given a purge request
        args = list_args(purge=True, start=None, end=None,
                         extension=None, call_id=None, severity=None)
        # When activity-log --purge runs
        mock_post = invoke_config_cmd(cx_config.cmd_activity_log, args, "post")
        # Then the purge endpoint is posted
        self.assertEqual(mock_post.call_args[0][0],
            "https://pbx.example.com/xapi/v1/ActivityLog/Pbx.PurgeLogs")

    def test_list_builds_getlogs_function_path(self):
        # Given explicit filters
        args = list_args(purge=False, start="2026-02-01T00:00:00Z",
                         end="2026-02-28T23:59:59Z", extension="100",
                         call_id="abc", severity="Error")
        # When activity-log runs
        mock_get = invoke_config_cmd(cx_config.cmd_activity_log, args)
        # Then the GetLogs function URL embeds every filter and drops $orderby
        url = mock_get.call_args[0][0]
        self.assertIn("ActivityLog/Pbx.GetLogs(startDate=2026-02-01T00:00:00Z,", url)
        self.assertIn("endDate=2026-02-28T23:59:59Z", url)
        self.assertIn("extension='100'", url)
        self.assertIn("call='abc'", url)
        self.assertIn("severity='Error'", url)
        self.assertNotIn("$orderby", mock_get.call_args.kwargs["params"])

    def test_list_defaults_to_empty_string_filters(self):
        # Given no optional filters
        args = list_args(purge=False, start=None, end=None,
                         extension=None, call_id=None, severity=None)
        # When activity-log runs
        mock_get = invoke_config_cmd(cx_config.cmd_activity_log, args)
        # Then optional filters serialize as empty strings
        url = mock_get.call_args[0][0]
        self.assertIn("extension=''", url)
        self.assertIn("call=''", url)
        self.assertIn("severity=''", url)


class TestConfigCmdBackups(unittest.TestCase):
    def test_create_posts_to_backups(self):
        # Given a backup creation request
        args = list_args(create=True, restore=None)
        # When backups --create runs
        mock_post = invoke_config_cmd(cx_config.cmd_backups, args, "post")
        # Then the Backups collection is posted
        self.assertEqual(mock_post.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Backups")

    def test_restore_posts_restore_endpoint(self):
        # Given a backup restore request
        args = list_args(create=False, restore="backup.zip")
        # When backups --restore runs
        mock_post = invoke_config_cmd(cx_config.cmd_backups, args, "post")
        # Then the quoted-name restore endpoint is posted
        self.assertEqual(mock_post.call_args[0][0],
            "https://pbx.example.com/xapi/v1/Backups('backup.zip')/Pbx.Restore")

    def test_list_orders_by_creation_time_desc(self):
        # Given default list args
        args = list_args(create=False, restore=None)
        # When backups are listed
        mock_get = invoke_config_cmd(cx_config.cmd_backups, args)
        # Then results are ordered newest first
        self.assertEqual(mock_get.call_args.kwargs["params"]["$orderby"],
                         "CreationTime desc")


class TestConfigCmdRestart(unittest.TestCase):
    def test_restart_without_confirm_exits(self):
        args = types.SimpleNamespace(confirm=False)
        with self.assertRaises(SystemExit):
            cx_config.cmd_restart(args)


class TestConfigCmdRestartConfirm(unittest.TestCase):
    def test_restart_with_confirm_posts_restart(self):
        # Given an explicit --confirm
        args = types.SimpleNamespace(confirm=True)
        # When restart runs
        mock_post = invoke_config_cmd(cx_config.cmd_restart, args, "post")
        # Then the restart endpoint is posted
        self.assertEqual(mock_post.call_args[0][0],
            "https://pbx.example.com/xapi/v1/Services/Pbx.Restart")


class TestConfigCmdEmergencyNumbers(unittest.TestCase):
    def test_add_posts_friendly_name_defaulting_to_number(self):
        # Given an emergency number with no explicit name
        args = list_args(add="911", name=None, delete=None)
        # When emergency-numbers --add runs
        mock_post = invoke_config_cmd(cx_config.cmd_emergency_numbers, args, "post")
        # Then the number doubles as the friendly name
        call = mock_post.call_args
        self.assertEqual(call[0][0],
                         "https://pbx.example.com/xapi/v1/EmergencyGeoLocations")
        self.assertEqual(call.kwargs["json"], {"FriendlyName": "911", "Id": 0})

    def test_add_uses_explicit_name(self):
        # Given an emergency number with an explicit name
        args = list_args(add="911", name="Emergency", delete=None)
        # When emergency-numbers --add runs
        mock_post = invoke_config_cmd(cx_config.cmd_emergency_numbers, args, "post")
        # Then the explicit name wins
        self.assertEqual(mock_post.call_args.kwargs["json"]["FriendlyName"], "Emergency")

    def test_delete_posts_bulk(self):
        # Given emergency number deletions
        args = list_args(add=None, name=None, delete=[1])
        # When emergency-numbers --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_emergency_numbers, args, "post")
        # Then BulkNumbersDelete receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/EmergencyGeoLocations/Pbx.BulkNumbersDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [1]})


class TestConfigCmdGetTokenCmd(unittest.TestCase):
    def test_prints_token_json(self):
        # Given a working token endpoint
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_token",
                               return_value={"access_token": "tok", "expires_in": 60}), \
             mock.patch("builtins.print") as mock_print:
            # When the token command runs
            cx_config.cmd_get_token(types.SimpleNamespace())
        # Then the raw token payload is printed as JSON
        printed = json.loads(mock_print.call_args[0][0])
        self.assertEqual(printed["access_token"], "tok")


if __name__ == "__main__":
    unittest.main()
