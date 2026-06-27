---
phase: 02-targeted-fixes
verified: 2026-06-27T00:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: Targeted Fixes Verification Report

**Phase Goal:** All audit-mandated fixes are applied, dead code is removed, and the full quality-tool suite (ruff, pyright, pytest) passes cleanly.
**Verified:** 2026-06-27
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every finding tagged "fix" in the audit report is resolved in an atomic, reviewed commit | ✓ VERIFIED | All 13 "fix"-tagged findings from `01-code-health-audit/REPORT.md` (F-01, F-02, F-03, F-05, F-08, F-09, F-10, F-11, F-13, F-20, F-21, F-22, F-30 — disposition tally "13 fix") map to the 7 plans, each landed via atomic task commits documented in SUMMARYs. Reviewed: `02-REVIEW.md` (deep, 23 files), status `resolved`. |
| 2 | Dead code and unused bloat identified by the audit is absent from `src/` | ✓ VERIFIED | `grep -rn 'outputs_options\|scan_by_epoch\|gt_kinds_supported\|yaml_hash' src/ benchmarks/` → no matches (F-30). Review-found dead code also gone: `merge_kind_counts`/`PassDiagnostics.merge` removed from `diagnostics.py` (IN-01), `hash_file`/`import hashlib` removed from `trial_record.py` (IN-02); `_ = asdict` hack removed from `rescore.py` (F-11). |
| 3 | `SweepParameter` construction is a single source (`from_mapping`); `_parser_fn_repr` lives in one shared location, not two | ✓ VERIFIED | `SweepParameter.from_mapping` is the only def (`parameters.py:34`); all 3 call sites route through it — `parameters.py:88`, `tool/loader.py:191`, `geodispbench3d_iof3d/factory.py:75`. `parser_fn_repr` has exactly one def (`trial_record.py:69`, in `__all__`), imported by `runner.py:41` and `rescore.py:49`; both former local defs gone. |
| 4 | `ruff`, `pyright`, and the full `pytest` suite (core, iof3d, f2s3) pass after every fix lands | ✓ VERIFIED | `pytest -p no:cov` → **83 passed, 0 failed, 0 skipped** (core 79 / iof3d 2 / f2s3 2). `ruff check .` → All checks passed. `ruff format --check .` → 57 files already formatted. `pyright_gate.py` → "PASS: no new pyright errors above baseline" (exit 0). See note below on pyright gate semantics. |

**Score:** 4/4 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/core/test_runner.py` | F-20 characterization net | ✓ VERIFIED | Present; part of the 83-passing suite. |
| `tests/core/test_store.py` | F-21 store tests | ✓ VERIFIED | Present; in suite. |
| `tests/core/test_evaluation.py` | F-22 failure-path tests | ✓ VERIFIED | Present; in suite. |
| `tests/core/test_parameters.py` | F-02 from_mapping tests | ✓ VERIFIED | Present; in suite. |
| `src/geodispbench3d/diagnostics.py` | F-08 PassDiagnostics counter | ✓ VERIFIED | Present; threaded through sweep/rescore/analyze; dead `merge` API removed (IN-01). |
| `pyright_gate.py` + `pyright-baseline.json` | Baseline-diff gate | ✓ VERIFIED | Present; gate exits 0 against the recorded 21-error floor. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `runner.py` / `rescore.py` | `trial_record.parser_fn_repr` | shared import (F-03) | ✓ WIRED | Single symbol imported by both; cache-key byte-identity locked by characterization test. |
| `tool/loader.py`, `parameters.py`, `iof3d/factory.py` | `SweepParameter.from_mapping` | classmethod (F-02) | ✓ WIRED | All 3 sites call `from_mapping`; `_coerce_hparam` removed from factory. |
| `cli._cmd_sweep` + `runner.run_with_suite` | `ExecutionConfig.ensure_supported()` | guard call (F-30) | ✓ WIRED | Called at `cli.py:139` and `runner.py:237` — bypass-proof for both CLI and programmatic entry. |
| JSON readers | `on_non_fatal` + closed except set (F-08/CR-01) | fail-soft counting | ✓ WIRED | `load_trial_record` / `read_prediction` catch `(OSError, json.JSONDecodeError, UnicodeDecodeError)`; `_surface_finite_case_signal` now takes `diagnostics` and records `"trial_summary"` (WR-01). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FIX-01 | 02-01/02/03/05/06 | "fix"-tagged findings resolved as atomic reviewed changes | ✓ SATISFIED | F-01/F-05/F-08/F-09/F-13 + test nets landed; commits atomic; reviewed. |
| FIX-02 | 02-06/07 | Dead code/unused bloat removed | ✓ SATISFIED | F-10/F-11/F-30 + IN-01/IN-02; greps clean; vulture no longer reports the four fields. |
| FIX-03 | 02-04/07 | Flagged duplication consolidated to single source | ✓ SATISFIED | `from_mapping` (F-02) + `parser_fn_repr` (F-03) single-sourced. |
| FIX-04 | 02-07 (terminal gate) | Full suite + ruff + pyright pass after fixes | ✓ SATISFIED | 83 passed / ruff clean / pyright gate exit 0. |

All four IDs are marked Complete in `.planning/REQUIREMENTS.md` traceability table. No orphaned requirements for this phase.

### Anti-Patterns Found

None. No debt markers (`TODO`/`FIXME`/`XXX`) introduced by the changeset; ruff is clean; the 5 review findings (CR-01 blocker + 2 warnings + 2 infos) were all fixed before verification (commits `06d95c7`, `ec7cbeb`, `4eb1754`, `9a7f0fe`, all present in git history).

### Note on Criterion 4 — pyright gate semantics

Criterion 4 says "pyright … pass without errors." Phase 2 deliberately and with documented rationale (D-08/D-11/D-12, `PYRIGHT-BASELINE.md`) adopted a **baseline-diff** gate, not a zero-error gate: pyright passes when no NEW errors appear above the recorded 21-error floor. The gate reports exit 0 (no new errors), and three plans (02-04, 02-07) registered net **reductions** (21→19). The 21 baseline errors are pre-existing and concentrated in deferred/untouched surfaces (`dashboard/app.py`, the iof3d adapter — F-12/F-15, both dispositioned `defer`/v2), not on any Phase-2-owned touched line. This is an intentional, in-repo-documented gate definition rather than incomplete work, so Criterion 4 is VERIFIED under the phase's ratified contract. Flagged here for visibility, not as a gap.

### Human Verification Required

None.

### Gaps Summary

No gaps. The phase goal is achieved in the codebase: all 13 audit "fix"-tagged findings plus the 5 follow-up review findings are resolved via atomic, reviewed commits; dead code and unused bloat are absent from `src/`; `SweepParameter` and `parser_fn_repr` are each single-sourced; and the full quality suite (ruff, ruff-format, pyright baseline-diff gate, pytest core+iof3d+f2s3 = 83 passed / 0 failed / 0 skipped) is green.

---

_Verified: 2026-06-27_
_Verifier: Claude (gsd-verifier)_
