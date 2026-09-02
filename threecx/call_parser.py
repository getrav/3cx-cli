"""Argument parser construction for the 3cx-call CLI.

``build_parser`` reproduces the parser exactly as previously declared in
``3cx-call``: same subcommand/argument declaration order, defaults, choices,
and help text, so ``-h`` output stays byte-identical. Subcommand handlers
bind late through the ``runtime`` facade module (``runtime.cmd_*``), keeping
the thin wrappers on the facade patchable.
"""

import argparse


def build_parser(runtime):
    parser = argparse.ArgumentParser(description="3CX Call Control API CLI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print request URL/method for debugging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_config = subparsers.add_parser("config", help="Save API credentials")
    p_config.add_argument("--fqdn", required=True, help="PBX FQDN")
    p_config.add_argument("--api-key", required=True, help="API Key")
    p_config.add_argument("--dn", required=True, help="Default DN (extension)")
    p_config.set_defaults(func=runtime.cmd_config)

    p_status = subparsers.add_parser("status", help="Get call control status")
    p_status.add_argument("--dn", help="DN (uses default if not specified)")
    p_status.set_defaults(func=runtime.cmd_status)

    p_devices = subparsers.add_parser("devices", help="List/get devices")
    p_devices.add_argument("--dn", help="DN (uses default if not specified)")
    p_devices.add_argument("--device-id", help="Get specific device")
    p_devices.set_defaults(func=runtime.cmd_devices)

    p_makecall = subparsers.add_parser("call", help="Make a call")
    p_makecall.add_argument("--destination", required=True, help="Destination number")
    p_makecall.add_argument("--timeout", type=int, default=30, help="Call timeout in seconds")
    p_makecall.add_argument("--device-id", help="Call from specific device")
    p_makecall.add_argument("--attached-data", help="JSON attached data")
    p_makecall.add_argument("--dn", help="DN (uses default if not specified)")
    p_makecall.set_defaults(func=runtime.cmd_make_call)

    p_participant = subparsers.add_parser("participant", help="Get participant(s)")
    p_participant.add_argument("--dn", help="DN (uses default if not specified)")
    p_participant.add_argument("--participant-id", type=int, help="Specific participant ID")
    p_participant.set_defaults(func=runtime.cmd_participant)

    p_action = subparsers.add_parser("action", help="Perform action on participant")
    p_action.add_argument("--participant-id", type=int, required=True)
    p_action.add_argument("--action", required=True, choices=["drop", "answer", "divert", "routeto", "transferto", "attach_participant_data", "attach_party_data"])
    p_action.add_argument("--destination", help="Destination for divert/routeto/transferto")
    p_action.add_argument("--reason", help="Reason for action")
    p_action.add_argument("--timeout", type=int, help="Timeout for action")
    p_action.add_argument("--attached-data", help="JSON attached data")
    p_action.add_argument("--dn", help="DN (uses default if not specified)")
    p_action.set_defaults(func=runtime.cmd_action)

    p_listen = subparsers.add_parser("listen", help="Listen for real-time events via WebSocket")
    p_listen.add_argument("--dn", help="DN (uses default if not specified)")
    p_listen.add_argument("--retries", type=int, default=5, help="Max reconnection attempts (default: 5)")
    p_listen.set_defaults(func=runtime.cmd_listen)

    p_stream = subparsers.add_parser("stream", help="Get/upload audio stream")
    p_stream.add_argument("--participant-id", type=int, required=True)
    p_stream.add_argument("--upload", help="Upload audio file (PCM 16-bit 8000Hz mono)")
    p_stream.add_argument("--output", help="Save stream to file")
    p_stream.add_argument("--dn", help="DN (uses default if not specified)")
    p_stream.set_defaults(func=runtime.cmd_stream)

    return parser
