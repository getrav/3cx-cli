# 3cx-config Command Reference

Complete reference for all `3cx-config` subcommands with flags and examples.

## Setup and Authentication

### config

Save API credentials to `~/.3cx-config.json`.

```bash
3cx-config config \
  --fqdn <your-pbx-fqdn> \
  --client-id <REDACTED> \
  --client-secret <REDACTED>
```

**Flags:**

- `--fqdn`: 3CX server hostname (without `https://`)
- `--client-id`: OAuth2 client ID
- `--client-secret`: OAuth2 client secret

### token

Get an access token. Usually not needed since tokens are auto-cached.

```bash
3cx-config token
```

### version

Get the 3CX version.

```bash
3cx-config version
```

## System Operations

### system-status

Get system status.

```bash
3cx-config system-status
```

### active-calls

List active calls.

```bash
3cx-config active-calls
3cx-config active-calls --top 10
```

**Flags:**

- `--top N`: Maximum number of calls to return
- `--drop CALL_ID`: End a specific call (mutating, requires confirmation)

### call-history

View call history.

```bash
3cx-config call-history --top 50
3cx-config call-history --start "2026-01-01T00:00:00Z" --end "2026-01-31T23:59:59Z"
3cx-config call-history --filter "StartTime gt 2024-01-01"
```

**Flags:**

- `--top N`: Maximum number of records
- `--skip N`: Number of records to skip
- `--start ISO8601`: Start time filter
- `--end ISO8601`: End time filter
- `--filter EXPR`: OData filter expression

### recordings

Manage call recordings.

```bash
3cx-config recordings
3cx-config recordings --download 123
3cx-config recordings --delete 123 456
```

**Flags:**

- `--download ID`: Download a specific recording
- `--delete ID [ID ...]`: Delete recordings (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

## Users and Departments

### departments

List or check departments.

```bash
3cx-config departments
3cx-config departments --name "Sales"
3cx-config departments --id 29
```

**Flags:**

- `--name NAME`: Filter by department name
- `--id ID`: Get a specific department by ID
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### create-department

Create a new department.

```bash
3cx-config create-department \
  --name "Support" \
  --prompt-set "<uuid>" \
  --language EN
```

**Flags:**

- `--name NAME`: Department name (required)
- `--prompt-set UUID`: Prompt set UUID (required)
- `--language CODE`: Language code (e.g., EN, ES, FR)

### delete-department

Delete a department by ID.

```bash
3cx-config delete-department --id 123
```

**Flags:**

- `--id ID`: Department ID to delete (required, mutating, requires confirmation)

### update-department

Update department settings.

```bash
3cx-config update-department --id 29 --transcription Both
3cx-config update-department --id 30 --transcription Nothing
```

**Flags:**

- `--id ID`: Department ID (required)
- `--transcription MODE`: Transcription mode (Both, Nothing, etc.)

### department-members

List department members.

```bash
3cx-config department-members --id 95
```

**Flags:**

- `--id ID`: Department ID (required)

### users

List users.

```bash
3cx-config users
3cx-config users --email user@example.com
3cx-config users --top 50 --skip 100
```

**Flags:**

- `--email EMAIL`: Filter by email
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### create-user

Create a new user.

```bash
3cx-config create-user \
  --first-name John \
  --last-name Doe \
  --email john@example.com \
  --password "<REDACTED>" \
  --extension 201 \
  --prompt-set "<uuid>"
```

**Flags:**

- `--first-name NAME`: First name (required)
- `--last-name NAME`: Last name (required)
- `--email EMAIL`: Email address (required)
- `--password <REDACTED>`: Password (required, use `<REDACTED>` in examples)
- `--extension EXT`: Extension number (required)
- `--prompt-set UUID`: Prompt set UUID (required)

### delete-users

Delete users by ID.

```bash
3cx-config delete-users --ids 37 38
```

**Flags:**

- `--ids ID [ID ...]`: User IDs to delete (required, mutating, requires confirmation)

### assign-role

Assign a role to a user in a department.

```bash
3cx-config assign-role --user-id 120 --group-id 95 --role managers
```

**Flags:**

- `--user-id ID`: User ID (required)
- `--group-id ID`: Department/group ID (required)
- `--role ROLE`: Role name (required, e.g., managers, users, system_owners)

## Communication

### live-chat

List live chat URLs.

```bash
3cx-config live-chat
3cx-config live-chat --check "mychat123"
```

**Flags:**

- `--check URL`: Check if a live chat URL is available
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### create-live-chat

Create a live chat URL.

```bash
3cx-config create-live-chat \
  --link "support-chat" \
  --group-id 95 \
  --group-name "DEFAULT" \
  --group-number "GRP0000"
```

**Flags:**

- `--link URL`: Live chat URL slug (required)
- `--group-id ID`: Department/group ID (required)
- `--group-name NAME`: Department name
- `--group-number NUM`: Department number

### parking

Manage shared parking.

```bash
3cx-config parking
3cx-config parking --create --group-ids 95 122
3cx-config parking --delete 126
```

**Flags:**

- `--create`: Create a new parking slot (mutating, requires confirmation)
- `--group-ids ID [ID ...]`: Group IDs for the parking slot
- `--delete ID`: Delete a parking slot (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

## Routing and Call Flow

### inbound-rules

Manage inbound routing rules.

```bash
3cx-config inbound-rules
3cx-config inbound-rules --id 5
3cx-config inbound-rules --delete 10 11
```

**Flags:**

- `--id ID`: Get a specific rule by ID
- `--delete ID [ID ...]`: Delete rules (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### outbound-rules

Manage outbound routing rules.

```bash
3cx-config outbound-rules
3cx-config outbound-rules --id 5
3cx-config outbound-rules --delete 10 11
```

**Flags:**

- `--id ID`: Get a specific rule by ID
- `--delete ID [ID ...]`: Delete rules (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### outbound-rules-update

Update an outbound rule.

```bash
3cx-config outbound-rules-update --id 5 --name "New Name"
```

**Flags:**

- `--id ID`: Rule ID (required)
- Additional flags depend on the rule properties to update

### create-outbound-rule

Create a new outbound rule.

```bash
3cx-config create-outbound-rule --name "Local Calls" --pattern "9XXXXXXXXX"
```

**Flags:**

- `--name NAME`: Rule name (required)
- `--pattern PATTERN`: Dial pattern (required)
- Additional flags depend on rule configuration

### ivrs

List or get IVR menus (read-only).

```bash
3cx-config ivrs
3cx-config ivrs --id 3
```

**Flags:**

- `--id ID`: Get a specific IVR by ID
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### queues

List or get queues (read-only).

```bash
3cx-config queues
3cx-config queues --id 3
```

**Flags:**

- `--id ID`: Get a specific queue by ID
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### ring-groups

List or get ring groups (read-only).

```bash
3cx-config ring-groups
3cx-config ring-groups --top 20
```

**Flags:**

- `--id ID`: Get a specific ring group by ID
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

## Infrastructure

### trunks

Manage SIP trunks.

```bash
3cx-config trunks
3cx-config trunks --id 1
3cx-config trunks --delete 5 6
```

**Flags:**

- `--id ID`: Get a specific trunk by ID
- `--delete ID [ID ...]`: Delete trunks (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### phones

Manage SIP devices (phones).

```bash
3cx-config phones
3cx-config phones --id 2
3cx-config phones --delete 7 8
```

**Flags:**

- `--id ID`: Get a specific device by ID
- `--delete ID [ID ...]`: Delete devices (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### contacts

Manage contacts.

```bash
3cx-config contacts
3cx-config contacts --id 42
3cx-config contacts --export
3cx-config contacts --delete 10 11
```

**Flags:**

- `--id ID`: Get a specific contact by ID
- `--export`: Export all contacts
- `--delete ID [ID ...]`: Delete contacts (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

## Security

### blacklist

Manage blacklisted phone numbers.

```bash
3cx-config blacklist
3cx-config blacklist --add "555-0000"
3cx-config blacklist --delete 1 2
```

**Flags:**

- `--add NUMBER`: Add a number to the blacklist (mutating, requires confirmation)
- `--delete ID [ID ...]`: Delete blacklist entries (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### ip-blocklist

Manage IP blocklist.

```bash
3cx-config ip-blocklist
3cx-config ip-blocklist --add "192.168.1.100" --description "Suspicious"
3cx-config ip-blocklist --delete 5
```

**Flags:**

- `--add IP`: Add an IP to the blocklist (mutating, requires confirmation)
- `--description TEXT`: Description for the blocklist entry
- `--delete ID [ID ...]`: Delete blocklist entries (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### activity-log

View or purge activity logs.

```bash
3cx-config activity-log
3cx-config activity-log --start "2026-02-01T00:00:00Z" --end "2026-02-28T23:59:59Z"
3cx-config activity-log --extension "100"
3cx-config activity-log --call-id "abc123"
3cx-config activity-log --severity "Error"
3cx-config activity-log --purge
```

**Flags:**

- `--start ISO8601`: Start time filter
- `--end ISO8601`: End time filter
- `--extension EXT`: Filter by extension
- `--call-id ID`: Filter by call ID
- `--severity LEVEL`: Filter by severity (Error, Warning, Info)
- `--purge`: Purge all logs (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

## System Control

### backups

Manage backups.

```bash
3cx-config backups
3cx-config backups --create
3cx-config backups --restore "backup_2026-02-27.zip"
```

**Flags:**

- `--create`: Create a new backup (mutating, requires confirmation)
- `--restore FILE`: Restore from a backup file (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

### restart

Restart the PBX.

```bash
3cx-config restart --confirm
```

**Flags:**

- `--confirm`: Required flag to confirm restart (mutating, requires explicit user confirmation)

### emergency-numbers

Manage emergency numbers.

```bash
3cx-config emergency-numbers
3cx-config emergency-numbers --add "911" --name "Emergency"
3cx-config emergency-numbers --delete 1
```

**Flags:**

- `--add NUMBER`: Add an emergency number (mutating, requires confirmation)
- `--name NAME`: Name for the emergency number
- `--delete ID [ID ...]`: Delete emergency numbers (mutating, requires confirmation)
- `--top N`, `--skip N`, `--filter EXPR`: Pagination and filtering

## Miscellaneous

### who-can-dial

Check dial permissions.

```bash
3cx-config who-can-dial --extension 100
```

**Flags:**

- `--extension EXT`: Extension to check (required)
