# Live PBX Safety Rules

Rules for operating against a live 3CX PBX without causing service disruption
or triggering security defenses.

## Credential Handling

### Where credentials live

- `~/.3cx-config.json` for the Configuration API (FQDN, client ID, client secret, cached token)
- `~/.3cx-call.json` for the Call Control API (FQDN, API key, DN)

File permissions are set to `0600` (owner read/write only).

### What never to do

- Never print, log, or echo the contents of credential files
- Never display `client_secret`, `api_key`, or cached `access_token` values in output
- Never pass credential values as inline examples; use placeholder values like `<REDACTED>` instead
- Never read credential files to debug (check file existence and permissions instead)

### Safe debugging

```bash
# Check that the config file exists and has correct permissions
ls -la ~/.3cx-config.json
ls -la ~/.3cx-call.json

# Verify the file is valid JSON without printing secrets
/usr/bin/python3 -c "import json; json.load(open('$HOME/.3cx-config.json')); print('valid')"
```

## Token Lifetime

The Configuration API uses OAuth2 client credentials. Tokens expire in
**60 seconds**. The CLI caches tokens automatically but keep cached tokens
for **no more than 45 seconds** to avoid expired token 401 errors.

The Call Control API uses a static API key. No token refresh is needed.

## Anti-Hacking Defenses

3CX has built-in fail2ban and auto-blacklisting. The following actions will
cause the firewall to drop connections to port 22 (SSH) and potentially 443
(HTTPS):

- Port scans against the PBX host
- Testing invalid usernames or passwords
- Repeated failed authentication attempts

When troubleshooting authentication failures:

1. Verify credentials are correct before retrying
2. Wait at least 15 minutes after a failed attempt before retrying
3. Check if the client IP has been blocked (contact PBX admin)

## Mutating Command Safety

### Always confirm before running

Before executing any command that changes PBX state, confirm with the user:

- What will change
- Which records are affected
- Whether the change is reversible

### High-risk commands

These commands have immediate, potentially irreversible effects:

| Command | Risk |
|---------|------|
| `restart --confirm` | Restarts the entire PBX, drops all active calls |
| `delete-users` | Removes user accounts |
| `delete-department` | Removes a department |
| `active-calls --drop` | Terminates an active call |
| `recordings --delete` | Permanently removes recordings |
| `backups --restore` | Overwrites current config with backup |
| `activity-log --purge` | Permanently removes log entries |
| `blacklist --add` | Blocks a phone number immediately |
| `ip-blocklist --add` | Blocks an IP address immediately |
| `call` | Initiates a live call |
| `action --action drop` | Drops a participant from a call |
| `action --action divert` | Redirects a ringing call |
| `action --action transferto` | Transfers a connected call |

### Lower-risk commands

These commands create or modify records but do not disrupt active operations:

| Command | Notes |
|---------|-------|
| `create-user` | Creates a new user (no impact on existing users) |
| `create-department` | Creates a new department |
| `update-department` | Modifies department settings |
| `create-live-chat` | Adds a chat URL |
| `inbound-rules --delete` | Removes routing rules (verify no active calls use them) |
| `outbound-rules --delete` | Removes routing rules |
| `trunks --delete` | Removes SIP trunks (verify not in use) |
| `phones --delete` | Removes device registrations |

## Troubleshooting Connectivity

### Step 1: Verify network reachability

```bash
# Check DNS resolution
host <your-pbx-fqdn>

# Check HTTPS connectivity (expect 401, not timeout)
curl -s -o /dev/null -w "%{http_code}" https://<your-pbx-fqdn>/xapi/v1/Pbx.GetVersion
```

### Step 2: Verify CLI authentication

```bash
# Configuration API
3cx-config version

# Call Control API
3cx-call status
```

### Step 3: Check common errors

| Error | Likely cause | Fix |
|-------|-------------|-----|
| 401 Unauthorized | Invalid credentials or expired token | Re-run `config` subcommand, verify credentials |
| 403 Forbidden | Insufficient permissions | Check API integration role (need System Owner for full access) |
| 404 Not Found | Wrong FQDN or invalid resource ID | Verify FQDN (no `https://` prefix) and resource ID |
| Connection timeout | Firewall or DNS issue | Check network connectivity, verify FQDN resolves |
| WebSocket disconnect | Network instability | Use `--retries` with `listen` command |

### Step 4: Use verbose mode

```bash
# See exact URLs and methods being called
3cx-call -v status
3cx-call -v call --destination 200
```

## WebSocket Listener Safety

The `listen` command opens a persistent WebSocket connection. When running
in production:

- Use `--retries` with a reasonable limit (default 5, up to 100 for long-running)
- Run in a terminal multiplexer (tmux, screen) to survive SSH disconnects
- Monitor memory usage (events accumulate over time)
- Use `Ctrl+C` to stop cleanly (no reconnection on manual exit)

## Backup Before Major Changes

Before making significant configuration changes:

```bash
# Create a backup
3cx-config backups --create

# Verify the backup was created
3cx-config backups
```

If something goes wrong, restore from the backup:

```bash
3cx-config backups --restore "<backup-filename>"
```
