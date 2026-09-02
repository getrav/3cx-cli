# 3cx-call: Call Control API Reference

Complete flag reference for all `3cx-call` subcommands. All commands accept
`-h` / `--help` for inline usage. The global `--verbose` / `-v` flag prints
the HTTP method and URL for every request.

## Setup and Status

### `config`

Save API credentials to `~/.3cx-call.json`.

```bash
3cx-call config \
  --fqdn <your-pbx-hostname> \
  --api-key <REDACTED> \
  --dn 100
```

| Flag | Required | Description |
|------|----------|-------------|
| `--fqdn` | Yes | PBX hostname (no `https://` prefix) |
| `--api-key` | Yes | API key from the integration |
| `--dn` | Yes | DN / extension for this integration |

### `status`

Get call control status. Optionally filter by DN.

```bash
3cx-call status
3cx-call status --dn 101
```

| Flag | Description |
|------|-------------|
| `--dn <dn>` | Filter status to a specific DN |

## Devices and Calls

### `devices`

List or inspect registered devices.

```bash
3cx-call devices
3cx-call devices --device-id "device-uuid"
```

| Flag | Description |
|------|-------------|
| `--device-id <id>` | Get a specific device by ID |

### `call`

Make a call to a destination.

```bash
3cx-call call --destination 1234567890
3cx-call call --destination 1234567890 --timeout 60
3cx-call call --destination 1234567890 --device-id "device-uuid"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--destination` | Yes | Destination number or extension |
| `--timeout` | No | Call timeout in seconds |
| `--device-id` | No | Specific device to use |

### `participant`

Get participant(s) in an active call.

```bash
3cx-call participant
3cx-call participant --participant-id 1
```

| Flag | Description |
|------|-------------|
| `--participant-id <id>` | Get a specific participant |

### `action`

Perform an action on a call participant.

```bash
3cx-call action --participant-id 1 --action answer
3cx-call action --participant-id 1 --action drop
3cx-call action --participant-id 1 --action divert --destination 200
3cx-call action --participant-id 1 --action transferto --destination 101
3cx-call action --participant-id 1 --action routeto --destination 102
3cx-call action --participant-id 1 --action attach_participant_data --attached-data '{"key":"value"}'
3cx-call action --participant-id 1 --action attach_party_data --attached-data '{"key":"value"}'
```

| Flag | Required | Description |
|------|----------|-------------|
| `--participant-id` | Yes | Target participant ID |
| `--action` | Yes | Action to perform |
| `--destination` | Conditional | Required for `divert`, `transferto`, `routeto` |
| `--attached-data` | Conditional | JSON data for `attach_participant_data`, `attach_party_data` |
| `--reason` | No | Divert reason code |

**Available actions:**

| Action | Description | Requires `--destination` |
|--------|-------------|--------------------------|
| `answer` | Answer incoming call | No |
| `drop` | End participation | No |
| `divert` | Redirect ringing call | Yes |
| `routeto` | Add alternative route | Yes |
| `transferto` | Transfer connected call | Yes |
| `attach_participant_data` | Attach data to participant | No |
| `attach_party_data` | Attach data to caller | No |

**Divert reason codes** (use with `--reason`):

- `NoAnswer`, `PhoneBusy`, `PhoneNotRegisterred`, `ForwardAll`
- `BasedOnCallerID`, `BasedOnDID`
- `OutOfOfficeHours`, `BreakTime`, `Holiday`, `OfficeHours`
- `NoDestinations`, `Polling`, `CallbackRequested`, `Callback`

## Real-Time Events

### `listen`

Listen for real-time call events via WebSocket.

```bash
3cx-call listen
3cx-call listen --retries 10
3cx-call listen --retries 0
```

| Flag | Description |
|------|-------------|
| `--retries N` | Max reconnection attempts (default: 5, 0 to disable) |

Reconnection uses exponential backoff (2s, 4s, 8s, up to 60s). On a successful
reconnect, the retry counter resets. Press `Ctrl+C` to stop cleanly.

**Event types received:**

| EventType | Description |
|-----------|-------------|
| 0 (Upsert) | Entity added or updated |
| 1 (Remove) | Entity removed |
| 2 (DTMF) | DTMF digits received |
| 4 (Response) | Response to request |

## Audio Streaming

### `stream`

Get or upload audio streams. Audio format is PCM 16-bit 8000Hz mono.

```bash
3cx-call stream --participant-id 1 --output audio.raw
3cx-call stream --participant-id 1 --upload response.raw
```

| Flag | Description |
|------|-------------|
| `--participant-id <id>` | Target participant |
| `--output <file>` | Download audio to a file |
| `--upload <file>` | Upload audio from a file |

**Converting audio with ffmpeg:**

```bash
# WAV to PCM
ffmpeg -i input.wav -f s16le -acodec pcm_s16le -ar 8000 -ac 1 output.raw

# PCM to WAV
ffmpeg -f s16le -ar 8000 -ac 1 -i input.raw output.wav
```
