---
phase: 02-targeted-fixes
plan: 01
subsystem: testing
tags: [pytest, characterization-test, ax, sweep-runner, regression-anchor, coverage]

# Dependency graph
requires:
  - phase: 01-code-health-audit
    provides: "REPORT.md F-20 finding (runner.py at 13% coverage) and the ratified fix set"
provides:
  - "tests/core/test_runner.py — F-20 characterization net against unmodified sweep/runner.py"
  - "Reusable in-test FakeAxClient (5-method, Ax-free) + StubAdapter (per-case canned prediction) harness"
  - "Regression anchor pinning the current NaN-ignoring survivor-mean aggregation (the contract F-05/02-03 and F-08/02-05 must consciously update)"
affects: [02-03, 02-05, runner-refactor]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Monkeypatch geodispbench3d.sweep.runner.AxClient BEFORE constructing AxSweepRunner (the constructor calls AxClient() unconditionally at runner.py:69)"
    - "FakeAxClient.create_experiment carries an EXPLICIT keyword signature (parameters/name/objective_name/minimize) so the runner's inspect.signature dispatch takes the real named branch, not the unsupported-signature fallback"
    - "StubAdapter returns a per-case prediction via TrialOutputs.extras; a tiny on-sys.path parser package (runner_stub_pkg) echoes it — distinct name from test_rescore's stub_pkg to avoid sys.modules cross-contamination"

key-files:
  created:
    - tests/core/test_runner.py
  modified: []

key-decisions:
  - "Coverage measured via `coverage run -m pytest -p no:cov` because the plan's `pytest --cov` flag crashes in this env on a torch/pytest-cov early-import conflict (RuntimeError: _has_torch_function already has a docstring). Named-behavior bar is primary (D-05); coverage is recorded secondary evidence."
  - "_normalize_trial_data object-attribute shape exercised via a 2-tuple of namespaces (one with .trial_index, one with .parameters): a single object carrying both attributes does NOT normalize because the runner's per-item `continue` skips the second attribute lookup."

patterns-established:
  - "Characterization tests assert TODAY's behavior of unmodified source; partial-failure case carries an inline REGRESSION ANCHOR comment naming the future plans (F-05/F-08) that must update it."

requirements-completed: [FIX-01, FIX-04]

coverage:
  - id: D1
    description: "Trial loop happy path (get_next_trial -> executor -> complete_trial), adapter prepare/teardown lifecycle, get_best_trial passthrough, and the named create_experiment dispatch branch are pinned against unmodified runner.py"
    requirement: "FIX-04"
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_trial_loop_happy_path_and_teardown"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_create_experiment_dispatch_takes_named_branch"
        status: pass
    human_judgment: false
  - id: D2
    description: "_normalize_trial_data covers the (int,dict) tuple, attribute-object, and TypeError-on-unparseable shapes"
    requirement: "FIX-01"
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_normalize_trial_data_tuple_int_dict"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_normalize_trial_data_object_attributes"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_normalize_trial_data_unparseable_raises_type_error"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cross-case aggregation: single-case short-circuit, multi-case finite mean, and the partial-failure NaN-ignoring survivor mean (F-05/F-08 regression anchor)"
    requirement: "FIX-04"
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_single_case_aggregation_short_circuits"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_multi_case_aggregation_means_finite_values"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_multi_case_partial_failure_ignores_nan_survivor_mean"
        status: pass
    human_judgment: false
  - id: D4
    description: "A healthy run stamps tool/dataset/parser provenance blocks into ax_trial/summary.json (the F-08 site)"
    requirement: "FIX-04"
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_provenance_blocks_stamped_into_summary_json"
        status: pass
    human_judgment: false

# Metrics
duration: 7min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 01: F-20 Runner Characterization Net Summary

**Ax-free FakeAxClient + StubAdapter harness pins the sweep trial loop, both cross-case aggregation paths, the NaN partial-failure survivor mean, `_normalize_trial_data` (3 shapes), provenance stamping, and adapter teardown — lifting `sweep/runner.py` from 13% to 72% coverage against unmodified source.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-27T07:56:47Z
- **Completed:** 2026-06-27T08:03:43Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Built the deterministic `FakeAxClient` (5 duck-typed methods) + `StubAdapter` harness, installed via `monkeypatch.setattr(runner_mod, "AxClient", FakeAxClient)` BEFORE runner construction — the mechanism the plan made explicit (constructor calls `AxClient()` at runner.py:69).
- Pinned the happy-path trial loop, `prepare`/`teardown` lifecycle (teardown asserted even on the all-success path via the `finally` at runner.py:218-219), `get_best_trial` passthrough, and the named `create_experiment` dispatch branch.
- Pinned `_normalize_trial_data` across the `(int, dict)` tuple, attribute-object, and `TypeError`-on-unparseable shapes.
- Pinned cross-case aggregation: single-case short-circuit, multi-case finite mean (0.4, 0.6 → 0.5), and the **partial-failure NaN-ignoring survivor mean** with an inline regression-anchor comment marking it as the contract F-05 (02-03) / F-08 (02-05) must consciously update.
- Pinned provenance stamping into `ax_trial/summary.json` (tool/dataset/parser blocks — the F-08 visibility site).
- **runner.py coverage recorded at 72%** (174 stmts, 48 missed), up from the 13% baseline. The uncovered span is largely the Ax-shim objective branches (runner.py:105-129, F-14/deferred) and the alternate `run()` entry point (150-171), exactly as the plan anticipated.

## Task Commits

1. **Task 1: fake-AxClient + stub-adapter harness, trial loop, normalize shapes** - `fdc7bd5` (test)
2. **Task 2: cross-case aggregation, NaN partial-failure, provenance** - `692e239` (test)

**Plan metadata:** committed separately with STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified
- `tests/core/test_runner.py` - F-20 characterization net (9 tests): harness + trial loop + teardown + normalize shapes + aggregation + partial-failure + provenance.

## Decisions Made
- **Coverage measurement workaround.** The plan's verify command uses `pytest --cov=geodispbench3d.sweep.runner`. In this conda env that crashes at collection with `RuntimeError: function '_has_torch_function' already has a docstring` — a known pytest-cov/torch early-import double-initialization conflict (runner.py imports `ax`, which imports `torch`). The `COVERAGE_CORE=sysmon` backend did not avoid it. Coverage was instead measured cleanly via `coverage run -m pytest tests/core/test_runner.py -p no:cov` + `coverage report`, which yielded the 72% figure. Per D-05 the named-behavior bar is the primary acceptance gate and coverage is recorded secondary evidence, so this does not weaken the plan's acceptance criteria. (Logged as a candidate deferred item — the project-wide `--cov` invocation should likely pre-import torch or pin a coverage core; out of scope for a test-only plan.)
- **`pytest` shim resolves to base.** Bare `pytest` in this shell runs the base-env Python 3.13 (no `geodispbench3d` installed); all runs use `conda run -n iof3d_cosicorr3d-dev312 python -m pytest …` so the env interpreter is used. This is a pre-existing env quirk affecting all tests, not specific to this plan.
- **Object-attribute normalize shape uses a 2-tuple of namespaces.** A single object exposing both `.trial_index` and `.parameters` does NOT normalize under the current runner (the per-item `continue` at runner.py:388-404 skips the second attribute on the same item). The test therefore pins the shape that actually works today — one namespace with `.trial_index`, one with `.parameters` — which is itself a useful characterization of the current behavior.

## Deviations from Plan

None - plan executed exactly as written. The two items above are environment/measurement workarounds (the plan's `--cov` flag and bare `pytest` are env-incompatible), not changes to the test scope or assertions. No source files were modified (characterization-only, as required).

## Issues Encountered
- `pytest --cov` torch double-docstring crash — resolved by measuring coverage via `coverage run -m pytest -p no:cov` (see Decisions). All 9 new tests pass without `--cov`; full suite is 41 passed, 0 skipped.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The `FakeAxClient` + `StubAdapter` harness and the partial-failure regression anchor are in place for plans 02-03 (F-05) and 02-05 (F-08) to extend.
- The `pyright_gate.py` referenced in this plan's verification block is created by plan 02-02 (not yet executed); pyright was run directly on the new file instead (0 errors, 0 warnings). No source changes here can raise the project pyright baseline.
- Wave-0 gate locally green: `ruff check .` + `ruff format --check .` clean (52 files), full `pytest` 41 passed / 0 skipped.

## Self-Check: PASSED
- FOUND: tests/core/test_runner.py
- FOUND commit: fdc7bd5 (Task 1)
- FOUND commit: 692e239 (Task 2)

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*
