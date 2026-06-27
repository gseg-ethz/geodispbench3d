---
phase: 04-licensing-metadata-packaging
plan: 02
subsystem: packaging
tags: [pep562, import-guard, pyproject, extras, pchandler, f2s3, iof3d, dormant-adapter, hydra-cli]

# Dependency graph
requires:
  - phase: 04-licensing-metadata-packaging
    plan: 01
    provides: reconciled pyproject metadata (BSD classifiers, public URLs) on which the extras edits build
provides:
  - "geodispbench3d_iof3d ships dormant: PEP 562 __getattr__ lazy re-export so `import geodispbench3d_iof3d` succeeds without iof3D/pc2img; gated symbols raise an actionable, chained ImportError"
  - "iof3d-ax reduced to a thin guarded launcher (cli.py) delegating to a new _sweep_cli.py; ImportError -> clean SystemExit, no raw traceback (in- and out-of-process)"
  - "pyproject: iof3d extra disabled (commented out, not []); f2s3 pinned to pchandler ~= 2.1; clean public install proven in-phase"
  - "tests/core/test_iof3d_import_guard.py — five-test simulated-absence guard + extras gate"
affects: [phase-05 release/publish (clean public install graph), tests/iof3d, tests/f2s3]

# Tech tracking
tech-stack:
  added:
    - "pchandler ~= 2.1 (f2s3 extra) — first-party gseg-ethz, 2.1.0 from public PyPI, symbol-compat VERIFIED (D-07)"
  patterns:
    - "PEP 562 module __getattr__ lazy re-export as the single chokepoint for optional-dependency gating, type-checker-friendly via a TYPE_CHECKING re-import block"
    - "Targeted import-failure translation: only ModuleNotFoundError whose top-level package is gated is relabelled (chained via from exc); all other failures re-raise unchanged"

key-files:
  created:
    - tests/core/test_iof3d_import_guard.py
    - src/geodispbench3d_iof3d/_sweep_cli.py
    - .planning/phases/04-licensing-metadata-packaging/deferred-items.md
  modified:
    - src/geodispbench3d_iof3d/__init__.py
    - src/geodispbench3d_iof3d/cli.py
    - pyproject.toml
    - tests/f2s3/conftest.py
    - tests/conftest.py
    - tests/iof3d/conftest.py
    - docs/tools/iof3d.md
    - .planning/phases/02-targeted-fixes/pyright-baseline.json

key-decisions:
  - "Guard translates ONLY ModuleNotFoundError whose top-level package is in {iof3D, pc2img} (chained via from exc); pchandler is deliberately NOT in the set, so a missing-pchandler / transitive-bug failure surfaces as its own genuine error (finding 5, threat T-04-03-R)"
  - "iof3d extra is commented out, not set to [] — a commented block makes `pip install geodispbench3d[iof3d]` warn the extra is unavailable (no hard-error, no private dep resolution); [] would falsely advertise an installable-but-empty extra (finding 7)"
  - "Pre-existing iof3d-ax --help hydra MissingConfigException (conf/ lacks __init__.py for the pkg:// provider) confirmed regression-neutral across the cli/_sweep_cli split and deferred (out of scope, SCOPE BOUNDARY)"
  - "Pre-existing accepted pyright error 'Never is not iterable' reattributed in the phase-02 baseline from cli.py to _sweep_cli.py because the _collect_run_kwargs code relocated unchanged by the split (no behavior change, baseline-diff gate green)"
  - "PKG-02 clean public install proven in-phase via a throwaway venv (user override of session-decision-2); only the full behavioral pytest tests/f2s3 against installed pchandler==2.1.0 still defers to the Phase 5 CI f2s3 job"

patterns-established:
  - "Optional tool adapters can ship dormant in the public wheel: package imports succeed, construction/CLI fails actionably, and the private dependency extra is commented out so the public resolution graph stays clean"

requirements-completed: [PKG-01, PKG-02, PKG-03]

coverage:
  - id: D1
    description: "import geodispbench3d_iof3d succeeds with iof3D/pc2img blocked; accessing Iof3dCallableAdapter raises actionable, chained ImportError"
    requirement: "PKG-01"
    verification:
      - kind: unit
        ref: "tests/core/test_iof3d_import_guard.py#test_public_import_succeeds_use_fails"
        status: pass
    human_judgment: false
  - id: D2
    description: "Non-gated parse_iof3d_output resolves under the same iof3D/pc2img block (pchandler present) — parser path not mis-mapped to a gated submodule"
    requirement: "PKG-01"
    verification:
      - kind: unit
        ref: "tests/core/test_iof3d_import_guard.py#test_parser_path_resolves_without_iof3d"
        status: pass
    human_judgment: false
  - id: D3
    description: "iof3d-ax (cli.main) exits cleanly with the actionable message in-process when iof3D is absent (no raw ImportError traceback)"
    requirement: "PKG-01"
    verification:
      - kind: unit
        ref: "tests/core/test_iof3d_import_guard.py#test_iof3d_ax_launcher_exits_cleanly"
        status: pass
    human_judgment: false
  - id: D4
    description: "Out-of-process `python -m geodispbench3d_iof3d.cli` under simulated absence exits 1, prints actionable stderr, shows NO Traceback"
    requirement: "PKG-01"
    verification:
      - kind: unit
        ref: "tests/core/test_iof3d_import_guard.py#test_iof3d_ax_subprocess_exits_1_no_traceback"
        status: pass
    human_judgment: false
  - id: D5
    description: "pyproject optional-dependencies has no active iof3d key and f2s3 == [pchandler ~= 2.1]; geodispbench3d_iof3d stays in setuptools packages"
    requirement: "PKG-01, PKG-03"
    verification:
      - kind: unit
        ref: "tests/core/test_iof3d_import_guard.py#test_extras_iof3d_commented_f2s3_pinned"
        status: pass
    human_judgment: false
  - id: D6
    description: "Clean public install: throwaway venv `pip install '.[f2s3]'` resolves pchandler 2.1.0 from public PyPI and imports parse_f2s3_output, with no iof3d extra / no private deps"
    requirement: "PKG-02, PKG-03"
    verification:
      - kind: integration
        ref: "throwaway-venv pip install '.[f2s3]' + parser import smoke (INSTALL_RC=0, SMOKE_RC=0, pchandler 2.1.0)"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-06-27
status: complete
---

# Phase 04 Plan 02: Dormant-iof3D Import Guard & Clean Public Install Summary

**`geodispbench3d_iof3d` now ships dormant via a PEP 562 lazy re-export — public import succeeds without iof3D, adapter use and `iof3d-ax` fail with an actionable chained error — while the `iof3d` extra is disabled and F2S3 carries its own `pchandler ~= 2.1` pin, proven to install cleanly from public PyPI in a throwaway venv.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-27T19:21:20Z
- **Completed:** 2026-06-27T19:39:57Z
- **Tasks:** 3 (TDD: RED then GREEN x2)
- **Files modified:** 11 (3 created, 8 modified) — 9 source/test/doc + 2 planning artifacts

## Accomplishments
- Refactored `geodispbench3d_iof3d/__init__.py` to a PEP 562 `__getattr__` lazy re-export (`_LAZY` map + `__dir__` + `TYPE_CHECKING` block). `import geodispbench3d_iof3d` no longer pulls iof3D/pc2img eagerly (D-02, PKG-01).
- The guard translates **only** a `ModuleNotFoundError` whose top-level package is in `{iof3D, pc2img}` into the actionable `_IOF3D_MISSING_HINT` (chained via `from exc`); every other failure (transitive bug, missing `pchandler`, regression in a target module) re-raises unchanged (finding 5; threat T-04-03-R).
- Split `cli.py` into a thin guarded `iof3d-ax` launcher (`ImportError` → `SystemExit`) plus a new `_sweep_cli.py` holding the unchanged hydra-decorated `main` + heavy imports (D-03).
- Disabled the `iof3d` extra by commenting the whole block out (not `[]`), with an accurate inline note on pip's warn-not-error behavior (finding 7); pinned `f2s3 = ["pchandler ~= 2.1"]` and recorded D-07 symbol-compat VERIFIED.
- Corrected conftest/doc hygiene: `tests/f2s3/conftest.py` credits pchandler to `[f2s3]`; `tests/conftest.py` + `tests/iof3d/conftest.py` drop the removed `[iof3d]`-extra guidance (finding 4); `docs/tools/iof3d.md` qualifies the legacy CLI for the dormant public wheel (finding 11).
- Added `tests/core/test_iof3d_import_guard.py` — five simulated-absence tests (in-process via `builtins.__import__`, out-of-process via `sys.meta_path`, `sys.modules` cleared with `monkeypatch.delitem(raising=False)` per finding 8) + the extras-assertion gate.
- **Proved PKG-02 in-phase:** a throwaway venv built from the mandated conda interpreter ran `pip install '.[f2s3]'`, resolving **pchandler 2.1.0** from public PyPI (not the dev-env editable 2.0.0rc8) and importing `parse_f2s3_output` cleanly — superseding session-decision-2's full deferral (finding 6).

## Task Commits

1. **Task 1: dormant-iof3D guard + extras tests (RED)** — `7dcdeb8` (test)
2. **Task 2: PEP 562 guard + cli launcher split (GREEN)** — `94011da` (feat)
3. **Task 3: disable iof3d extra, pin f2s3 pchandler, fix hygiene (GREEN)** — `2de4245` (feat)

## Files Created/Modified
- `tests/core/test_iof3d_import_guard.py` (NEW) — five-test guard + extras gate.
- `src/geodispbench3d_iof3d/_sweep_cli.py` (NEW) — relocated hydra-decorated `main`, `_collect_run_kwargs`, and the `hydra`/`iof3D`/adapter imports (behavior unchanged).
- `src/geodispbench3d_iof3d/__init__.py` — PEP 562 `__getattr__`/`__dir__`/`_LAZY`/`_IOF3D_MISSING_HINT` + `TYPE_CHECKING` re-imports; `__all__` unchanged.
- `src/geodispbench3d_iof3d/cli.py` — thin guarded `iof3d-ax` launcher.
- `pyproject.toml` — `iof3d` extra commented out; `f2s3 = ["pchandler ~= 2.1"]` + D-07/finding-6 note.
- `tests/f2s3/conftest.py`, `tests/conftest.py`, `tests/iof3d/conftest.py` — extra-source hygiene.
- `docs/tools/iof3d.md` — legacy-CLI line qualified for the dormant wheel.
- `.planning/phases/02-targeted-fixes/pyright-baseline.json` — reattribute the pre-existing `Never is not iterable` error from `cli.py` to `_sweep_cli.py`.
- `.planning/phases/04-licensing-metadata-packaging/deferred-items.md` (NEW) — pre-existing `iof3d-ax --help` hydra-conf defect logged.

## Decisions Made
- Guard relabels only genuine iof3D/pc2img absence; `pchandler` intentionally excluded so its absence surfaces as a real error (finding 5).
- `iof3d` extra commented out rather than `[]` for accurate pip semantics (finding 7).
- PKG-02 clean install proven in-phase (user override of session-decision-2); full behavioral `pytest tests/f2s3` against installed `pchandler==2.1.0` still defers to Phase 5 CI.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pyright baseline reattribution after the cli/_sweep_cli split**
- **Found during:** Task 2
- **Issue:** The accepted pre-existing pyright error `"Never" is not iterable` (in `_collect_run_kwargs`) moved file from `cli.py` to `_sweep_cli.py` with the unchanged code. The phase-02 baseline keys on filename, so the baseline-diff gate read it as a NEW error and failed.
- **Fix:** Reattributed the single baseline entry's `file` field from `cli.py` to `_sweep_cli.py` (no behavior/type change to the moved code, honoring the plan's "unchanged" mandate). Gate then reports no new errors.
- **Files modified:** `.planning/phases/02-targeted-fixes/pyright-baseline.json`
- **Commit:** `94011da`

## Issues Encountered
- **Pre-existing (out of scope, deferred):** `iof3d-ax --help` raises `hydra.errors.MissingConfigException: Primary config module 'geodispbench3d_iof3d.conf' not found`. Verified by temporarily restoring the original `cli.py` topology that it predates this plan and is regression-neutral across the split (finding 12's actual intent — config-path resolution unchanged — is satisfied). Root cause is the bundled `conf/` dir lacking an `__init__.py` for Hydra's `pkg://` provider in the editable install. Logged to `deferred-items.md`.
- **Env quirk (carried from 04-01):** `conda run -n iof3d_cosicorr3d-dev312 pytest` resolves a user-level pytest under the wrong interpreter; all runs used `conda run -n iof3d_cosicorr3d-dev312 python -m pytest`.
- The clean-venv `.[f2s3]` install is slow (~9 min) because the base deps include `ax-platform` (torch/botorch); run with an extended timeout.

## Verification Results
- `python -m pytest tests/core/test_iof3d_import_guard.py` — 5 passed (all guard + extras tests GREEN).
- `python -m pytest tests/core` — 125 passed (120 prior + 5 new; no regressions).
- `python -m pytest` (full suite) — 129 passed (iof3d/f2s3 run real in the dev env; real iof3D adapter still imports).
- `ruff check src/geodispbench3d_iof3d tests` + `ruff format --check src/geodispbench3d_iof3d` — clean.
- Baseline-diff pyright (`pyright_gate.py`) — PASS: no new errors vs baseline (after reattribution).
- Clean public install (throwaway venv, mandated conda interpreter, dev env NOT mutated): `pip install '.[f2s3]'` → `INSTALL_RC=0`, **pchandler 2.1.0** from public PyPI, `parse_f2s3_output` import → `SMOKE_RC=0`.
- `iof3d-ax` editable reinstall smoke: confirmed the cli/_sweep_cli split does not change Hydra `config_path="conf"` resolution (identical behavior before/after; pre-existing conf-pkg defect deferred).

## User Setup Required

None — no external service configuration required. (Network access to PyPI was used for the in-phase clean-install proof.)

## Next Phase Readiness
- The public install graph resolves without iof3D: the `iof3d` extra is disabled, the dormant adapter ships in the wheel, and F2S3 carries a proven `pchandler ~= 2.1` pin. Phase 4's three publish blockers (Private classifier, README/LICENSE mismatch from 04-01; unresolvable iof3d extra from 04-02) are cleared.
- Phase 5 CI should add the behavioral `f2s3` job (`pytest tests/f2s3` against installed `pchandler==2.1.0` in the `f2s3-dev312` binary env) and may address the deferred `iof3d-ax --help` hydra-conf packaging defect.

## Self-Check: PASSED

All created files exist on disk; all task commits (`7dcdeb8`, `94011da`, `2de4245`) present in git history.

---
*Phase: 04-licensing-metadata-packaging*
*Completed: 2026-06-27*
