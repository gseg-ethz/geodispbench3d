---
phase: 04-licensing-metadata-packaging
plan: 01
subsystem: packaging
tags: [pyproject, classifiers, pypi, license, bsd-3-clause, citation, readme, metadata]

# Dependency graph
requires:
  - phase: 03-cli-hardening
    provides: stabilized CLI surface and test layout (tests/core) that this plan extends
provides:
  - pyproject.toml metadata reconciled for first public PyPI release (Private classifier removed; Beta/audience/topic classifiers + Documentation/Changelog URLs added)
  - README License section reconciled to BSD-3-Clause with a no-timeline [iof3d]-unavailable note and stale dormant-iof3D references removed
  - tests/core/test_packaging_metadata.py — a stdlib metadata-assertion gate pinning LIC-01..04
affects: [04-02 packaging/import-guard plan, phase-05 release/publish (release-please, twine, PyPI)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Metadata-as-contract: a pure-stdlib pytest (tomllib + pathlib) pins publish-relevant metadata so packaging drift fails CI before it ships to PyPI"

key-files:
  created:
    - tests/core/test_packaging_metadata.py
  modified:
    - pyproject.toml
    - README.md

key-decisions:
  - "Documentation/Changelog URLs point at forward-valid blob/main targets (docs/index.md, CHANGELOG.md) on the public gseg-ethz/geodispbench3d repo; CHANGELOG.md is created by release-please in Phase 5 — the URL is intentionally forward-valid (RESEARCH Focus 3)"
  - "[iof3d]-unavailable README note carries no timeline (session decision 1); the adapter is described as shipping in the wheel but dormant until iof3D is public"
  - "CITATION.cff and LICENSE confirmed already BSD-3-Clause — confirm-only, no edit (LIC-04)"

patterns-established:
  - "Metadata gate: tests/core/test_packaging_metadata.py asserts every publish-blocking truth/prohibition (no Private classifier, required trove classifiers, public Documentation/Changelog URLs, README BSD-not-Proprietary, no stale iof3d extra references, tolerant CITATION/LICENSE BSD parse)"

requirements-completed: [LIC-01, LIC-02, LIC-03, LIC-04]

coverage:
  - id: D1
    description: "Publish-blocking 'Private :: Do Not Upload' classifier removed from pyproject.toml"
    requirement: "LIC-02"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_no_private_classifier"
        status: pass
    human_judgment: false
  - id: D2
    description: "Honest first-public-release classifiers present (Development Status :: 4 - Beta, Intended Audience :: Science/Research, Topic :: Scientific/Engineering)"
    requirement: "LIC-03"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_required_maturity_audience_topic_classifiers_present"
        status: pass
    human_judgment: false
  - id: D3
    description: "[project.urls] carries public Documentation and Changelog URLs (github.com/gseg-ethz/geodispbench3d host/path)"
    requirement: "LIC-03"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_project_urls_documentation_and_changelog_public"
        status: pass
    human_judgment: false
  - id: D4
    description: "README License section states BSD-3-Clause and no longer says Proprietary (also fixes the PyPI long-description via dynamic readme)"
    requirement: "LIC-01"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_readme_license_is_bsd_not_proprietary"
        status: pass
    human_judgment: false
  - id: D5
    description: "README install section notes the [iof3d] extra is currently unavailable until iof3D publishes, with no timeline"
    requirement: "LIC-01"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_readme_notes_iof3d_extra_unavailable"
        status: pass
    human_judgment: false
  - id: D6
    description: "README drops the stale combined-extras command ([iof3d,f2s3,dashboard]) and the 'gated by [iof3d]' layout text"
    requirement: "LIC-01"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_readme_no_stale_iof3d_extra_references"
        status: pass
    human_judgment: false
  - id: D7
    description: "CITATION.cff and LICENSE confirmed BSD-3-Clause"
    requirement: "LIC-04"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py#test_citation_and_license_are_bsd"
        status: pass
    human_judgment: false

# Metrics
duration: 4min
completed: 2026-06-27
status: complete
---

# Phase 04 Plan 01: Licensing & Metadata Reconciliation Summary

**BSD-3-Clause reconciled across README/pyproject/LICENSE/CITATION, the publish-blocking `Private :: Do Not Upload` classifier removed, Beta/audience/topic classifiers plus public Documentation/Changelog URLs added, all pinned by a new stdlib metadata gate.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-27T19:12:55Z
- **Completed:** 2026-06-27T19:16:48Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 edited)

## Accomplishments
- Removed the publish-blocking `Private :: Do Not Upload` classifier (and its remove-before-publish comment) from `pyproject.toml` — the F-26 publish blocker (LIC-02).
- Added the three honest first-public-release trove classifiers (`Development Status :: 4 - Beta`, `Intended Audience :: Science/Research`, `Topic :: Scientific/Engineering`) and public `Documentation`/`Changelog` URLs (LIC-03).
- Reconciled the README License section to BSD-3-Clause (dropping "Proprietary") — the F-27 mismatch; this also corrects the PyPI long-description since `dynamic = ["readme"]` (LIC-01).
- Added a no-timeline note that the `[iof3d]` extra is currently unavailable until iof3D publishes, dropped the stale combined `[iof3d,f2s3,dashboard]` install command, and reworded the repository-layout text off "gated by [iof3d]" to dormant-in-wheel (LIC-01, review finding 1).
- Confirmed `CITATION.cff` and `LICENSE` already declare BSD-3-Clause (LIC-04).
- Added `tests/core/test_packaging_metadata.py` (pure stdlib) pinning all of the above as a live CI gate.

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Write the metadata-assertion test (RED)** - `8b10649` (test)
2. **Task 2: Reconcile pyproject.toml classifiers and project URLs** - `2107e25` (feat, GREEN)
3. **Task 3: Reconcile README license + iof3d note, confirm CITATION/LICENSE** - `0505954` (feat, GREEN)

_Note: this plan is structured as one TDD cycle — Task 1 is the RED gate (test fails on the un-reconciled tree), Tasks 2-3 are the GREEN implementation that makes it pass._

## Files Created/Modified
- `tests/core/test_packaging_metadata.py` - New stdlib gate: 7 functions asserting no Private classifier, required classifiers, public Documentation/Changelog URLs, README BSD-not-Proprietary, [iof3d]-unavailable note, no stale iof3d extra references, tolerant CITATION/LICENSE BSD parse.
- `pyproject.toml` - Removed Private classifier + comment; added 3 trove classifiers; added Documentation + Changelog URLs under `[project.urls]`.
- `README.md` - License section → BSD-3-Clause; install section gains no-timeline [iof3d]-unavailable note; combinable command drops `iof3d`; repository-layout text reworded off "gated by [iof3d]".

## Decisions Made
- Documentation/Changelog URLs use forward-valid `blob/main` targets (`docs/index.md`, `CHANGELOG.md`); the changelog file is created by release-please in Phase 5, so the URL is intentionally forward-valid (per RESEARCH Focus 3).
- The `[iof3d]`-unavailable README note carries no timeline (session decision 1); the adapter is framed as shipping in the wheel but dormant until iof3D is public.
- CITATION.cff and LICENSE were confirm-only (already BSD-3-Clause); no edit made.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The mandated `conda run -n iof3d_cosicorr3d-dev312 pytest ...` resolves to a user-level `~/.local/bin/pytest` running under base python3.13 (no pandas), causing spurious collection errors in the broader core suite. Re-running via `conda run -n iof3d_cosicorr3d-dev312 python -m pytest` uses the env interpreter correctly: full core suite is green (120 passed). The new metadata test is stdlib-only and passes under either invocation. This is an env-invocation quirk, not a regression — noted here for downstream plans.

## Verification Results
- `python -m pytest tests/core/test_packaging_metadata.py` — 7 passed (GREEN).
- `python -m pytest tests/core` — 120 passed (no regressions).
- `ruff check pyproject.toml tests/core/test_packaging_metadata.py` + `ruff format --check` — clean.
- Baseline-diff pyright (`.planning/phases/02-targeted-fixes/pyright_gate.py`) — PASS: no new errors vs develop.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Two of the publish blockers (Private classifier, README/LICENSE mismatch) are cleared; metadata is publish-clean and gated by a live test.
- Plan 04-02 (packaging / iof3D import-guard, PKG-01) is unblocked.
- Phase 5 release tooling can rely on the metadata gate; the `Changelog` URL becomes live once release-please creates `CHANGELOG.md`.

## Self-Check: PASSED

All created files exist on disk; all task commits (`8b10649`, `2107e25`, `0505954`) present in git history.

---
*Phase: 04-licensing-metadata-packaging*
*Completed: 2026-06-27*
