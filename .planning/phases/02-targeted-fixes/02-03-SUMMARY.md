---
phase: 02-targeted-fixes
plan: 03
subsystem: testing
tags: [pyright, typing, ax, sweep, observability, dataclass, provenance]

# Dependency graph
requires:
  - phase: 02-01
    provides: F-20 characterization net (FakeAxClient + StubAdapter) for runner.py
  - phase: 02-02
    provides: pyright baseline-diff gate (pyright_gate.py) + PYRIGHT-BASELINE.md floor
provides:
  - SuiteConfig-typed runner consumers (run_with_suite, _evaluate_across_cases) and cli.py command handlers; zero attr-defined ignores in cli.py
  - Collapsed provenance lookup to the single typed access suite.tool.source_path (F-13 folded into F-01)
  - SweepRunSummary return contract from run_with_suite (best_trial + objective finite/total)
  - Objective-specific finite-case signal (objective_cases_finite/total) surfaced via per-trial log line + dedicated trial-level summary artifact + SweepRunSummary/CLI line, OFF the Ax objective payload
  - trial_summary_path / write_trial_summary helpers in trial_record.py (UTC-aware recorded_at)
affects: [02-05, 02-07, F-08, non_fatal_failures]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TYPE_CHECKING import for cross-package annotations to avoid sweep/__init__ partial-init cycles under `from __future__ import annotations`"
    - "Observability signals surfaced OFF the Ax objective payload (log line + durable artifact + typed return), never injected into complete_trial(raw_data=...)"
    - "Fail-soft durable artifact writes: a trial-level summary write can never fail a trial"

key-files:
  created: []
  modified:
    - src/geodispbench3d/sweep/runner.py
    - src/geodispbench3d/sweep/trial_record.py
    - src/geodispbench3d/cli.py
    - tests/core/test_runner.py

key-decisions:
  - "recorded_at is stamped inside write_trial_summary (datetime.now(UTC)) rather than at a new runner site, keeping timestamp generation in the I/O module and avoiding a new deprecated-utcnow caller"
  - "_surface_finite_case_signal extracted as a helper so the per-trial log + artifact write live in one fail-soft place (the site 02-05 extends with non_fatal_failures)"
  - "SuiteConfig annotations use TYPE_CHECKING imports (cycle-safe; both files already use future annotations) instead of a runtime import that would re-enter sweep/__init__"

patterns-established:
  - "Finite-case visibility: objective-specific finite/total counted AFTER aggregation for self._objective_name, never a metric-agnostic count"
  - "SweepRunSummary is the extension point for sweep outcome metadata (02-05 appends non_fatal_failures additively)"

requirements-completed: [FIX-01]

coverage:
  - id: D1
    description: "run_with_suite/_evaluate_across_cases/_cmd_sweep/_cmd_rescore typed SuiteConfig; 0 attr-defined ignores in cli.py; no NEW pyright error above the 02-02 baseline (F-01)"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "conda run -n iof3d_cosicorr3d-dev312 python .planning/phases/02-targeted-fixes/pyright_gate.py (exit 0)"
        status: pass
      - kind: integration
        ref: "tests/core (51 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Provenance lookup collapsed to the direct typed access suite.tool.source_path; .raw/__source_path__ fallback removed; behavior preserved (F-13)"
    requirement: FIX-01
    verification:
      - kind: integration
        ref: "tests/core/test_runner.py + tests/core/test_rescore.py (12 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Objective-specific objective_cases_finite/total surfaced via per-trial log line + dedicated trial-level artifact + SweepRunSummary/CLI line, ABSENT from complete_trial(raw_data=...), NaN-ignoring mean math unchanged (F-05/D-02)"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_f05_partial_failure_surfaced_off_ax_objective"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_multi_case_partial_failure_ignores_nan_survivor_mean (mean unchanged + finite<total)"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_multi_case_aggregation_means_finite_values (all-finite mean == pre-F-05 0.5)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 03: Runner typing + finite-case surfacing Summary

**Retyped the runner/CLI suite-consumer cluster to SuiteConfig (15 attr-defined ignores gone, provenance chain collapsed to suite.tool.source_path), and surfaced objective-specific partial-case failure via a SweepRunSummary return + per-trial log line + dedicated trial-level JSON artifact — all off the Ax objective payload, mean math byte-for-byte unchanged.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-27T08:32Z
- **Completed:** 2026-06-27T08:44Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- **F-01:** `run_with_suite`, `_evaluate_across_cases`, `_cmd_sweep`, and `_cmd_rescore` are now typed `SuiteConfig` (was `Any`/`object`); all 15 `# type: ignore[attr-defined]` markers removed from cli.py; the 3 Ax-import ignores in runner.py retained. Pyright baseline-diff gate reports no NEW error.
- **F-13:** The 4-deep `getattr-or-getattr-raw-lambda` provenance lookup collapsed to the single typed `suite.tool.source_path` (the `.raw`/`__source_path__` tail was dead now that `source_path` is always populated by `load_tool_config`). Behavior-preserving.
- **F-05:** `run_with_suite` now returns a frozen `SweepRunSummary(best_trial, objective_name, objective_cases_finite, objective_cases_total)`. The objective-specific finite/total (counted for `self._objective_name` after aggregation) is surfaced three ways off the Ax objective: a per-trial log line (warning when `finite < total`, else info), a dedicated trial-level artifact at `<run_dir_root>/trial_summaries/trial_<i>.json`, and the `SweepRunSummary`/CLI summary line. The Ax `complete_trial(raw_data=...)` dict is unchanged and the NaN-ignoring mean math is byte-for-byte identical.

## Task Commits

Each task was committed atomically:

1. **Task 1: F-01 retype suite-consumer cluster to SuiteConfig** - `b496b78` (fix)
2. **Task 2: F-13 collapse provenance chain to suite.tool.source_path** - `04e0cc9` (refactor)
3. **Task 3: F-05 objective-specific finite-case signal** - `4df7fbe` (feat)

**Pre-wave rollback tag:** `wave1-pre-02-03` (at `e540edd`)

## Files Created/Modified
- `src/geodispbench3d/sweep/runner.py` - Typed `suite` params; collapsed provenance lookup; added `SweepRunSummary` dataclass; `_evaluate_across_cases` returns `(aggregated, finite, total)`; new `_surface_finite_case_signal` helper (log + fail-soft artifact write); `run_with_suite` accumulates and returns the across-trial aggregate; `__all__` extended.
- `src/geodispbench3d/sweep/trial_record.py` - Added `trial_summary_path` + `write_trial_summary` (atomic tmp+replace, UTC-aware `recorded_at` via `datetime.now(UTC)`); `__all__` extended; imported `UTC`.
- `src/geodispbench3d/cli.py` - Retyped `_cmd_sweep`/`_cmd_rescore` `suite` param to `SuiteConfig` (TYPE_CHECKING import); removed 15 attr-defined ignores; `_cmd_sweep` reads `result.best_trial` and logs the finite-case summary line.
- `tests/core/test_runner.py` - Updated the 3 direct `_evaluate_across_cases` callers to unpack the tuple and assert finite/total; updated `run_with_suite` caller for the `SweepRunSummary` return; consciously updated the partial-failure regression anchor (mean unchanged + `finite == total - 1`); added `test_f05_partial_failure_surfaced_off_ax_objective` covering the log line, the artifact JSON, the SweepRunSummary aggregate, and raw_data absence.

## Decisions Made
- **TYPE_CHECKING imports for `SuiteConfig`:** A runtime `from geodispbench3d.suite.loader import SuiteConfig` in runner.py risks a `sweep/__init__` partial-init cycle (suite.loader → tool.loader → sweep.parameters re-enters the package mid-init). Both files already use `from __future__ import annotations`, so a `TYPE_CHECKING` import fully satisfies pyright while eliminating the cycle risk. Applied symmetrically in cli.py.
- **`recorded_at` stamped in `write_trial_summary`:** Keeps timestamp generation in the I/O helper (one offset-aware `datetime.now(UTC)` site) rather than adding a new timestamp caller in the runner; honors the plan's "do NOT introduce a new utcnow site" note.
- **Extracted `_surface_finite_case_signal`:** Consolidates the log line + fail-soft artifact write into a single helper, which is exactly the site 02-05 will extend with the non-fatal failure counter.

## Deviations from Plan

None - plan executed exactly as written. The two minor structuring choices (extracting `_surface_finite_case_signal`; stamping `recorded_at` inside `write_trial_summary` rather than in the runner payload) are presentation-only and preserve every specified behavior, key, and artifact shape.

## Issues Encountered
- **Env pytest path:** bare `pytest` (per AGENTS.md/plan verify commands) resolved to the base conda env (Python 3.13, no editable install) and failed collection with `ModuleNotFoundError: geodispbench3d`. Switched all test invocations to `conda run -n iof3d_cosicorr3d-dev312 python -m pytest`, consistent with the 02-01 finding about pytest path resolution in this env. The `pyright_gate.py` command runs correctly as written.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave-1 gate satisfied: `ruff check .` + `ruff format --check .` clean (55 files), full `pytest` 56 passed / 0 skipped, `pyright_gate.py` exit 0 (no NEW errors above the 02-02 baseline).
- `SweepRunSummary` is in place for 02-05 to extend additively with `non_fatal_failures`; the fail-soft artifact-write site (`_surface_finite_case_signal`) is the documented extension point for the non-fatal counter (F-08).
- Files were disjoint from 02-04 (F-02), so the parallel wave-1 plan is unaffected.

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*

## Self-Check: PASSED

- Files verified present: runner.py, trial_record.py, cli.py, tests/core/test_runner.py, 02-03-SUMMARY.md
- Commits verified in git log: b496b78 (F-01), 04e0cc9 (F-13), 4df7fbe (F-05)
- Wave-1 gate: pyright_gate.py exit 0; ruff check/format clean; full pytest 56 passed / 0 skipped
