---
name: 3cx-pbx-cli
description: >
  Operate 3CX PBX systems via the `3cx-config` and `3cx-call` CLI tools.
  Covers configuration inspection, people and department management, routing
  and call flow, recordings, call control, real-time event streaming, and
  safe troubleshooting. Not for raw curl or direct API calls, database edits,
  port scans, invalid login probes, or reading credential file contents.
  Avoid using this skill for non-3CX telephony systems.
---

# 3CX PBX CLI Skill

This skill covers operation of two command-line tools that interact with 3CX PBX
APIs:

- **`3cx-config`**: Configuration REST API (users, departments, routing, recordings, system)
- **`3cx-call`**: Call Control API (make calls, manage participants, stream audio, listen to events)

## Tool Availability

On hosts where the tools are installed on `PATH`, run them directly (`3cx-config
version`). On the repo host they are symlinked into `/usr/local/bin` from
`/home/rc/projects/3cx/`. Otherwise, run from the repository root as `./3cx-config` /
`./3cx-call` with `/usr/bin/python3`. Both require Python 3 with `requests` and
`websocket-client` installed. If the bare command is not found and no repo checkout
exists, stop and ask the user to install the tools — do not fall back to raw API calls.
## When to Use

Use this skill when the task involves:

- Inspecting 3CX system configuration (users, departments, routing rules, trunks)
- Managing people and departments (create, update, delete users or departments)
- Configuring call routing (inbound/outbound rules, IVRs, queues, ring groups)
- Working with call recordings (list, download, delete)
- Making or managing calls via the Call Control API
- Listening to real-time call events via WebSocket
- Troubleshooting 3CX API connectivity or authentication

## When Not to Use

Do not use this skill for:

- Raw `curl` or direct HTTP API calls (use the CLI tools instead)
- Direct database edits to the 3CX SQLite or PostgreSQL backend
- Port scans or network probing of the PBX host
- Testing invalid usernames or passwords (triggers fail2ban)
- Reading or printing credential file contents
- Non-3CX telephony systems (Asterisk, FreeSWITCH, Elastix standalone)

## Safety-First Principles

### Read-Only Discovery is the Default

Always start with read-only commands to understand the current state:

- List users: `3cx-config users`
- List departments: `3cx-config departments`
- Check system status: `3cx-config system-status`
- View active calls: `3cx-call status`

Only after understanding the current state, proceed to mutations.

### Require Explicit Confirmation for Mutating Commands

Before running any command that creates, updates, deletes, or restarts, confirm
with the user:

**Mutating commands include:**

- `create-user`, `delete-users`, `assign-role`
- `create-department`, `delete-department`, `update-department`
- `create-live-chat`, `parking --create`, `parking --delete`
- `active-calls --drop`
- `recordings --delete`, `recordings --download`
- `inbound-rules --delete`, `outbound-rules --delete`, `outbound-rules-update`, `create-outbound-rule`
- `trunks --delete`, `phones --delete`, `contacts --delete`
- `blacklist --add`, `blacklist --delete`
- `ip-blocklist --add`, `ip-blocklist --delete`
- `activity-log --purge`
- `backups --create`, `backups --restore`
- `restart --confirm`
- `emergency-numbers --add`, `emergency-numbers --delete`
- `call` (initiates a live call)
- `action` with `drop`, `divert`, `transferto`, `routeto`

**Safe read-only commands (no confirmation needed):**

- All list/get commands without `--delete`, `--create`, `--add`, `--drop`, `--purge`, `--restore`
- `version`, `system-status`, `status`, `devices`, `participant`
- `listen` (read-only event stream)
- `stream --output` (downloads audio to a file, does not mutate PBX state)

### Never Expose Credential Contents

Credential files live at:

- `~/.3cx-config.json` (Configuration API: FQDN, client ID, client secret, cached token)
- `~/.3cx-call.json` (Call Control API: FQDN, API key, DN)

**Rules:**

- Never print, log, or echo the contents of these files
- Never display `client_secret`, `api_key`, or cached `access_token` values
- Refer to these paths only when explaining where credentials are stored
- Use placeholder values like `<REDACTED>` in examples, never real credentials

### Token Lifetime and Caching

The Configuration API uses OAuth2 client credentials flow. Tokens expire in
**60 seconds**. The CLI caches tokens and refreshes them automatically, but
cache them for **no more than 45 seconds** to avoid stale token errors.

The Call Control API uses a static API key (no token refresh needed).

## Workflow Patterns

### Pattern 1: Inspect Before Mutate

Before creating or deleting anything, list the current state:

```bash
# List existing departments
3cx-config departments

# List existing users
3cx-config users

# Check system status
3cx-config system-status
```

Then proceed with the mutation after confirming with the user.

### Pattern 2: Verify After Mutate

After a create/update/delete, verify the change took effect:

```bash
# After creating a user
3cx-config users --filter "Email eq 'newuser@example.com'"

# After deleting a department
3cx-config departments

# After updating a department
3cx-config departments --id 29
```

### Pattern 3: Test Connectivity First

Before troubleshooting, verify the CLI can reach the PBX:

```bash
# Configuration API
3cx-config version

# Call Control API
3cx-call status
```

If these fail, check credentials and network connectivity (see
[references/live-safety.md](references/live-safety.md)).

### Pattern 4: Paginate Large Lists

Most list commands support `--top` and `--skip` for pagination:

```bash
# Get first 50 users
3cx-config users --top 50

# Get next 50 users (skip first 50)
3cx-config users --top 50 --skip 50

# Filter with OData expressions
3cx-config departments --filter "Name eq 'Sales'"
```

## Quick Reference: 3cx-config Subcommands

### Setup and Authentication

- `config`: Save API credentials (FQDN, client ID, client secret)
- `token`: Get access token (usually auto-cached)
- `version`: Get 3CX version

### System Operations

- `system-status`: Get system status
- `active-calls`: List active calls (use `--drop` to end a call)
- `call-history`: View call history (supports date filtering)
- `recordings`: Manage call recordings (list, download, delete)

### Users and Departments

- `departments`: List or check departments
- `create-department`: Create a new department
- `delete-department`: Delete a department by ID
- `update-department`: Update department settings (e.g., transcription)
- `department-members`: List department members
- `users`: List users (supports pagination and filtering)
- `create-user`: Create a new user
- `delete-users`: Delete users by ID
- `assign-role`: Assign a role to a user in a department

### Communication

- `live-chat`: List live chat URLs
- `create-live-chat`: Create a live chat URL
- `parking`: Manage shared parking (list, create, delete)

### Routing and Call Flow

- `inbound-rules`: Manage inbound routing rules
- `outbound-rules`: Manage outbound routing rules
- `outbound-rules-update`: Update an outbound rule
- `create-outbound-rule`: Create a new outbound rule
- `ivrs`: List or get IVR menus (read-only)
- `queues`: List or get queues (read-only)
- `ring-groups`: List or get ring groups (read-only)

### Infrastructure

- `trunks`: Manage SIP trunks
- `phones`: Manage SIP devices (phones)
- `contacts`: Manage contacts (list, export, delete)

### Security

- `blacklist`: Manage blacklisted phone numbers
- `ip-blocklist`: Manage IP blocklist
- `activity-log`: View or purge activity logs

### System Control

- `backups`: Manage backups (list, create, restore)
- `restart`: Restart the PBX (requires `--confirm`)
- `emergency-numbers`: Manage emergency numbers

### Miscellaneous

- `who-can-dial`: Check dial permissions

## Quick Reference: 3cx-call Subcommands

### Setup and Status

- `config`: Save API credentials (FQDN, API key, DN)
- `status`: Get call control status (optionally filter by DN)

### Devices and Calls

- `devices`: List or get devices
- `call`: Make a call to a destination
- `participant`: Get participant(s) in a call
- `action`: Perform an action on a participant (answer, drop, divert, transferto, routeto)

### Real-Time Events

- `listen`: Listen for real-time events via WebSocket (supports `--retries` for reconnection)

### Audio Streaming

- `stream`: Get or upload audio streams (PCM 16-bit 8000Hz mono)

## Detailed Command Reference

For full flag details and examples, read:

- [references/configuration-api.md](references/configuration-api.md): All `3cx-config` subcommands with flags
- [references/call-control-api.md](references/call-control-api.md): All `3cx-call` subcommands with flags
- [references/live-safety.md](references/live-safety.md): Safety rules and troubleshooting for live PBX operations

## OData Pagination and Filtering

Most list commands in `3cx-config` support OData-style pagination and filtering:

| Flag | Default | Description |
|------|---------|-------------|
| `--top N` | 100 | Maximum number of items to return |
| `--skip N` | 0 | Number of items to skip (for pagination) |
| `--filter EXPR` | (none) | OData `$filter` expression |

Examples:

```bash
# Get third page of 50 users
3cx-config users --top 50 --skip 100

# Filter departments by name
3cx-config departments --filter "Name eq 'Sales'"

# Filter call history by date
3cx-config call-history --filter "StartTime gt 2024-01-01" --top 200
```

## Audio Format

Audio streams use **PCM 16-bit 8000Hz mono** format. Convert with `ffmpeg`:

```bash
# WAV to PCM
ffmpeg -i input.wav -f s16le -acodec pcm_s16le -ar 8000 -ac 1 output.raw

# PCM to WAV
ffmpeg -f s16le -ar 8000 -ac 1 -i input.raw output.wav
```

## WebSocket Events

The `listen` command receives these event types:

| EventType | Description |
|-----------|-------------|
| 0 (Upsert) | Entity added or updated |
| 1 (Remove) | Entity removed |
| 2 (DTMF) | DTMF digits received |
| 4 (Response) | Response to request |

Reconnection uses exponential backoff (2s, 4s, 8s, up to 60s) with a default
of 5 retry attempts. Use `--retries N` to adjust.

## User Roles

| Role | Description |
|------|-------------|
| `system_owners` | Full system access |
| `system_admins` | System administration |
| `group_owners` | Department owner |
| `managers` | Department manager |
| `group_admins` | Department administrator |
| `receptionists` | Receptionist |
| `users` | Standard user |

## API Endpoint Mapping

Some CLI command names differ from their underlying 3CX API endpoint names:

| CLI Command | API Endpoint | Notes |
|-------------|-------------|-------|
| `phones` | `SipDevices` | Hardware/softphone devices |
| `ivrs` | `CallFlowApps` | IVR / Auto-attendant menus |
| `emergency-numbers` | `EmergencyGeoLocations` | E911 / emergency routing |
| `call-history` | `ReportCallLogData/Pbx.GetCallLogData(...)` | OData function with date params |
| `activity-log` | `ActivityLog/Pbx.GetLogs(...)` | OData function with filter params |
| `departments` | `Groups` | Department/group management |
