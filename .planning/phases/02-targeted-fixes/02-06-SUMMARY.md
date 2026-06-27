---
phase: 02-targeted-fixes
plan: 06
subsystem: infra
tags: [datetime, timezone, utc, imports, lazy-import, lint, hygiene, F-09, F-10, F-11]

# Dependency graph
requires:
  - phase: 02-05
    provides: F-08 diagnostics + the runner/rescore/predictions_cache fail-soft sites this plan's timestamp/import edits sit alongside
  - phase: 02-02
    provides: pyright baseline-diff gate (pyright_gate.py)
  - phase: 02-01
    provides: F-20 characterization net (FakeAxClient + StubAdapter) covering runner.py
provides:
  - Timezone-aware UTC timestamps (datetime.now(UTC)) across all 5 stamp sites, no hand-appended "Z"; offset-aware isoformat values proven parseable via datetime.fromisoformat
  - runner.py in-loop internal/stdlib imports hoisted to module top (trial_record provenance classes, update_trial_record, write_trial_summary, predictions_cache.write_prediction, dataclasses.asdict, math) without breaking lazy Ax gating
  - rescore.py freed of the dead `_ = asdict` lint-suppression hack and its asdict import
affects: [02-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Timestamps use timezone-aware datetime.now(UTC); isoformat already encodes the +00:00 offset, so no manual 'Z' is appended; strftime ID-format sites just swap the call (output unchanged)"
    - "Internal/stdlib imports live at module top; only genuinely optional/heavy deps (Ax) stay lazy/guarded — tests/core/test_imports.py is the authoritative lazy-gating guard, not a grep"

key-files:
  created: []
  modified:
    - src/geodispbench3d/sweep/trial_record.py
    - src/geodispbench3d/sweep/rescore.py
    - src/geodispbench3d/analysis/runner.py
    - src/geodispbench3d/results/predictions_cache.py
    - src/geodispbench3d/sweep/runner.py
    - tests/core/test_predictions_cache.py
    - tests/core/test_rescore.py
    - tests/core/test_runner.py

key-decisions:
  - "Kept the helper NAMES _utcnow / _utcnow_compact — only the call inside them changed from datetime.utcnow() to datetime.now(UTC); the acceptance grep targets the CALL `datetime.utcnow(`, not the substring `utcnow`"
  - "Hoisted only geodispbench3d-internal + stdlib imports in runner.py; the Ax import stays in its guarded top-level try (runner.py:21-32) so optional-dep gating is preserved"
  - "Left the in-loop `from geodispbench3d.metrics.registry import MetricRegistry` (runner.py run_with_suite) lazy — it was out of scope for the F-10 hoist list and is not one of the called-out in-loop imports"

patterns-established:
  - "Stamp UTC times with datetime.now(UTC).isoformat(); never hand-append 'Z' to an isoformat value"

requirements-completed: [FIX-01, FIX-02]

coverage:
  - id: D1
    description: "F-09 — all 5 datetime.utcnow() call sites use timezone-aware datetime.now(UTC); isoformat sites drop the manual 'Z' and emit offset-aware (+00:00) timestamps that parse via datetime.fromisoformat; strftime ID-format output is unchanged"
    requirement: "FIX-01"
    verification:
      - kind: unit
        ref: "tests/core/test_predictions_cache.py#test_write_and_read_roundtrip (cached_at: fromisoformat, tzinfo not None, no trailing Z)"
        status: pass
      - kind: unit
        ref: "tests/core/test_rescore.py#test_rescore_default_options (rescored_at: fromisoformat, tzinfo not None, no trailing Z)"
        status: pass
      - kind: other
        ref: "grep -rn 'datetime.utcnow(' src/geodispbench3d returns nothing; grep -rn '+ \"Z\"' returns nothing"
        status: pass
    human_judgment: false
  - id: D2
    description: "F-10 — in-loop internal/stdlib imports in runner.py hoisted to module top without pulling Ax/iof3D/streamlit to module level"
    requirement: "FIX-02"
    verification:
      - kind: unit
        ref: "tests/core/test_imports.py#test_framework_imports_without_tool_extras + test_framework_has_no_iof3d_or_pchandler_imports"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_f08_cache_write_failure_counted_and_run_completes (patches hoisted geodispbench3d.sweep.runner.write_prediction)"
        status: pass
    human_judgment: false
  - id: D3
    description: "F-11 — dead `_ = asdict` lint-suppression hack and the asdict import removed from rescore.py; ruff clean"
    requirement: "FIX-02"
    verification:
      - kind: other
        ref: "ruff check src/geodispbench3d/sweep/rescore.py — All checks passed; grep 'asdict' rescore.py returns nothing"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 06: Mechanical Hygiene Cluster (F-09/F-10/F-11) Summary

**Timezone-aware UTC timestamps (offset-aware, no manual "Z", proven fromisoformat-parseable), runner.py internal imports hoisted to module top with lazy Ax gating intact, and the dead `_ = asdict` hack removed from rescore.py.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-27T11:14:19+02:00 (wave3-pre-02-06 tag base)
- **Completed:** 2026-06-27T11:20:00+02:00
- **Tasks:** 3
- **Files modified:** 8 (5 source, 3 test)

## Accomplishments
- F-09: replaced all 5 `datetime.utcnow()` calls with `datetime.now(UTC)`; dropped the hand-appended `"Z"` on the 3 isoformat sites (trial_record `_utcnow`, rescore inline `rescored_at`, predictions_cache `cached_at`) so they emit offset-aware `+00:00`; the 2 strftime ID-format sites (`_utcnow_compact` in rescore + analysis) just swapped the call, output unchanged. The utcnow DeprecationWarnings are gone.
- F-09: added `datetime.fromisoformat` parse assertions (offset-aware, no trailing `"Z"`) for both `cached_at` and `rescored_at`, guarding the `+00:00` vs `Z` change against lexical/Z-only consumers.
- F-10: hoisted the in-loop internal/stdlib imports in runner.py (trial_record provenance classes, `update_trial_record`, `write_trial_summary`, `predictions_cache.write_prediction`, `dataclasses.asdict`, `math`) to module top; the Ax import stays lazy/guarded and `tests/core/test_imports.py` confirms no iof3D/pchandler/Ax reaches module level.
- F-11: deleted the dead `_ = asdict` lint-suppression line and removed `asdict` from the dataclasses import in rescore.py (kept `dataclass`, still used); ruff clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: F-09 timezone-aware timestamps** - `13b105f` (fix)
2. **Task 2: F-10 hoist in-loop imports** - `2b3bca3` (refactor)
3. **Task 3: F-11 remove dead `_ = asdict`** - `e3e73b8` (refactor)

**Plan metadata:** _(final docs commit — SUMMARY + STATE + ROADMAP)_

## Files Created/Modified
- `src/geodispbench3d/sweep/trial_record.py` - `_utcnow` now `datetime.now(UTC).isoformat()` (no `"Z"`)
- `src/geodispbench3d/sweep/rescore.py` - inline `rescored_at` + `_utcnow_compact` swapped to `now(UTC)`; UTC imported; dead `_ = asdict` + asdict import removed (F-11)
- `src/geodispbench3d/analysis/runner.py` - `_utcnow_compact` swapped to `now(UTC)`; UTC imported
- `src/geodispbench3d/results/predictions_cache.py` - inline `cached_at` now `now(UTC).isoformat()` (no `"Z"`); UTC imported
- `src/geodispbench3d/sweep/runner.py` - in-loop internal/stdlib imports hoisted to module top; `import math` + `from dataclasses import asdict` added to top block
- `tests/core/test_predictions_cache.py` - fromisoformat parse assertion for `cached_at`
- `tests/core/test_rescore.py` - fromisoformat parse assertion for `rescored_at`
- `tests/core/test_runner.py` - F-08 cache-write test repatched to the hoisted binding (deviation, see below)

## Decisions Made
- Kept the helper names `_utcnow` / `_utcnow_compact`; only the call inside them changed. The acceptance check targets the CALL `datetime.utcnow(`, not the substring `utcnow`.
- Hoisted only internal/stdlib imports; left the lazy `MetricRegistry` import in `run_with_suite` alone (out of the F-10 scope list) and kept the Ax import guarded/lazy.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Repointed the F-08 cache-write test's monkeypatch to the hoisted binding**
- **Found during:** Task 2 (F-10 hoist)
- **Issue:** `tests/core/test_runner.py::test_f08_cache_write_failure_counted_and_run_completes` patched `geodispbench3d.results.predictions_cache.write_prediction`, relying on runner's in-loop import re-resolving the source module at call time. Hoisting `write_prediction` to runner's module namespace meant the source-module patch no longer affected the bound name, so the failing-write path never fired and `non_fatal_failures` stayed 0 (test failed).
- **Fix:** Updated the monkeypatch target to `geodispbench3d.sweep.runner.write_prediction` and refreshed the explanatory comment to reference the F-10 hoist. Test intent and assertions unchanged.
- **Files modified:** tests/core/test_runner.py
- **Verification:** `pytest tests/core` → 66 passed; full `pytest` → 70 passed
- **Committed in:** `2b3bca3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix is the direct and necessary consequence of the planned F-10 hoist — a test that asserted the old lazy-import binding location had to follow the symbol to its new home. No scope creep; no production behavior change.

## Issues Encountered
- `conda run -n iof3d_cosicorr3d-dev312 pytest ...` resolves `pytest` to the base env (Python 3.13, no package) and errors with `ModuleNotFoundError: No module named 'geodispbench3d'`. Per the orchestrator's note, all runs used `conda run -n iof3d_cosicorr3d-dev312 python -m pytest ...` instead. Not a code issue.

## Wave-3 Gate
- `ruff check .` — All checks passed
- `ruff format --check .` — 57 files already formatted
- `python -m pytest` — 70 passed, 0 skipped (remaining warnings are pre-existing pydantic/timm deprecations, not utcnow)
- `python .planning/phases/02-targeted-fixes/pyright_gate.py` — `PASS: no new pyright errors above baseline` (exit 0)
- `tests/core/test_imports.py` — green (lazy gating intact)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- F-09/F-10/F-11 mechanical-hygiene cluster fully resolved; persistence/runner files are clean for 02-07.
- No blockers.

## Self-Check: PASSED

- All 8 modified files present; 3 task commits (`13b105f`, `2b3bca3`, `e3e73b8`) verified in git history.

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*
