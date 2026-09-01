# AGENTS.md - Developer & Agent Guide for 3CX Integration

This guide provides instructions, architectural context, connection details, and commands for AI coding agents and human developers operating within this repository.

---

## 1. System Overview & Architecture

This repository contains tools, libraries, and web services for integrating with a live **3CX PBX v20** server (running on Debian Linux).

```
                      ┌───────────────────────────────────────────────┐
                      │              3CX PBX System                   │
                      │  FQDN: pbx.rs74.net (silkcrafts.elastix.com)  │
                      │  Host IP: 65.49.60.50 (Port 22 SSH)           │
                      └───────┬───────────────────────────────┬───────┘
                              │                               │
            OAuth2 Token      │                               │ X-API-KEY / Route Point
         /connect/token       │                               │ /callcontrol/ & wss://
                              ▼                               ▼
               ┌───────────────────────────────┐  ┌───────────────────────────────┐
               │    Configuration REST API     │  │        Call Control API       │
               │         (/xapi/v1/)           │  │     (HTTP + WebSocket)        │
               └──────────────┬────────────────┘  └───────────────┬───────────────┘
                              │                                   │
                              ▼                                   ▼
               ┌───────────────────────────────┐  ┌───────────────────────────────┐
               │          `3cx-config`         │  │           `3cx-call`          │
               │  - Users, Depts, Inbound/Out  │  │  - Make/Drop/Hold Calls       │
               │  - Blocklists, Trunks, System │  │  - Participant operations     │
               │  - Recordings metadata/DL     │  │  - Real-time event streams    │
               └──────────────┬────────────────┘  └───────────────┬───────────────┘
                              │                                   │
                              └───────────────┬───────────────────┘
                                              │
                                              ▼
                             ┌───────────────────────────────────┐
                             │       Sync & Web Applications     │
                             │  - `sync-recordings` (Pipeline)   │
                             │  - `web/server.ts` (Bun proxy)    │
                             │  - LocalVoice (Whisper STT / TTS) │
                             └───────────────────────────────────┘
```

---

## 2. Verified Connection Details

### A. Configuration REST API (`3cx-config`)
- **Base URL**: `https://pbx.rs74.net/xapi/v1/`
- **Authentication**: OAuth 2.0 Client Credentials flow (`POST https://pbx.rs74.net/connect/token`)
- **Credential Storage**: `~/.3cx-config.json`
  ```json
  {
    "fqdn": "pbx.rs74.net",
    "client_id": "<redacted>",
    "client_secret": "<redacted>"
  }
  ```
- **Token Expiry**: 3CX tokens expire in **60 seconds**. Always use safe caching (`<= 45s`) to prevent stale token errors.
- **Role Requirement**: The API integration in 3CX must be assigned `System Owner` or `System Admin` under a specific department (e.g. `DEFAULT`) for full endpoint access.

### B. Call Control API (`3cx-call`)
- **Base URL**: `https://pbx.rs74.net/callcontrol/`
- **WebSocket URL**: `wss://pbx.rs74.net/callcontrol/events`
- **Authentication**: `X-API-KEY: <api-key>`
- **Credential Storage**: `~/.3cx-call.json`
  ```json
  {
    "fqdn": "pbx.rs74.net",
    "api_key": "<redacted>",
    "dn": "ai"
  }
  ```
- **License Prerequisite**: 8SC+ Enterprise License (`ENT/AI` or `ENT+`).

### C. Direct Host Access (SSH)
- **Host IP**: `65.49.60.50`
- **Port**: `22`
- **User**: `root`
- **Authentication**: SSH Private Key (`~/.ssh/id_ed25519`)
- **Command**:
  ```bash
  ssh root@65.49.60.50
  ```
- **Anti-Hacking Defense**: 3CX has built-in fail2ban/auto-blacklisting. **Do NOT run automated port scans or test invalid usernames**, as the firewall will temporarily drop port 22 connections.

---

## 3. Project Structure & Core Scripts

| File / Directory | Purpose | Key Commands |
|---|---|---|
| [`3cx-config`](file:///home/rc/projects/3cx/3cx-config) | Configuration REST API CLI | `./3cx-config system-status`<br>`./3cx-config users`<br>`./3cx-config recordings` |
| [`3cx-call`](file:///home/rc/projects/3cx/3cx-call) | Call Control CLI & WebSocket listener | `/usr/bin/python3 ./3cx-call status`<br>`./3cx-call call --destination 100`<br>`./3cx-call listen` |
| [`sync-recordings`](file:///home/rc/projects/3cx/sync-recordings) | Recordings ETL & Transcription | `./sync-recordings` |
| [`web/`](file:///home/rc/projects/3cx/web) | Bun proxy server + Recordings UI | `cd web && bun run server.ts` (Port 7001) |
| [`test_cli.py`](file:///home/rc/projects/3cx/test_cli.py) | Unit tests with mock responses | `/usr/bin/python3 -m unittest test_cli.py` |
| [`3cx.db3`](file:///home/rc/projects/3cx/3cx.db3) | SQLite database for recordings/transcripts | `sqlite3 3cx.db3` |

---

## 4. Python Environment & Dependencies

Dependencies required:
- `requests`
- `websocket-client` (for `3cx-call`)
- `indic-transliteration` (for `sync-recordings`)

**Recommended execution**:
Use `/usr/bin/python3` which contains system packages for `requests` and `websocket`, or activate the virtual environment:
```bash
source /home/rc/projects/3cx/venv/bin/activate
pip install requests websocket-client indic-transliteration
```

---

## 5. Testing & Verification

Run the entire test suite to verify CLI commands and arg-parsing:
```bash
/usr/bin/python3 -m unittest test_cli.py
```

Test live API connectivity:
```bash
./3cx-config version
./3cx-config system-status
/usr/bin/python3 ./3cx-call status
```

---

## 6. Rules & Conventions for Agents

1. **Never Log or Hardcode Secrets**: Never print API keys, client secrets, or auth tokens in commit messages or output logs.
2. **Preserve Relative Paths**: Scripts should dynamically resolve their base directory with `os.path.dirname(os.path.abspath(__file__))`.
3. **Respect Token Lifetime**: When calling 3CX REST APIs, handle HTTP 401 gracefully by refreshing the token and retrying once.
4. **Non-Destructive Operations**: Always confirm with `--confirm` or check before deleting or restarting services on live PBX systems.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
