"""Argument parser construction for the 3cx-config CLI.

``build_parser`` reproduces the parser exactly as previously declared in
``3cx-config``: same subcommand/argument declaration order, defaults, choices,
and help text, so ``-h`` output stays byte-identical. Subcommand handlers
bind late through the ``runtime`` facade module (``runtime.cmd_*``), keeping
the thin wrappers on the facade patchable.
"""

import argparse


def build_parser(runtime):
    parser = argparse.ArgumentParser(description="3CX Configuration REST API CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # config, token
    p_config = subparsers.add_parser("config", help="Save API credentials")
    p_config.add_argument("--fqdn", required=True, help="PBX FQDN")
    p_config.add_argument("--client-id", required=True, help="Client ID")
    p_config.add_argument("--client-secret", required=True, help="Client Secret")
    p_config.set_defaults(func=runtime.cmd_config)

    p_token = subparsers.add_parser("token", help="Get access token")
    p_token.set_defaults(func=runtime.cmd_get_token)

    # version, system-status
    p_version = subparsers.add_parser("version", help="Get 3CX version")
    p_version.set_defaults(func=runtime.cmd_version)

    p_status = subparsers.add_parser("system-status", help="Get system status")
    p_status.set_defaults(func=runtime.cmd_system_status)

    # departments, create-department, delete-department
    p_depts = subparsers.add_parser("departments", help="List/check departments")
    p_depts.add_argument("--name", help="Filter by name")
    runtime.add_list_args(p_depts)
    p_depts.set_defaults(func=runtime.cmd_departments)

    p_create_dept = subparsers.add_parser("create-department", help="Create department")
    p_create_dept.add_argument("--name", required=True)
    p_create_dept.add_argument("--language", default="EN")
    p_create_dept.add_argument("--prompt-set", required=True)
    p_create_dept.add_argument("--timezone", default="51")
    p_create_dept.add_argument("--sys-from", default="300")
    p_create_dept.add_argument("--sys-to", default="319")
    p_create_dept.add_argument("--trunk-from", default="340")
    p_create_dept.add_argument("--trunk-to", default="345")
    p_create_dept.add_argument("--user-from", default="320")
    p_create_dept.add_argument("--user-to", default="339")
    p_create_dept.set_defaults(func=runtime.cmd_create_department)

    p_del_dept = subparsers.add_parser("delete-department", help="Delete department")
    p_del_dept.add_argument("--id", type=int, required=True)
    p_del_dept.set_defaults(func=runtime.cmd_delete_department)

    p_update_dept = subparsers.add_parser("update-department", help="Update department settings")
    p_update_dept.add_argument("--id", type=int, required=True, help="Department ID")
    p_update_dept.add_argument("--transcription", choices=["Both", "Nothing", "Inherit"], help="Transcription mode")
    p_update_dept.set_defaults(func=runtime.cmd_update_department)

    # users, create-user, delete-users, assign-role
    p_users = subparsers.add_parser("users", help="List users")
    p_users.add_argument("--email", help="Filter by email")
    runtime.add_list_args(p_users)
    p_users.set_defaults(func=runtime.cmd_users)

    p_create_user = subparsers.add_parser("create-user", help="Create user")
    p_create_user.add_argument("--first-name", required=True)
    p_create_user.add_argument("--last-name", required=True)
    p_create_user.add_argument("--email", required=True)
    p_create_user.add_argument("--password", required=True)
    p_create_user.add_argument("--extension", required=True)
    p_create_user.add_argument("--language", default="EN")
    p_create_user.add_argument("--prompt-set", required=True)
    p_create_user.set_defaults(func=runtime.cmd_create_user)

    p_del_users = subparsers.add_parser("delete-users", help="Delete users")
    p_del_users.add_argument("--ids", type=int, nargs="+", required=True)
    p_del_users.set_defaults(func=runtime.cmd_delete_users)

    p_role = subparsers.add_parser("assign-role", help="Assign role to user")
    p_role.add_argument("--user-id", type=int, required=True)
    p_role.add_argument("--group-id", type=int, required=True)
    p_role.add_argument("--role", required=True, choices=["system_owners", "system_admins", "group_owners", "managers", "group_admins", "receptionists", "users"])
    p_role.set_defaults(func=runtime.cmd_assign_role)

    # live-chat, create-live-chat
    p_chat = subparsers.add_parser("live-chat", help="List live chat URLs")
    p_chat.add_argument("--check", help="Check if URL exists")
    runtime.add_list_args(p_chat)
    p_chat.set_defaults(func=runtime.cmd_live_chat)

    p_create_chat = subparsers.add_parser("create-live-chat", help="Create live chat URL")
    p_create_chat.add_argument("--link", required=True)
    p_create_chat.add_argument("--group-id", type=int, required=True)
    p_create_chat.add_argument("--group-name", required=True)
    p_create_chat.add_argument("--group-number", required=True)
    p_create_chat.set_defaults(func=runtime.cmd_create_live_chat)

    # parking
    p_parking = subparsers.add_parser("parking", help="Manage shared parking")
    p_parking.add_argument("--create", action="store_true")
    p_parking.add_argument("--delete", type=int, help="Parking ID to delete")
    p_parking.add_argument("--group-ids", type=int, nargs="+")
    runtime.add_list_args(p_parking)
    p_parking.set_defaults(func=runtime.cmd_parking)

    # active-calls, call-history, recordings (Tier 1)
    p_calls = subparsers.add_parser("active-calls", help="List active calls or drop a call")
    p_calls.add_argument("--drop", type=int, help="Call ID to drop")
    runtime.add_list_args(p_calls)
    p_calls.set_defaults(func=runtime.cmd_active_calls)

    p_history = subparsers.add_parser("call-history", help="View call history")
    p_history.add_argument("--start", type=str, help="Start date (ISO 8601, e.g. 2026-01-01T00:00:00Z)")
    p_history.add_argument("--end", type=str, help="End date (ISO 8601)")
    runtime.add_list_args(p_history)
    p_history.set_defaults(func=runtime.cmd_call_history)

    p_rec = subparsers.add_parser("recordings", help="Manage call recordings")
    p_rec.add_argument("--download", type=int, help="Recording ID to download")
    p_rec.add_argument("--delete", type=int, nargs="+", help="Recording IDs to delete")
    runtime.add_list_args(p_rec)
    p_rec.set_defaults(func=runtime.cmd_recordings)

    # inbound-rules, outbound-rules, ivrs, queues, ring-groups (Tier 2)
    p_inbound = subparsers.add_parser("inbound-rules", help="Manage inbound rules")
    p_inbound.add_argument("--id", type=int, help="Rule ID to retrieve")
    p_inbound.add_argument("--delete", type=int, nargs="+", help="Rule IDs to delete")
    runtime.add_list_args(p_inbound)
    p_inbound.set_defaults(func=runtime.cmd_inbound_rules)

    p_outbound = subparsers.add_parser("outbound-rules", help="Manage outbound rules")
    p_outbound.add_argument("--id", type=int, help="Rule ID to retrieve")
    p_outbound.add_argument("--delete", type=int, nargs="+", help="Rule IDs to delete")
    runtime.add_list_args(p_outbound)
    p_outbound.set_defaults(func=runtime.cmd_outbound_rules)

    p_ivrs = subparsers.add_parser("ivrs", help="List/get IVRs")
    p_ivrs.add_argument("--id", type=int, help="IVR ID to retrieve")
    runtime.add_list_args(p_ivrs)
    p_ivrs.set_defaults(func=runtime.cmd_ivrs)

    p_queues = subparsers.add_parser("queues", help="List/get queues")
    p_queues.add_argument("--id", type=int, help="Queue ID to retrieve")
    runtime.add_list_args(p_queues)
    p_queues.set_defaults(func=runtime.cmd_queues)

    p_rgroups = subparsers.add_parser("ring-groups", help="List/get ring groups")
    p_rgroups.add_argument("--id", type=int, help="Ring group ID to retrieve")
    runtime.add_list_args(p_rgroups)
    p_rgroups.set_defaults(func=runtime.cmd_ring_groups)

    # trunks, phones, contacts (Tier 3)
    p_trunks = subparsers.add_parser("trunks", help="Manage SIP trunks")
    p_trunks.add_argument("--id", type=int, help="Trunk ID to retrieve")
    p_trunks.add_argument("--delete", type=int, nargs="+", help="Trunk IDs to delete")
    runtime.add_list_args(p_trunks)
    p_trunks.set_defaults(func=runtime.cmd_trunks)

    p_phones = subparsers.add_parser("phones", help="Manage phones")
    p_phones.add_argument("--id", type=int, help="Phone ID to retrieve")
    p_phones.add_argument("--delete", type=int, nargs="+", help="Phone IDs to delete")
    runtime.add_list_args(p_phones)
    p_phones.set_defaults(func=runtime.cmd_phones)

    p_contacts = subparsers.add_parser("contacts", help="Manage contacts")
    p_contacts.add_argument("--id", type=int, help="Contact ID to retrieve")
    p_contacts.add_argument("--delete", type=int, nargs="+", help="Contact IDs to delete")
    p_contacts.add_argument("--export", action="store_true", help="Export contacts to CSV")
    runtime.add_list_args(p_contacts)
    p_contacts.set_defaults(func=runtime.cmd_contacts)

    # blacklist, ip-blocklist, activity-log (Tier 4)
    p_blacklist = subparsers.add_parser("blacklist", help="Manage blacklisted numbers")
    p_blacklist.add_argument("--add", type=str, help="Phone number to blacklist")
    p_blacklist.add_argument("--delete", type=int, nargs="+", help="Blacklist entry IDs to delete")
    runtime.add_list_args(p_blacklist)
    p_blacklist.set_defaults(func=runtime.cmd_blacklist)

    p_ipblock = subparsers.add_parser("ip-blocklist", help="Manage IP blocklist")
    p_ipblock.add_argument("--add", type=str, help="IP address to block")
    p_ipblock.add_argument("--description", type=str, help="Description for blocked IP")
    p_ipblock.add_argument("--delete", type=int, nargs="+", help="Blocklist entry IDs to delete")
    runtime.add_list_args(p_ipblock)
    p_ipblock.set_defaults(func=runtime.cmd_ip_blocklist)

    p_actlog = subparsers.add_parser("activity-log", help="View or purge activity log")
    p_actlog.add_argument("--purge", action="store_true", help="Purge all logs")
    p_actlog.add_argument("--start", type=str, help="Start date (ISO 8601, e.g. 2026-01-01T00:00:00Z)")
    p_actlog.add_argument("--end", type=str, help="End date (ISO 8601)")
    p_actlog.add_argument("--extension", type=str, help="Filter by extension")
    p_actlog.add_argument("--call-id", type=str, help="Filter by call ID")
    p_actlog.add_argument("--severity", type=str, help="Filter by severity")
    runtime.add_list_args(p_actlog)
    p_actlog.set_defaults(func=runtime.cmd_activity_log)

    # backups, restart, emergency-numbers (Tier 5)
    p_backups = subparsers.add_parser("backups", help="Manage backups")
    p_backups.add_argument("--create", action="store_true", help="Create a new backup")
    p_backups.add_argument("--restore", type=str, help="Backup filename to restore")
    runtime.add_list_args(p_backups)
    p_backups.set_defaults(func=runtime.cmd_backups)

    p_restart = subparsers.add_parser("restart", help="Restart the PBX")
    p_restart.add_argument("--confirm", action="store_true", help="Confirm PBX restart")
    p_restart.set_defaults(func=runtime.cmd_restart)

    p_emergency = subparsers.add_parser("emergency-numbers", help="Manage emergency numbers")
    p_emergency.add_argument("--add", type=str, help="Emergency number to add")
    p_emergency.add_argument("--name", type=str, help="Name for emergency number")
    p_emergency.add_argument("--delete", type=int, nargs="+", help="Emergency number IDs to delete")
    runtime.add_list_args(p_emergency)
    p_emergency.set_defaults(func=runtime.cmd_emergency_numbers)

    # New commands: department-members, who-can-dial, outbound-rules-update
    p_dept_members = subparsers.add_parser("department-members", help="Show department membership")
    p_dept_members.add_argument("--user", type=int, help="Show departments for specific extension")
    p_dept_members.add_argument("--department", type=int, help="Show members of specific department")
    p_dept_members.set_defaults(func=runtime.cmd_department_members)

    p_who_can_dial = subparsers.add_parser("who-can-dial", help="Show which extensions can dial out")
    p_who_can_dial.add_argument("--extension", type=int, help="Show routing for specific extension")
    p_who_can_dial.set_defaults(func=runtime.cmd_who_can_dial)

    p_outbound_update = subparsers.add_parser("outbound-rules-update", help="Update an outbound rule")
    p_outbound_update.add_argument("--id", type=int, required=True, help="Rule ID to update")
    p_outbound_update.add_argument("--groups", type=str, help="Comma-separated GroupIds (e.g. 30,34)")
    p_outbound_update.add_argument("--trunk", type=int, help="Trunk ID for Route 0")
    p_outbound_update.add_argument("--caller-id", type=str, help="Caller ID for Route 0")
    p_outbound_update.add_argument("--prepend", type=str, help="Prepend digits for Route 0")
    p_outbound_update.add_argument("--strip-digits", type=int, help="Strip digits for Route 0")
    p_outbound_update.add_argument("--name", type=str, help="Rule name")
    p_outbound_update.add_argument("--prefix", type=str, help="Digit prefix pattern")
    p_outbound_update.add_argument("--priority", type=int, help="Rule priority (integer)")
    p_outbound_update.set_defaults(func=runtime.cmd_outbound_rules_update)

    p_outbound_create = subparsers.add_parser("create-outbound-rule", help="Create a new outbound rule")
    p_outbound_create.add_argument("--name", type=str, required=True, help="Rule name")
    p_outbound_create.add_argument("--prefix", type=str, help="Digit prefix pattern")
    p_outbound_create.add_argument("--priority", type=int, help="Rule priority (integer)")
    p_outbound_create.add_argument("--groups", type=str, help="Comma-separated GroupIds (e.g. 30,34)")
    p_outbound_create.add_argument("--trunk", type=int, help="Trunk ID for Route 0")
    p_outbound_create.add_argument("--caller-id", type=str, help="Caller ID for Route 0")
    p_outbound_create.add_argument("--prepend", type=str, help="Prepend digits for Route 0")
    p_outbound_create.add_argument("--strip-digits", type=int, help="Strip digits for Route 0")
    p_outbound_create.set_defaults(func=runtime.cmd_create_outbound_rule)

    return parser
