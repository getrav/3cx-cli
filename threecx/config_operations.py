"""Operations handlers for the 3cx-config CLI: version, system status,
active calls, recordings, call history, activity log, backups, restart.

Seams resolve through the ``runtime`` facade at call time (see
``threecx.config_people`` for the pattern).
"""

import json


def cmd_version(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    resp = runtime.requests.get(runtime.api_url(config, "SystemStatus"), headers=headers)
    data = resp.json()
    if resp.status_code < 400:
        print(json.dumps({"Version": data.get("Version"), "FQDN": data.get("FQDN")}, indent=2))
    else:
        runtime.handle_response(resp)


def cmd_system_status(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    resp = runtime.requests.get(runtime.api_url(config, "SystemStatus"), headers=headers)
    runtime.handle_response(resp)


def cmd_active_calls(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.drop:
        resp = runtime.requests.post(runtime.api_url(config, f"ActiveCalls({args.drop})/Pbx.DropCall"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "ActiveCalls"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_recordings(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.download:
        resp = runtime.requests.get(runtime.api_url(config, f"Recordings/Pbx.DownloadRecording(recId={args.download})"), headers=headers)
        if resp.status_code >= 400:
            print(f"Error {resp.status_code}: {resp.text}", file=runtime.sys.stderr)
            runtime.sys.exit(1)
        fname = f"recording_{args.download}.wav"
        with open(fname, "wb") as f:
            f.write(resp.content)
        print(f"Saved to {fname}")
    elif args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "Recordings/Pbx.BulkRecordingsDelete"), headers=headers, json={"Ids": args.delete})
        runtime.handle_response(resp)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Recordings"), headers=headers, params=params)
        runtime.handle_response(resp)


def cmd_call_history(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    params = runtime.build_list_params(args)
    params.pop("$orderby", None)
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    default_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    default_end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    start = args.start or default_start
    end = args.end or default_end
    path = (
        f"ReportCallLogData/Pbx.GetCallLogData("
        f"periodFrom={start},"
        f"periodTo={end},"
        f"sourceType=0,sourceFilter='',"
        f"destinationType=0,destinationFilter='',"
        f"callsType=0,"
        f"callTimeFilterType=0,"
        f"callTimeFilterFrom='00:00',callTimeFilterTo='23:59',"
        f"hidePcalls=true)"
    )
    resp = runtime.requests.get(runtime.api_url(config, path), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_activity_log(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.purge:
        resp = runtime.requests.post(runtime.api_url(config, "ActivityLog/Pbx.PurgeLogs"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        params.pop("$orderby", None)
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        default_start = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        default_end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        start = args.start or default_start
        end = args.end or default_end
        ext = args.extension or ""
        call = args.call_id or ""
        severity = args.severity or ""
        path = f"ActivityLog/Pbx.GetLogs(startDate={start},endDate={end},extension='{ext}',call='{call}',severity='{severity}')"
        resp = runtime.requests.get(runtime.api_url(config, path), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_backups(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.create:
        resp = runtime.requests.post(runtime.api_url(config, "Backups"), headers=headers)
    elif args.restore:
        resp = runtime.requests.post(runtime.api_url(config, f"Backups('{args.restore}')/Pbx.Restore"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        params["$orderby"] = "CreationTime desc"
        resp = runtime.requests.get(runtime.api_url(config, "Backups"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_restart(runtime, args):
    if not args.confirm:
        print("Error: --confirm flag required to restart the PBX", file=runtime.sys.stderr)
        runtime.sys.exit(1)
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    resp = runtime.requests.post(runtime.api_url(config, "Services/Pbx.Restart"), headers=headers)
    runtime.handle_response(resp)
