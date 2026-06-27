# Phase 5: CI/CD & Release - Research

**Researched:** 2026-06-27
**Domain:** GitHub Actions CI/CD, OIDC trusted publishing to PyPI, release-please, branch-protection rulesets, Sphinx/ReadTheDocs
**Confidence:** HIGH (canonical template `gseg-ethz/PCHandler` fetched live; all action SHAs + PyPI versions verified this session)

## Summary

This phase is an **adaptation of a solved reference**, not a greenfield design. The sibling repo `gseg-ethz/PCHandler` (same org, same author) already ships the exact CI/CD + publish + release-please + ruleset + RTD topology this phase needs, and all of its current artifacts were fetched live via `gh api` during this research. The dominant planning activity is **porting PCHandler's patterns onto geodispbench3d's shape** (matrix suites, the dormant iof3D plugin, setuptools_scm versioning), not inventing pipeline architecture.

There is **one genuinely new constraint** that PCHandler does not have and that breaks a naive mirror: `pchandler 2.1.0` (the dependency behind geodispbench3d's `f2s3` extra) declares `requires-python = ">=3.12,<3.13"` on PyPI `[VERIFIED: pypi.org/pypi/pchandler/json]`. The `f2s3` test job therefore **cannot run on Python 3.11** — `pip install .[f2s3,dev]` will fail to resolve there. The test matrix must split: `core` on {3.11, 3.12}, `f2s3` on {3.12 only}. This is the highest-risk pitfall in the phase and shapes both the matrix and the D-08 required-status-check contexts.

The second substantive item is that D-01a's "genuinely 0-error pyright" is **not purely a config change**. Excluding the private `geodispbench3d_iof3d` package removes the bulk of the standing red (unresolvable `iof3D`/`pc2img` imports), and installing the now-public `pchandler` resolves the `f2s3` adapter's imports — but the ROADMAP records "a few pre-existing type-narrowing errors" in the core that scoping will *not* hide. The plan needs an explicit task to enumerate and fix those residual core errors to actually reach exit-0.

**Primary recommendation:** Mirror PCHandler's `publish-pypi.yml`, `publish-testpypi.yml`, `release-please.yml` (workflow_run + GitHub-App-token), the two rulesets, the `.readthedocs.yaml`, and the SHA-pinning discipline verbatim where possible; deviate only for (a) the `core`/`f2s3` matrix split forced by pchandler's 3.12-only pin, (b) setuptools_scm-driven versioning (no `x-release-please-version` string in `conf.py`), and (c) a `Release-As: 0.2.0` bootstrap commit to seed the first public version.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Keep pyright as the enforced CI type gate — mypy rejected.
- **D-01a:** Make pyright *genuinely* 0-errors by scoping to the tool-agnostic core. Exclude the `geodispbench3d_iof3d` plugin package from the lint-job pyright run and treat unresolvable plugin imports as ignored; iof3D adapter type-checked only inside the (disabled) iof3d test job. Supersedes Phase 2 D-11/D-12 baseline-diff with a real green gate. (Exact `pyrightconfig.json`/per-job mechanics = planning detail.)
- **D-02:** lint and test run in parallel; build `needs: [test]`. Drop the linear lint→test→build chain.
- **D-03:** Expand the test matrix to Python 3.11 AND 3.12. ubuntu-only. `core` + `f2s3` jobs enabled; `iof3d` matrix job stays disabled.
- **D-04:** Two publish workflows, OIDC trusted publishing, GitHub Environments.
  - `publish-pypi.yml`: `on: release: published`; `build` → `publish` (`needs: build`), Environment `pypi`, `permissions: id-token: write` + `attestations: write`, `pypa/gh-action-pypi-publish` (default real-PyPI URL), PEP 740 attestations on.
  - `publish-testpypi.yml`: manual `workflow_dispatch` dry-run to Environment `testpypi` (`repository-url: https://test.pypi.org/legacy/`, `attestations: false`, `skip-existing: true`, `id-token: write` only).
- **D-05:** `release-please.yml` triggers `on: workflow_run: workflows: [CI]: types: [completed]: branches: [main]`, gated `if: workflow_run.conclusion == 'success'`. Authenticate via `actions/create-github-app-token` with the reused gseg-ethz GitHub App (`APP_ID`/`APP_PRIVATE_KEY`). Move floating `vX`/`vX.Y` tags after `release_created`. Replaces the current `on: push: main` + `GITHUB_TOKEN||PAT` wiring.
- **D-06:** First public release is v0.2.0, not v1.0. Milestone relabeled v1.0 → v0.2 (update PROJECT.md/STATE/init `milestone_version`). Seed the release-please manifest (currently `0.0.0`) so the first cut lands `0.2.0` (manifest seed / `Release-As: 0.2.0` — exact mechanism a planning detail).
- **D-07:** Pin all GitHub Actions by commit SHA. Apply across `ci.yml` + the new workflows.
- **D-08:** Two rulesets, `protect-main` (on `main`) and `protect-develop` (on `develop`). Each: `pull_request` with `required_approving_review_count: 0`, all merge methods; `required_status_checks` with `strict: false`, contexts = the final CI job names (lint, test 3.11, test 3.12, build); `non_fast_forward`, `deletion`, `required_linear_history`, no bypass actors. Delivered as a committed `gh api` apply script + docs; enabled at milestone-ship, not now.
- **D-09:** Full Sphinx scaffold + RTD config now; RTD activates at go-public. Add `docs/source/conf.py` + `myst-parser` (consume existing Markdown), make a docs build pass, add `.readthedocs.yaml` mirroring PCHandler (sphinx config path, install `docs` extra, post_build LICENSE copy). Add `myst-parser` to the `docs` extra. RTD project import/activation deferred until repo is public. A docs-build CI check is a planning option.

### Claude's Discretion

- Exact `pyrightconfig.json` exclude mechanics and per-job pyright invocation. → **Recommendation below (Pyright Scoping section).**
- Precise CI job names / matrix shape (must match D-08 required-check contexts). → **Recommendation below (CI Topology section).**
- release-please v0.2.0 seeding mechanism (manifest seed vs `Release-As`). → **Recommendation: `Release-As: 0.2.0` bootstrap commit.**
- Whether the docs build is a blocking or informative CI job. → **Recommendation: blocking (`-W`), runs on 3.12 in its own job, not in `needs:` of build/test.**
- Whether to factor a `setup-python-deps` composite action (PCHandler does). → **Recommendation: yes, but parametrized (`python-version` + `extras` inputs) so the matrix can reuse it.**

### Deferred Ideas (OUT OF SCOPE)

- iof3D re-enablement (`iof3d` extra + its CI test job + matrix slot) — Phase 4 deferral, ~6 months out.
- Full governance ruleset (CODEOWNERS, required-review count, signed-commit enforcement) — its own phase if wanted.
- OS matrix (macOS / Windows) — ubuntu-only.
- GPU / canary workflows (PCHandler has `canary.yml`, `gpu-image-refresh.yml`) — not in scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CICD-01 | CI runs lint (ruff), type-check (pyright), and the full test matrix across 3.11/3.12 | CI Topology section: lint job (ruff+pyright, genuine 0-error via D-01a scoping) ‖ test matrix (core 3.11/3.12, f2s3 3.12). Pchandler-3.12 pitfall forces the split. |
| CICD-02 | CI builds wheel + sdist and validates (`twine check`) | Build job (mirror existing `ci.yml` build job: `python -m build` + `twine check dist/*` + install-smoke), `needs: [test]`. Publish path rebuilds + can re-`twine check`. |
| CICD-03 | A tagged release publishes to PyPI via OIDC trusted publishing, no stored tokens | `publish-pypi.yml` (D-04) — verbatim mirror of PCHandler: `release: published` → build → publish job with `id-token: write` + Environment `pypi`, `pypa/gh-action-pypi-publish`. Requires PyPI pending publisher (external prereq). |
| CICD-04 | Release automation (release-please) aligned end-to-end with publish | `release-please.yml` (D-05) `workflow_run` after CI + GitHub-App token; `release: published` event from the GitHub Release release-please creates triggers `publish-pypi.yml`. Manifest seed (D-06). |
| PROT-01 | Branch protection for `main` + `develop` | Rulesets section: two `gh api` rulesets mirroring PCHandler's `protect-main`/`protect-develop-gsd`, contexts pinned to the new CI job names. |
| DOCS-01 | Sphinx + ReadTheDocs wiring | Docs section: `docs/source/conf.py` + myst-parser over existing Markdown, `.readthedocs.yaml` mirror, `docs` extra bump. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lint + type-check gate | GitHub Actions (CI) | local conda env (AGENTS.md) | Quality enforced in CI; reproduced locally via `conda run -n iof3d_cosicorr3d-dev312`. |
| Test matrix | GitHub Actions (CI) | — | Multi-Python validation only meaningful on hosted runners. |
| Build + twine check | GitHub Actions (CI build job) | — | Distribution validation gate before publish. |
| Trusted publishing | GitHub Actions + PyPI OIDC | GitHub Environments | OIDC short-lived token minted per-run; Environment scopes the trusted publisher. |
| Version bump + changelog + tag | release-please (GitHub Actions) | git tags / setuptools_scm | release-please owns the *decision*; setuptools_scm reads the resulting tag for the wheel version. |
| Branch protection | GitHub repo rulesets (API) | committed apply script | Enforcement lives in repo settings, delivered reproducibly via `gh api`. |
| Docs build + hosting | Sphinx (local/CI) + ReadTheDocs | `.readthedocs.yaml` | Build is reproducible locally/CI; hosting activates post-public. |

## Standard Stack

### Core (GitHub Actions, SHA-pinned per D-07)

All SHAs below were fetched live and cross-checked against their git tags via the GitHub API this session, and are the exact pins the canonical template `gseg-ethz/PCHandler` currently uses.

| Action | Pinned SHA | Tag | Purpose | Provenance |
|--------|-----------|-----|---------|-----------|
| `actions/checkout` | `93cb6efe18208431cddfb8368fd83d5badbf9bfd` | v5.0.1 | repo checkout | `[VERIFIED: GitHub API git/ref/tags + PCHandler]` |
| `actions/setup-python` | `a309ff8b426b58ec0e2a45f0f869d46889d02405` | v6.2.0 | Python toolchain | `[VERIFIED: GitHub API + PCHandler]` |
| `actions/cache` | `27d5ce7f107fe9357f9df03efb73ab90386fccae` | v5.0.5 | pip cache | `[VERIFIED: GitHub API + PCHandler]` |
| `actions/upload-artifact` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | v7.0.1 | dist artifact upload | `[VERIFIED: GitHub API + PCHandler]` |
| `actions/download-artifact` | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` | v8.0.1 | dist artifact download | `[VERIFIED: GitHub API + PCHandler]` |
| `pypa/gh-action-pypi-publish` | `cef221092ed1bacb1cc03d23a2d87d1d172e277b` | v1.14.0 | OIDC trusted publish | `[VERIFIED: GitHub API annotated-tag deref + PCHandler]` |
| `actions/create-github-app-token` | `bcd2ba49218906704ab6c1aa796996da409d3eb1` | v3.2.0 | mint App token for release-please | `[VERIFIED: GitHub API + PCHandler]` |
| `googleapis/release-please-action` | `45996ed1f6d02564a971a2fa1b5860e934307cf7` | v5.0.0 | release PR + tag/release | `[VERIFIED: GitHub API + PCHandler]` |

> **Note on `pypa/gh-action-pypi-publish`:** v1.14.0 is an *annotated* tag. `git/ref/tags/v1.14.0` returns the tag-object SHA (`6733eb7…`); dereferencing it yields the commit `cef2210…`, which is the correct pin. Verified this session.
>
> **Note on `release-please-action`:** the **current local** `release-please.yml` uses `@v4`. PCHandler (the mirror source) is on **v5.0.0** (`45996ed…`). v5 is a re-tag of the v4-era action with the same inputs used here (`token`, `config-file`, `manifest-file`, outputs `release_created`/`major`/`minor`). **Recommend matching PCHandler at v5.0.0** for mirror fidelity; this is a major-tag bump and a `[deliberate-informed]` user-facing change — surface it in the plan.

### Supporting (Python tooling, versions verified on PyPI this session)

| Library | Version | Purpose | Provenance |
|---------|---------|---------|-----------|
| `pchandler` (dep of `f2s3` extra) | `2.1.0`, requires-python `>=3.12,<3.13` | F2S3 parser deps | `[VERIFIED: pypi.org/pypi/pchandler/json]` — **the 3.11 blocker** |
| `myst-parser` | latest `5.1.0` (requires-python `>=3.11`) | render existing Markdown via Sphinx | `[VERIFIED: pypi.org/pypi/myst-parser/json]` |
| `sphinx` | currently pinned `~=5.1`; latest `9.1.0` (requires-python `>=3.12`) | docs builder | `[VERIFIED: pypi.org/pypi/sphinx/json]` |
| `sphinx-rtd-theme` | latest `3.1.0` | RTD HTML theme (PCHandler uses it) | `[VERIFIED: pypi.org/pypi/sphinx-rtd-theme/json]` |
| `build`, `twine` | unpinned (CI build job) | sdist/wheel + `twine check` | `[CITED: existing ci.yml]` |
| `ruff` | `~=0.15` (CI pins `0.15.12`) | lint + format | `[CITED: pyproject dev extra + ci.yml]` |
| `pyright` | `~=1.1` (CI pins `1.1.392`) | type gate | `[CITED: pyproject dev extra + ci.yml]` |

**Docs toolchain version decision (needs user confirmation — `[deliberate-informed]`):** `sphinx ~= 5.1` (current pin) is old. myst-parser 5.x and sphinx 9.x both target newer Sphinx/Python. Two coherent options:
- **(a) Minimal change:** keep `sphinx ~= 5.1`, add `myst-parser ~= 1.0` (the myst line that still supports Sphinx 5) + `sphinx-rtd-theme`. Lowest churn; risk of myst/Sphinx-5 edge cases. `[ASSUMED]` on the exact `myst-parser ~=1.0`↔Sphinx-5 compatibility window — verify at install time.
- **(b) Mirror PCHandler:** bump to a modern set, e.g. `sphinx ~= 8.1` + `myst-parser ~= 4.0` + `sphinx-rtd-theme ~= 3.0`, docs build on 3.12 only. Closer to the reference, better long-term. `[ASSUMED]` on the exact triple — pin against a resolved install during the plan.

Recommend **(b)** for mirror fidelity, but it is a dependency bump → ask the user (per the interactive-mode rule) before locking.

**Installation (docs extra, option b shape):**
```toml
docs = ["sphinx ~= 8.1", "myst-parser ~= 4.0", "sphinx-rtd-theme ~= 3.0"]
```
Verify the resolved versions with `conda run -n iof3d_cosicorr3d-dev312 pip install -e .[docs]` before committing the pins.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `workflow_run` + GitHub App token (D-05) | `on: push: main` + PAT | PAT is a stored long-lived secret (violates the no-tokens spirit) and a fine-grained PAT still can't re-trigger required checks as cleanly; GitHub App token is the solved PCHandler pattern. |
| OIDC trusted publishing (D-04) | API-token publish | Stored long-lived token; explicitly rejected by CICD-03. |
| setuptools_scm version (existing) | release-please `python` release-type editing `__version__` | geodispbench3d already derives version from git tags; keep single source of truth. |
| `myst-parser` over existing `.md` | rewrite docs as `.rst` | Pointless churn; the existing Markdown is current and good. |

## Package Legitimacy Audit

> This phase installs no new *runtime* dependencies into the product. New additions are dev/docs-only Python packages plus SHA-pinned GitHub Actions.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `myst-parser` | PyPI | mature (executablebooks) | very high | github.com/executablebooks/MyST-Parser | OK | Approved |
| `sphinx-rtd-theme` | PyPI | mature | very high | github.com/readthedocs/sphinx_rtd_theme | OK | Approved |
| `sphinx` | PyPI | mature | very high | github.com/sphinx-doc/sphinx | OK | Approved (already a dep) |
| `pchandler` | PyPI | first-party (gseg-ethz) | low (org pkg) | github.com/gseg-ethz/PCHandler | OK | Already pinned in `f2s3` extra (Phase 4); **3.12-only** |

GitHub Actions are all pinned to commit SHAs verified against their published tags via the GitHub API this session (see Standard Stack table). No `[SLOP]`/`[SUS]` verdicts.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
                        ┌─────────────────────────── PR / push (main, develop) ───────────────────────────┐
                        │                                                                                  │
                        ▼                                                                                  │
   ┌──────────────────────── ci.yml (name: CI) ────────────────────────┐                                  │
   │                                                                    │                                  │
   │   lint  ─────────────┐         test (matrix) ─────────┐           │   (lint ∥ test run in parallel,  │
   │   ruff + ruff-format │         core / 3.11             │           │    D-02; build needs: [test])    │
   │   pyright (0-error,  │         core / 3.12             │           │                                  │
   │   D-01a scoped)      │         f2s3 / 3.12 (pchandler) │           │                                  │
   │                      │              │                  │           │                                  │
   │   docs-build (3.12,  │              ▼                  │           │                                  │
   │   sphinx -W, blocking)│        build ◄── needs:[test] ─┘           │                                  │
   │                       │        python -m build → twine check       │                                  │
   │                       │        → install-smoke → upload-artifact   │                                  │
   └───────────────────────┴────────────────────────────────────────────┘                                 │
                        │ CI conclusion == success on main                                                 │
                        ▼                                                                                   │
   ┌──────── release-please.yml (on: workflow_run [CI] completed, branch main) ────────┐                   │
   │  if conclusion == 'success'                                                        │                   │
   │  create-github-app-token (gseg-ethz App, APP_ID/APP_PRIVATE_KEY)                   │                   │
   │  release-please-action → maintains Release PR; on merge cuts tag vX.Y.Z + Release  │                   │
   │  if release_created: move floating vX / vX.Y tags                                  │                   │
   └───────────────────────────────────┬───────────────────────────────────────────────┘                  │
                                        │ GitHub Release "published"                                        │
                                        ▼                                                                    │
   ┌──────── publish-pypi.yml (on: release: published) ────────┐                                            │
   │  build job (checkout fetch-tags → python -m build)         │   setuptools_scm reads tag vX.Y.Z         │
   │      │ upload-artifact                                     │   → wheel/sdist version == X.Y.Z          │
   │      ▼                                                     │                                            │
   │  publish job  needs:[build]  Environment: pypi             │                                            │
   │      id-token: write + attestations: write (PEP 740)       │── OIDC ──► PyPI trusted publisher ────────┘
   │      pypa/gh-action-pypi-publish (default upload URL)      │
   └───────────────────────────────────────────────────────────┘

   ┌──────── publish-testpypi.yml (on: workflow_dispatch — manual dry-run) ────────┐
   │  build → publish (Environment: testpypi, id-token only,                        │── OIDC ──► TestPyPI
   │  repository-url=test.pypi.org/legacy/, attestations:false, skip-existing:true) │
   └────────────────────────────────────────────────────────────────────────────────┘

   Enforcement layer (PROT-01, enabled at milestone-ship):
     rulesets/protect-main, protect-develop → required_status_checks = exact CI job names above
```

### Recommended Project Structure (new/changed files)
```
.github/
├── actions/
│   └── setup-python-deps/action.yml   # parametrized composite (python-version, extras)
├── workflows/
│   ├── ci.yml                         # RESTRUCTURE (D-02/D-03/D-07): lint ∥ test-matrix, build needs:[test], docs-build
│   ├── release-please.yml             # REPLACE (D-05): workflow_run + App token
│   ├── publish-pypi.yml               # NEW (D-04): release:published → OIDC publish
│   └── publish-testpypi.yml           # NEW (D-04): workflow_dispatch dry-run
├── scripts/
│   └── apply-rulesets.sh              # NEW (D-08): gh api ruleset apply script
└── rulesets/
    ├── protect-main.json              # NEW (D-08): ruleset payload
    └── protect-develop.json           # NEW (D-08): ruleset payload
.readthedocs.yaml                      # NEW (D-09)
docs/source/conf.py                    # NEW (D-09): sphinx + myst config
docs/source/index.md (+ existing .md)  # WIRE existing Markdown via myst toctree
pyproject.toml                         # docs extra bump (+ myst-parser); no version changes (setuptools_scm)
pyrightconfig.json                     # exclude geodispbench3d_iof3d (D-01a)
.release-please-manifest.json          # seed for 0.2.0 (D-06)
docs/source/_static/                   # theme assets (optional)
```

### Pattern 1: OIDC trusted publishing (publish-pypi.yml) — verbatim mirror
**What:** `release: published` triggers a `build` job (fresh checkout with `fetch-tags` so setuptools_scm sees the tag) that uploads dist artifacts, then a `publish` job (`needs: build`) bound to GitHub Environment `pypi` with `id-token: write` + `attestations: write`, invoking `pypa/gh-action-pypi-publish` with no `repository-url` (defaults to real PyPI).
**When to use:** the CICD-03 publish path.
**Example (PCHandler, adapt `pchandler`→`geodispbench3d`):**
```yaml
# Source: gseg-ethz/PCHandler .github/workflows/publish-pypi.yml (fetched 2026-06-27)
name: Publish to PyPI
"on":
  release:
    types: [published]
jobs:
  build:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
        with: { fetch-depth: 0, fetch-tags: true }
      - uses: ./.github/actions/setup-python-deps   # or inline setup-python
      - run: pip install build && python -m build --wheel --sdist
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a  # v7.0.1
        with: { name: "dist-${{ github.run_id }}", path: dist/, retention-days: 1 }
  publish-to-pypi:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: pypi, url: https://pypi.org/p/geodispbench3d }
    permissions: { id-token: write, attestations: write }
    steps:
      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c  # v8.0.1
        with: { name: "dist-${{ github.run_id }}", path: dist/ }
      - uses: pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b  # v1.14.0
        # attestations default true (PEP 740); default upload URL = real PyPI
```
**Recommended deviation:** add a `twine check dist/*` step in the `build` job to satisfy CICD-02 on the publish path too (PCHandler's build job omits it; geodispbench3d's existing CI build job has it — keep the habit).

### Pattern 2: release-please via workflow_run + GitHub-App token (the protected-main fix)
**What:** `GITHUB_TOKEN`'s pushes don't trigger downstream workflows and can't satisfy required checks on a protected `main`. Mint a GitHub-App token instead; trigger release-please only after CI succeeds.
**When to use:** D-05, the core CICD-04 wiring.
**Example:**
```yaml
# Source: gseg-ethz/PCHandler .github/workflows/release-please.yml (fetched 2026-06-27)
name: release-please
on:
  workflow_run:
    workflows: [CI]            # MUST match ci.yml `name:` exactly
    types: [completed]
    branches: [main]
permissions: { contents: write, pull-requests: write, issues: write }
jobs:
  release-please:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - id: app-token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1  # v3.2.0
        with: { app-id: ${{ secrets.APP_ID }}, private-key: ${{ secrets.APP_PRIVATE_KEY }} }
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
        with: { fetch-depth: 0, fetch-tags: true, token: ${{ steps.app-token.outputs.token }} }
      - uses: googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7  # v5.0.0
        id: release
        with: { token: ${{ steps.app-token.outputs.token }}, config-file: release-please-config.json }
      - name: Tag major and minor versions
        if: ${{ steps.release.outputs.release_created == 'true' }}
        run: |
          git config user.name github-actions[bot]
          git config user.email 41898282+github-actions[bot]@users.noreply.github.com
          git tag -d v${{ steps.release.outputs.major }} || true
          git push origin :refs/tags/v${{ steps.release.outputs.major }} || true
          git tag -a v${{ steps.release.outputs.major }} -m "Release v${{ steps.release.outputs.major }}"
          git push origin v${{ steps.release.outputs.major }}
          # repeat for v${major}.${minor}
```
**Note:** PCHandler's `release-please-action` call omits `manifest-file` (it relies on the config default `.release-please-manifest.json`). geodispbench3d's current call passes it explicitly — either is fine; keep `manifest-file` if you want it explicit.

### Pattern 3: Parametrized composite setup action
**What:** PCHandler's `setup-python-deps` hard-codes Python 3.12 + `.[dev]`, which can't serve a multi-Python, multi-extra matrix. Parametrize it.
**Example:**
```yaml
# .github/actions/setup-python-deps/action.yml (adapted from PCHandler)
name: Setup Python + deps (geodispbench3d)
inputs:
  python-version: { default: "3.12" }
  extras:         { default: "dev" }       # e.g. "f2s3,dev"
runs:
  using: composite
  steps:
    - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
      with: { python-version: ${{ inputs.python-version }} }
    - uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
      with:
        path: ~/.cache/pip
        key: pip-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('pyproject.toml') }}
    - shell: bash
      run: pip install -e ".[${{ inputs.extras }}]"
```
Caller MUST `actions/checkout` before invoking (local composite needs the repo on disk).

### Anti-Patterns to Avoid
- **Running `f2s3` on Python 3.11.** `pip install .[f2s3,dev]` fails — `pchandler 2.1.0` is `>=3.12,<3.13`. Use matrix `include:` to keep `f2s3` to 3.12 only.
- **Letting `GITHUB_TOKEN` cut releases on protected main.** Its pushes don't trigger required checks → release PR stuck. Use the App token (D-05).
- **Forgetting `fetch-tags: true` in build/publish checkout.** setuptools_scm would derive a `0.1.0`/`+dirty` fallback version, publishing a wrong version.
- **Required-status-check contexts that don't match rendered job names.** A matrix job's check name is `JobName (axis1, axis2)`; a one-character mismatch silently never satisfies the gate. Pin contexts to the exact rendered strings.
- **`attestations: true` on TestPyPI.** PEP 740 support on TestPyPI is inconsistent; the dry-run sets `attestations: false`.
- **Config-only pyright "green."** Scoping hides the plugin imports but not the residual core type errors — those must be fixed in code.

## Pyright Scoping (D-01a) — recommended mechanics

**Goal:** `pyright` exits 0 on the public tool-agnostic surface in the lint job.

1. **`pyrightconfig.json`:** add the private plugin package and its tests to `exclude`:
   ```jsonc
   "exclude": [
     "**/__pycache__", "**/.pytest_cache", "build", "dist", ".venv",
     "src/geodispbench3d/_version.py",
     "src/geodispbench3d_iof3d",     // private; iof3D/pc2img unresolvable in public CI
     "tests/iof3d"                    // its tests import the iof3D stack
   ]
   ```
   Keep `reportMissingImports: "warning"` (warnings don't fail pyright's exit code; only errors do). `[CITED: microsoft.github.io/pyright/#/configuration — exit code is nonzero only on errors]`
2. **Lint job installs `.[f2s3,dev]` on Python 3.12.** `pchandler` is now public and 3.12-compatible, so the `geodispbench3d_f2s3` adapter's imports resolve and it type-checks for real (no need to also exclude it). This is a deliberate improvement over the existing lint job, which installs only `.[dev]`.
3. **Residual core errors:** the ROADMAP records "a few pre-existing type-narrowing errors" beyond the plugin imports. **Add an explicit plan task** to run the scoped pyright locally (`conda run -n iof3d_cosicorr3d-dev312 pyright`), enumerate the remaining errors, and fix them in code until exit 0. Do not assume the exclude alone is sufficient.
4. **Disabled `iof3d` test job:** when re-enabled (future), it runs pyright with the iof3D stack installed over `src/geodispbench3d_iof3d`. Out of scope now; just leave the package excluded from the lint run.

## CI Topology (D-02/D-03) — recommended job + matrix shape

**`ci.yml` keeps `name: CI`** (release-please's `workflow_run.workflows: [CI]` depends on this exact string).

| Job (recommended `name:`) | Runs on | Trigger gate | Notes |
|---------------------------|---------|--------------|-------|
| `Lint (ruff + pyright)` | 3.12 | independent (D-02) | ruff check, ruff format --check, pyright (scoped). Installs `.[f2s3,dev]`. |
| `Test (core, 3.11)` | 3.11 | independent | `pip install -e .[dev]`; `pytest tests/core` |
| `Test (core, 3.12)` | 3.12 | independent | `pip install -e .[dev]`; `pytest tests/core` |
| `Test (f2s3, 3.12)` | 3.12 | independent | `pip install -e .[f2s3,dev]`; `pytest tests/f2s3` — **3.12 only (pchandler pin)** |
| `Build wheel + install smoke` | 3.12 | `needs: [test]` | `python -m build` → `twine check dist/*` → install-smoke → upload-artifact |
| `Docs build` | 3.12 | independent (recommend blocking) | `pip install -e .[docs]`; `sphinx-build -W --keep-going -b html docs/source docs/_build/html` |

**Matrix mechanism (use `include:` for asymmetric combos):**
```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - { suite: core, python: "3.11", extras: "dev" }
      - { suite: core, python: "3.12", extras: "dev" }
      - { suite: f2s3, python: "3.12", extras: "f2s3,dev" }
name: Test (${{ matrix.suite }}, ${{ matrix.python }})
```
This renders check names `Test (core, 3.11)`, `Test (core, 3.12)`, `Test (f2s3, 3.12)`.

**D-08 required-status-check contexts (exact strings):**
```
Lint (ruff + pyright)
Test (core, 3.11)
Test (core, 3.12)
Test (f2s3, 3.12)
Build wheel + install smoke
```
(Decide whether `Docs build` is also required; recommend **not** required initially since RTD activates post-public, but make it blocking-on-PR so regressions surface.)

> **Open question for the planner/user:** D-08 CONTEXT lists contexts as "lint, test 3.11, test 3.12, build" — i.e. it anticipated *symmetric* 3.11+3.12 testing. Because `f2s3` is 3.12-only, "test 3.11" maps to `Test (core, 3.11)` and there is **no** `f2s3` 3.11 check. Confirm the four/five context list above with the user when writing the ruleset payloads.

## Version Seeding (D-06) — recommended mechanism

**Context:** local `.release-please-manifest.json` = `"0.0.0"`; release-type `simple` with `bump-minor-pre-major: true`. From 0.0.0 a `feat` would cut **0.1.0**, not 0.2.0. The package's *actual* published version comes from the git tag via setuptools_scm, so whatever tag release-please creates becomes the wheel version — the first tag **must be exactly `v0.2.0`**.

**Recommended:** one-shot **`Release-As: 0.2.0`** footer on a commit that lands in the first release window:
```
chore: bootstrap 0.2.0 release

Release-As: 0.2.0
```
This forces release-please to cut exactly 0.2.0 regardless of conventional-commit math; after the release, the manifest auto-updates to `0.2.0` and normal bumping resumes. `[CITED: github.com/googleapis/release-please — "Release-As" bootstrap]`

**Alternative (sticky, discouraged):** `"release-as": "0.2.0"` in `release-please-config.json` — persists across runs and must be manually removed after the first cut; easy to forget. Prefer the commit footer.

**`conf.py` version:** since version is setuptools_scm-derived, **do not** hardcode a version string with `x-release-please-version` in `conf.py` (PCHandler does this only because it pins a literal version). Instead derive it:
```python
from importlib.metadata import version as _v
release = _v("geodispbench3d"); version = ".".join(release.split(".")[:2])
```
Then geodispbench3d needs **no** `extra-files` entry in `release-please-config.json` (unlike PCHandler).

## Branch Protection / Rulesets (D-08, PROT-01)

PCHandler's two rulesets were fetched verbatim. Each has identical rule bodies; only `conditions.ref_name.include` and the status-check contexts differ.

**PCHandler `protect-main` rule body (the template):** `[VERIFIED: gh api repos/gseg-ethz/PCHandler/rulesets/18108142]`
- `pull_request`: `required_approving_review_count: 0`, `dismiss_stale_reviews_on_push: false`, `require_code_owner_review: false`, `require_last_push_approval: false`, `required_review_thread_resolution: false`, `allowed_merge_methods: [merge, squash, rebase]`
- `required_status_checks`: `strict_required_status_checks_policy: false`, `do_not_enforce_on_create: false`, contexts `[{context: "Lint (pre-commit)"}, {context: "Tests (pytest)"}]`
- `non_fast_forward`, `deletion`, `required_linear_history`
- `bypass_actors: []`, `enforcement: active`

**Adaptation for geodispbench3d:**
- `protect-main`: `conditions.ref_name.include = ["refs/heads/main"]`
- `protect-develop`: `conditions.ref_name.include = ["refs/heads/develop"]` (our dev branch is plain `develop`; PCHandler's was `develop/gsd`)
- **contexts → the five exact CI job names** from the CI Topology section (not PCHandler's two).

**Delivery (D-08):** committed JSON payloads + a `gh api` apply script, **enabled at milestone-ship**:
```bash
# .github/scripts/apply-rulesets.sh
gh api --method POST repos/gseg-ethz/geodispbench3d/rulesets --input .github/rulesets/protect-main.json
gh api --method POST repos/gseg-ethz/geodispbench3d/rulesets --input .github/rulesets/protect-develop.json
# (use --method PUT repos/.../rulesets/<id> to update an existing ruleset)
```
**Do not run this during phase execution** — it would lock out the in-flight milestone PR (the milestone PR to `main` strips `.planning/`, and required checks must be green/passing first). The script + docs are the deliverable; the user runs it at ship time.

## Docs / Sphinx + ReadTheDocs (D-09, DOCS-01)

**`.readthedocs.yaml` (mirror PCHandler):** `[VERIFIED: gh api repos/gseg-ethz/PCHandler/.readthedocs.yaml]`
```yaml
version: 2
build:
  os: ubuntu-24.04
  tools: { python: "3.12" }
  jobs:
    post_build:
      - cp LICENSE $READTHEDOCS_OUTPUT/html/LICENSE.txt
sphinx:
  configuration: docs/source/conf.py
python:
  install:
    - method: pip
      path: .
      extra_requirements: [docs]    # PCHandler uses "doc"; geodispbench3d's extra is named "docs"
```
> **Naming mismatch to honor:** PCHandler's docs extra is `doc`; geodispbench3d's existing extra is `docs`. Keep `docs` (it's already declared) and reference `docs` in `.readthedocs.yaml` and the CI docs job. Do not blindly copy `doc`.

**`docs/source/conf.py` (geodispbench3d-shaped, NOT PCHandler's heavy nitpicky config):** PCHandler's `conf.py` is ~250 lines of autodoc/nitpick_ignore tuning for a typed numeric library with intersphinx to GSEGUtils/open3d/py4dgeo — **do not copy it**. geodispbench3d's docs are narrative Markdown, so a minimal myst config is correct:
```python
# docs/source/conf.py
from importlib.metadata import version as _v
project = "geodispbench3d"
author = "Nicholas Meyer"
copyright = "2026, Nicholas Meyer"
release = _v("geodispbench3d"); version = ".".join(release.split(".")[:2])
extensions = ["myst_parser"]            # add sphinx.ext.autodoc later only if API docs wanted
myst_enable_extensions = ["colon_fence", "deflist"]
html_theme = "sphinx_rtd_theme"
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
```

**Wiring the existing Markdown:** the existing `docs/` tree is flat Markdown with subdirs (`integrating/`, `reference/`, `tools/`) and a root `index.md` that already uses relative links. Two viable layouts:
- **(a) Move** the Markdown under `docs/source/` and add a myst `toctree` in `docs/source/index.md`. Cleanest for Sphinx (source dir self-contained). The existing relative links mostly survive.
- **(b) Keep** Markdown in `docs/` and set the Sphinx source dir to `docs/` with `conf.py` at `docs/conf.py`. Avoids moving files but diverges from PCHandler's `docs/source` layout and from the `.readthedocs.yaml` path above.

Recommend **(a)** (`docs/source/` root) to match `.readthedocs.yaml: configuration: docs/source/conf.py`. The existing `index.md` "Read me first / Pre-built tools / Integrating / Reference" bullet structure converts directly into a myst `{toctree}`.

**CI docs job:** `sphinx-build -W --keep-going -b html docs/source docs/_build/html` (warnings-as-errors, like PCHandler). Recommend **blocking on PR** but **not** a D-08 required check (RTD hosting is post-public).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Publishing to PyPI securely | custom `twine upload` with a stored token | `pypa/gh-action-pypi-publish` + OIDC trusted publisher | No long-lived secret; PEP 740 attestations free. |
| Version bump + changelog + tag | hand-edited CHANGELOG / manual tags | `googleapis/release-please-action` | Conventional-commit driven, already configured. |
| Re-triggering checks on protected main | a PAT in a secret | `actions/create-github-app-token` | App token re-triggers workflows + satisfies required checks; no stored long-lived token. |
| Branch protection | clicking repo settings by hand | `gh api` ruleset JSON + apply script | Reproducible, reviewable, version-controlled (D-08). |
| Rendering Markdown docs in Sphinx | converting `.md` → `.rst` | `myst-parser` | Keeps the existing, current Markdown as the source of truth. |
| Deriving the published version | hardcoded `__version__` strings | setuptools_scm (already wired) + git tag from release-please | Single source of truth; no version drift. |

**Key insight:** every component of this phase has an established, SHA-pinnable action or a config-driven tool. The only *code* this phase writes is glue (composite action, ruleset JSON, conf.py, a possible publish-gate script) plus the residual pyright fixes. The risk is not "build it wrong" but "wire two solved pieces together with a mismatched string" (workflow name, check context, environment name, extra name).

## Optional: publish-gate guard (mirror PCHandler `check_publish_gate.py`)

PCHandler runs `.github/scripts/check_publish_gate.py` in its lint job to assert publish steps appear **only** in `publish-pypi.yml`/`publish-testpypi.yml` under the right Environments. This is a cheap supply-chain guard against an accidental `pypa/gh-action-pypi-publish` / `twine upload` slipping into another workflow. `[VERIFIED: gh api PCHandler check_publish_gate.py]`

Recommend porting it (adapt the `ALLOWED` map to geodispbench3d's two publish files) as a **discretionary hardening task** — not a CONTEXT requirement, but low-cost and aligned with the "nothing ships unverified" core value. Flag for user opt-in.

## Common Pitfalls

### Pitfall 1: pchandler is Python-3.12-only → f2s3 can't run on 3.11
**What goes wrong:** A symmetric `core+f2s3 × {3.11,3.12}` matrix; the `f2s3 / 3.11` job dies at `pip install .[f2s3,dev]` because `pchandler 2.1.0` requires `>=3.12,<3.13`.
**Why it happens:** D-03 reads as "core + f2s3 across 3.11 AND 3.12"; pchandler's pin (verified on PyPI this session) makes f2s3@3.11 impossible.
**How to avoid:** matrix `include:` — `core` on {3.11, 3.12}, `f2s3` on {3.12}. Update the D-08 contexts to match (no `f2s3 3.11` context).
**Warning signs:** `ResolutionImpossible` / "requires a different Python" in the f2s3 3.11 job install step.

### Pitfall 2: workflow `name:` / `workflows:` string drift
**What goes wrong:** `release-please.yml`'s `workflow_run.workflows: [CI]` never fires because someone renamed the CI workflow.
**How to avoid:** keep `ci.yml` `name: CI`; treat the string as an interface. Same discipline for Environment names (`pypi`/`testpypi`) and required-check contexts.
**Warning signs:** release-please workflow shows zero runs after merges to main.

### Pitfall 3: setuptools_scm version drift on the publish path
**What goes wrong:** publish builds a wheel versioned `0.1.0` or `…+dirty` / `…dev` instead of the release tag.
**Why it happens:** checkout without `fetch-depth: 0` + `fetch-tags: true`; setuptools_scm falls back to `fallback_version = "0.1.0"`.
**How to avoid:** every build/publish checkout uses `fetch-depth: 0, fetch-tags: true` (PCHandler does). Confirm `local_scheme = "no-local-version"` (already set) so no `+local` suffix that PyPI rejects.
**Warning signs:** `twine check` passes but the uploaded version is wrong / rejected as a local-version.

### Pitfall 4: required checks set before the pipeline is green = self-lockout
**What goes wrong:** Enabling rulesets with required contexts that don't yet pass (or before the App token is wired) blocks the milestone PR to `main`.
**How to avoid:** D-08 explicitly defers ruleset enablement to milestone-ship. Ship the script, run it last.
**Warning signs:** the `main` PR shows "Required statuses must pass" with checks that never started.

### Pitfall 5: GitHub-App / trusted-publisher prerequisites missing at first release
**What goes wrong:** First tagged release fails to publish — no PyPI pending publisher, or the gseg-ethz App isn't installed / `APP_ID`/`APP_PRIVATE_KEY` not shared, or Environments `pypi`/`testpypi` don't exist.
**How to avoid:** these are **external prerequisites** (CONTEXT canonical_refs §External prerequisites) the user must provision. The plan should include a `checkpoint:human-verify` gate that confirms them before the first real publish, and the TestPyPI `workflow_dispatch` dry-run as the proof step.
**Warning signs:** `gh-action-pypi-publish` errors "Trusted publishing exchange failure" / "environment not found" / App-token step fails auth.

## Runtime State Inventory

> This phase touches state that lives **outside git** (GitHub repo settings + external services). Captured here because, like a rename phase, "edit the files" is insufficient — repo/service config must also be provisioned. Verified against CONTEXT canonical_refs and `gh` this session.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no datastores involved. | None |
| Live service config | GitHub **rulesets** (none exist on geodispbench3d yet — `gh api` to apply at ship); GitHub **Environments** `pypi`/`testpypi` (must be created); **secrets** `APP_ID`/`APP_PRIVATE_KEY` (must be shared from the gseg-ethz App); **PyPI/TestPyPI pending trusted publishers** (must be registered out-of-band); **ReadTheDocs** project import (post-public). | User-provisioned external prereqs + committed apply script. |
| OS-registered state | None (hosted runners only; no self-hosted runner like PCHandler's GPU host). | None |
| Secrets/env vars | `APP_ID`, `APP_PRIVATE_KEY` (repo secrets); no PyPI tokens by design (OIDC). The existing `RELEASE_PLEASE_TOKEN||GITHUB_TOKEN` wiring is **removed** by D-05. | Add App secrets; remove PAT reliance. |
| Build artifacts | `src/geodispbench3d/_version.py` is setuptools_scm-generated (gitignored); no stale artifacts to migrate. First git tag `v0.2.0` is the new state that makes setuptools_scm emit `0.2.0`. | Ensure first tag is exactly `v0.2.0` (D-06). |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stored PyPI API token | OIDC trusted publishing (`id-token: write`) | PyPI GA 2023 | No long-lived secret; required by CICD-03. |
| Unsigned uploads | PEP 740 attestations (default on in `gh-action-pypi-publish`) | 2024 | Provenance on PyPI; on for real PyPI, off for TestPyPI. |
| `@v4` floating action tags | commit-SHA pins | supply-chain norm (post tj-actions 2025) | D-07; deterministic, audit-friendly. |
| `on: push: main` + PAT for release-please | `on: workflow_run` + GitHub-App token | PCHandler `gsd/phase-8-release-please-fix` | Works with protected `main`; D-05. |

**Deprecated/outdated in the current repo:**
- `release-please.yml` `on: push: main` + `secrets.RELEASE_PLEASE_TOKEN || secrets.GITHUB_TOKEN` — replaced by D-05.
- `ci.yml` linear `lint → test → build` `needs:` chain — replaced by D-02 (lint ∥ test, build needs test).
- `ci.yml` single Python 3.12 — replaced by D-03 matrix.
- `@v4`/`@v5` action tags in `ci.yml` + `release-please.yml` — replaced by SHA pins (D-07).

## Validation Architecture

> `workflow.nyquist_validation` not explicitly disabled in config → section included. Note: the test *framework* (pytest) is already validated in Phases 2-4; this phase's deliverables are **workflows/config**, so validation is observational (CI run status, dry-run publish) rather than new unit tests.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest `~= 8.4` (existing); plus workflow/YAML validation by running CI itself |
| Config file | `pyproject.toml` (no `[tool.pytest.ini_options]` yet — tests run by path) |
| Quick run command | `conda run -n iof3d_cosicorr3d-dev312 python -m pytest tests/core -v` |
| Full suite command | `conda run -n iof3d_cosicorr3d-dev312 python -m pytest` (core + f2s3; f2s3 needs the `f2s3-dev312` env for the binary) |

### Phase Requirements → Validation Map
| Req | Behavior | Validation type | Command / observation |
|-----|----------|-----------------|------------------------|
| CICD-01 | lint+pyright+matrix green on push/PR | CI observation | Push to a branch; all of `Lint`, `Test (core,3.11/3.12)`, `Test (f2s3,3.12)`, `Docs build` pass. Locally: `conda run -n iof3d_cosicorr3d-dev312 ruff check . && ruff format --check . && pyright` exits 0 (genuine, scoped). |
| CICD-02 | wheel+sdist pass twine check | CI build job + local | `conda run -n iof3d_cosicorr3d-dev312 python -m build && twine check dist/*` → "PASSED"; install-smoke imports + `geodispbench3d --help`. |
| CICD-03 | OIDC publish, no tokens | TestPyPI dry-run | `workflow_dispatch` of `publish-testpypi.yml` → artifact lands on test.pypi.org via OIDC; confirm no PyPI token secret exists. |
| CICD-04 | release-please end-to-end | CI observation | Conventional-commit merge to main → release-please opens/updates Release PR → merge cuts `v0.2.0` tag + GitHub Release → `publish-pypi.yml` fires on `release: published`. |
| PROT-01 | branch protection | gh api readback | After `apply-rulesets.sh`: `gh api repos/gseg-ethz/geodispbench3d/rulesets` shows `protect-main`/`protect-develop` with the exact contexts; a direct push to `main` is rejected. |
| DOCS-01 | docs build passes | CI/local build | `sphinx-build -W --keep-going -b html docs/source docs/_build/html` exits 0; RTD import deferred to post-public. |

### Sampling Rate
- **Per task commit:** `conda run -n iof3d_cosicorr3d-dev312 ruff check . && pyright` (fast gate) + `actionlint`/YAML parse on changed workflows if available.
- **Per wave merge:** full local pytest + `python -m build && twine check dist/*`.
- **Phase gate:** a real branch push exercising the full CI run green; one TestPyPI `workflow_dispatch` dry-run before declaring CICD-03 met.

### Wave 0 Gaps
- [ ] No `actionlint` in the toolchain — recommend adding a lightweight workflow-lint step (or local `actionlint`) to catch YAML/expression errors before pushing. Optional.
- [ ] No `[tool.pytest.ini_options]` — not required for this phase; tests run by path.
- [ ] The genuine 0-error pyright is a **prerequisite gap**: residual core type errors must be fixed (not just excluded) — treat as a Wave-0/early task with its own verification (`pyright` exit 0 on the scoped config).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI (authed) | fetching template, applying rulesets | ✓ | account NixtonM, scopes incl. `repo`, `admin:public_key`, `read:org` | — |
| `gseg-ethz/PCHandler` access | template mirror | ✓ | PUBLIC | docs fallback (not needed) |
| `pchandler` on PyPI | `f2s3` extra | ✓ | 2.1.0 (`>=3.12,<3.13`) | — (drives the 3.12-only matrix) |
| conda env `iof3d_cosicorr3d-dev312` | local lint/test/build per AGENTS.md | assumed ✓ | py3.12 | — |
| conda env `f2s3-dev312` | f2s3 binary behavioral tests | assumed ✓ | — | f2s3 CI job covers parser-shape tests |
| GitHub App (gseg-ethz) on repo | release-please token | **external prereq** | — | none — blocks release path until provisioned |
| PyPI/TestPyPI pending publishers | OIDC publish | **external prereq** | — | none — blocks publish until registered |
| GitHub Environments `pypi`/`testpypi` | publish jobs | **external prereq** | — | can be created via `gh api` |
| ReadTheDocs project | docs hosting | **deferred** (post-public) | — | config committed now; activate later |

**Missing dependencies with no fallback (must be user-provisioned before first release, not before planning):**
- gseg-ethz GitHub App install + `APP_ID`/`APP_PRIVATE_KEY` secrets.
- PyPI + TestPyPI pending trusted publishers for project `geodispbench3d`.
- GitHub Environments `pypi` + `testpypi`.

These are explicitly listed in CONTEXT as "USER must provide — not blockers for planning." The plan should gate the first real publish behind a `checkpoint:human-verify`.

## Security Domain

> `security_enforcement` not disabled → included. This phase's security surface is supply-chain + secrets, not application input handling.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OIDC trusted publishing (no static PyPI creds); GitHub-App token (short-lived) |
| V6 Cryptography | yes (indirect) | PEP 740 attestations / Sigstore signing via `gh-action-pypi-publish` — never hand-roll |
| V10 Malicious Code / supply chain | yes | SHA-pinned actions (D-07); publish-gate script (optional); least-privilege `permissions:` per job |
| V5 Input Validation | n/a | no user-facing input added in this phase |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Compromised mutable action tag (tj-actions class) | Tampering/Elevation | Pin every action by commit SHA (D-07); all pins verified this session |
| Leaked long-lived PyPI token | Info disclosure/Spoofing | OIDC trusted publishing; zero stored tokens (CICD-03) |
| Accidental publish from a non-publish workflow | Tampering | `environment:` scoping + optional `check_publish_gate.py` lint guard |
| Over-privileged workflow token | Elevation | Per-job minimal `permissions:` (`contents: read` on build, `id-token: write` only where publishing) |
| Release cut from unverified commits | Tampering | release-please gated `if: workflow_run.conclusion == 'success'` (D-05); branch protection (D-08) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `googleapis/release-please-action` v5.0.0 keeps the same inputs/outputs (`token`, `config-file`, `release_created`, `major`, `minor`) used by the local v4 call | Standard Stack / Pattern 2 | release-please step fails or behaves differently; mitigated — PCHandler runs v5 with exactly this call shape today. |
| A2 | Modern docs triple (`sphinx ~=8.1` + `myst-parser ~=4.0` + `sphinx-rtd-theme ~=3.0`) resolves cleanly together | Standard Stack (option b) | docs build install fails; mitigated — pin against a resolved `pip install -e .[docs]` before committing. |
| A3 | `myst-parser ~=1.0` is the line compatible with `sphinx ~=5.1` (option a) | Standard Stack (option a) | minimal-change path breaks; verify if option (a) chosen. |
| A4 | conda envs `iof3d_cosicorr3d-dev312` / `f2s3-dev312` exist and are usable locally | Validation / Environment | local verification commands fail; per AGENTS.md they are mandated and assumed present. |
| A5 | The "few pre-existing core type-narrowing errors" (from ROADMAP) are fixable in-phase without large refactors | Pyright Scoping | genuine 0-error gate (D-01a) slips; enumerate early (Wave 0) to size the work. |
| A6 | geodispbench3d's GitHub repo name/owner is `gseg-ethz/geodispbench3d` (per pyproject URLs) for ruleset/publisher registration | Rulesets / publish | wrong API targets; confirmed via `[project.urls]` repository field. |

## Open Questions

1. **release-please-action v4 → v5 bump.**
   - What we know: PCHandler (mirror) uses v5.0.0; local uses v4; same call shape.
   - What's unclear: any v5 behavior change the author hit.
   - Recommendation: adopt v5.0.0 SHA for mirror fidelity; surface the bump to the user (interactive-mode `[deliberate-informed]` change).
2. **Docs source layout (`docs/source/` move vs `docs/` in place) and Sphinx version line.**
   - Recommendation: `docs/source/` + modern Sphinx (option b); confirm the dependency bump with the user before locking the `docs` extra.
3. **D-08 contexts given the asymmetric matrix (no `f2s3 3.11`).**
   - Recommendation: five contexts as listed; confirm with the user when writing ruleset JSON since CONTEXT D-08 anticipated a symmetric 3.11/3.12 set.
4. **Is `Docs build` a required check?**
   - Recommendation: blocking-on-PR but NOT a D-08 required status check until RTD activates post-public.
5. **Port `check_publish_gate.py`?**
   - Recommendation: yes as discretionary hardening; user opt-in.

## Sources

### Primary (HIGH confidence — fetched live this session)
- `gh api repos/gseg-ethz/PCHandler/contents/.github/workflows/{publish-pypi,publish-testpypi,release-please,ci}.yml` — full workflow bodies (job names, triggers, `needs:`, `permissions:`, SHA-pinned `uses:`, environment names).
- `gh api repos/gseg-ethz/PCHandler/rulesets/{18108142,18108143}` — full ruleset rule bodies.
- `gh api .../contents/.readthedocs.yaml`, `.../docs/source/conf.py`, `.../.github/actions/setup-python-deps/action.yml`, `.../release-please-config.json`, `.../.release-please-manifest.json`, `.../.github/scripts/check_publish_gate.py`.
- GitHub API `git/ref/tags` + annotated-tag deref — every action SHA cross-checked to its tag.
- `pypi.org/pypi/{pchandler,myst-parser,sphinx,sphinx-rtd-theme}/json` — versions + requires-python (pchandler 3.12-only confirmed).
- Local: `.github/workflows/{ci,release-please}.yml`, `pyproject.toml`, `pyrightconfig.json`, `release-please-config.json`, `.release-please-manifest.json`, `docs/` tree, `AGENTS.md`, ROADMAP/REQUIREMENTS/CONTEXT.

### Secondary (MEDIUM confidence)
- `[CITED]` pyright exit-code semantics (errors fail, warnings don't); release-please `Release-As` bootstrap — official docs, applied from established knowledge.

### Tertiary (LOW confidence)
- `[ASSUMED]` exact myst-parser/Sphinx version-compatibility windows (A2/A3) — verify at install.

## Metadata

**Confidence breakdown:**
- Workflows / publish / release-please / rulesets: HIGH — verbatim from the live canonical mirror, same author, dated 2026-06-25/27.
- Action SHA pins: HIGH — each verified against its tag via GitHub API this session.
- Matrix shape / pchandler 3.12 constraint: HIGH — pchandler requires-python read directly from PyPI.
- Docs toolchain pins: MEDIUM — packages confirmed on PyPI; exact compatible triple needs an install-time resolve.
- Residual pyright work sizing: MEDIUM — ROADMAP attests "a few" errors but they were not enumerated this session.

**Research date:** 2026-06-27
**Valid until:** ~2026-07-27 (action SHAs / PyPI versions are fast-moving; re-verify pins if planning slips a month).
