"""Routing handlers for the 3cx-config CLI: inbound/outbound rules, IVRs,
queues, ring groups, trunks.

Seams resolve through the ``runtime`` facade at call time (see
``threecx.config_people`` for the pattern).
"""


def cmd_inbound_rules(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "InboundRules/Pbx.BulkInboundRulesDelete"), headers=headers, json={"Ids": args.delete})
    elif args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"InboundRules({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "InboundRules"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_outbound_rules(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "OutboundRules/Pbx.BulkNumbersDelete"), headers=headers, json={"Ids": args.delete})
    elif args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"OutboundRules({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "OutboundRules"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_ivrs(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    # IVRs in 3CX v20+ are stored as Receptionists, not CallFlowApps
    if args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"Receptionists({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Receptionists"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_queues(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"Queues({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Queues"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_ring_groups(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"RingGroups({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "RingGroups"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_trunks(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.delete:
        resp = runtime.requests.post(runtime.api_url(config, "Trunks/Pbx.BulkNumbersDelete"), headers=headers, json={"Ids": args.delete})
    elif args.id:
        resp = runtime.requests.get(runtime.api_url(config, f"Trunks({args.id})"), headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "Trunks"), headers=headers, params=params)
    runtime.handle_response(resp)
