---
phase: 01-code-health-audit
plan: 02
subsystem: audit-report
tags: [audit, code-health, report, findings, disposition]
status: complete
dependency_graph:
  requires:
    - 01-01 (EVIDENCE.md + audit-evidence/ mechanical detector captures)
    - .planning/codebase/CONCERNS.md (re-verified, now superseded)
  provides:
    - REPORT.md (authoritative dispositioned findings record; Phase 2 input contract)
    - 32 stable finding IDs (F-01..F-32) for Phase 2/3/4/5 to reference
  affects:
    - Phase 2 (fix-scoped from REPORT findings)
    - Phase 3 (route-forward CLI findings)
    - Phase 4 (route-forward licensing/packaging findings)
    - Phase 5 (route-forward CI findings)
tech_stack:
  added: []
  patterns:
    - reasoned manual file:line review as audit spine (D-08)
    - detectors as corroboration only (EVIDENCE.md cross-refs)
key_files:
  created:
    - .planning/phases/01-code-health-audit/REPORT.md
  modified: []
decisions:
  - "evaluation.py is indirectly covered (~80%), not untested — corrected CONCERNS via F-22 (superseded)"
  - "Surfaced no-subprocess-timeout as new finding F-32 during AUDIT-03 review"
  - "2 Blocker findings (Private classifier F-26, README/LICENSE mismatch F-27) gate public publish; both route-forward to Phase 4"
metrics:
  tasks: 2
  files_created: 1
  findings: 32
  completed: 2026-06-26
status_note: read-only audit — zero src/ or pyproject.toml changes
---

# Phase 1 Plan 2: Code-Health Audit Report Summary

Produced the single Phase 1 deliverable — `REPORT.md`, a greppable-by-ID audit of 32
findings (F-01..F-32) driven by reasoned file:line reading of the whole repo, each
severity-classified (Blocker/Major/Minor) and disposition-recommended
(fix/defer/accept/route-forward), superseding CONCERNS.md via a machine-checkable
traceability appendix.

## What was built

- **`.planning/phases/01-code-health-audit/REPORT.md`** — summary findings table over
  32 stable-ID detail sections, plus an AUDIT-03 CLI-surface risk section and a CONCERNS
  Traceability appendix.
  - **AUDIT-01** (bloat / dead code / duplication / bugs): F-04, F-05, F-07, F-08, F-09,
    F-10, F-11, F-17, F-30 (+ coverage F-20..F-23).
  - **AUDIT-02** (three named anti-patterns, each a finding with a disposition): F-01
    (untyped `SuiteConfig`), F-02 (duplicated `SweepParameter` coercion x3), F-03
    (duplicated `_parser_fn_repr`).
  - **AUDIT-03** (focused per-surface risk): dedicated section for `cli.py`,
    `CliToolAdapter`, and the F2S3 `conda run` surface — findings F-06, F-07, F-16, F-32.
  - **AUDIT-04** (severity + disposition on every finding): all 32 carry both; the table
    and detail sections are 1:1.
  - **D-07 design-sensibility** (first-class category): the four named seeds formalized as
    F-12 (220-line `build_app_config_from_parameters`), F-13 (provenance `getattr` chain),
    F-11 (`_ = asdict` hack), F-07 (stdout heuristic).
  - **D-10**: every CONCERNS.md finding re-verified and mapped in the traceability appendix.

## Key findings (highlights)

- **2 Blockers** gate the public PyPI publish: F-26 (`Private :: Do Not Upload`
  classifier) and F-27 (README "Proprietary" vs BSD-3-Clause `LICENSE`) — both route to Phase 4.
- **Silent-degradation cluster** (F-05 cross-case mean hides failures, F-07 stdout
  heuristic, F-08 broad-except swallowing) is the highest-value correctness theme.
- **iof3D adapter** (F-12/F-15/F-23) is the largest, most coupled, CI-untestable surface;
  its fate is gated on Phase 4 publishability.

## Deviations from Plan

### Auto-added finding (Rule 2 — completeness)

**1. [Rule 2 - Missing critical finding] F-32 — `CliToolAdapter` has no subprocess timeout**
- **Found during:** Task 2, AUDIT-03 `CliToolAdapter` surface review.
- **Issue:** `subprocess.run` at `cli_adapter.py:107-114` passes no `timeout=`; a hung
  tool stalls the entire sweep with no watchdog. Not in CONCERNS.md.
- **Resolution:** Recorded as finding F-32 (Major, route-forward → Phase 3), keeping the
  table/section count at 32:32. No code change (read-only plan).

### Re-verification correction

**2. [D-10 re-verify] CONCERNS "evaluation.py untested" softened**
- CONCERNS labeled `evaluation.py` untested; measured coverage is ~80% (indirectly
  exercised). Mapped as `superseded` in the traceability appendix; F-22 re-scopes the
  real gap to the failure paths (`:89-93`, `:177-179`).

Otherwise the plan executed as written.

## Notes for downstream phases

- **Phase 2** consumes the `fix`-disposed findings (13 of them) as atomic fix-commit units.
- **Dispositions are recommendations** (D-05) — Phase 2 discussion ratifies the final set.
- **Coverage honesty:** plugin-package coverage cited in REPORT was measured in the iof3D
  dev env where the suites ran; CI/lean envs self-skip and would read 0%/low (preserved
  as an explicit note in the coverage section).

## Known Stubs

None. REPORT.md is complete prose + tables; no placeholder or TODO stubs.

## Self-Check

PASSED — REPORT.md and 01-02-SUMMARY.md exist on disk; both task commits
(5842a7b, 0ede06e) present in git history; read-only invariant intact (no src/ or
pyproject.toml modification).
