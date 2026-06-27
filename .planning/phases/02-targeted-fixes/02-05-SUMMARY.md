---
phase: 02-targeted-fixes
plan: 05
subsystem: observability
tags: [fail-soft, diagnostics, exceptions, logging, dataclass, cli, F-08]

# Dependency graph
requires:
  - phase: 02-03
    provides: SweepRunSummary return contract (extended additively here with non_fatal_failures)
  - phase: 02-02
    provides: pyright baseline-diff gate (pyright_gate.py)
  - phase: 02-01
    provides: F-20 characterization net (FakeAxClient + StubAdapter) for runner.py
provides:
  - PassDiagnostics typed counter model (geodispbench3d/diagnostics.py) with add()/merge()
  - non_fatal_failures field on EvaluationOutput, SweepRunSummary, _RescoreOutcome, RescoreSummary, AnalysisSummary
  - on_non_fatal keyword-only callback on read_prediction + load_trial_record (counts genuine read failures, not absent/empty)
  - 8 IO/serialization broad-except sites narrowed to re-derived closed sets; 4 plugin-callable boundaries documented-broad
  - Aggregate "N non-fatal failures" CLI summary line in sweep / rescore / analyze
affects: [02-07, F-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Typed PassDiagnostics counter threaded through a pass; every fail-soft site records into it; CLI surfaces the aggregate"
    - "Low-level readers carry an optional on_non_fatal callback so a swallowed read failure is countable without changing the None/{} fallback"
    - "_invoke_metric returns (value, raised) so a metric that raised is distinguishable from one that returned None"
    - "Arbitrary plugin-callable boundaries stay broad with a documented reason; only IO/serialization sites narrow to closed exception sets"

key-files:
  created:
    - src/geodispbench3d/diagnostics.py
  modified:
    - src/geodispbench3d/sweep/evaluation.py
    - src/geodispbench3d/sweep/runner.py
    - src/geodispbench3d/sweep/rescore.py
    - src/geodispbench3d/results/predictions_cache.py
    - src/geodispbench3d/sweep/trial_record.py
    - src/geodispbench3d/analysis/runner.py
    - src/geodispbench3d/cli.py
    - tests/core/test_runner.py
    - tests/core/test_rescore.py
    - tests/core/test_analyze.py
    - tests/core/test_evaluation.py

key-decisions:
  - "rescore append-site narrowed to (OSError, AttributeError, TypeError) — re-derived by tracing the callee (a malformed-but-valid summary whose rescore_log is a non-list truthy yields AttributeError on .append); the original plan's (OSError, JSONDecodeError) would NOT have preserved fail-soft"
  - "_invoke_metric changed to return (value, raised) rather than counting via a side channel — keeps the counting explicit and lets a legitimate None stay uncounted"
  - "diagnostics threaded as a keyword-only default-None param on _evaluate_across_cases so the 4 existing direct test callers keep working unchanged while run_with_suite passes the sweep-wide counter"
  - "_record_run_hash returns bool (ok) so the run-hash append failure counts at its caller without giving the method a diagnostics dependency"

patterns-established:
  - "PassDiagnostics is the per-pass non-fatal counter; SweepRunSummary/RescoreSummary/AnalysisSummary carry the rolled-up total for the CLI"

requirements-completed: [FIX-01]

coverage:
  - id: D1
    description: "PassDiagnostics typed model + non_fatal_failures on all five output/summary types; 8 IO sites narrowed, 4 plugin boundaries documented-broad; touched debug logs promoted to warning (F-08)"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/core/test_evaluation.py (parser-raise / metric-raise / non-scalar-skip counted; legitimate None not counted)"
        status: pass
      - kind: other
        ref: "grep: except Exception count==2 in evaluation.py; rescore append set (OSError, AttributeError, TypeError)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Counter threaded through sweep/rescore/analyze; readers carry on_non_fatal; fail-soft control flow preserved (no site becomes fatal)"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_f08_cache_write_failure_counted_and_run_completes (monkeypatched write_prediction -> OSError -> non_fatal_failures==1, run completes)"
        status: pass
      - kind: unit
        ref: "tests/core/test_rescore.py#test_rescore_malformed_rescore_log_is_counted_fail_soft (non-list rescore_log -> AttributeError counted fail-soft, run still scored)"
        status: pass
      - kind: unit
        ref: "tests/core/test_analyze.py#test_analyze_corrupt_prediction_counted_fail_soft (corrupt JSON read -> counted, readable ones still score)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Aggregate 'N non-fatal failures' line emitted by each CLI summary (sweep/rescore/analyze), each asserted by a direct caplog test (F-08)"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_cli_sweep_emits_non_fatal_failures_line"
        status: pass
      - kind: unit
        ref: "tests/core/test_rescore.py#test_cli_rescore_emits_non_fatal_failures_line"
        status: pass
      - kind: unit
        ref: "tests/core/test_analyze.py#test_cli_analyze_emits_non_fatal_failures_line"
        status: pass
      - kind: other
        ref: "conda run -n iof3d_cosicorr3d-dev312 python .planning/phases/02-targeted-fixes/pyright_gate.py (exit 0)"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 05: Fail-soft diagnostics (F-08) Summary

**Turned silent fail-soft degradation into "swallowed but counted and warned": a typed `PassDiagnostics` counter is threaded through the sweep / rescore / analyze passes, the 8 IO/serialization broad-except sites are narrowed to re-derived closed exception sets (the 4 arbitrary plugin-callable boundaries stay broad with a documented reason), low-level readers gained an `on_non_fatal` callback, touched debug logs became warnings, and each CLI summary now prints an aggregate "N non-fatal failures" line — all while preserving fail-soft control flow byte-for-byte.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-27T08:56Z
- **Completed:** 2026-06-27T09:11Z
- **Tasks:** 3
- **Files modified:** 10 (+1 created)

## Accomplishments

- **PassDiagnostics (new):** `geodispbench3d/diagnostics.py` defines a mutable `PassDiagnostics(non_fatal_failures, by_kind)` with `add(kind, n=1)` (no-op for n<=0) and `merge(other)`; `__all__` declared. It is an observability counter, never a control-flow signal.
- **Narrowing (F-08 part 1):** the 8 IO/serialization sites now catch re-derived closed sets — `runner.py` mkdir→`OSError`, provenance-stamp→`(OSError, TypeError)`, cache-write→`(OSError, TypeError)`, run-hash-append→`OSError`; `rescore.py` cache-write→`(OSError, TypeError)`, append→`(OSError, AttributeError, TypeError)`; `predictions_cache.read_prediction`→`(OSError, json.JSONDecodeError)`; `trial_record.load_trial_record`→`(OSError, json.JSONDecodeError)`. The 4 arbitrary-callable boundaries (`evaluation.py` parser + metric, `rescore.py` outer `evaluate_trial`, `analysis/runner.py` analyze `evaluate_trial`) stay `except Exception` with a one-line documented reason. The two Ax trial-failure handlers (`log_trial_failure`) were left untouched.
- **Visibility (F-08 part 2):** every touched swallowing site's `logger.debug` became `logger.warning` (lazy %-style). The plugin boundaries already logged at `exception` level (≥ warning) and were left.
- **Counter threading (F-08 part 3):** `non_fatal_failures` is now a field on `EvaluationOutput`, `SweepRunSummary` (additive, after `objective_cases_total`), `_RescoreOutcome`, `RescoreSummary`, and `AnalysisSummary`. `evaluate_trial` counts parser-raise / metric-raise / non-scalar-skip (with `_invoke_metric` now returning `(value, raised)`). The sweep holds one `PassDiagnostics` recording `evaluation` / `provenance_stamp` / `prediction_cache` / `run_hash`; rescore folds per-outcome counts plus suite-level corrupt reads (`load_trial_record` + cache-read `on_non_fatal`); analyze counts corrupt prediction reads plus evaluation skips.
- **Reader callbacks:** `read_prediction` and `load_trial_record` gained a keyword-only `on_non_fatal: Callable[[Exception], None] | None = None`, invoked only on a genuine read failure (absent file / cache miss stays uncounted). Default `None` keeps `update_trial_record` / `append_rescore_entry` / `read_provenance` behavior-identical.
- **CLI lines:** `_cmd_sweep`, `_cmd_rescore`, and `_cmd_analyze` each log an aggregate `"%d non-fatal failures (swallowed, fail-soft) during the <pass>"` line beside the existing summary, each asserted by a direct caplog test.

## Task Commits

Each task was committed atomically:

1. **Task 1: PassDiagnostics + narrowed excepts + reader callbacks** — `6150cd4` (fix)
2. **Task 2: thread PassDiagnostics through every pass; non_fatal_failures fields** — `22ccafa` (feat)
3. **Task 3: aggregate "N non-fatal failures" CLI line + direct CLI tests** — `2513b91` (feat)

**Pre-wave rollback tag:** `wave2-pre-02-05` (at `0d7608e`)

## Files Created/Modified

- `src/geodispbench3d/diagnostics.py` — **new** `PassDiagnostics` typed counter (`add`/`merge`) + `merge_kind_counts` helper; `__all__` declared.
- `src/geodispbench3d/sweep/evaluation.py` — `EvaluationOutput.non_fatal_failures`; `evaluate_trial` counts parser/metric/non-scalar swallows; `_invoke_metric` returns `(value, raised)`; both plugin boundaries documented-broad.
- `src/geodispbench3d/sweep/runner.py` — imports `PassDiagnostics`; `SweepRunSummary.non_fatal_failures` (additive); `run_with_suite` holds one `PassDiagnostics` and threads it into `_evaluate_across_cases` (keyword-only, default-None for direct callers); narrowed provenance/cache/mkdir/run-hash sites; `_record_run_hash` now returns `bool`.
- `src/geodispbench3d/sweep/rescore.py` — imports `PassDiagnostics`; `_RescoreOutcome.non_fatal_failures` + `RescoreSummary.non_fatal_failures`; narrowed cache-write + append sites; outer `evaluate_trial` documented-broad; `_rescore_one` accumulates per-outcome counts and forwards an `on_cache_read_failure` callback to `_try_cache_lookup`; suite-level `load_trial_record` carries an `on_non_fatal`; aggregate folded into the summary + log line.
- `src/geodispbench3d/results/predictions_cache.py` — `read_prediction` narrowed to `(OSError, json.JSONDecodeError)` + keyword-only `on_non_fatal`.
- `src/geodispbench3d/sweep/trial_record.py` — `load_trial_record` narrowed + keyword-only `on_non_fatal` (absent-file early return never calls it).
- `src/geodispbench3d/analysis/runner.py` — imports `PassDiagnostics`; `AnalysisSummary.non_fatal_failures`; analyze `evaluate_trial` documented-broad and counted; `read_prediction` `on_non_fatal`; aggregate folded into the summary + log line.
- `src/geodispbench3d/cli.py` — aggregate "N non-fatal failures" line in `_cmd_sweep` / `_cmd_rescore` / `_cmd_analyze`.
- `tests/core/test_runner.py` — sweep cache-write-OSError counter test (fail-soft, run completes), clean-sweep zero-failures test, and a direct `_cmd_sweep` CLI-line test (fake `AxSweepRunner`).
- `tests/core/test_rescore.py` — clean-pass zero-failures test, malformed-`rescore_log` (dict → AttributeError) fail-soft counter test, and a direct `_cmd_rescore` CLI-line test (end-to-end).
- `tests/core/test_analyze.py` — corrupt-prediction fail-soft counter test and a direct `_cmd_analyze` CLI-line test (end-to-end).
- `tests/core/test_evaluation.py` — `non_fatal_failures` assertions added to the existing parser-raise / metric-raise / non-scalar-skip / legitimate-None paths (the F-22 anchor whose docstring already anticipated this field).

## Decisions Made

- **Corrected rescore append exception set:** the plan's `key_links` (codex HIGH) flagged that the original `(OSError, json.JSONDecodeError)` would not preserve fail-soft, because `load_trial_record` already swallows `JSONDecodeError`, so the live failure mode for `append_rescore_entry` is an `AttributeError` from `.append` on a non-list `rescore_log`. Implemented `(OSError, AttributeError, TypeError)` and pinned it with `test_rescore_malformed_rescore_log_is_counted_fail_soft`.
- **`_invoke_metric` returns `(value, raised)`:** the cleanest way to count a metric that *raised* without conflating it with a metric that legitimately returned `None` (the latter must stay uncounted). Verified by the two evaluation tests.
- **`diagnostics` as keyword-only default-None on `_evaluate_across_cases`:** keeps the 4 existing direct test callers (which pass 6 positional args) working unchanged while `run_with_suite` passes the sweep-wide counter — no churn to the F-20 net beyond the new assertions.
- **`_record_run_hash` returns `bool`:** the run-hash append lives in a helper also used by `_default_executor`; returning "ok" lets the caller count the failure without giving the helper a diagnostics dependency.

## Deviations from Plan

- **[Rule 2 — coverage] Extended `tests/core/test_evaluation.py`** with `non_fatal_failures` assertions, even though Task 2's `<files>` list named only `test_runner.py` and `test_rescore.py`. `test_evaluation.py` is the direct unit test of `EvaluationOutput` and its own docstring already anticipated this field ("which adds a `non_fatal_failures` count to `EvaluationOutput`"). The additions are field-specific (no whole-dataclass equality), low-risk, and strengthen the regression anchor for the new counting. No production behavior changed.
- **Scope note (not a deviation):** the fail-soft `write_trial_summary` site in `_surface_finite_case_signal` (runner) is a 9th IO site introduced by 02-03 and is **not** in this plan's enumerated 8-site narrowing list, so it was left as-is (it already logs at warning). Following the plan's explicit site inventory exactly rather than widening scope.

Otherwise the plan executed as written.

## Issues Encountered

- **Pyright caught `SimpleNamespace` args:** the first cut of the CLI tests passed `types.SimpleNamespace` to `_cmd_sweep`/`_cmd_rescore`/`_cmd_analyze`, which the baseline-diff gate flagged as 3 NEW `reportArgumentType` errors (`SimpleNamespace` is not `argparse.Namespace`). Switched the CLI-arg fixtures to `argparse.Namespace(...)`; gate returned to exit 0. (`test_runner.py` still uses `SimpleNamespace` for the non-CLI `_normalize_trial_data` stubs, which is fine.)
- **Env pytest path (carried from 02-01/02-03):** bare `pytest` resolves to the base conda env; all test invocations used `conda run -n iof3d_cosicorr3d-dev312 python -m pytest`. The `utcnow()` DeprecationWarnings in `rescore.py` / `predictions_cache.py` / `trial_record.py` are pre-existing (F-09 scope) and out of this plan's bounds.

## Threat Surface

No new security-relevant surface. Per the plan's `<threat_model>`, F-08 is an observability change: the corrupt-cache → miss and corrupt-summary → empty fallbacks are **preserved** (now counted via `on_non_fatal`, never weakened), the `_safe_segment` path sanitizer is untouched, and the 4 arbitrary-callable boundaries stay broad so a plugin `ValueError`/`KeyError` still cannot crash a pass (T-02-04 mitigated). No threat flags.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave-2 gate satisfied: `ruff check .` + `ruff format --check .` clean (57 files); full `pytest` 70 passed / 0 skipped; `pyright_gate.py` exit 0 (no NEW errors above the 02-02 baseline).
- F-08 is fully resolved (narrowing + typed counter + CLI line). `PassDiagnostics` is available for any later pass that needs to record fail-soft failures.

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*

## Self-Check: PASSED

- Files verified present: `src/geodispbench3d/diagnostics.py`, `02-05-SUMMARY.md`
- Commits verified in git log: `6150cd4` (Task 1), `22ccafa` (Task 2), `2513b91` (Task 3)
- Wave-2 gate: `ruff check .` + `ruff format --check .` clean; full `pytest` 70 passed / 0 skipped; `pyright_gate.py` exit 0
