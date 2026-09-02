"""Infrastructure handlers for the 3cx-config CLI: parking, phones, contacts,
blacklist, IP blocklist, emergency numbers.

Seams resolve through the ``runtime`` facade at call time (see
``threecx.config_people`` for the pattern).
"""


def cmd_parking(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.create:
        data = {"Groups": [{"GroupId": gid} for gid in args.group_ids], "Id": 0}
        resp = runtime.requests.post(runtime.api_url(config, "Parkings"), headers=headers, json=data)
    elif args.delete:
        resp = runtime.requests.delete(runtime.api_url(config, f"Parkings({args.delete})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Parkings"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_phones(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "SipDevices/Pbx.BulkNumbersDelete"), headers=headers, json={"Ids": args.delete})
    elif args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"SipDevices({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "SipDevices"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_contacts(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.export:
        resp = runtime.requests.get(runtime.api_url(config, "Contacts/Pbx.Export"), headers=headers)
        if resp.status_code >= 400:
            print(f"Error {resp.status_code}: {resp.text}", file=runtime.sys.stderr)
            runtime.sys.exit(1)
        fname = "contacts_export.csv"
        with open(fname, "wb") as f:
            f.write(resp.content)
        print(f"Exported to {fname}")
    elif args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "Contacts/Pbx.BulkNumbersDelete"), headers=headers, json={"Ids": args.delete})
        runtime.handle_response(resp)
    elif args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"Contacts({args.id})"), headers=headers)
        runtime.handle_response(resp)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Contacts"), headers=headers, params=params)
        runtime.handle_response(resp)


def cmd_blacklist(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.add:
        resp = runtime.requests.post(runtime.api_url(config, "BlackListNumbers"), headers=headers, json={"Number": args.add, "Id": 0})
        runtime.handle_response(resp)
    elif args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "BlackListNumbers/Pbx.BulkNumbersDelete"), headers=headers, json={"Ids": args.delete})
        runtime.handle_response(resp)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "BlackListNumbers"), headers=headers, params=params)
        runtime.handle_response(resp)


def cmd_ip_blocklist(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.add:
        resp = runtime.requests.post(runtime.api_url(config, "Blocklist"), headers=headers, json={"IpAddress": args.add, "Id": 0, "Description": args.description or ""})
        runtime.handle_response(resp)
    elif args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "Blocklist/Pbx.BulkIpsDelete"), headers=headers, json={"Ids": args.delete})
        runtime.handle_response(resp)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Blocklist"), headers=headers, params=params)
        runtime.handle_response(resp)


def cmd_emergency_numbers(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.add:
        resp = runtime.requests.post(runtime.api_url(config, "EmergencyGeoLocations"), headers=headers, json={"FriendlyName": args.name or args.add, "Id": 0})
        runtime.handle_response(resp)
    elif args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "EmergencyGeoLocations/Pbx.BulkNumbersDelete"), headers=headers, json={"Ids": args.delete})
        runtime.handle_response(resp)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "EmergencyGeoLocations"), headers=headers, params=params)
        runtime.handle_response(resp)
