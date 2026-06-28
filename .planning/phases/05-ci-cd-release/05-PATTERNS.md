# Phase 5: CI/CD & Release - Pattern Map

**Mapped:** 2026-06-27
**Files analyzed:** 14 (8 new, 6 modified) + 1 optional
**Analogs found:** 14 / 14 (6 local-tree analogs, 8 documented-in-RESEARCH PCHandler templates)

> **Read this first (analog provenance):** This phase is an *adaptation of a solved
> reference*. Most "new" files have **no local-tree analog** — their authoritative
> source is the `gseg-ethz/PCHandler` template, already **fetched verbatim into
> `05-RESEARCH.md`** (Patterns 1-3, the rulesets section, the `.readthedocs.yaml`
> block, the `conf.py` block). Where this map says *"analog = RESEARCH.md §X"*, the
> planner should copy the excerpt from RESEARCH, not search the codebase. Where it
> says *"analog = `<local file>`"*, the existing repo file is the pattern to copy/edit
> in place. All GitHub Action SHA pins live in **RESEARCH.md → Standard Stack table**
> — treat that table as the single source of truth for `uses:` pins (D-07).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.github/workflows/ci.yml` | config (CI workflow) | event-driven (push/PR) | `.github/workflows/ci.yml` (self, restructure) | exact (in-place) |
| `.github/workflows/release-please.yml` | config (workflow) | event-driven (workflow_run) | self + RESEARCH.md §Pattern 2 (PCHandler) | exact (rewrite) |
| `.github/workflows/publish-pypi.yml` | config (workflow) | event-driven (release:published) | RESEARCH.md §Pattern 1 (PCHandler); build steps from local `ci.yml` build job | exact (template) |
| `.github/workflows/publish-testpypi.yml` | config (workflow) | event-driven (workflow_dispatch) | sibling `publish-pypi.yml` + RESEARCH.md D-04 | role-match (template) |
| `.github/actions/setup-python-deps/action.yml` | config (composite action) | request-response (setup) | RESEARCH.md §Pattern 3 (PCHandler, parametrized) | role-match (template) |
| `.github/scripts/apply-rulesets.sh` | utility (script) | batch (gh api apply) | RESEARCH.md §Rulesets (Delivery block) | role-match (template) |
| `.github/rulesets/protect-main.json` | config (ruleset payload) | data (declarative) | RESEARCH.md §Rulesets (PCHandler 18108142 body) | exact (template) |
| `.github/rulesets/protect-develop.json` | config (ruleset payload) | data (declarative) | sibling `protect-main.json` (delta = ref + contexts) | exact (sibling) |
| `.readthedocs.yaml` | config | data (declarative) | RESEARCH.md §Docs (PCHandler verbatim) | exact (template) |
| `docs/source/conf.py` | config (sphinx) | request-response (build) | RESEARCH.md §Version Seeding + §Docs conf.py block | role-match (template, NOT PCHandler's heavy conf) |
| `docs/source/index.md` (+ moved `.md`) | content (docs) | transform (md→html) | `docs/index.md` (self, add myst toctree) | exact (in-place) |
| `pyproject.toml` | config (build/deps) | data (declarative) | `pyproject.toml` (self, targeted edits) | exact (in-place) |
| `pyrightconfig.json` | config (type-check) | data (declarative) | `pyrightconfig.json` (self, add excludes) | exact (in-place) |
| `.release-please-manifest.json` | config (version seed) | data (declarative) | self + `release-please-config.json` | exact (in-place) |
| `.github/scripts/check_publish_gate.py` *(optional)* | utility (lint guard) | transform/validation | RESEARCH.md §Optional publish-gate (PCHandler) | role-match (template) |

---

## Pattern Assignments

### `.github/workflows/ci.yml` (config, event-driven) — RESTRUCTURE in place

**Analog:** `.github/workflows/ci.yml` (self). Restructure per D-02/D-03(superseded→3.12-only)/D-07; do NOT rebuild. Matrix + job-name shapes come from RESEARCH.md §CI Topology.

**Keep verbatim — trigger + top-level permissions** (lines 1-10):
```yaml
name: CI                         # interface string — release-please workflow_run depends on it
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
permissions:
  contents: read
```
> Critical: `name: CI` is load-bearing (release-please `workflow_run.workflows: [CI]`). Do not rename. RESEARCH §Pitfall 2.

**Keep + SHA-pin — build job (already has twine check + install-smoke)** (lines 86-125). This is the existing CICD-02 implementation; preserve its structure, swap `@v4/@v5` tags for SHA pins from RESEARCH Standard Stack, keep `needs: [test]`:
```yaml
build:
  name: Build wheel + install smoke
  needs: [test]
  steps:
    - uses: actions/checkout@v4      # → SHA-pin 93cb6efe… (v5.0.1), keep fetch-depth:0 + fetch-tags:true (lines 91-95)
    - run: python -m build           # line 105
    - run: twine check dist/*        # line 108 — CICD-02
    - run: |                         # install-smoke into fresh venv (lines 113-118) — KEEP verbatim
        python -m venv /tmp/smoke-env
        /tmp/smoke-env/bin/pip install dist/*.whl
        /tmp/smoke-env/bin/geodispbench3d --help
    - uses: actions/upload-artifact@v4  # → SHA-pin 043fb46d… (v7.0.1)
```

**REPLACE — lint job** (current lines 13-45): currently installs only `.[dev]` and runs `pyright` unscoped. New: install `.[f2s3,dev]` on 3.12 (pchandler now public → f2s3 imports resolve), run scoped pyright (genuine 0-error, D-01a). Keep the existing `ruff check .` / `ruff format --check .` steps (lines 30-34) and the pinned-tools comment pattern (line 28: `ruff==0.15.12 pyright==1.1.392`).

**REPLACE — test job** (current lines 47-84): drop `needs: [lint]` (D-02: lint ∥ test). Drop the `enabled` string-flag pattern (lines 57-63, 68-84) in favor of `include:` matrix. New matrix from RESEARCH §CI Topology:
```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - { suite: core, python: "3.12", extras: "dev" }
      - { suite: f2s3, python: "3.12", extras: "f2s3,dev" }   # 3.12-only (pchandler pin)
name: Test (${{ matrix.suite }}, ${{ matrix.python }})
```
> Per Planning Amendment (D-03 SUPERSEDED): **3.12-only**, no 3.11 axis. Renders `Test (core, 3.12)` + `Test (f2s3, 3.12)`. The dormant `iof3d` slot is simply omitted (was lines 60, the `enabled:"false"` row).

**ADD — docs-build job** (no analog in current ci.yml): independent (not in any `needs:`), blocking-on-PR. `pip install -e .[docs]` then `sphinx-build -W --keep-going -b html docs/source docs/_build/html`. RESEARCH §Docs / §CI Topology.

**ADD (optional hardening, per Planning Amendments):** `actionlint` step + `check_publish_gate.py` invocation inside the lint job.

---

### `.github/workflows/release-please.yml` (config, event-driven) — REPLACE

**Analog:** self (for the `release-please-action` call shape + config/manifest wiring) + **RESEARCH.md §Pattern 2** (the new trigger + App-token mechanics, PCHandler-verbatim).

**Replace — trigger** (current lines 14-16 `on: push: branches:[main]`) → `workflow_run` after CI:
```yaml
on:
  workflow_run:
    workflows: [CI]          # must match ci.yml name: exactly
    types: [completed]
    branches: [main]
```

**Keep — permissions** (current lines 18-21, unchanged): `contents: write`, `pull-requests: write`, `issues: write`.

**Replace — token wiring** (current lines 32-37): the `secrets.RELEASE_PLEASE_TOKEN || secrets.GITHUB_TOKEN` pattern (line 35) is removed. New: gate `if: github.event.workflow_run.conclusion == 'success'`, mint App token via `actions/create-github-app-token` (`secrets.APP_ID` / `secrets.APP_PRIVATE_KEY`), pass that token to both checkout and the release-please action. Bump `googleapis/release-please-action@v4` (line 32) → **v5.0.0** SHA `45996ed1…` (Planning Amendment D-05/D-07).

**Keep — config/manifest args** (current lines 36-37): `config-file: release-please-config.json` + `manifest-file: .release-please-manifest.json` (explicit is fine; PCHandler omits manifest-file but keeping it is acceptable).

**Add — floating-tag move step** (no analog locally): `if: steps.release.outputs.release_created == 'true'`, move `vX` / `vX.Y` tags. Copy from RESEARCH §Pattern 2.

---

### `.github/workflows/publish-pypi.yml` (config, event-driven) — NEW

**Analog:** **RESEARCH.md §Pattern 1** (PCHandler verbatim, fetched 2026-06-27). Build-job hardening (`twine check`) borrowed from local `ci.yml` build job (line 108).

Two-job shape: `build` (`permissions: contents: read`, checkout with `fetch-depth:0 + fetch-tags:true`, `python -m build`, upload-artifact) → `publish-to-pypi` (`needs: build`, `environment: { name: pypi, url: https://pypi.org/p/geodispbench3d }`, `permissions: { id-token: write, attestations: write }`, download-artifact, `pypa/gh-action-pypi-publish` default URL). **Deviation (RESEARCH-recommended):** add `twine check dist/*` to the build job (mirror local CI habit). All SHAs from Standard Stack table.

---

### `.github/workflows/publish-testpypi.yml` (config, event-driven) — NEW

**Analog:** sibling `publish-pypi.yml` (above) with D-04 testpypi deltas: `on: workflow_dispatch`; `environment: { name: testpypi }`; publish step gets `repository-url: https://test.pypi.org/legacy/`, `attestations: false` (PEP 740 inconsistent on TestPyPI — RESEARCH anti-pattern), `skip-existing: true`, `permissions: { id-token: write }` only (no attestations write).

---

### `.github/actions/setup-python-deps/action.yml` (config, composite) — NEW

**Analog:** **RESEARCH.md §Pattern 3** (PCHandler's hard-coded composite, parametrized). Inputs `python-version` (default `"3.12"`) + `extras` (default `"dev"`); `using: composite`; steps = `setup-python` (SHA `a309ff8b…`) + `actions/cache` (SHA `27d5ce7f…`) + `pip install -e ".[${{ inputs.extras }}]"`. Caller must `actions/checkout` first. Discretionary (D-config) — RESEARCH recommends adopting it so the matrix + publish builds share one setup.

---

### `.github/rulesets/protect-main.json` (config, data) — NEW

**Analog:** **RESEARCH.md §Branch Protection** (PCHandler `protect-main` body, id 18108142, fetched verbatim). Rule body: `pull_request` (`required_approving_review_count: 0`, `allowed_merge_methods:[merge,squash,rebase]`), `required_status_checks` (`strict_required_status_checks_policy: false`), `non_fast_forward`, `deletion`, `required_linear_history`, `bypass_actors: []`, `enforcement: active`.

**geodispbench3d deltas:**
- `conditions.ref_name.include = ["refs/heads/main"]`.
- `required_status_checks` contexts = the **exact rendered CI job names** (Planning Amendment, 3.12-only):
  ```
  Lint (ruff + pyright)
  Test (core, 3.12)
  Test (f2s3, 3.12)
  Build wheel + install smoke
  ```
  (NOT PCHandler's `Lint (pre-commit)` / `Tests (pytest)`; NOT the symmetric 3.11/3.12 set the original D-08 anticipated.)

---

### `.github/rulesets/protect-develop.json` (config, data) — NEW

**Analog:** sibling `protect-main.json`. Only delta: `conditions.ref_name.include = ["refs/heads/develop"]` (plain `develop`, not PCHandler's `develop/gsd`). Same rule body + same status-check contexts.

---

### `.github/scripts/apply-rulesets.sh` (utility, batch) — NEW

**Analog:** **RESEARCH.md §Branch Protection (Delivery block)**.
```bash
gh api --method POST repos/gseg-ethz/geodispbench3d/rulesets --input .github/rulesets/protect-main.json
gh api --method POST repos/gseg-ethz/geodispbench3d/rulesets --input .github/rulesets/protect-develop.json
# --method PUT repos/.../rulesets/<id> to update existing
```
> Deliverable only — **not run during phase execution** (D-08: enable at milestone-ship to avoid self-lockout, RESEARCH Pitfall 4).

---

### `.readthedocs.yaml` (config, data) — NEW

**Analog:** **RESEARCH.md §Docs (PCHandler `.readthedocs.yaml`, fetched verbatim)**. `version: 2`, `build.os: ubuntu-24.04`, `tools.python: "3.12"`, `post_build` LICENSE copy, `sphinx.configuration: docs/source/conf.py`, `python.install` pip path `.` with `extra_requirements: [docs]`.
> **Naming delta to honor:** PCHandler's extra is `doc`; geodispbench3d's is `docs`. Use `docs` (RESEARCH explicit warning).

---

### `docs/source/conf.py` (config, sphinx) — NEW

**Analog:** **RESEARCH.md §Docs conf.py block** (the minimal geodispbench3d-shaped config) + **§Version Seeding** (importlib.metadata version derivation). **Do NOT copy PCHandler's ~250-line nitpicky autodoc conf** (RESEARCH explicit). Key lines: `extensions = ["myst_parser"]`, `html_theme = "sphinx_rtd_theme"`, `release = _v("geodispbench3d")` (setuptools_scm-derived → no `x-release-please-version` string, no `extra-files` entry).

---

### `docs/source/index.md` + moved Markdown (content, transform) — WIRE existing

**Analog:** `docs/index.md` (self). The existing root index already has the section structure ("Read me first" / "Pre-built tools" / "Integrating your own tool" / "Reference", lines 15-39) that converts directly into a myst `{toctree}`. RESEARCH §Docs recommends **layout (a)**: move the flat Markdown tree (`concepts.md`, `quickstart.md`, `integrating/`, `reference/`, `tools/`, `rescoring-and-analysis.md`) under `docs/source/` so it matches `.readthedocs.yaml: configuration: docs/source/conf.py`. Existing relative links mostly survive.

---

### `pyproject.toml` (config, build) — MODIFY in place

**Analog:** self. Targeted edits (line numbers from current file):
- Line 8: `requires-python = "~=3.11"` → `"~=3.12"` (Planning Amendment D-03 SUPERSEDED).
- Line 17: drop `"Programming Language :: Python :: 3.11"` classifier (keep 3.12 on line 18).
- Line 115: `target-version = "py311"` → `"py312"`.
- Line 86: `docs = ["sphinx ~= 5.1"]` → `docs = ["sphinx ~= 8.1", "myst-parser ~= 4.0", "sphinx-rtd-theme ~= 3.0"]` (Planning Amendment D-09 EXTENDED — **pin against a resolved `pip install -e .[docs]` before committing**, RESEARCH A2).
- `[project.scripts]` (line 40): unchanged (entry points already correct).

---

### `pyrightconfig.json` (config, type-check) — MODIFY in place

**Analog:** self. Edits:
- Line 12: `"pythonVersion": "3.11"` → `"3.12"` (Planning Amendment).
- `exclude` array (lines 3-10): add `"src/geodispbench3d_iof3d"` and `"tests/iof3d"` (D-01a scoping — RESEARCH §Pyright Scoping). Keep `reportMissingImports: "warning"` (line 14) so warnings don't fail exit code.
> Config alone is insufficient: RESEARCH §Pyright Scoping step 3 + Wave-0 Gaps — an explicit plan task must enumerate + **fix in code** the residual core type-narrowing errors to reach genuine exit-0.

---

### `.release-please-manifest.json` (config, version seed) — MODIFY

**Analog:** self (`{".": "0.0.0"}`) + `release-please-config.json` (release-type `simple`, `bump-minor-pre-major: true`, lines 6-7). RESEARCH §Version Seeding: **preferred mechanism is a one-shot `Release-As: 0.2.0` commit footer**, not editing the manifest sticky `release-as`. After the first cut the manifest auto-updates to `0.2.0`. (D-06.) The `changelog-sections` config (lines 12-25) needs no change.

---

### `.github/scripts/check_publish_gate.py` (utility, validation) — NEW *(optional, Planning Amendment: INCLUDED)*

**Analog:** **RESEARCH.md §Optional publish-gate** (PCHandler `check_publish_gate.py`). Adapt the `ALLOWED` map to geodispbench3d's two publish files; invoke from the lint job. Asserts `pypa/gh-action-pypi-publish` / `twine upload` appear only in `publish-pypi.yml` / `publish-testpypi.yml`.

---

## Shared Patterns

### Action SHA pinning (D-07)
**Source:** RESEARCH.md §Standard Stack table (all SHAs verified live this session).
**Apply to:** every `uses:` in `ci.yml`, `release-please.yml`, `publish-pypi.yml`, `publish-testpypi.yml`, `setup-python-deps/action.yml`.
Replace all `@vN` tags with the pinned commit SHA + a `# vX.Y.Z` trailing comment. Current local files use floating tags (`ci.yml` lines 17/19/65/67/91/97/121; `release-please.yml` lines 27/32) — all must be pinned.

### Interface strings (must match exactly)
**Source:** RESEARCH.md §Pitfall 2.
**Apply to:** all workflows + ruleset payloads.
- `ci.yml` `name: CI` ↔ `release-please.yml` `workflow_run.workflows: [CI]`.
- Rendered matrix job names (`Test (core, 3.12)`, `Test (f2s3, 3.12)`) ↔ ruleset `required_status_checks` contexts.
- Environment names `pypi` / `testpypi` ↔ PyPI/TestPyPI pending-publisher registration + GitHub Environments.
- `docs` extra name ↔ `.readthedocs.yaml` `extra_requirements` ↔ CI docs job install.
A one-character drift silently never satisfies the gate.

### Least-privilege workflow permissions
**Source:** local `ci.yml` line 9 (`permissions: contents: read`) + RESEARCH §Security Domain.
**Apply to:** all workflows. `contents: read` default; `id-token: write` only on publish jobs; `attestations: write` only on real-PyPI publish; `contents/pull-requests/issues: write` only on release-please.

### setuptools_scm tag fidelity
**Source:** local `ci.yml` build job (lines 91-95, `fetch-depth:0 + fetch-tags:true`) + RESEARCH §Pitfall 3.
**Apply to:** every build/publish checkout. Without it the wheel version falls back wrong. `local_scheme = "no-local-version"` already set.

### Local verification gate (AGENTS.md conda mandate)
**Source:** RESEARCH §Validation Architecture.
**Apply to:** every task's done-check. `conda run -n iof3d_cosicorr3d-dev312 <ruff|pyright|pytest|python -m build>` — never bare tools.

---

## No Analog Found

No file is without a usable analog. The 8 "new" files all have a verbatim PCHandler template captured in `05-RESEARCH.md`; the planner should treat RESEARCH as the analog source for those rather than searching the local tree (which has no publish workflows, composite actions, rulesets, scripts, or `docs/source/` layout yet).

| File | Why no local analog | Substitute analog |
|------|---------------------|-------------------|
| `publish-pypi.yml` / `publish-testpypi.yml` | repo has never published to PyPI | RESEARCH §Pattern 1 + local `ci.yml` build job |
| `setup-python-deps/action.yml` | no composite actions exist | RESEARCH §Pattern 3 |
| `rulesets/*.json` + `apply-rulesets.sh` | no rulesets applied yet | RESEARCH §Branch Protection |
| `.readthedocs.yaml` / `docs/source/conf.py` | no Sphinx scaffold yet | RESEARCH §Docs |
| `check_publish_gate.py` | no lint guard scripts | RESEARCH §Optional publish-gate |

## Metadata

**Analog search scope:** `.github/workflows/`, `.github/` (no actions/scripts/rulesets present), `docs/` (flat Markdown, no `source/`), `pyproject.toml`, `pyrightconfig.json`, `release-please-config.json`, `.release-please-manifest.json`.
**Files scanned:** 9 local config/workflow files + docs tree (15 Markdown files).
**External template:** `gseg-ethz/PCHandler` — captured verbatim in `05-RESEARCH.md` (not re-fetched here).
**Pattern extraction date:** 2026-06-27
