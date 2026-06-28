---
phase: 05-ci-cd-release
plan: 01
subsystem: infra
tags: [python-3.12, pyright, ruff, sphinx, myst-parser, packaging, pyproject, ci]

requires:
  - phase: 04-licensing-metadata-packaging
    provides: reconciled pyproject metadata (BSD-3-Clause, public classifiers/URLs), f2s3 extra pinned to pchandler ~=2.1
provides:
  - Python 3.12-only package baseline (requires-python ~=3.12, no 3.11 classifier, ruff/pyright target 3.12)
  - Genuine 0-error pyright gate scoped over src + tests on .[f2s3,dev], private iof3D plugin excluded
  - Modern docs toolchain in the docs extra (sphinx ~=8.1, myst-parser ~=4.0, sphinx-rtd-theme ~=3.0)
  - Source-of-truth docs carrying PROT-01, DOCS-01, the 3.12 wording, and the v0.2 milestone
affects: [05-02 docs scaffold, 05-03 release path, 05-04 branch protection, 05-05 CI restructure, 05-06 integration verification]

tech-stack:
  added: [myst-parser ~=4.0, sphinx-rtd-theme ~=3.0, sphinx bumped 5.1 -> 8.1]
  patterns:
    - "PEP 695 inline type parameters for generic helpers (py312 ruff UP047/UP049)"
    - "typing.cast at loose-stub boundaries (pandas, duck-typed Ax trial data) instead of blanket ignores"
    - "OmegaConf containers coerced to dict[str, Any] before crossing a Mapping[str, Any] boundary"
    - "pyright scope = src + tests, private plugin excluded, errors (not warnings) drive the gate"

key-files:
  created: []
  modified:
    - pyproject.toml
    - pyrightconfig.json
    - tests/core/test_packaging_metadata.py
    - src/geodispbench3d/cli.py
    - src/geodispbench3d/dashboard/app.py
    - src/geodispbench3d/sweep/runner.py
    - src/geodispbench3d/tool/loader.py
    - tests/core/test_loaders.py
    - tests/core/test_rescore.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/PROJECT.md
    - .planning/STATE.md

key-decisions:
  - "Python 3.12-only (D-03 SUPERSEDED): pchandler 2.1 requires >=3.12,<3.13, so a symmetric 3.11+3.12 matrix is impossible; the whole package moves to 3.12"
  - "Modern docs triple committed at the ~= pins that actually resolved: sphinx 8.3.0, myst-parser 4.0.1, sphinx-rtd-theme 3.0.2"
  - "13 residual pyright errors fixed in code (no blanket ignores, no scope narrowing); zero per-line suppressions were needed"
  - "Milestone relabelled v1.0 -> v0.2; first public release will be v0.2.0"

patterns-established:
  - "Pyright gate: errorCount==0 from --outputjson over src+tests on .[f2s3,dev], not a baseline-diff and not a shell text match"
  - "cast() at third-party-stub boundaries is the sanctioned fix when our own code is already correct"

requirements-completed: []  # advances CICD-01 (foundation) and registers PROT-01/DOCS-01, but completes none — they are delivered by 05-05/05-04/05-02 respectively

coverage:
  - id: D1
    description: "Package declares Python 3.12-only (requires-python ~=3.12, no 3.11 classifier, ruff target py312) with a regression test"
    requirement: "CICD-01"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_requires_python_is_312_only / test_no_python_311_classifier / test_ruff_target_version_is_py312"
        status: pass
    human_judgment: false
  - id: D2
    description: "Scoped pyright exits with errorCount==0 over src + tests on .[f2s3,dev] (private iof3D plugin excluded, f2s3 in scope)"
    requirement: "CICD-01"
    verification:
      - kind: integration
        ref: "conda run -n iof3d_cosicorr3d-dev312 pyright --outputjson -> summary.errorCount == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "docs extra resolves and imports (sphinx 8.3.0, myst-parser 4.0.1, sphinx-rtd-theme 3.0.2) — DOCS-01 foundation"
    requirement: "DOCS-01"
    verification:
      - kind: integration
        ref: "pip install -e .[docs] && python -c 'import sphinx, myst_parser, sphinx_rtd_theme'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Source-of-truth docs carry PROT-01 + DOCS-01, the Python 3.12 wording, and the v0.2 milestone"
    requirement: "PROT-01"
    verification:
      - kind: other
        ref: "grep PROT-01/DOCS-01 in REQUIREMENTS.md + ROADMAP.md; no `milestone: v1.0` in STATE.md"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-06-28
status: complete
---

# Phase 5 Plan 01: Foundation — Python 3.12 baseline & genuine 0-error pyright Summary

**Python 3.12-only migration with a genuinely 0-error pyright gate (13 residual src+test errors fixed in code), a modern Sphinx/myst docs extra, and every planning source-of-truth updated for 3.12, PROT-01/DOCS-01, and the v0.2 milestone.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-28T07:09Z
- **Completed:** 2026-06-28T07:21Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments
- Migrated the package to Python 3.12-only: `requires-python = "~=3.12"`, dropped the 3.11 classifier, set ruff `target-version = "py312"` and pyright `pythonVersion = "3.12"`, with new regression assertions in `test_packaging_metadata.py`.
- Reached a **genuine** 0-error pyright gate (errorCount==0 from `--outputjson`) scoped over **src AND tests** on `.[f2s3,dev]` — the private `geodispbench3d_iof3d` plugin + `tests/iof3d` are excluded, but `geodispbench3d_f2s3` stays in scope (pchandler is public). All 13 residual type errors were fixed in code; zero suppressions were needed.
- Bumped the docs extra to the modern triple and confirmed it resolves cleanly: sphinx 8.3.0, myst-parser 4.0.1, sphinx-rtd-theme 3.0.2.
- Updated REQUIREMENTS/ROADMAP/PROJECT/STATE for the 3.12-only scope, added PROT-01 and DOCS-01, and relabelled the milestone v1.0 → v0.2.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate to Python 3.12-only + bump docs extra + pin 3.12 metadata with a regression test** - `7dac987` (feat)
2. **Task 2: Scope pyright over src AND tests and fix residual type-narrowing errors to exit 0** - `80afbf3` (fix)
3. **Task 3: Update requirements/roadmap/project/state for 3.12, PROT-01, DOCS-01, v0.2** - `8570903` (docs)

## Files Created/Modified
- `pyproject.toml` - requires-python ~=3.12, dropped 3.11 classifier, ruff target py312, docs extra → sphinx/myst-parser/sphinx-rtd-theme triple
- `pyrightconfig.json` - pythonVersion 3.12; exclude `src/geodispbench3d_iof3d` + `tests/iof3d`; tests stay in include; f2s3 in scope
- `tests/core/test_packaging_metadata.py` - 3.12-only regression assertions (requires-python, absent 3.11 classifier, ruff py312)
- `src/geodispbench3d/cli.py` - PEP 695 inline type parameter for `_load_or_clean_exit` (py312 ruff UP047/UP049)
- `src/geodispbench3d/dashboard/app.py` - cast Series/DataFrame in `_apply_filters` to satisfy pandas' loose stubs
- `src/geodispbench3d/sweep/runner.py` - `cast("Any", item)` for duck-typed Ax trial attribute access
- `src/geodispbench3d/tool/loader.py` - coerce the OmegaConf container to `dict[str, Any]` before the Mapping[str, Any] boundary
- `tests/core/test_loaders.py`, `tests/core/test_rescore.py` - assert-narrow `GroundTruthSpec | None` and `Path | None` Optionals
- `.planning/REQUIREMENTS.md` - PROT-01 + DOCS-01 (defs + traceability rows, 26 total), CICD-01 reworded to "Python 3.12"
- `.planning/ROADMAP.md` - Phase 5 success criterion #1 → "Python 3.12"; Requirements line gains PROT-01, DOCS-01
- `.planning/PROJECT.md` - 3.12-only scope (D-03 SUPERSEDED), first public release v0.2.0
- `.planning/STATE.md` - milestone v1.0 → v0.2

## Decisions Made
- **Docs pins match resolved versions.** The committed `~=` triple (`sphinx ~=8.1`, `myst-parser ~=4.0`, `sphinx-rtd-theme ~=3.0`) was validated against a real `pip install -e .[docs]`; the actually-resolved versions are sphinx **8.3.0**, myst-parser **4.0.1**, sphinx-rtd-theme **3.0.2** — all satisfied by the committed pins, no speculative pin.
- **No pyright suppressions.** Every residual error was fixable in our own code (Optionals narrowed, OmegaConf container retyped, casts at loose-stub boundaries). The plan's fallback of a single per-line `# pyright: ignore` was not needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] New ruff UP047/UP049 errors from the py312 target bump**
- **Found during:** Task 2 (ruff check after setting `target-version = "py312"`)
- **Issue:** Raising the ruff target to py312 activated pyupgrade rules UP047 ("generic function should use type parameters") and then UP049 ("generic function uses private type parameters") on `src/geodispbench3d/cli.py`'s `_load_or_clean_exit`, which used a module-level `_T = TypeVar("_T")`. `ruff check .` failed.
- **Fix:** Converted to a PEP 695 inline type parameter (`def _load_or_clean_exit[T](...)`), removed the `TypeVar` import and the module-level `_T` definition.
- **Files modified:** src/geodispbench3d/cli.py
- **Verification:** `ruff check .` → "All checks passed!"; pyright still errorCount==0; core suite still green.
- **Committed in:** `80afbf3` (Task 2 commit)

**2. [Rule 3 - Blocking] ruff format drift in the new packaging assertions**
- **Found during:** Task 2 (`ruff format --check .`)
- **Issue:** The multi-line `assert (...)` form I wrote in `test_packaging_metadata.py` (added in Task 1) was not in the formatter's canonical shape, so `ruff format --check` reported it would reformat.
- **Fix:** Ran `ruff format` on the file (formatter moved the assertion message after the condition).
- **Files modified:** tests/core/test_packaging_metadata.py
- **Verification:** `ruff format --check .` → all 62 files already formatted; packaging tests still pass.
- **Committed in:** `80afbf3` (Task 2 commit; the format-only delta to the Task 1 file paired with the py312 ruff change that surfaced it)

**3. [Requirements ledger correction] Reverted premature requirement completion**
- **Found during:** State updates (post-Task 3)
- **Issue:** The plan frontmatter declares `requirements: [CICD-01, PROT-01, DOCS-01]`, so the standard `requirements mark-complete` step checked all three off. But this plan only establishes the foundation: CICD-01 (the actual CI workflow) is delivered in 05-05, DOCS-01 (the sphinx build) in 05-02, and PROT-01 (branch-protection rulesets + apply script) in 05-04 — none of those artifacts exist yet.
- **Fix:** Reverted CICD-01, PROT-01, DOCS-01 to `[ ]` / Pending in REQUIREMENTS.md (checkbox + traceability), and set this SUMMARY's `requirements-completed` to `[]`. The requirement *definitions* (PROT-01, DOCS-01) and the 3.12 rewording remain — that registration is this plan's actual deliverable.
- **Files modified:** .planning/REQUIREMENTS.md, .planning/phases/05-ci-cd-release/05-01-SUMMARY.md
- **Verification:** REQUIREMENTS.md traceability shows all Phase 5 rows Pending; the PROT-01/DOCS-01 definitions are present.
- **Committed in:** final metadata commit

---

**Total deviations:** 3 (2 auto-fixed blocking lint issues from the py312 bump; 1 requirements-ledger correction)
**Impact on plan:** The two auto-fixes were necessary to keep the lint gate green under the new py312 target. The ledger correction keeps the requirements ledger honest — completion is left to the plans that actually deliver each artifact. No scope creep.

## Issues Encountered
- **Wrong interpreter on bare `pytest`.** `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core` resolved to a base-env Python 3.13 `pytest` (no pandas) and failed at collection. Re-ran as `conda run -n iof3d_cosicorr3d-dev312 python -m pytest tests/core` per the project's known invocation rule — 128 passed.
- **Shared-env dependency-conflict warnings.** `pip install -e .[f2s3,dev]` emitted resolver warnings for `geocosicorr3d` (geopandas/psutil) — pre-existing in the shared dev env, out of scope for this plan, not introduced here.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The genuine 0-error pyright gate, the 3.12-only baseline, and the resolvable docs extra are the foundation Wave 2+ builds on: 05-02 (Sphinx docs scaffold over the docs extra), 05-03 (release path), 05-04 (branch protection / PROT-01), 05-05 (CI restructure to a 3.12-only matrix), 05-06 (integration verification).
- No blockers. The `gecodispbench3d_f2s3` adapter type-checks for real against public pchandler 2.1.0; the docs triple is install-proven.

## Self-Check: PASSED

- All 13 modified files present on disk.
- All three task commits found in git history (`7dac987`, `80afbf3`, `8570903`).

---
*Phase: 05-ci-cd-release*
*Completed: 2026-06-28*
