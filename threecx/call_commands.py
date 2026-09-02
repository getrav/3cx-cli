"""HTTP command implementations for the 3cx-call CLI.

Each ``cmd_*`` takes the ``runtime`` facade module (the dynamically loaded
``3cx-call`` script, i.e. ``cx_call`` in tests) and resolves every seam —
``load_config``, ``get_headers``, ``api_url``, ``verbose_request``,
``handle_response`` — through it at call time, so module-level monkeypatches
on the facade keep working exactly as before the split.
"""

import json


def cmd_status(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    dn = args.dn or config.get("dn", "")
    url = runtime.api_url(config, dn) if dn else runtime.api_url(config)
    resp = runtime.verbose_request("get", url, verbose=args.verbose, headers=headers)
    runtime.handle_response(resp)


def cmd_devices(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    dn = args.dn or config.get("dn", "")
    if args.device_id:
        url = runtime.api_url(config, f"{dn}/devices/{args.device_id}")
    else:
        url = runtime.api_url(config, f"{dn}/devices")
    resp = runtime.verbose_request("get", url, verbose=args.verbose, headers=headers)
    runtime.handle_response(resp)


def cmd_make_call(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    dn = args.dn or config.get("dn", "")
    data = {"destination": args.destination, "timeout": args.timeout}
    if args.attached_data:
        data["attacheddata"] = json.loads(args.attached_data)
    if args.device_id:
        url = runtime.api_url(config, f"{dn}/devices/{args.device_id}/makecall")
    else:
        url = runtime.api_url(config, f"{dn}/makecall")
    resp = runtime.verbose_request("post", url, verbose=args.verbose, headers=headers, json=data)
    runtime.handle_response(resp)


def cmd_participant(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    dn = args.dn or config.get("dn", "")
    if args.participant_id:
        url = runtime.api_url(config, f"{dn}/participants/{args.participant_id}")
    else:
        url = runtime.api_url(config, f"{dn}/participants")
    resp = runtime.verbose_request("get", url, verbose=args.verbose, headers=headers)
    runtime.handle_response(resp)


def cmd_action(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    dn = args.dn or config.get("dn", "")
    url = runtime.api_url(config, f"{dn}/participants/{args.participant_id}/{args.action}")
    data = {}
    if args.destination:
        data["destination"] = args.destination
    if args.reason:
        data["reason"] = args.reason
    if args.timeout:
        data["timeout"] = args.timeout
    if args.attached_data:
        data["attacheddata"] = json.loads(args.attached_data)
    resp = runtime.verbose_request("post", url, verbose=args.verbose, headers=headers, json=data if data else None)
    runtime.handle_response(resp)


def cmd_stream(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    dn = args.dn or config.get("dn", "")
    url = runtime.api_url(config, f"{dn}/participants/{args.participant_id}/stream")
    stream_headers = {k: v for k, v in headers.items() if k != "Content-Type"}

    if args.upload:
        with open(args.upload, "rb") as f:
            audio_data = f.read()
        resp = runtime.verbose_request("post", url, verbose=args.verbose, headers=stream_headers, data=audio_data)
        if resp.status_code >= 400:
            runtime.handle_response(resp)
        print(f"Stream uploaded: {resp.status_code}")
    else:
        resp = runtime.verbose_request("get", url, verbose=args.verbose, headers=stream_headers)
        if resp.status_code >= 400:
            runtime.handle_response(resp)
        if args.output:
            with open(args.output, "wb") as f:
                f.write(resp.content)
            print(f"Stream saved to {args.output}")
        else:
            print(f"Stream received: {len(resp.content)} bytes")
