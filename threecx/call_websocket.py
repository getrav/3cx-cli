"""WebSocket listen command for the 3cx-call CLI.

Implements the reconnect-with-backoff event listener. Config/auth seams
(``load_config``, ``ws_url``, ``get_token``) resolve through the ``runtime``
facade module at call time, while the ``websocket``/``threading``/``time``
module references are shared globals, so patching ``cx_call.websocket``,
``cx_call.threading``, or the global ``time`` module affects this code
exactly as before the split.
"""

import json
import sys
import threading
import time

import websocket


def cmd_listen(runtime, args):
    config = runtime.load_config()
    dn = args.dn or config.get("dn", "")
    ws_url_str = runtime.ws_url(config)
    max_retries = args.retries
    attempt = 0

    while attempt <= max_retries:
        connected = threading.Event()
        should_reconnect = threading.Event()
        should_reconnect.set()  # default to reconnect on unexpected close

        def on_message(ws, message):
            data = json.loads(message)
            event_type = data.get("EventType")
            if event_type == 0:
                print(f"[UPSERT] {data.get('Entity')}")
                if data.get("AttachedData"):
                    print(json.dumps(data.get("AttachedData"), indent=2))
            elif event_type == 1:
                print(f"[REMOVE] {data.get('Entity')}")
            elif event_type == 2:
                attached = data.get("AttachedData", {})
                print(f"[DTMF] {attached.get('Response', {}).get('dtmf', '')}")
            elif event_type == 4:
                print(f"[RESPONSE] {json.dumps(data.get('AttachedData', {}), indent=2)}")
            else:
                print(f"[EVENT] {json.dumps(data, indent=2)}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}", file=sys.stderr)

        def on_open(ws):
            nonlocal attempt
            attempt = 0  # reset on successful connection
            connected.set()
            if args.verbose:
                print(f"[WS] Connected to {ws_url_str}", file=sys.stderr)
            sub_msg = {"RequestId": int(time.time()), "Path": f"/callcontrol/{dn}", "RequestData": {"subscribe": True}}
            ws.send(json.dumps(sub_msg))
            print(f"Subscribed to /callcontrol/{dn}. Press Ctrl+C to stop.")

        def on_close(ws, close_status_code, close_msg):
            print("Connection closed", file=sys.stderr)

        ws = websocket.WebSocketApp(
            ws_url_str,
            header=[f"Authorization: Bearer {runtime.get_token(config)}"],
            on_message=on_message,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close
        )

        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        try:
            while ws_thread.is_alive():
                ws_thread.join(timeout=1)
        except KeyboardInterrupt:
            print("\nStopping...", file=sys.stderr)
            should_reconnect.clear()
            ws.close()
            return

        if not should_reconnect.is_set():
            return

        attempt += 1
        if attempt <= max_retries:
            delay = min(2 ** attempt, 60)
            print(f"Reconnecting in {delay}s (attempt {attempt}/{max_retries})...", file=sys.stderr)
            try:
                time.sleep(delay)
            except KeyboardInterrupt:
                print("\nStopping...", file=sys.stderr)
                return

    print(f"Max retries ({max_retries}) exceeded. Giving up.", file=sys.stderr)
    sys.exit(1)
