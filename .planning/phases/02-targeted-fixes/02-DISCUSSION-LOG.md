# Phase 2: Targeted Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-27
**Phase:** 2-targeted-fixes
**Areas discussed:** Scope ratification, F-08 except boundary, Test scope & order, Commit/wave batching, F-30 fields, F-22 depth

---

## Scope ratification (D-05 gate)

| Option | Description | Selected |
|--------|-------------|----------|
| All 13 as recommended | Accept the audit's full fix set unchanged; treat F-05's behavior change as in-scope hardening | ✓ |
| All 13, but F-05 careful | Keep all 13 but treat F-05 as surface-the-failure only, not re-defining aggregation | |
| Move F-05 to defer | Pull F-05 out as too behaviorally risky for this milestone | |

**User's choice:** All 13 as recommended
**Notes:** Full fix set ratified (F-01,02,03,05,08,09,10,11,13,20,21,22,30). F-05 included with its audit fix sketch (surface per-trial case coverage / finite-case count; penalize/threshold acceptable stronger options).

---

## F-08 except boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Audit's narrow+count+warn | Narrow to expected types, debug→warning, per-pass failure counter surfaced in CLI summaries; keep fail-soft | ✓ |
| Narrow+warn, skip counter | Narrow + warn but no aggregate counter plumbing | |
| Counter is its own concern | Narrow+warn now; defer the aggregate summary line to Phase 3 | |

**User's choice:** Audit's narrow+count+warn
**Notes:** Full reconciliation with CONVENTIONS best-effort pattern — make degradation countable and visible without making side-effect failures fatal. The "N non-fatal failures" summary line is wanted in this phase, not deferred.

---

## Test scope & order

**Q1 — ordering relative to runner.py refactors:**

| Option | Description | Selected |
|--------|-------------|----------|
| Tests first (safety net) | F-20 characterization tests before the F-01/F-05/F-08/F-13 refactors | ✓ |
| Refactor first, test after | Apply refactors, then backfill to coverage targets | |
| Mixed by finding | Test-first only for behavioral (F-05/F-08), refactor-first for safe ones | |

**Q2 — bar for "done":**

| Option | Description | Selected |
|--------|-------------|----------|
| Behavior-anchored | Target the specific named untested behaviors; success = paths exercised, not a % | |
| Coverage % gate | Explicit numeric coverage targets gating the phase | |
| Both | Behavior-anchored primary + coverage floor as secondary guard | ✓ |

**User's choice:** Tests first; bar = Both
**Notes:** Tests-first chosen specifically because runner.py is at 13% coverage and the behavioral refactors land there. Floor numbers left to planner, anchored to no-regression + meaningful lift on runner.py/store.py/evaluation.py.

---

## Commit/wave batching

**Q1 — commit granularity:**

| Option | Description | Selected |
|--------|-------------|----------|
| One commit per finding | ~13 ID-referencing commits, 1:1 with the audit table | |
| Grouped by theme | Cluster related findings into fewer commits | |
| You decide | Planner chooses grain per finding, keeping the suite green | ✓ |

**Q2 — green gate frequency:**

| Option | Description | Selected |
|--------|-------------|----------|
| Every commit green | ruff+pyright+full pytest after every commit | |
| Every wave green | Quality gate at each wave boundary; intermediate commits may be transiently red | ✓ |

**User's choice:** Commit grain = You decide; Green gate = Every wave
**Notes:** Commits should still reference stable finding IDs for traceability. Wave-boundary gate keeps iteration fast within a wave.

---

## F-30 fields

| Option | Description | Selected |
|--------|-------------|----------|
| Guard, don't delete | Keep parallel_trials/override_tool_mode behind a not-implemented guard; delete the truly-dead fields | ✓ |
| Delete all dead fields | Remove every unread field including the forward-compat ones | |
| You decide per field | Planner triages each field | |

**User's choice:** Guard, don't delete
**Notes:** Rule = guard if it maps to a tracked v2 requirement (EXEC-01 parallel sweeps), delete otherwise. Delete: outputs_options, scan_by_epoch, gt_kinds_supported, yaml_hash.

---

## F-22 depth

| Option | Description | Selected |
|--------|-------------|----------|
| Direct for behavioral, indirect OK else | Direct tests where there's real failure-path logic; accept indirect for thin pass-throughs | ✓ |
| Direct tests for all 3 | Each indirectly-covered module gets its own test module | |
| You decide | Planner judges per module | |

**User's choice:** Direct for behavioral, indirect OK else
**Notes:** Consistent with the behavior-anchored + floor decision from the test-scope area.

---

## Claude's Discretion

- Commit granularity per finding (atomic vs grouped), subject to wave-green gate.
- Mechanical findings F-09 (datetime.utcnow), F-10 (import hoist), F-11 (dead-import) — exact form.
- F-01 breadth: whether to sweep type:ignore removals beyond the suite-consumer cluster.
- F-05 escalation strength (count-only vs penalize/threshold).
- Coverage floor numbers (F-20/21/22).

## Deferred Ideas

None — discussion stayed within phase scope. The audit's defer/accept/route-forward findings are recorded in REPORT.md and excluded by the Phase 2 scope statement, not surfaced as new deferred ideas here.
