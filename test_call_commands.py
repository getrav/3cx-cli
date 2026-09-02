#!/usr/bin/env python3
"""cx_call command HTTP contracts: status, devices, make-call, participant,
action, stream, and the listen WebSocket contract."""

import json
import types
import unittest
from io import StringIO
from unittest import mock

from cx_test_support import (
    CALL_CREDS,
    CALL_HEADERS,
    cx_call,
    invoke_call_cmd,
    make_response,
)


class TestCallCmdStatus(unittest.TestCase):
    def _args(self, dn=None):
        return types.SimpleNamespace(dn=dn, verbose=False)

    def test_uses_config_dn_in_url(self):
        # Given a default DN in the saved config
        # When status runs without --dn
        mock_get = invoke_call_cmd(cx_call.cmd_status, self._args())
        # Then the config DN appears in the URL with auth headers
        call = mock_get.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/callcontrol/100")
        self.assertEqual(call.kwargs["headers"], CALL_HEADERS)

    def test_arg_dn_overrides_config(self):
        # Given an explicit --dn
        # When status runs
        mock_get = invoke_call_cmd(cx_call.cmd_status, self._args(dn="200"))
        # Then the argument DN wins
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/callcontrol/200")

    def test_no_dn_uses_base_url(self):
        # Given a config with no DN at all
        with mock.patch.object(cx_call, "load_config",
                               return_value={"fqdn": "pbx.example.com", "api_key": "k"}), \
             mock.patch.object(cx_call, "get_headers",
                               return_value=dict(CALL_HEADERS)), \
             mock.patch.object(cx_call, "handle_response"), \
             mock.patch("requests.get", return_value=make_response(200)) as mock_get:
            # When status runs
            cx_call.cmd_status(self._args())
        # Then the bare callcontrol URL is used
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/callcontrol")


class TestCallCmdDevices(unittest.TestCase):
    def test_list_devices_url(self):
        # Given no device id
        args = types.SimpleNamespace(dn=None, device_id=None, verbose=False)
        # When devices runs
        mock_get = invoke_call_cmd(cx_call.cmd_devices, args)
        # Then the DN's device collection is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/callcontrol/100/devices")

    def test_single_device_url(self):
        # Given a device id
        args = types.SimpleNamespace(dn=None, device_id="dev-1", verbose=False)
        # When devices --device-id runs
        mock_get = invoke_call_cmd(cx_call.cmd_devices, args)
        # Then the single device entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/callcontrol/100/devices/dev-1")


class TestCallCmdMakeCall(unittest.TestCase):
    def _args(self, **overrides):
        base = dict(dn=None, verbose=False, destination="200", timeout=30,
                    device_id=None, attached_data=None)
        base.update(overrides)
        return types.SimpleNamespace(**base)

    def test_posts_destination_and_timeout(self):
        # Given a plain outbound call
        # When call runs
        mock_post = invoke_call_cmd(cx_call.cmd_make_call, self._args(), "post")
        # Then the makecall endpoint receives destination and timeout
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/callcontrol/100/makecall")
        self.assertEqual(call.kwargs["json"], {"destination": "200", "timeout": 30})

    def test_attached_data_is_json_parsed(self):
        # Given JSON attached data
        # When call runs with --attached-data
        mock_post = invoke_call_cmd(
            cx_call.cmd_make_call, self._args(attached_data='{"crm": "1"}'), "post")
        # Then the parsed object lands under attacheddata
        self.assertEqual(mock_post.call_args.kwargs["json"]["attacheddata"],
                         {"crm": "1"})

    def test_device_id_changes_url(self):
        # Given a specific originating device
        # When call runs with --device-id
        mock_post = invoke_call_cmd(
            cx_call.cmd_make_call, self._args(device_id="dev-9"), "post")
        # Then the device-scoped makecall URL is used
        self.assertEqual(mock_post.call_args[0][0],
            "https://pbx.example.com/callcontrol/100/devices/dev-9/makecall")


class TestCallCmdParticipant(unittest.TestCase):
    def test_list_participants_url(self):
        # Given no participant id
        args = types.SimpleNamespace(dn=None, participant_id=None, verbose=False)
        # When participant runs
        mock_get = invoke_call_cmd(cx_call.cmd_participant, args)
        # Then the participant collection is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/callcontrol/100/participants")

    def test_single_participant_url(self):
        # Given a participant id
        args = types.SimpleNamespace(dn=None, participant_id=7, verbose=False)
        # When participant --participant-id runs
        mock_get = invoke_call_cmd(cx_call.cmd_participant, args)
        # Then the single participant entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/callcontrol/100/participants/7")


class TestCallCmdAction(unittest.TestCase):
    def _args(self, **overrides):
        base = dict(dn=None, verbose=False, participant_id=1, action="drop",
                    destination=None, reason=None, timeout=None, attached_data=None)
        base.update(overrides)
        return types.SimpleNamespace(**base)

    def test_posts_to_action_url_with_none_payload_when_empty(self):
        # Given a drop action with no optional fields
        # When action runs
        mock_post = invoke_call_cmd(cx_call.cmd_action, self._args(), "post")
        # Then the action URL is posted with json=None
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/callcontrol/100/participants/1/drop")
        self.assertIsNone(call.kwargs["json"])

    def test_divert_payload_includes_destination_reason_timeout(self):
        # Given a divert with all optional fields
        # When action runs
        mock_post = invoke_call_cmd(cx_call.cmd_action, self._args(
            action="divert", destination="200", reason="NoAnswer", timeout=15), "post")
        # Then all fields are posted
        self.assertEqual(mock_post.call_args.kwargs["json"], {
            "destination": "200", "reason": "NoAnswer", "timeout": 15})

    def test_attached_data_parsed(self):
        # Given JSON attached data
        # When action runs
        mock_post = invoke_call_cmd(cx_call.cmd_action, self._args(
            action="attach_party_data", attached_data='{"k": 1}'), "post")
        # Then the parsed object lands under attacheddata
        self.assertEqual(mock_post.call_args.kwargs["json"],
                         {"attacheddata": {"k": 1}})


class TestCallCmdStream(unittest.TestCase):
    def _args(self, **overrides):
        base = dict(dn=None, verbose=False, participant_id=1, upload=None, output=None)
        base.update(overrides)
        return types.SimpleNamespace(**base)

    def test_upload_posts_raw_audio_without_content_type(self):
        # Given an audio file to upload
        m_open = mock.mock_open(read_data=b"AUDIO")
        with mock.patch.object(cx_call, "load_config",
                               return_value=dict(CALL_CREDS)), \
             mock.patch.object(cx_call, "get_headers",
                               return_value=dict(CALL_HEADERS)), \
             mock.patch("builtins.open", m_open), \
             mock.patch("requests.post", return_value=make_response(200)) as mock_post, \
             mock.patch("builtins.print"):
            # When stream --upload runs
            cx_call.cmd_stream(self._args(upload="in.raw"))
        # Then raw bytes are posted with Content-Type stripped from the headers
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/callcontrol/100/participants/1/stream")
        self.assertEqual(call.kwargs["headers"], {"Authorization": "Bearer t"})
        self.assertEqual(call.kwargs["data"], b"AUDIO")

    def test_download_writes_output_file(self):
        # Given a downloadable stream
        resp = make_response(200)
        resp.content = b"PCM"
        m_open = mock.mock_open()
        with mock.patch.object(cx_call, "load_config",
                               return_value=dict(CALL_CREDS)), \
             mock.patch.object(cx_call, "get_headers",
                               return_value=dict(CALL_HEADERS)), \
             mock.patch("builtins.open", m_open), \
             mock.patch("requests.get", return_value=resp) as mock_get, \
             mock.patch("builtins.print"):
            # When stream --output runs
            cx_call.cmd_stream(self._args(output="out.raw"))
        # Then the stream endpoint is fetched and bytes land in the output file
        self.assertEqual(mock_get.call_args[0][0],
            "https://pbx.example.com/callcontrol/100/participants/1/stream")
        m_open.assert_called_once_with("out.raw", "wb")
        m_open().write.assert_called_once_with(b"PCM")

    def test_download_without_output_prints_byte_count(self):
        # Given a downloadable stream and no --output
        resp = make_response(200)
        resp.content = b"12345"
        with mock.patch.object(cx_call, "load_config",
                               return_value=dict(CALL_CREDS)), \
             mock.patch.object(cx_call, "get_headers",
                               return_value=dict(CALL_HEADERS)), \
             mock.patch("requests.get", return_value=resp), \
             mock.patch("builtins.print") as mock_print:
            # When stream runs
            cx_call.cmd_stream(self._args())
        # Then the byte count is reported
        mock_print.assert_called_once_with("Stream received: 5 bytes")


class TestCallListenWebSocketContract(unittest.TestCase):
    """WebSocket URL, auth header, subscribe message, and event rendering."""

    def _run_listen(self, args):
        """Run cmd_listen with a dead connection (thread never alive).
        Returns the WebSocketApp mock. With retries=0 the loop exits once."""
        with mock.patch.object(cx_call, "load_config",
                               return_value=dict(CALL_CREDS)), \
             mock.patch.object(cx_call, "get_token", return_value="tok123"), \
             mock.patch.object(cx_call.websocket, "WebSocketApp") as mock_wsapp, \
             mock.patch.object(cx_call.threading, "Thread") as mock_thread, \
             mock.patch("builtins.print"), \
             mock.patch("sys.stderr", StringIO()):
            mock_thread.return_value.is_alive.return_value = False
            try:
                cx_call.cmd_listen(args)
            except SystemExit:
                pass
        return mock_wsapp

    def test_connects_to_wss_url_with_bearer_header(self):
        # Given default listen args with no retries
        args = types.SimpleNamespace(dn=None, retries=0, verbose=False)
        # When listen connects
        mock_wsapp = self._run_listen(args)
        # Then the WebSocket URL and bearer header match the config
        call = mock_wsapp.call_args
        self.assertEqual(call[0][0], "wss://pbx.example.com/callcontrol/ws")
        self.assertEqual(call.kwargs["header"], ["Authorization: Bearer tok123"])

    def test_gives_up_after_max_retries_with_exit_1(self):
        # Given a connection that never comes up and no retry budget
        args = types.SimpleNamespace(dn=None, retries=0, verbose=False)
        err = StringIO()
        # When listen runs, it exits 1 with a give-up message
        with mock.patch.object(cx_call, "load_config",
                               return_value=dict(CALL_CREDS)), \
             mock.patch.object(cx_call, "get_token", return_value="tok123"), \
             mock.patch.object(cx_call.websocket, "WebSocketApp"), \
             mock.patch.object(cx_call.threading, "Thread") as mock_thread, \
             mock.patch("sys.stderr", err):
            mock_thread.return_value.is_alive.return_value = False
            with self.assertRaises(SystemExit) as cm:
                cx_call.cmd_listen(args)
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Max retries", err.getvalue())

    def test_on_open_sends_subscribe_request(self):
        # Given a captured on_open handler
        args = types.SimpleNamespace(dn=None, retries=0, verbose=False)
        mock_wsapp = self._run_listen(args)
        on_open = mock_wsapp.call_args.kwargs["on_open"]
        fake_ws = mock.MagicMock()
        # When the socket opens
        with mock.patch("builtins.print"):
            on_open(fake_ws)
        # Then a subscribe request for the config DN is sent
        payload = json.loads(fake_ws.send.call_args[0][0])
        self.assertEqual(payload["Path"], "/callcontrol/100")
        self.assertEqual(payload["RequestData"], {"subscribe": True})
        self.assertIn("RequestId", payload)

    def test_on_message_prints_event_labels(self):
        # Given a captured on_message handler
        args = types.SimpleNamespace(dn=None, retries=0, verbose=False)
        mock_wsapp = self._run_listen(args)
        on_message = mock_wsapp.call_args.kwargs["on_message"]
        # When events of each known type arrive
        with mock.patch("builtins.print") as mock_print:
            on_message(None, json.dumps({"EventType": 0, "Entity": "call-1"}))
            on_message(None, json.dumps({"EventType": 1, "Entity": "call-2"}))
            on_message(None, json.dumps({"EventType": 2,
                                         "AttachedData": {"Response": {"dtmf": "5"}}}))
            on_message(None, json.dumps({"EventType": 9, "Foo": 1}))
        # Then each is rendered with its label
        printed = [c[0][0] for c in mock_print.call_args_list]
        self.assertIn("[UPSERT] call-1", printed)
        self.assertIn("[REMOVE] call-2", printed)
        self.assertIn("[DTMF] 5", printed)
        self.assertTrue(any(p.startswith("[EVENT]") for p in printed))

    def test_on_message_response_event_prints_json(self):
        # Given a captured on_message handler
        args = types.SimpleNamespace(dn=None, retries=0, verbose=False)
        mock_wsapp = self._run_listen(args)
        on_message = mock_wsapp.call_args.kwargs["on_message"]
        # When a response event arrives
        with mock.patch("builtins.print") as mock_print:
            on_message(None, json.dumps({"EventType": 4, "AttachedData": {"x": 1}}))
        # Then it is rendered as a [RESPONSE] JSON block
        printed = [c[0][0] for c in mock_print.call_args_list]
        self.assertTrue(any(p.startswith("[RESPONSE]") and '"x"' in p
                            for p in printed))


if __name__ == "__main__":
    unittest.main()
