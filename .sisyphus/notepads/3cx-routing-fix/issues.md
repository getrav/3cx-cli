# Task 1 Issues — 3CX Routing Fix Plan

## 2026-04-24

### ISSUE: Flowroute-PSTN trunk (ID 81) missing from API
- System status reports 4 trunks registered, but trunks API only returns 3
- Expected trunk "Flowroute-PSTN" with ID 81 not found
- May need investigation via web admin console

### ISSUE: All IVRs returned empty
- Inbound rules reference IVRs 806, 810, 813, 814 but none exist in the API
- Confirms "lost IVR configs" reported in the routing issue
- IVRs will need to be recreated

### ISSUE: SC-Out +1 outbound rule has invalid trunk (TrunkId=-1)
- Rule Priority 2 references no valid trunk
- SohoFab and Syosset Office members using this rule will fail to dial +1 prefixed numbers

### ISSUE: Task 4 live testing blocked by architecture
- **CRITICAL**: `3cx-call` originates from "ai" DN which is NOT in any routing department
- **Routing rules match by department (GroupIds), not DN** — test calls from "ai" DN cannot trigger outbound rule matching
- Only Ext 110 (Sarika Shah, Dept 30 Syosset Office) is in a PoshTex department
- No extensions exist in SilkCrafts departments (31, 32, 33)
- **WORKAROUND**: Outbound rules CONFIGURATION VERIFIED via API (Task 2 confirmed priorities, groups, trunks, callerIDs). Live routing path verification requires user to manually test calls from real extensions.

### ISSUE: 3CX OAuth token expires after 60 seconds (rate limiting)
- PBX returns `expires_in: 60` for client_credentials tokens
- CLI updated to refresh token every 45 seconds to avoid 403 errors
- This is a 3CX API quirk — JWT token has 1-hour expiry but OAuth token only valid for 60s

## Session 2 — Tasks 8-11 Issues (2026-04-24)

### ISSUE: Holiday routing not configured for PoshTex/SilkCrafts
- Inbound Rule 1 (PoshTex): AlterDestinationDuringHolidays=false → holidays use after-hours IVR
- Inbound Rule 4 (SilkCrafts): AlterDestinationDuringHolidays=false → holidays use after-hours IVR
- Inbound Rule 5 (Tech Team): AlterDestinationDuringHolidays=true BUT HolidaysDestination has empty IVR Number
- NOT in scope to fix per plan constraints (NO office hours modifications)

### ISSUE: Tech Team Rule 5 has empty Number fields
- OfficeHoursDestination: Type=Extension, Number="" (empty)
- OutOfOfficeHoursDestination: Type=Extension, Number="" (empty)
- HolidaysDestination: Type=IVR, Number="" (empty)
- May inherit from department defaults via Console

### ISSUE: SohoFab (Group 29) assigned to SC-Out+1 but has 0 extensions
- Recommendation: Remove Group 29 from SC-Out+1 to clean up routing

### BLOCKER: IVR Restoration (Tasks 5-7)
- Cannot proceed without Console credentials and IVR DTMF specs
- All IVR API queries return empty array (CLI limitation)
- Inbound rules correctly reference IVR numbers 806, 810, 813, 814

## Session 3 — Task 5-6 Resolution (2026-04-24)

### RESOLVED: IVR Restoration (Tasks 5-7) — IVRs Already Exist
- **Root Cause**: CLI `ivrs` command queries `/xapi/v1/CallFlowApps` (always empty), but IVRs are stored as `Receptionist` entities at `/xapi/v1/Receptionists`
- **Resolution**: All 4 required IVRs (806, 810, 813, 814) confirmed existing with correct names via Receptionists API
- **Impact**: Tasks 5-6 were unnecessary — IVRs were never lost, just invisible to CLI's wrong endpoint
- **Recommendation**: Update `3cx-config` CLI to query `/Receptionists` instead of `/CallFlowApps`
