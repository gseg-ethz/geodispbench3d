---
phase: 05-ci-cd-release
plan: 02
subsystem: docs
tags: [sphinx, myst-parser, readthedocs, docs, packaging, links]

requires:
  - phase: 05-ci-cd-release
    plan: 01
    provides: docs extra (sphinx 8.3.0, myst-parser 4.0.1, sphinx-rtd-theme 3.0.2) resolved and import-proven; Python 3.12-only baseline
provides:
  - Self-contained Sphinx source tree under docs/source/ (existing Markdown moved, not rewritten to rST)
  - A warnings-as-errors (-W --keep-going) myst build that exits 0 over the existing docs — the target for Plan 05's docs-build CI job
  - .readthedocs.yaml mirroring PCHandler but referencing the `docs` extra; RTD project import deferred to post-public (D-09)
  - All repo-escaping relative doc links rewritten to absolute github blob/main (files) / tree/main (dirs) URLs; in-tree doc-to-doc links kept relative and -W-validated
affects: [05-05 CI restructure (docs-build job target), public RTD registration post-milestone]

tech-stack:
  added: []
  patterns:
    - "myst_heading_anchors=3 generates GitHub-style implicit header anchors so existing `file.md#section` cross-refs resolve under -W"
    - "Repo-escaping links rewritten to absolute github URLs (blob/main for files, tree/main for directories); in-tree links stay relative"
    - "Docs version derived from importlib.metadata.version (setuptools_scm), never hardcoded"

key-files:
  created:
    - docs/source/conf.py
    - .readthedocs.yaml
  modified:
    - docs/source/index.md
    - docs/source/concepts.md
    - docs/source/quickstart.md
    - docs/source/rescoring-and-analysis.md
    - docs/source/integrating/index.md
    - docs/source/integrating/datasets.md
    - docs/source/integrating/metrics.md
    - docs/source/reference/yaml-schemas.md
    - docs/source/tools/iof3d.md
    - docs/source/tools/f2s3.md
    - pyproject.toml
    - .gitignore

key-decisions:
  - "Adopted layout (a): git mv the flat docs/ Markdown under docs/source/ so the source dir is self-contained and matches .readthedocs.yaml configuration: docs/source/conf.py"
  - "Directory link targets use github tree/main (not blob/main) since GitHub 404s on blob/main/<dir>; file targets use blob/main per the Phase 04 convention — both are absolute https github.com/gseg-ethz URLs (keeps the packaging URL test green)"
  - "Kept the descriptive index bullet lists (relative in-tree links, -W-validated) and added :hidden: {toctree} groups for Sphinx navigation, instead of replacing the prose with bare toctrees"
  - "DOCS-01 is delivered by this plan (passing -W sphinx-build + PCHandler-mirroring .readthedocs.yaml)"

requirements-completed: [DOCS-01]

coverage:
  - id: D1
    description: "sphinx-build -W --keep-going -b html docs/source docs/_build/html exits 0 over the existing Markdown"
    requirement: "DOCS-01"
    verification:
      - kind: integration
        ref: "conda run -n iof3d_cosicorr3d-dev312 sphinx-build -W --keep-going -b html docs/source docs/_build/html -> exit 0, 0 warnings, index.html produced"
        status: pass
    human_judgment: false
  - id: D2
    description: ".readthedocs.yaml references docs/source/conf.py and the `docs` extra (not `doc`)"
    requirement: "DOCS-01"
    verification:
      - kind: unit
        ref: "yaml.safe_load asserts sphinx.configuration==docs/source/conf.py and 'docs' in python.install[0].extra_requirements"
        status: pass
    human_judgment: false
  - id: D3
    description: "project.urls.Documentation repointed to docs/source/index.md (blob/main); packaging URL test stays green"
    requirement: "DOCS-01"
    verification:
      - kind: unit
        ref: "tests/core/test_packaging_metadata.py::test_project_urls_documentation_and_changelog_public"
        status: pass
    human_judgment: false
  - id: D4
    description: "No repo-escaping relative link remains under docs/source/; in-tree doc links preserved relative"
    requirement: "DOCS-01"
    verification:
      - kind: other
        ref: "! grep -rEn '](\\.\\./(src|README|LICENSE)' docs/source; resolution-based rewrite resolved to true repo-root paths"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-06-28
status: complete
---

# Phase 5 Plan 02: Sphinx docs scaffold over the existing Markdown Summary

**Wired the existing narrative Markdown into a self-contained `docs/source/` Sphinx tree with a minimal myst config that builds warnings-clean under `-W`, rewrote every repo-escaping relative link to an absolute GitHub URL, repointed the packaged Documentation URL, and added a PCHandler-mirroring `.readthedocs.yaml` (referencing the `docs` extra) ready to activate hosting once the repo is public.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-06-28T07:28Z
- **Completed:** 2026-06-28T07:34Z
- **Tasks:** 3
- **Files modified/created:** 12 content files (+ docs tree renamed via git mv)

## Accomplishments
- Moved the flat `docs/` Markdown tree (concepts, quickstart, rescoring-and-analysis, `integrating/`, `reference/`, `tools/`) under `docs/source/` via `git mv` so the Sphinx source dir is self-contained and matches `.readthedocs.yaml`'s `configuration: docs/source/conf.py`.
- Converted the root `index.md` into a myst index: kept the descriptive bullet lists (relative in-tree links, validated by `-W`) and added `:hidden:` `{toctree}` groups (Read me first / Pre-built tools / Integrating / Reference) covering every page so there are no orphan-document warnings.
- Rewrote **every** repo-escaping relative link (`../src`, `../../src`, `../benchmarks`, `../AGENTS.md`) to an absolute `https://github.com/gseg-ethz/geodispbench3d/...` URL — `blob/main` for files, `tree/main` for directories — using a resolution-based script that resolves each link against the file's *original* `docs/` location (recovering the true repo-root target) while deciding in-tree-vs-escaping from the *new* `docs/source/` location. In-tree doc-to-doc links (`../integrating/cli-tool.md#...`) kept relative.
- Added a minimal `docs/source/conf.py`: `myst_parser` with `colon_fence`+`deflist`, `sphinx_rtd_theme`, `.md`/`.rst` `source_suffix`, version from `importlib.metadata.version("geodispbench3d")` (setuptools_scm, no hardcoded string), no autodoc/nitpick.
- Reached a genuinely warnings-clean `sphinx-build -W --keep-going` (exit 0, 0 warnings, `index.html` produced).
- Repointed `pyproject.toml` `project.urls.Documentation` from `docs/index.md` to `docs/source/index.md` (review HIGH 05-02) so the published Documentation URL is not dead after the move; packaging URL test stays green.
- Added `.readthedocs.yaml` (version 2, ubuntu-24.04, python 3.12, LICENSE post_build copy, `docs/source/conf.py`, `pip install .[docs]`) using the `docs` extra name (not PCHandler's `doc`). RTD project import deferred to post-public (D-09).

## Task Commits

Each task was committed atomically:

1. **Task 1: Move Markdown under docs/source, rewrite repo-escaping links, repoint Documentation URL** - `139a2a7` (docs)
2. **Task 2: Add minimal myst conf.py; make existing Markdown warnings-clean under -W** - `9edb8ff` (docs)
3. **Task 3: Add .readthedocs.yaml mirroring PCHandler (docs extra)** - `5b36eaf` (docs)

## Files Created/Modified
- `docs/source/conf.py` (new) - minimal myst config; `myst_heading_anchors=3`; metadata-derived version.
- `.readthedocs.yaml` (new) - PCHandler-mirroring build config referencing the `docs` extra.
- `docs/source/index.md` - intro prose + descriptive bullets + `:hidden:` toctree groups.
- `docs/source/{concepts,quickstart,rescoring-and-analysis}.md`, `integrating/{index,datasets,metrics}.md`, `reference/yaml-schemas.md`, `tools/{iof3d,f2s3}.md` - repo-escaping links rewritten to absolute GitHub URLs; `rescoring-and-analysis.md` also had one pseudo-JSON fence relabeled `json`->`text`.
- `pyproject.toml` - `project.urls.Documentation` -> `docs/source/index.md` (blob/main).
- `.gitignore` - ignore `docs/_build/` (generated HTML).
- (whole `docs/` Markdown tree renamed `docs/X` -> `docs/source/X` via `git mv`.)

## Decisions Made
- **Directory vs file URL kind.** The plan literally said rewrite escaping links to `blob/main/<path>`, but GitHub 404s on `blob/main/<directory>`. To keep the publication-ready docs link-correct, directory targets (those ending in `/`) were rewritten to `tree/main/` and file targets to `blob/main/`. Both remain absolute `https://github.com/gseg-ethz/geodispbench3d/...` URLs, so the packaging URL test and the Phase 04 host-path convention are still satisfied. Documented here as a minor refinement of the plan's URL form (Rule 1 — correctness).
- **Hidden toctrees over bare toctrees.** Kept the existing one-line page descriptions in `index.md` (useful to readers, and the relative links are `-W`-validated) and added `:hidden:` `{toctree}` groups purely for Sphinx's navigation sidebar — rather than discarding the prose for visible toctrees.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Link-rewrite resolution had to account for the git mv**
- **Found during:** Task 1
- **Issue:** The escaping links were authored relative to the *original* `docs/` location. A naive resolve against the *new* `docs/source/` location produced wrong repo-root paths (e.g. `docs/src/...` instead of `src/...`).
- **Fix:** The rewrite script decides in-tree-vs-escaping from the new location (so `-W` still validates surviving relative links) but resolves the absolute-URL target against the file's original `docs/` location, recovering the true repo-root path.
- **Files modified:** the 8 docs pages with escaping links.
- **Verification:** printed rewrite map inspected; `! grep -rEn '](\.\./(src|README|LICENSE)' docs/source` passes; in-tree `../integrating/...` links confirmed preserved.
- **Committed in:** `139a2a7`

**2. [Rule 1/3 - Blocking] Six `-W` warnings surfaced by the move (broke Task 2's core deliverable)**
- **Found during:** Task 2 (first `sphinx-build -W` run)
- **Issue:** Four `myst.xref_missing` warnings (in-tree `file.md#section` anchor links: `subprocess-contract`, `locating-outputs`, `package-cli-exit-codes`, `how-f2s3-plugs-in`) because myst's implicit heading anchors are off by default; plus one `misc.highlighting_failure` from an illustrative pseudo-JSON block (`[...]`, `sha256:...` placeholders) that pygments can't lex as `json`. (Reported as 6 because two pages reference the same missing anchor.)
- **Fix:** Set `myst_heading_anchors = 3` in `conf.py` (all four target headers are h2, so depth 3 covers them); relabeled the one pseudo-JSON fence in `rescoring-and-analysis.md` from `json` to `text`.
- **Files modified:** `docs/source/conf.py`, `docs/source/rescoring-and-analysis.md`
- **Verification:** `sphinx-build -W --keep-going` re-run -> exit 0, 0 warnings, `index.html` produced.
- **Committed in:** `9edb8ff`

**3. [Rule 3 - Blocking] Untracked generated build output**
- **Found during:** Task 2 (post-build `git status`)
- **Issue:** `docs/_build/` (generated HTML) was untracked and not ignored.
- **Fix:** Added `docs/_build/` to `.gitignore`.
- **Files modified:** `.gitignore`
- **Committed in:** `9edb8ff`

---

**Total deviations:** 3 (all auto-fixed; none architectural). All were required to satisfy the plan's own success criterion — a warnings-clean `-W` build over the existing Markdown.
**Impact on plan:** None to scope; the docs build is genuinely warnings-clean and the link rewrite is correct against the true repo root.

## Issues Encountered
- **Bare `pytest` resolves to the wrong interpreter.** Used `conda run -n iof3d_cosicorr3d-dev312 python -m pytest ...` for the packaging-metadata gate per the project rule (the plan's verify line wrote bare `pytest`).

## User Setup Required
None for this plan. RTD project registration on readthedocs.org is deferred to **post-public** (D-09) — `.readthedocs.yaml` is committed and ready, but the project is not imported on RTD while the repo is private.

## Next Phase Readiness
- Plan 05 (CI restructure) can wire a docs-build job that runs `sphinx-build -W --keep-going -b html docs/source docs/_build/html` against the `docs` extra — the target now exists and is green.
- No blockers. Public RTD import remains the only post-public follow-up.

## Self-Check: PASSED

- All created/modified artifacts present on disk (`docs/source/index.md`, `docs/source/conf.py`, `.readthedocs.yaml`, `docs/source/tools/`).
- All three task commits found in git history (`139a2a7`, `9edb8ff`, `5b36eaf`).
- `sphinx-build -W` exits 0 with 0 warnings.

---
*Phase: 05-ci-cd-release*
*Completed: 2026-06-28*
