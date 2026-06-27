---
phase: 02-targeted-fixes
plan: 04
subsystem: refactoring
tags: [sweep-parameters, dedup, classmethod, pyright, tdd, F-02]

requires:
  - phase: 02-02
    provides: pyright_gate.py baseline-diff gate (line-number-independent multiset signatures)
provides:
  - SweepParameter.from_mapping classmethod as the single source of truth for 11-field sweep-param coercion
  - Three call sites (parameters.py, tool/loader.py, iof3d/factory.py) routed through from_mapping
  - tests/core/test_parameters.py parameterized coverage of from_mapping
  - Net -2 pyright errors (values-list patterns cleared at tool/loader.py and factory.py)
affects: [sweep, tool-loader, iof3d-factory]

tech-stack:
  added: []
  patterns:
    - "Classmethod constructor (from_mapping) as single-sourcing seam for duplicated YAML->dataclass coercion"
    - "Explicit None-narrowing local (raw = get(); x = list(raw) if raw is not None else None) to satisfy pyright over two-read .get patterns"

key-files:
  created:
    - tests/core/test_parameters.py
  modified:
    - src/geodispbench3d/sweep/parameters.py
    - src/geodispbench3d/tool/loader.py
    - src/geodispbench3d_iof3d/factory.py

key-decisions:
  - "from_mapping is a classmethod on SweepParameter, NOT a module-level export — not added to parameters.py __all__"
  - "Single atomic commit (D-07/D-08) rather than RED/GREEN split commits, per plan's explicit atomic-commit policy referencing F-02"
  - "Verification via the 02-02 baseline-diff gate (exit 0), not raw 'pyright && ...' — factory.py carries an accepted deferred error unrelated to F-02"

patterns-established:
  - "Duplicated coercion blocks collapse into a classmethod factory on the target dataclass"

requirements-completed: [FIX-03]

coverage:
  - id: D1
    description: "SweepParameter.from_mapping single-sources the 11-field coercion; all three previously-duplicated inline blocks route through it"
    requirement: "FIX-03"
    verification:
      - kind: unit
        ref: "tests/core/test_parameters.py (5 cases: all 11 fields, omitted defaults, values=None, tuple-vs-list, missing name)"
        status: pass
      - kind: integration
        ref: "tests/core/test_loaders.py (loader-built SweepParameters stay green — behavior-identical)"
        status: pass
    human_judgment: false
  - id: D2
    description: "from_mapping typing clears the values-list pyright errors at tool/loader.py and factory.py with no new errors (net -2)"
    requirement: "FIX-03"
    verification:
      - kind: automated
        ref: "conda run -n iof3d_cosicorr3d-dev312 python .planning/phases/02-targeted-fixes/pyright_gate.py (exit 0; total errors 21->19)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 04: SweepParameter.from_mapping single-sourcing Summary

**Collapsed three byte-identical 11-field SweepParameter coercion blocks into one `SweepParameter.from_mapping` classmethod, with parameterized tests and a net -2 pyright reduction (values-list patterns cleared).**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-06-27
- **Tasks:** 1
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Added `SweepParameter.from_mapping(entry)` classmethod to `parameters.py` — the single source of truth for the 11-field coercion (name, kind/type, value_type, values, lower, upper, log_scale, step, activates_on, is_ordered, sort_values).
- Routed all three previously-duplicated sites through it: `load_sweep_config` (parameters.py), `_load_hyperparameters` (tool/loader.py), and the iof3D factory (`_coerce_hparam` removed entirely, factory now calls `from_mapping` directly).
- Typed the values extraction with explicit None-narrowing (`raw_values = entry.get("values"); values = list(raw_values) if raw_values is not None else None`), clearing the two values-list pyright errors at tool/loader.py and factory.py — total project errors dropped 21 → 19.
- Created `tests/core/test_parameters.py` with 5 parameterized/unit cases covering all 11 fields, omitted defaults, `values=None`, tuple-vs-list normalization, and the missing-`name` KeyError.

## Task Commits

TDD-developed (RED confirmed locally via `AttributeError: ... has no attribute 'from_mapping'`), committed atomically per the plan's D-07/D-08 single-commit policy:

1. **Task 1: Add SweepParameter.from_mapping, route all three sites through it, and unit-test it** - `33e55cf` (refactor)

**Plan metadata:** `<meta-hash>` (docs: complete plan)

## Files Created/Modified
- `src/geodispbench3d/sweep/parameters.py` - Added `from_mapping` classmethod; `load_sweep_config` now builds params via a list comprehension over `from_mapping`.
- `src/geodispbench3d/tool/loader.py` - `_load_hyperparameters` reduced to a one-line comprehension over `from_mapping`.
- `src/geodispbench3d_iof3d/factory.py` - Removed the `_coerce_hparam` helper; `param_defs` built via `from_mapping`.
- `tests/core/test_parameters.py` - New parameterized from_mapping tests (5 cases).

## Decisions Made
- `from_mapping` is a classmethod on `SweepParameter`, **not** a module-level export — deliberately not added to `parameters.py` `__all__` (per plan note removing that instruction).
- Single atomic commit instead of RED/GREEN split, honoring the plan's explicit atomic-commit-referencing-F-02 policy (D-07/D-08). TDD discipline was still followed locally: the new test was written and confirmed failing before implementation.
- Verification uses the 02-02 baseline-diff gate (`pyright_gate.py`, exit 0) rather than a raw `pyright && pytest` — factory.py carries an accepted deferred error unrelated to F-02, so a zero-error gate would fail by construction. The gate passed and additionally registered a net reduction.

## Deviations from Plan

None - plan executed exactly as written. The `_coerce_hparam` helper in factory.py became dead after routing through `from_mapping` and was removed (anticipated by the plan's "inline coercion blocks replaced by from_mapping calls").

## Issues Encountered
- `conda run -n iof3d_cosicorr3d-dev312 pytest` resolved to the base-env `pytest` (python 3.13) where the package is not installed. Resolved by invoking through the env interpreter: `conda run -n iof3d_cosicorr3d-dev312 python -m pytest ...`. All test/gate runs used the correct env python (3.12), verified via `sys.executable`.

## Verification Evidence
- `tests/core/test_parameters.py` + `tests/core/test_loaders.py`: 10 passed.
- Full suite: `python -m pytest` → 62 passed, 0 skipped (iof3D dev env runs the plugin suites).
- `ruff check .` → all checks passed; `ruff format --check .` → 56 files already formatted.
- `pyright_gate.py` → "PASS: no new pyright errors above baseline" (exit 0); total errors 21 → 19 (tool/loader.py 3→2, factory.py 2→1).
- Acceptance greps: `SweepParameter.from_mapping` present at all three call sites; `from_mapping` appears as a `def` in parameters.py but not inside `__all__`.

## Next Phase Readiness
- F-02 (FIX-03) resolved. Disjoint from the 02-03 runner cluster; no shared files, Wave-1 parallel-safe.
- No blockers.

## Self-Check: PASSED

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*
