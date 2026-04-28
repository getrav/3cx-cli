# 3CX CLI Tools & Routing Configuration Improvements

**Created**: 2026-04-24
**Status**: Draft

---

## Problem Statement

### CLI Tool Issues
1. **`ivrs` endpoint fixed** — Already corrected (CallFlowApps → Receptionists)
2. **Outbound rules have broken routes** — Rules contain Routes with TrunkId=-1 that need cleanup
3. **No outbound-rules modification support** — CLI only supports read/delete, not update
4. **No department membership visibility** — Users API returns PrimaryGroupId but not full group membership

### Routing Configuration Issues
1. **SC-Out +1 has wrong GroupIds** — Shows [32, 33] (SilkCrafts) but routes to Trunk 56 (PoshTex)
2. **Department isolation unclear** — Users appear to dial out successfully but API shows they're not in routing departments
3. **Outbound rules have broken fallback routes** — Routes 1-4 all have TrunkId=-1

---

## Acceptance Criteria

### Must Have
- [ ] All outbound rules cleaned (no TrunkId=-1 routes)
- [ ] CLI command to show user→department membership mapping
- [ ] CLI command to modify outbound rules (not just read/delete)
- [ ] SC-Out +1 routing verified correct (either PoshTex depts→Trunk 56 OR SilkCrafts depts→Trunk 80)

### Must NOT Have
- [ ] NO changes to trunk configurations
- [ ] NO changes to office hours
- [ ] NO changes to emergency numbers
- [ ] NO breaking existing working routes

### Nice to Have
- [ ] CLI command to list which extensions can dial out (based on department→outbound rule mapping)
- [ ] Better rate limiting error messages (suggest waiting 180s)

---

## Implementation Tasks

### Wave 1: CLI Improvements (independent)

#### T1. Add `department-members` Command
**What to do**: Add new command to show full department membership (not just PrimaryGroupId)

**Commands**:
```bash
3cx-config department-members                    # List all departments with members
3cx-config department-members --id 30           # Show members of specific department
3cx-config department-members --user 108        # Show all departments for user 108
```

**Implementation**:
- Query `/xapi/v1/Groups` with `$expand=Members` or check user endpoint for group array
- Map users to their routing departments
- Show which outbound rules apply to each user

**Evidence**: `.sisyphus/evidence/task-1-department-members.json`

---

#### T2. Add `outbound-rules --update` Support
**What to do**: Extend outbound-rules command to support PATCH operations

**Commands**:
```bash
3cx-config outbound-rules --id 3 --trunk 56     # Update route trunk
3cx-config outbound-rules --id 3 --caller-id 2126297241  # Update caller ID
3cx-config outbound-rules --id 3 --groups 29,30,34  # Update GroupIds
3cx-config outbound-rules --id 3 --clean-routes  # Remove broken TrunkId=-1 routes
```

**Implementation**:
- Add argument parser for update flags
- Implement PATCH request to `/xapi/v1/OutboundRules(ID)`
- Handle route array updates (replace broken routes)

**Evidence**: `.sisyphus/evidence/task-2-outbound-update.json`

---

#### T3. Add `who-can-dial` Command
**What to do**: New command that shows which extensions can dial out and via which trunk

**Commands**:
```bash
3cx-config who-can-dial                         # List all users with outbound routing
3cx-config who-can-dial --extension 108         # Show routing for specific extension
```

**Implementation**:
- Cross-reference users→departments→outbound rules→trunks
- Show trunk name, caller ID, and applicable rule

**Evidence**: `.sisyphus/evidence/task-3-who-can-dial.json`

---

### Wave 2: Routing Fixes (depends on T1, T2)

#### T4. Clean Broken Routes from Outbound Rules
**What to do**: Remove all Routes with TrunkId=-1 from outbound rules

**Current State**:
- SilkCrafts-out: Route 0 valid (Trunk 80), Routes 1-4 broken (TrunkId=-1)
- PoshTex-out: Route 0 valid (Trunk 56), Routes 1-4 broken (TrunkId=-1)
- SC-Out +1: Route 0 valid (Trunk 56), Routes 1-4 broken (TrunkId=-1)

**Fix**: Keep only Route 0, remove Routes 1-4

**Evidence**: `.sisyphus/evidence/task-4-clean-routes.json`

---

#### T5. Verify SC-Out +1 Configuration
**What to do**: Investigate and fix SC-Out +1 routing

**Current State**:
- GroupIds: [32, 33] (Operator group, Silk Crafts) — SilkCrafts departments
- Route 0: Trunk 56 (Flowroute-posh) — PoshTex trunk
- This routes SilkCrafts +1 calls through PoshTex trunk (wrong company)

**Options**:
1. **Fix routing**: Change TrunkId from 56 → 80 (Flowroute-SilkCrafts)
2. **Fix departments**: Change GroupIds from [32,33] → [29,30,34] (PoshTex departments)
3. **Delete rule**: If +1 prefix handling not needed

**Decision Required**: Ask user which option

**Evidence**: `.sisyphus/evidence/task-5-sc-out-fix.json`

---

#### T6. Verify Department Assignments
**What to do**: Ensure all users who need outbound access are in correct departments

**Current Observation**:
- Ext 108 (Ravi Shah) successfully dials via PoshTex-out
- But API shows PrimaryGroupId=28 (Everyone), not routing department
- 3CX v20 department membership may differ from PrimaryGroupId

**Investigation**:
- Use new `department-members` command to get full membership
- Cross-check with call history to verify actual routing

**Evidence**: `.sisyphus/evidence/task-6-dept-assignments.json`

---

### Wave 3: Final Verification

#### F1. Configuration Quality Review
Run all verification commands:
```bash
3cx-config system-status        # Trunks registered
3cx-config outbound-rules       # No TrunkId=-1
3cx-config who-can-dial         # All users mapped
3cx-config department-members   # Membership verified
```

**Evidence**: `.sisyphus/evidence/final-config-review.json`

---

## Commit Strategy

1. `feat(3cx-config): add department-members, outbound-update, who-can-dial commands`
2. `fix(3cx): clean broken routes from outbound rules`
3. `docs(3cx): document routing improvements`

---

## Open Questions for User

1. **SC-Out +1 routing**: Should +1 prefix calls route via PoshTex (Trunk 56) or SilkCrafts (Trunk 80)?
2. **Department naming**: Which users belong to PoshTex vs SilkCrafts companies?
3. **+1 prefix handling**: Is this rule still needed, or should it be deleted?

---

## Dependencies

- T1 → T6 (need department-members to verify assignments)
- T2 → T4, T5 (need outbound-update to clean routes)
- T4, T5 → F1 (need fixes done before verification)