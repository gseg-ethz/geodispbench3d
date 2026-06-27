---
phase: 02-targeted-fixes
plan: 02
subsystem: testing
tags: [pytest, coverage, pyright, type-checking, parquet, evaluation-glue, ci-gate]

# Dependency graph
requires:
  - phase: 01-code-health-audit
    provides: "F-21/F-22 audit findings (untested store + evaluation failure paths) and the D-08 green-gate intent"
provides:
  - "Direct test net for results/store.py (create / append / empty-rows), 100% coverage"
  - "Direct failure-path test net for sweep/evaluation.py (parser-fail, metric-raise, non-scalar, needs-assembly, gt-kind filter), 100% coverage"
  - "Recorded pyright baseline (pyright-baseline.json + PYRIGHT-BASELINE.md): 21 errors / 9 warnings floor"
  - "Reusable stdlib-only baseline-diff gate pyright_gate.py consumed by 02-03/02-04/02-05/02-07"
affects: [02-03, 02-04, 02-05, 02-07, "F-08 evaluation narrowing", "D-11 pyright gate"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Baseline-diff gate: line-number-independent (file, rule, normalized-message) signatures compared as a Counter multiset; fails only on NEW errors"
    - "In-test MetricRegistry subclass (_StubRegistry) injects callables by definition id without dotted-path resolution"
    - "Coverage measured via `coverage run` with torch pre-imported (sidesteps the Ax->torch double-import crash that pytest-cov triggers)"

key-files:
  created:
    - tests/core/test_store.py
    - tests/core/test_evaluation.py
    - .planning/phases/02-targeted-fixes/pyright-baseline.json
    - .planning/phases/02-targeted-fixes/PYRIGHT-BASELINE.md
    - .planning/phases/02-targeted-fixes/pyright_gate.py
  modified: []

key-decisions:
  - "Made _StubRegistry subclass the real MetricRegistry so the F-22 test file adds 0 pyright errors to the baseline (would otherwise have baked 9 reportArgumentType errors into the floor)"
  - "Gate baseline is the dev-env capture (pyright 1.1.403 + full extras), because later waves rerun the gate in that same env; the CI-faithful 1.1.392/.[dev] number (16 errors) is recorded as a doc-only reference and is a strict subset"
  - "Measured coverage with `coverage run` + a torch pre-import shim instead of the plan's `pytest --cov`, which crashes on a torch double-import in this env"

patterns-established:
  - "Pattern: pyright no-regression operationalized as a machine-checkable multiset diff, not a raw `pyright &&` pass/fail"
  - "Pattern: failure-path tests assert specific fields only (never whole-dataclass equality) so a later ADDED field (F-08's non_fatal_failures) stays tolerated"

requirements-completed: [FIX-01, FIX-04]

coverage:
  - id: D1
    description: "results/store.py create-new-parquet, append-to-existing round-trip, and empty-rows short-circuit are directly tested (store.py 100% coverage, >=90% target)"
    requirement: "FIX-04"
    verification:
      - kind: unit
        ref: "tests/core/test_store.py (coverage run --include=*/results/store.py -> 100%)"
        status: pass
    human_judgment: false
  - id: D2
    description: "sweep/evaluation.py parser-fail->None, metric-raise->skip, non-scalar->skip, needs-based kwarg assembly, and _gt_kind_matches filtering are directly tested (evaluation.py 100% coverage, >=95% target)"
    requirement: "FIX-01"
    verification:
      - kind: unit
        ref: "tests/core/test_evaluation.py (coverage run --include=*/sweep/evaluation.py -> 100%)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Recorded pyright baseline + reusable baseline-diff gate; gate exits 0 against its own freshly-captured baseline and is ruff-clean; no mypy / no CI / no pyproject edits"
    requirement: "FIX-04"
    verification:
      - kind: automated
        ref: "conda run -n iof3d_cosicorr3d-dev312 python .planning/phases/02-targeted-fixes/pyright_gate.py (exit 0, PASS)"
        status: pass
      - kind: automated
        ref: "ruff check .planning/phases/02-targeted-fixes/pyright_gate.py (All checks passed)"
        status: pass
    human_judgment: false

# Metrics
duration: ~55min
completed: 2026-06-27
status: complete
---

# Phase 02 Plan 02: Wave-0 Test Nets + Pyright Baseline Gate Summary

**Direct store/evaluation failure-path test nets (both 100% coverage) plus a recorded pyright floor (21 errors / 9 warnings) and a reusable stdlib-only baseline-diff gate that later waves diff against instead of a raw `pyright &&`.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-06-27
- **Tasks:** 3
- **Files created:** 5

## Accomplishments
- **F-21:** `tests/core/test_store.py` directly covers `ResultsStore.append` create / append-round-trip / empty-rows short-circuit, plus `append_record_rows` parent-dir creation and the missing-file read path — **store.py 100% coverage** (target >=90%).
- **F-22:** `tests/core/test_evaluation.py` pins all of `evaluate_trial`'s failure logic — parser-raises -> `prediction=None` while trial scalars survive, one metric raising is skipped while others survive, a non-scalar objective value is warned-and-skipped, `needs`-based kwarg assembly injects only declared inputs, and `_gt_kind_matches` filters by GT kind — **evaluation.py 100% coverage** (target >=95%). Assertions check specific fields only, so F-08's future `non_fatal_failures` field stays tolerated.
- **D-08/D-11/D-12:** Captured the pyright floor (`pyright-baseline.json` raw `--outputjson`, 21 errors / 9 warnings / 54 files at 1.1.403 + full extras) and built `pyright_gate.py`, a stdlib-only multiset diff gate that fails only on NEW errors above baseline. It exits 0 self-consistently and is ruff-clean. `PYRIGHT-BASELINE.md` records counts, per-file breakdown, error rules, exact command, the Phase-2-owned file list, the verbatim gate rule, and the D-12 CI-faithful reference (1.1.392 + `.[dev]` only: 16 errors / 22 warnings — a strict subset).

## Task Commits

1. **Task 1: F-21 store tests** - `5a45c17` (test)
2. **Task 2: F-22 evaluation tests** - `e0ffb94` (test), `1560e2c` (test: type-compat refinement), `0211ff4` (style: ruff format)
3. **Task 3: pyright baseline + gate** - `367a7fe` (chore)

## Files Created/Modified
- `tests/core/test_store.py` - Direct F-21 tests for the parquet results store (100% coverage).
- `tests/core/test_evaluation.py` - Direct F-22 failure-path tests for the evaluation glue (100% coverage); `_StubRegistry` subclasses `MetricRegistry` for type-compat.
- `.planning/phases/02-targeted-fixes/pyright-baseline.json` - Verbatim `pyright --outputjson` floor (1.1.403, dev env).
- `.planning/phases/02-targeted-fixes/PYRIGHT-BASELINE.md` - Baseline doc: counts, per-file table, rules, command, Phase-2-owned files, gate rule, D-12 CI-faithful reference.
- `.planning/phases/02-targeted-fixes/pyright_gate.py` - Reusable stdlib-only baseline-diff gate (consumed by 02-03/04/05/07).

## Decisions Made
- **_StubRegistry subclasses MetricRegistry.** Passing a duck-typed stub to `evaluate_trial(registry=...)` produced 9 `reportArgumentType` errors that would have inflated the pyright floor to 30. Subclassing the real registry makes the test file pyright-clean and keeps the baseline honest at 21 (matching 02-RESEARCH).
- **Gate baseline = dev-env capture, not CI.** Later waves rerun `pyright_gate.py` in `iof3d_cosicorr3d-dev312` (1.1.403 + full extras), so that capture is authoritative. The CI-faithful number (pyright 1.1.392, `.[dev]` only, env `gdb3d-pyright-ci`) is 16 errors / 22 warnings and is recorded doc-only; it is a strict subset because the iof3d adapter's `reportArgumentType` errors degrade to missing-import warnings without the extras.
- **Line-number-independent signatures.** The gate reduces each error to `(repo-relative path, rule, normalized message)` and compares as a `Counter`, so refactors that shift lines do not register as new errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Coverage measurement method changed (`pytest --cov` -> `coverage run` with torch pre-import)**
- **Found during:** Tasks 1 & 2 (coverage verification)
- **Issue:** The plan's verify command `conda run -n ... pytest --cov=<module>` fails two ways in this env: (a) bare `conda run pytest` resolves to base python 3.13 (`No module named geodispbench3d`), and (b) under `--cov`, importing `geodispbench3d.sweep.evaluation` triggers `sweep/__init__` -> Ax -> botorch -> torch, and coverage's tracer crashes torch's C-extension init with `RuntimeError: function '_has_torch_function' already has a docstring`. pytest-cov's `--cov` flag is also not registered in the env (only the `coverage` package is).
- **Fix:** Measured coverage via `coverage run` of a tiny scratch runner that pre-imports torch once before pytest collection pulls in the Ax->torch chain, then filtered at report time with `--include`. The tests themselves run green under the normal `python -m pytest` invocation used by the full-suite gate.
- **Files modified:** none in-repo (measurement method only; scratch runner lives outside the repo)
- **Verification:** store.py 100% / evaluation.py 100% reported; full `python -m pytest tests/` = 55 passed, 0 skipped.
- **Committed in:** n/a (no repo artifact; the test files are the deliverable)

**2. [Rule 2 - Missing Critical / quality] _StubRegistry made type-clean to protect the baseline**
- **Found during:** Task 3 (baseline capture)
- **Issue:** The first baseline capture showed 30 errors, not the expected 21 — the new `test_evaluation.py` added 9 `reportArgumentType` errors by passing a non-`MetricRegistry` stub.
- **Fix:** Made `_StubRegistry` subclass `MetricRegistry`. Re-captured baseline -> 21 errors / 9 warnings (matches 02-RESEARCH).
- **Files modified:** tests/core/test_evaluation.py
- **Verification:** `breakdown.py` over the recaptured JSON shows 0 errors in either new test file; gate exits 0.
- **Committed in:** `1560e2c`

---

**Total deviations:** 2 (1 blocking verification-tooling adaptation, 1 quality fix to keep the baseline honest)
**Impact on plan:** No change to deliverables or scope. Both adaptations were necessary to produce the exact artifacts the plan specifies (accurate coverage numbers; an honest 21-error floor).

## Issues Encountered
- **torch + coverage double-import crash** (described in Deviation 1). Root cause: `sweep/__init__.py` eagerly imports `AxSweepRunner`, pulling the Ax->botorch->torch chain; coverage's tracer breaks torch's C-extension docstring registration on first import. Worked around by pre-importing torch before collection. Not a code defect — a known coverage/torch interaction.

## User Setup Required
None - no external service configuration required.

A best-effort named conda env `gdb3d-pyright-ci` was created to capture the D-12 CI-faithful pyright number (1.1.392 + `.[dev]`). It is incidental tooling, not a project dependency, and can be removed with `conda env remove -n gdb3d-pyright-ci`.

## Next Phase Readiness
- `pyright_gate.py` is ready for 02-03/02-04/02-05/02-07 to use as their green-gate (replaces every raw `pyright &&`). Invoke: `conda run -n iof3d_cosicorr3d-dev312 python .planning/phases/02-targeted-fixes/pyright_gate.py`.
- F-22 failure-path behavior is now pinned, so 02-05 (F-08) can narrow `evaluation.py`'s excepts and add `non_fatal_failures` against a regression anchor.
- Wave-0 gate is green: `ruff check .` + `ruff format --check .` clean, full `pytest` 55 passed / 0 skipped, gate exit 0.

## Self-Check: PASSED

All 6 created files exist on disk; all 5 task commits (`5a45c17`, `e0ffb94`, `1560e2c`, `0211ff4`, `367a7fe`) are present in git history.

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*
