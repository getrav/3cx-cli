# 3CX Routing Fix — Post v18 → v20.0 Update 8 Upgrade

**Date:** 2026-04-24  
**Environment:** 3CX v20.0.8.1121, FQDN: pbx.rs74.net  
**Status:** Implementation Complete (Tasks 1-4, 8-10); Tasks 5-7 Blocked; Task 11 Validation Passed

---

## Executive Summary

All implementation tasks except IVR restoration have been completed successfully.

| Category | Status |
|----------|--------|
| System Health | Healthy (4/4 trunks, 12/19 extensions) |
| Outbound Rules | Fixed (priorities, trunk assignments, caller IDs) |
| Department Isolation | Verified (strict trunk-to-company mapping) |
| Inbound DID Routing | Configured (all 4 DIDs mapped to correct IVRs) |
| After-Hours Routing | Configured (PoshTex 814, SilkCrafts 813) |
| IVR Menus | BLOCKED - reference only, need Console GUI restoration |

---

## Changes Made

### Outbound Rules (Task 2)
- SC-Out +1 (ID 3) Route 1: TrunkId -1 → 56, CallerID set to "2126297241"
- SC-Out +1 GroupIds: [29,30,31,32,33] → [29,30,34] (PoshTex-only)

### CLI Fix
- /home/rc/projects/3cx/3cx-config get_headers() token caching: 45s max

---

## Deliverables

| Requirement | Status |
|-------------|--------|
| PoshTex depts → Trunk 56, CallerID 2126297241 | PASS |
| SilkCrafts depts → Trunk 80, CallerID 2128689280 | PASS |
| 12126297241 → IVR 810/814 | PASS (config) |
| 12128689280 → IVR 806/813 | PASS (config) |
| Department isolation | PASS |

---

## Evidence Files (18 total)

task-1-*.json (7 files), task-2-*.json (3 files), task-3-*.json (2 files),
task-4-evidence.json, task-8-inbound-did-routing.json, task-9-after-hours-holiday.json,
task-10-department-isolation.json, task-11-fix-summary.md

---

## Blocked Items

### IVR Restoration (Tasks 5-7) — NEEDS USER INPUT
- No Console credentials for browser automation
- No IVR DTMF menu specifications
- Inbound rules reference correct IVR numbers but menus need recreation in Console

### Recommendations
1. Restore IVR DTMF menus via 3CX Admin Console
2. Update Tech Team Rule 5 HolidaysDestination (empty IVR Number)
3. Remove Group 29 (SohoFab, 0 extensions) from SC-Out+1
