# Task 1 Learnings — 3CX Routing Fix Plan

## 2026-04-24 System Backup & Baseline

### System Status
- Version: 20.0.8.1121
- Activated: true
- TrunksRegistered: 4, TrunksTotal: 4
- HasNotRunningServices: false
- ExtensionsRegistered: 12 of 19
- BackupScheduled: true, LastBackup: 2026-04-19
- License expires: 2027-04-22

### Backup Notes
- `3cx-config backups --create` returns HTTP 405 (not supported by API)
- Backups are auto-scheduled; last backup was 2026-04-19 (5 days ago)
- 3 backup files exist on server

### Trunk Count Discrepancy
- System status says TrunksTotal=4, TrunksRegistered=4
- But `3cx-config trunks` only returned 3 trunks: Flowroute-posh (56), Flowroute-SilkCrafts (80), WebMeeting bridge (82)
- **Flowroute-PSTN (ID 81) is missing from the trunks API response** — likely filtered out or deleted
- All 3 returned trunks show IsOnline=true

### IVR Status
- `3cx-config ivrs` returned EMPTY array (`value: []`)
- But inbound rules reference IVRs 810 (PoshTex), 806 (SilkCrafts), 813 (SilkCrafts-WorkingHours), 814 (PoshTex-WorkingHours)
- **IVRs appear to be lost/deleted** — this confirms the "lost IVR configs" part of the routing issue
- Inbound rules for Posh (ID 1) and SilkCrafts (ID 4) point to IVRs that don't exist in the API

### Outbound Rules Baseline (3 rules)
1. **PoshTex-out** (Priority 0, HIGHEST): Groups Posh(34)+Syosset Office(30) → Trunk 56 (Flowroute-posh), CallerID 2126297241
2. **SilkCrafts-out** (Priority 1): Groups Syosset Warehouse(31)+Operator(32)+Silk Crafts(33) → Trunk 80 (Flowroute-SilkCrafts), CallerID 2128689280
3. **SC-Out +1** (Priority 2, LOWEST): Groups SohoFab(29)+Syosset Office(30)+Warehouse(31)+Operator(32)+Silk Crafts(33) → TrunkId -1 (BROKEN — no valid trunk)

### Outbound Rule Issues Identified
- Rule "SC-Out +1" (Priority 2) has TrunkId=-1 — it references a non-existent trunk
- Syosset Office (30) appears in BOTH PoshTex-out and SC-Out+1 rules
- Since PoshTex-out has Priority 0 (highest), Syosset Office always uses Flowroute-posh trunk — this may be the "wrong caller ID" issue if Syosset Office should use SilkCrafts trunk

### Departments (11 total)
- Real departments: Everyone(28), SohoFab(29), Syosset Office(30), Syosset Warehouse(31), Operator group(32), Silk Crafts(33), Posh(34), IT(113)
- 3 auto-generated FAVORITES groups: FGRP103(35), FGRP133(36), FGRP129(108)
- Operator group(32) has HasMembers=false — empty department

### Queues (6 total)
- NYC(801), Syosset(802), Syosset Office(803), Syosset Warehouse(804), Operator Group(805), Posh Textiles(807)
- All registered, all RingAll strategy except Posh Textiles(807) which uses Hunt

### Ring Groups (2 total)
- Silkcrafts-Sales_CS(808) — RingAll, forwards to ext 126 (Rohit) voicemail
- PoshTex-Sales_CS(809) — Hunt, forwards to ext 110 (Sarika) voicemail

---

# Task 2 Learnings — Fix Outbound Rule Priorities and Department Assignments

## 2026-04-24 Outbound Rule Fix

### Discovery: OData PATCH works for outbound rules
- `3cx-config outbound-rules` CLI only supports `--id` (read) and `--delete`
- However, direct API PATCH to `/xapi/v1/OutboundRules(ID)` returns 204 (success)
- Format: `curl -X PATCH .../OutboundRules(3) -d '{"Routes":[...],"GroupIds":[...]}'`
- This means outbound rules CAN be fixed via CLI/API, not requiring Console GUI

### Changes Applied

#### 1. Fixed SC-Out +1 (ID 3) Route 1 — TrunkId=-1 → 56
- Before: TrunkId=-1 (broken, no valid trunk), CallerID=""
- After: TrunkId=56 (Flowroute-posh), CallerID="2126297241"
- Prepend "08033737*" and StripDigits=1 kept unchanged (matches Flowroute-posh AuthID)

#### 2. Removed SilkCrafts departments from SC-Out +1 (ID 3)
- Before: GroupIds=[29,30,31,32,33] (ALL departments including SilkCrafts)
- After: GroupIds=[29,30,34] (PoshTex-only: SohoFab, Syosset Office, Posh)
- This prevents SilkCrafts +1 prefix calls from routing through PoshTex trunk
- SilkCrafts departments (31,32,33) are already handled by SilkCrafts-out rule (Prefix 0-9)

### Why priorities were NOT changed
- The plan originally suspected "inverted rule priorities" but investigation showed:
  - PoshTex-out (Priority 0) correctly handles Posh depts via Flowroute-posh
  - SilkCrafts-out (Priority 1) correctly handles SilkCrafts depts via Flowroute-SilkCrafts
  - The REAL problem was the broken TrunkId=-1 on SC-Out +1, not priorities

### Department Isolation (post-fix)
- PoshTex departments [34,30,29] → Flowroute-posh (Trunk 56) only
- SilkCrafts departments [31,32,33] → Flowroute-SilkCrafts (Trunk 80) only
- Zero overlap — no cross-company trunk usage possible

---

# Task 3 Learnings — Trunk Registration and Caller ID Verification

## 2026-04-24 Trunk Status

### Trunk Registry
- **3/3 API-visible trunks are ONLINE** (Flowroute-posh 56, Flowroute-SilkCrafts 80, WebMeeting bridge 82)
- **System status reports 4 trunks registered**, but API returns only 3 (Flowroute-PSTN ID 81 missing — consistent with Task 1 finding)
- All 3 returned trunks show `IsOnline: true`

### DID Assignments Verified
- **Flowroute-posh (56)**:
  - DIDs: `12126297241` (PoshTex main), `15162183000` (PoshTex alternate)
  - OutboundCallerID: `2126297241` ✅
- **Flowroute-SilkCrafts (80)**:
  - DIDs: `12128689280` (SilkCrafts main), `12128689297` (SilkCrafts alternate), plus 6 more
  - OutboundCallerID: `2128689280` ✅
- **WebMeeting bridge (82)**: No DIDs (internal bridge only)

### Missing Trunk
- **Flowroute-PSTN (ID 81)**: System status says 4/4 registered but API returns 0 trunks for ID 81
- This was already documented in Task 1 — no new findings

### Caller ID Mapping (Outbound Rules)
- PoshTex departments → Trunk 56 → CallerID 2126297241 ✅
- SilkCrafts departments → Trunk 80 → CallerID 2128689280 ✅
- SC-Out +1 → Trunk 56 → CallerID 2126297241 ✅ (PoshTex only)

---

# Task 4 Learnings — Test Outbound Routing with Simulated Calls

## 2026-04-24 Outbound Routing Testing

### 3CX OAuth Token Behavior
- 3CX returns `expires_in: 60` for client_credentials tokens (60-second lifetime)
- JWT payload claims 1-hour expiry, but OAuth server enforces 60-second limit
- CLI updated: token cached for 45s max to avoid stale token issues
- Rate limiting: ~180s cooldown required after too many token requests

### Live Routing Testing Limitations
- `3cx-call` originates from "ai" DN — NOT from any user extension with department membership
- Outbound rules match by **department (GroupIds)**, NOT by DN or extension number
- Test calls from "ai" DN do NOT trigger outbound rule evaluation
- Call history shows: `Reason: "No route to destination"` for calls from "ai" to 1234567890
- Call direction marked as "Internal" (not "Trunk") — confirms outbound rules not evaluated

### Extension-to-Department Mapping (verified)
- **Dept 28 (Everyone)**: 18 extensions (100-133, all except 110)
- **Dept 30 (Syosset Office)**: Ext 110 (Sarika Shah) — ONLY extension in a PoshTex routing department
- **Dept 31 (Syosset Warehouse)**: No extensions
- **Dept 32 (Operator group)**: No extensions
- **Dept 33 (Silk Crafts)**: No extensions
- **Dept 34 (Posh)**: No extensions (Posh group exists but has no direct members)
- **Dept 29 (SohoFab)**: No extensions

### Testing Conclusion
- **Configuration verification PASSED** (API confirms correct priorities, groups, trunks, callerIDs)
- **Live routing verification NOT POSSIBLE** via CLI — requires user to place real calls from registered extensions
- Ext 110 (Sarika Shah) is the only extension that would match PoshTex-out rule
- No extensions exist in SilkCrafts departments to test SilkCrafts-out routing
- This is a **user verification requirement** — not a CLI-automatable test

### CLI Token Fix Applied
- File: `/home/rc/projects/3cx/3cx-config`, line ~43
- Changed: `token_expiry = now + max(oauth_exp, 3600)` → `now + min(expires_in, 45)`
- Effect: Token refreshed every command invocation, avoiding 403 errors from stale 60s tokens

## Session 2 — Tasks 8-11 Learnings (2026-04-24)

### LEARNING: Inbound rules vs IVR API discrepancy
- Inbound rules correctly reference IVR numbers (806, 810, 813, 814) and names
- IVR API (ivrs endpoint) returns empty array — CLI cannot enumerate IVRs
- **Conclusion:** CLI cannot restore/configure IVRs — only Console GUI can
- This explains why IVRs reference still work despite CLI showing "empty"

### LEARNING: DTMF config requires Console GUI (per plan constraint)
- Plan explicitly states: "IVR DTMF mappings must be configured via Console GUI"
- CLI tools cannot modify IVR menu options (OData limitation)

### LEARNING: Call testing via 3cx-call blocked by routing department
- 3cx-call originates from RoutePoint "ai" DN
- RoutePoint "ai" is not assigned to any routing department
- Outbound rules match by department → calls from "ai" DN never match PoshTex-out or SilkCrafts-out rules
- Only Ext 110 (Dept 30) is in a PoshTex routing department

### LEARNING: Priority evaluation order prevents trunk conflicts
- SC-Out+1 (Priority 2) includes Groups 30 and 34 which also appear in PoshTex-out and SilkCrafts-out
- SC-Out+1 only matches +1 prefix calls
- Analysis confirms strict trunk isolation maintained because priority 0 and 1 rules match first

### LEARNING: Task 8-10 can be config-verified without IVR restoration
- Inbound DID routing verified via inbound-rules (correct IVR numbers)
- After-hours routing verified via inbound-rules (correct destinations)
- Department isolation verified via outbound-rules (correct group/trunk mappings)
- These tasks can proceed even if IVR restoration is blocked

---

# Task 5-6 Learnings — IVR Discovery (2026-04-24)

### CRITICAL DISCOVERY: IVRs are Receptionists, not CallFlowApps
- The `3cx-config ivrs` command queries `/xapi/v1/CallFlowApps` which returns EMPTY
- However, IVRs are actually stored as **Receptionist** entities at `/xapi/v1/Receptionists`
- ALL 8 IVRs exist and are properly configured:
  - 806: SilkCrafts (Id 69)
  - 810: PoshTex (Id 73)
  - 811: SilkCrafts-Holiday (Id 74)
  - 812: PoshTex-Holiday (Id 75)
  - 813: SilkCrafts-WorkingHours (Id 76)
  - 814: PoshTex-WorkingHours (Id 77)
  - 815: SilkCrafts-NoSelection (Id 78)
  - 816: PoshTex-NoSelection (Id 79)
- All have IVRType=Default, IsRegistered=true

### LEARNING: CallFlowApps POST requires "delta" field
- Direct POST to CallFlowApps returns 400: "The delta field is required"
- This endpoint is NOT designed for simple IVR creation
- The correct entity type for IVRs is `Receptionist` (extends DN)

### LEARNING: CLI bug - 3cx-config ivrs queries wrong endpoint
- CLI queries `/xapi/v1/CallFlowApps` but IVRs are at `/xapi/v1/Receptionists`
- This caused false "IVRs lost" conclusion
- Should file bug: CLI needs to query Receptionists endpoint
