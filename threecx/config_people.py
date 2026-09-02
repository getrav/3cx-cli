"""People handlers for the 3cx-config CLI: departments, users, roles, live chat.

Each ``cmd_*`` takes the ``runtime`` facade module (the dynamically loaded
``3cx-config`` script, i.e. ``cx_config`` in tests) and resolves every seam —
``load_config``, ``get_headers``, ``build_list_params``, ``api_url``,
``handle_response``, ``requests``, ``sys`` — through it at call time, so
module-level monkeypatches on the facade keep working exactly as before the
split.
"""


def cmd_departments(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    params = runtime.build_list_params(args)
    if args.name:
        params["$filter"] = f"Name eq '{args.name}'"
    resp = runtime.requests.get(runtime.api_url(config, "Groups"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_create_department(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    data = {
        "AllowCallService": True,
        "Id": 0,
        "Language": args.language,
        "Name": args.name,
        "PromptSet": args.prompt_set,
        "Props": {
            "LiveChatMaxCount": 20,
            "PersonalContactsMaxCount": 500,
            "PromptsMaxCount": 10,
            "SystemNumberFrom": args.sys_from,
            "SystemNumberTo": args.sys_to,
            "TrunkNumberFrom": args.trunk_from,
            "TrunkNumberTo": args.trunk_to,
            "UserNumberFrom": args.user_from,
            "UserNumberTo": args.user_to
        },
        "TimeZoneId": args.timezone,
        "DisableCustomPrompt": True
    }
    resp = runtime.requests.post(runtime.api_url(config, "Groups"), headers=headers, json=data)
    runtime.handle_response(resp)


def cmd_delete_department(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    resp = runtime.requests.post(runtime.api_url(config, "Groups/Pbx.DeleteCompanyById"), headers=headers, json={"Id": args.id})
    runtime.handle_response(resp)


def cmd_update_department(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    data = {}
    if args.transcription is not None:
        data["TranscriptionMode"] = args.transcription
    if not data:
        print("Error: No update flags provided. Use --transcription.", file=runtime.sys.stderr)
        runtime.sys.exit(1)
    resp = runtime.requests.patch(runtime.api_url(config, f"Groups({args.id})"), headers=headers, json=data)
    runtime.handle_response(resp)


def cmd_users(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    params = runtime.build_list_params(args)
    params["$orderby"] = "Number"
    if args.email:
        params["$filter"] = f"tolower(EmailAddress) eq '{args.email.lower()}'"
        params["$top"] = 1
    url = runtime.api_url(config, "Users")
    resp = runtime.requests.get(url, headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_create_user(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    data = {
        "AccessPassword": args.password,
        "EmailAddress": args.email,
        "FirstName": args.first_name,
        "LastName": args.last_name,
        "Id": 0,
        "Language": args.language,
        "Number": args.extension,
        "PromptSet": args.prompt_set,
        "SendEmailMissedCalls": True,
        "VMEmailOptions": "Notification",
        "Require2FA": False
    }
    resp = runtime.requests.post(runtime.api_url(config, "Users"), headers=headers, json=data)
    runtime.handle_response(resp)


def cmd_delete_users(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    resp = runtime.requests.post(runtime.api_url(config, "Users/Pbx.BatchDelete"), headers=headers, json={"ids": args.ids})
    runtime.handle_response(resp)


def cmd_assign_role(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    data = {"Groups": [{"GroupId": args.group_id, "Rights": {"RoleName": args.role}}], "Id": args.user_id}
    resp = runtime.requests.patch(runtime.api_url(config, f"Users({args.user_id})"), headers=headers, json=data)
    runtime.handle_response(resp)


def cmd_live_chat(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    if args.check:
        url = runtime.api_url(config, f"WebsiteLinks?$filter=Link eq '{args.check}'")
        resp = runtime.requests.get(url, headers=headers)
    else:
        params = runtime.build_list_params(args)
        resp = runtime.requests.get(runtime.api_url(config, "WebsiteLinks"), headers=headers, params=params)
    runtime.handle_response(resp)


def cmd_create_live_chat(runtime, args):
    config = runtime.load_config()
    headers = runtime.get_headers(config)
    data = {
        "Advanced": {"CommunicationOptions": "PhoneAndChat", "EnableDirectCall": True, "IgnoreQueueOwnership": False, "CallTitle": ""},
        "CallsEnabled": True,
        "ChatEnabled": True,
        "DefaultRecord": True,
        "DN": {"Id": args.group_id, "Name": args.group_name, "Number": args.group_number, "Type": "Group"},
        "General": {"AllowSoundNotifications": True, "Authentication": "None", "DisableOfflineMessages": False, "Greeting": "DesktopAndMobile"},
        "Group": args.group_number,
        "Link": args.link,
        "Name": "",
        "Styling": {"Animation": "NoAnimation", "Minimized": True},
        "Translations": {"GreetingMessage": "", "StartChatButtonText": "", "UnavailableMessage": ""},
        "Website": []
    }
    resp = runtime.requests.post(runtime.api_url(config, "WebsiteLinks"), headers=headers, json=data)
    runtime.handle_response(resp)
