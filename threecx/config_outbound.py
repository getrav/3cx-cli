"""Outbound dial-plan handlers for the 3cx-config CLI: department membership,
who-can-dial, outbound rule update/create.

Seams resolve through the ``runtime`` facade at call time (see
``threecx.config_people`` for the pattern).
"""


def cmd_department_members(runtime, args):
    """Show department membership for users."""
    config = runtime.load_config()
    headers = runtime.get_headers(config)

    # Get all users and departments
    users_resp = runtime.requests.get(runtime.api_url(config, "Users"), headers=headers, params={"$top": 100, "$orderby": "Number"})
    depts_resp = runtime.requests.get(runtime.api_url(config, "Groups"), headers=headers, params={"$top": 100, "$orderby": "Id"})

    if users_resp.status_code >= 400 or depts_resp.status_code >= 400:
        print("Error fetching data", file=runtime.sys.stderr)
        runtime.sys.exit(1)

    users = users_resp.json().get("value", [])
    depts = depts_resp.json().get("value", [])

    # Build dept lookup
    dept_lookup = {d["Id"]: d.get("Name", f"#{d['Id']}") for d in depts}

    if args.user:
        # Show departments for specific user
        user = next((u for u in users if u.get("Number") == str(args.user)), None)
        if not user:
            print(f"User {args.user} not found", file=runtime.sys.stderr)
            runtime.sys.exit(1)
        name = f"{user.get('FirstName', '')} {user.get('LastName', '')}".strip()
        primary = user.get("PrimaryGroupId")
        print(f"Extension {args.user}: {name}")
        print(f"  PrimaryGroupId: {primary} ({dept_lookup.get(primary, 'Unknown')})")
        # Note: 3CX API doesn't expose full group membership array
    elif args.department:
        # Show members of specific department
        dept = next((d for d in depts if d["Id"] == args.department), None)
        if not dept:
            print(f"Department {args.department} not found", file=runtime.sys.stderr)
            runtime.sys.exit(1)
        print(f"Department {args.department}: {dept.get('Name')}")
        print(f"  HasMembers: {dept.get('HasMembers')}")
        # Find users with this PrimaryGroupId
        members = [u for u in users if u.get("PrimaryGroupId") == args.department]
        for u in members:
            name = f"{u.get('FirstName', '')} {u.get('LastName', '')}".strip()
            print(f"    {u.get('Number')}: {name}")
        if not members:
            print("    No users with this PrimaryGroupId")
    else:
        # Show all users with their departments
        print("=== Users and Departments ===")
        for u in users:
            num = u.get("Number")
            name = f"{u.get('FirstName', '')} {u.get('LastName', '')}".strip()
            primary = u.get("PrimaryGroupId")
            dept_name = dept_lookup.get(primary, f"#{primary}")
            print(f"{num}: {name} → {dept_name}")


def cmd_who_can_dial(runtime, args):
    """Show which extensions can dial out and via which trunk."""
    config = runtime.load_config()
    headers = runtime.get_headers(config)

    # Get users, departments, outbound rules, and trunks
    users_resp = runtime.requests.get(runtime.api_url(config, "Users"), headers=headers, params={"$top": 100, "$orderby": "Number"})
    depts_resp = runtime.requests.get(runtime.api_url(config, "Groups"), headers=headers, params={"$top": 100, "$orderby": "Id"})
    rules_resp = runtime.requests.get(runtime.api_url(config, "OutboundRules"), headers=headers, params={"$top": 50, "$orderby": "Id"})
    trunks_resp = runtime.requests.get(runtime.api_url(config, "Trunks"), headers=headers, params={"$top": 50, "$orderby": "Id"})

    # Better error reporting
    for name, r in [("Users", users_resp), ("Groups", depts_resp), ("OutboundRules", rules_resp), ("Trunks", trunks_resp)]:
        if r.status_code >= 400:
            print(f"Error fetching {name}: HTTP {r.status_code}", file=runtime.sys.stderr)
            if r.status_code == 403:
                print("Rate limited - wait 60 seconds and retry", file=runtime.sys.stderr)
            runtime.sys.exit(1)

    users = users_resp.json().get("value", [])
    depts = depts_resp.json().get("value", [])
    rules = rules_resp.json().get("value", [])
    trunks = trunks_resp.json().get("value", [])

    # Build lookups
    dept_lookup = {d["Id"]: d.get("Name", f"#{d['Id']}") for d in depts}
    trunk_lookup = {t["Id"]: t.get("Name", f"#{t['Id']}") for t in trunks}

    # Build rule→dept→trunk mapping (use first valid route)
    rule_map = {}
    for r in rules:
        group_ids = r.get("GroupIds", [])
        routes = r.get("Routes", [])
        valid_route = next((rt for rt in routes if rt.get("TrunkId", -1) > 0), None)
        if valid_route:
            trunk_id = valid_route.get("TrunkId")
            trunk_name = trunk_lookup.get(trunk_id, f"#{trunk_id}")
            caller_id = valid_route.get("CallerID", "")
            for gid in group_ids:
                rule_map[gid] = {
                    "rule": r.get("Name"),
                    "trunk_id": trunk_id,
                    "trunk_name": trunk_name,
                    "caller_id": caller_id
                }

    if args.extension:
        # Show routing for specific extension
        user = next((u for u in users if u.get("Number") == str(args.extension)), None)
        if not user:
            print(f"Extension {args.extension} not found", file=runtime.sys.stderr)
            runtime.sys.exit(1)
        name = f"{user.get('FirstName', '')} {user.get('LastName', '')}".strip()
        primary = user.get("PrimaryGroupId")

        print(f"Extension {args.extension}: {name}")
        print(f"  PrimaryGroupId: {primary} ({dept_lookup.get(primary, 'Unknown')})")

        routing = rule_map.get(primary)
        if routing:
            print(f"  CAN DIAL OUT via: {routing['rule']}")
            print(f"    Trunk: {routing['trunk_name']} (ID {routing['trunk_id']})")
            print(f"    CallerID: {routing['caller_id']}")
        else:
            print("  ❌ CANNOT DIAL OUT (no outbound rule for department)")
    else:
        # Show all users
        print("=== Outbound Dial Permissions ===")
        can_dial = []
        cannot_dial = []

        for u in users:
            num = u.get("Number")
            name = f"{u.get('FirstName', '')} {u.get('LastName', '')}".strip()
            primary = u.get("PrimaryGroupId")
            routing = rule_map.get(primary)

            if routing:
                can_dial.append({
                    "ext": num,
                    "name": name,
                    "dept": dept_lookup.get(primary, f"#{primary}"),
                    "trunk": routing["trunk_name"],
                    "caller_id": routing["caller_id"]
                })
            else:
                cannot_dial.append({
                    "ext": num,
                    "name": name,
                    "dept": dept_lookup.get(primary, f"#{primary}")
                })

        if can_dial:
            print("\n✅ CAN DIAL OUT:")
            for u in can_dial:
                print(f"  {u['ext']}: {u['name']} → {u['trunk']} (CallerID: {u['caller_id']})")

        if cannot_dial:
            print("\n❌ CANNOT DIAL OUT:")
            for u in cannot_dial:
                print(f"  {u['ext']}: {u['name']} (dept: {u['dept']})")


def cmd_outbound_rules_update(runtime, args):
    """Update an outbound rule via PATCH."""
    config = runtime.load_config()
    headers = runtime.get_headers(config)

    if not args.id:
        print("Error: --id required for update", file=runtime.sys.stderr)
        runtime.sys.exit(1)

    # Get current rule
    resp = runtime.requests.get(runtime.api_url(config, f"OutboundRules({args.id})"), headers=headers)
    if resp.status_code >= 400:
        print(f"Error fetching rule {args.id}: {resp.status_code}", file=runtime.sys.stderr)
        runtime.sys.exit(1)

    rule = resp.json()

    # Build update payload
    update_data = {}

    if args.groups:
        # Parse comma-separated group IDs
        group_ids = [int(g.strip()) for g in args.groups.split(",")]
        update_data["GroupIds"] = group_ids

    if args.trunk:
        # Update first route's TrunkId
        routes = rule.get("Routes", [])
        if routes:
            routes[0]["TrunkId"] = args.trunk
            update_data["Routes"] = routes

    if args.caller_id:
        # Update first route's CallerID
        routes = rule.get("Routes", [])
        if routes:
            routes[0]["CallerID"] = args.caller_id
            update_data["Routes"] = routes

    if args.prepend:
        # Update first route's Prepend
        routes = rule.get("Routes", [])
        if routes:
            routes[0]["Prepend"] = args.prepend
            update_data["Routes"] = routes

    if args.strip_digits:
        # Update first route's StripDigits
        routes = rule.get("Routes", [])
        if routes:
            routes[0]["StripDigits"] = args.strip_digits
            update_data["Routes"] = routes

    if args.name:
        update_data["Name"] = args.name

    if args.prefix:
        update_data["Prefix"] = args.prefix

    if args.priority is not None:
        update_data["Priority"] = args.priority

    if not update_data:
        print("Error: No update flags provided", file=runtime.sys.stderr)
        runtime.sys.exit(1)

    # Send PATCH
    patch_resp = runtime.requests.patch(
        runtime.api_url(config, f"OutboundRules({args.id})"),
        headers=headers,
        json=update_data
    )

    if patch_resp.status_code == 204:
        print(f"Rule {args.id} updated successfully")
        # Show updated rule
        verify_resp = runtime.requests.get(runtime.api_url(config, f"OutboundRules({args.id})"), headers=headers)
        if verify_resp.status_code < 400:
            updated = verify_resp.json()
            print(f"  Name: {updated.get('Name')}")
            print(f"  GroupIds: {updated.get('GroupIds')}")
            routes = updated.get("Routes", [])
            if routes:
                r0 = routes[0]
                print(f"  Route 0: TrunkId={r0.get('TrunkId')}, CallerID={r0.get('CallerID')}, Prepend={r0.get('Prepend')}, Strip={r0.get('StripDigits')}")
    else:
        print(f"Error {patch_resp.status_code}: {patch_resp.text}", file=runtime.sys.stderr)
        runtime.sys.exit(1)


def cmd_create_outbound_rule(runtime, args):
    """Create a new outbound rule via POST."""
    config = runtime.load_config()
    headers = runtime.get_headers(config)

    if not args.name:
        print("Error: --name required for create", file=runtime.sys.stderr)
        runtime.sys.exit(1)

    # Build routes: first route populated, rest empty
    routes = [{
        "Append": "",
        "CallerID": args.caller_id or "",
        "Prepend": args.prepend or "",
        "StripDigits": args.strip_digits or 0,
        "TrunkId": args.trunk or -1,
    }]
    for _ in range(4):
        routes.append({
            "Append": "",
            "CallerID": "",
            "Prepend": "",
            "StripDigits": 0,
            "TrunkId": -1,
        })

    # Parse groups
    group_ids = []
    if args.groups:
        group_ids = [int(g.strip()) for g in args.groups.split(",")]

    rule_data = {
        "Name": args.name,
        "Prefix": args.prefix or "",
        "Priority": args.priority if args.priority is not None else 0,
        "NumberLengthRanges": "",
        "GroupIds": group_ids,
        "Routes": routes,
        "DNRanges": [],
    }

    resp = runtime.requests.post(runtime.api_url(config, "OutboundRules"), headers=headers, json=rule_data)

    if resp.status_code == 201:
        print(f"Rule '{args.name}' created successfully")
        # Try to show the created rule
        location = resp.headers.get("Location", "")
        if location:
            # Extract ID from Location header if available
            verify_resp = runtime.requests.get(location, headers=headers)
            if verify_resp.status_code < 400:
                created = verify_resp.json()
                print(f"  ID: {created.get('Id')}")
                print(f"  Name: {created.get('Name')}")
                print(f"  Prefix: {created.get('Prefix')}")
                print(f"  Priority: {created.get('Priority')}")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=runtime.sys.stderr)
        runtime.sys.exit(1)
