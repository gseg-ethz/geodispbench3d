# Phase 5: CI/CD & Release - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver an automated CI/CD + release pipeline that takes `geodispbench3d` from
"works for us" to "publishes itself":

1. A **green quality gate** on every push/PR — ruff lint + format, a *genuinely
   0-error* pyright type check, and the full pytest matrix across Python 3.11 + 3.12.
2. **Build + validation** — wheel + sdist, `twine check`, install-smoke.
3. **OIDC trusted publishing** to public PyPI on a tagged release (no stored
   long-lived tokens), with a manual TestPyPI dry-run.
4. **release-please wired end-to-end** so a merge to `main` flows to a tag, a
   GitHub Release, and a PyPI publish automatically.

**In-scope additions decided during discussion (beyond CICD-01..04):**
- **Branch protection** for `main` and `develop` — the enforcement layer that
  makes the green checks mandatory (tracked as **PROT-01**).
- **Sphinx + ReadTheDocs wiring** — scaffold a Sphinx build over the existing
  Markdown docs + `.readthedocs.yaml`, activated at go-public (tracked as **DOCS-01**).

**Out of scope:** re-enabling the iof3D adapter/extra (stays disabled until iof3D
publishes publicly, ~6 months — Phase 4 deferral); GPU/canary CI; any new
framework features; macOS/Windows OS matrix.

**Guiding template:** the sibling repo **`gseg-ethz/PCHandler`** (same org, same
author, more mature) is the canonical reference. Its already-solved CI, publish,
release-please, branch-protection, and RTD setup are mirrored here unless noted.
</domain>

<decisions>
## Implementation Decisions

### Type-check CI policy (resolves Phase 2 D-13)
- **D-01: Keep pyright as the enforced CI type gate — mypy rejected.** The
  pyright-vs-mypy question carried from Phase 2 (D-13) is decided in favour of
  pyright: it is already wired (`pyrightconfig.json`, basic mode), and a mypy
  swap is a disproportionate lift (new dep, config, annotation churn) for a
  pyright-shaped codebase.
- **D-01a — Make pyright genuinely 0-errors by scoping to the tool-agnostic core.**
  The standing red is dominated by unresolvable `iof3D` / `pchandler` /
  `pc2img` imports. Per Phase 4, iof3D is **private at go-live**, so CI *cannot*
  `pip install` the `iof3d` extra from a public index — installing-the-extra is
  not an option. Resolution: exclude the `geodispbench3d_iof3d` plugin package
  from the lint-job pyright run and treat the unresolvable plugin imports as
  ignored, so the public surface type-checks clean (0 errors). The iof3D adapter
  is type-checked only inside the (disabled) `iof3d` test job, where its stack is
  present. This **supersedes** the Phase 2 D-11/D-12 "no-new-errors vs baseline"
  operationalization with a real green gate (exact `pyrightconfig.json` /
  per-job mechanics are a planning detail).

### CI topology (gate coupling)
- **D-02 — lint and test run in parallel; build gated behind test.**
  Drop the linear `lint → test → build` chain (build `needs: [test]`). Rationale discussed: the chain's *masking*
  failure (a red lint skipped the whole matrix) was a symptom of the gate being
  *chronically* red — fixed by D-01a. Running lint and test independently means a
  type failure can no longer hide a test regression; gating build behind test
  keeps uploaded artifacts tied to a passing suite. Publish-time safety lives on
  the release path (D-04/D-05), **not** PR CI (nothing ships from a PR), so PR-CI
  coupling is purely a feedback/noise tradeoff.

### Python / OS matrix
- **D-03: Expand the test matrix to Python 3.11 AND 3.12** (CICD-01; CI currently
  runs 3.12 only). ubuntu-only — backend/library, no OS matrix. `core` + `f2s3`
  jobs enabled; the `iof3d` matrix job stays **disabled** (Phase 4).

### Publish model (mirror PCHandler)
- **D-04: Two publish workflows, OIDC trusted publishing, GitHub Environments.**
  - `publish-pypi.yml`: trigger `on: release: published`; `build` job → `publish`
    job (`needs: build`) using Environment **`pypi`**, `permissions: id-token:
    write` + `attestations: write`, `pypa/gh-action-pypi-publish` (default
    real-PyPI URL), PEP 740 attestations on.
  - `publish-testpypi.yml`: manual **`workflow_dispatch`** dry-run to Environment
    **`testpypi`** (`repository-url: https://test.pypi.org/legacy/`,
    `attestations: false`, `skip-existing: true`, `id-token: write` only).

### release-please wiring (mirror PCHandler — solves the protected-main token problem)
- **D-05 — workflow_run after CI, authenticated by the gseg-ethz GitHub App.**
  `release-please.yml` triggers `on: workflow_run: workflows: [CI]: types:
  [completed]: branches: [main]`, gated `if: workflow_run.conclusion ==
  'success'`. Authenticates via **`actions/create-github-app-token`** with the
  **reused gseg-ethz GitHub App** (`APP_ID` / `APP_PRIVATE_KEY` secrets) — the App
  token re-triggers workflows and passes required checks on a protected `main`,
  which `GITHUB_TOKEN` cannot. Also moves floating `vX` / `vX.Y` tags after
  `release_created`. (Replaces the current `on: push: main` + `GITHUB_TOKEN||PAT`
  wiring.)

### Versioning
- **D-06: First public release is v0.2.0, not v1.0.** Milestone relabeled
  **v1.0 → v0.2** (update PROJECT.md / STATE / init `milestone_version`). The
  release-please manifest (`.release-please-manifest.json`, currently `0.0.0`) is
  seeded so the first cut lands **0.2.0** (manifest seed / `Release-As: 0.2.0`
  bootstrap — exact mechanism a planning detail).

### Supply-chain hardening
- **D-07: Pin all GitHub Actions by commit SHA** (mirror PCHandler; current
  workflows use `@vN` tags). Apply across `ci.yml` + the new workflows.

### Branch protection (mirror PCHandler — PROT-01)
- **D-08 — Two rulesets, protect-main (on main) and protect-develop (on develop).**
  Mirror PCHandler's `protect-main` + `protect-develop-gsd`
  rulesets (our dev branch is plain `develop`). Each ruleset rule set:
  - `pull_request` — `required_approving_review_count: 0`, all merge methods
    (solo-dev-friendly; no self-approval deadlock).
  - `required_status_checks` — `strict: false`; contexts = the **final CI job
    names** (lint, test 3.11, test 3.12, build).
  - `non_fast_forward`, `deletion`, `required_linear_history`, **no bypass actors**.
  - Delivered as a committed **`gh api` apply script + docs**; **enabled at
    milestone-ship**, not now (avoids mid-release lockout).

### Sphinx / ReadTheDocs (DOCS-01)
- **D-09: Full Sphinx scaffold + RTD config now; RTD activates at go-public.**
  Add `docs/source/conf.py` + **`myst-parser`** (to consume the existing Markdown
  in `docs/`), make a docs build pass, and add `.readthedocs.yaml` mirroring
  PCHandler (sphinx config path, install the `docs` extra, post_build LICENSE
  copy). Add `myst-parser` to the `docs` extra in `pyproject.toml`. The RTD
  project import/activation is deferred until the repo is public ("stays red
  until going public"). A docs-build CI check is a planning option.

### Claude's Discretion
- Exact `pyrightconfig.json` exclude mechanics and per-job pyright invocation.
- Precise CI job names / matrix shape (must match the D-08 required-check contexts).
- release-please v0.2.0 seeding mechanism (manifest seed vs `Release-As`).
- Whether the docs build is a blocking or informative CI job.
- Whether to factor a `setup-python-deps` composite action (PCHandler does).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & prior decisions
- `.planning/ROADMAP.md` — Phase 5 section, incl. the "CI-health evidence"
  note (standing-red pyright, `needs:`-gated matrix skip) and the carried D-13
  type-check open question.
- `.planning/REQUIREMENTS.md` — CICD-01..04 (lines 47-50). **New scope
  requirements to add:** PROT-01 (branch protection), DOCS-01 (Sphinx/RTD).
- `.planning/phases/02-targeted-fixes/02-CONTEXT.md` — D-11/D-12 (pyright
  CI-faithful baseline) and D-13 (mypy deferral) that D-01/D-01a resolve.
- `.planning/phases/04-licensing-metadata-packaging/04-CONTEXT.md` — iof3D
  stays private; `iof3d` extra + its test job disabled; `pchandler ~= 2.1` pin.
  Grounds why CI cannot install the iof3d extra (D-01a).

### Code / config this phase reworks
- `.github/workflows/ci.yml` — current lint→test→build pipeline to restructure (D-02/D-03).
- `.github/workflows/release-please.yml` — current `on: push: main` + token
  wiring to replace with D-05.
- `release-please-config.json` + `.release-please-manifest.json` — manifest at
  `0.0.0`; seed for v0.2.0 (D-06).
- `pyproject.toml` — `requires-python = "~=3.11"`, `docs = ["sphinx ~= 5.1"]`
  extra (add `myst-parser`), `[project.scripts]`.
- `pyrightconfig.json` — type-check config to scope (D-01a).
- `docs/` — existing Markdown (concepts.md, quickstart.md, index.md, …) to wire
  into Sphinx via myst (D-09).
- `AGENTS.md` — conda-env mandate for local pytest/pyright/ruff invocations.

### Template repo (re-fetch via `gh`, same org)
- **`gseg-ethz/PCHandler`** — the canonical template. Specific artifacts:
  - Rulesets `protect-main` (id 18108142) + `protect-develop-gsd` (id 18108143).
  - `.github/workflows/publish-pypi.yml`, `publish-testpypi.yml`, `release-please.yml`.
  - `.readthedocs.yaml`, `docs/source/conf.py`.

### External prerequisites (USER must provide — not blockers for planning)
1. Confirm the **gseg-ethz GitHub App** is installed on `geodispbench3d` and
   `APP_ID` / `APP_PRIVATE_KEY` secrets are shared to the repo.
2. Create **PyPI** + **TestPyPI** *pending* trusted publishers for project
   `geodispbench3d`, owner `gseg-ethz`, workflow `publish-pypi.yml` / env `pypi`
   (and `publish-testpypi.yml` / env `testpypi`).
3. Create GitHub **Environments** `pypi` + `testpypi` (optional approval gate on
   `pypi`) — can be done via `gh api`.
4. Import `gseg-ethz/geodispbench3d` on **ReadTheDocs** once the repo is public.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/ci.yml`: already has lint / test-matrix / build+twine-check
  / install-smoke jobs — **restructure (D-02/D-03), don't rebuild**.
- `.github/workflows/release-please.yml` + `release-please-config.json`: working
  changelog-sections config; rework the trigger/token toward the PCHandler pattern.
- `docs/` Markdown content: real, current content to surface via Sphinx+myst (D-09).
- `docs = ["sphinx ~= 5.1"]` extra already declared in `pyproject.toml`.

### Established Patterns
- Memory: **CI pyright is standing-red** and phases historically merged on a
  no-new-errors baseline gate, not green CI — **this phase resolves that** (D-01a).
- Memory: **phase branches are retained until the milestone ships to `main`,
  then deleted** — relevant to the ship/branch-protection sequencing (D-08).
- AGENTS.md conda-env mandate governs how the local green-gate is verified.

### Integration Points
- New `publish-pypi.yml` consumes the GitHub Release that release-please creates
  (D-04 ← D-05).
- D-08 required-status-check contexts must exactly match the D-02/D-03 CI job names.
- D-05 GitHub App token is what lets the release PR pass D-08's required checks
  on a protected `main`.
</code_context>

<specifics>
## Specific Ideas

- Mirror `gseg-ethz/PCHandler` as closely as practical across publish,
  release-please, branch protection, and RTD — it is the same author's solved
  reference, including its `gsd/phase-8-release-please-fix` work (the App-token fix).
- Branch protection must cover **both** `main` and `develop` (user caveat),
  mirroring PCHandler's two-ruleset setup.
- "Stays red until going public" = wire Sphinx/RTD config now; the RTD project
  only activates once the repo is public.
</specifics>

<deferred>
## Deferred Ideas

- **iof3D re-enablement** (`iof3d` extra + its CI test job + matrix slot) once
  iof3D publishes publicly (~6 months) — Phase 4 deferral, future milestone.
- **Full governance ruleset** (CODEOWNERS, required-review count, signed-commit
  enforcement) — beyond the chosen minimal protection (D-08); its own phase if wanted.
- **OS matrix** (macOS / Windows) — not now; ubuntu-only.
- **GPU / canary workflows** (PCHandler has `canary.yml`, `gpu-image-refresh.yml`)
  — not in scope for this framework's release pipeline.

</deferred>

<planning_amendments>
## Planning-Session Amendments (2026-06-27, post-research)

Decisions made during `/gsd-plan-phase 5` after research surfaced new constraints.
These **extend or supersede** the locked decisions above and are authoritative for
the plans.

- **D-03 SUPERSEDED — drop Python 3.11; package is Python 3.12-only.** Research
  confirmed `pchandler 2.1.0` (the `f2s3` extra's dep) declares
  `requires-python = ">=3.12,<3.13"`, so `f2s3` cannot install on 3.11 and a
  symmetric 3.11+3.12 matrix is impossible. **User decision:** move the entire
  package to 3.12 rather than run an asymmetric matrix. Concretely:
  - `pyproject.toml`: `requires-python = "~=3.12"` (was `~=3.11`); drop the
    `Programming Language :: Python :: 3.11` classifier (keep 3.12).
  - `ruff` `target-version = "py312"`; `pyright` `pythonVersion = "3.12"`.
  - CI test matrix is **3.12 only**: `Test (core, 3.12)` + `Test (f2s3, 3.12)`.
  - **D-08 required-status-check contexts** become: `Lint (ruff + pyright)`,
    `Test (core, 3.12)`, `Test (f2s3, 3.12)`, `Build wheel + install smoke`.
  - A plan task **updates ROADMAP Phase 5 success criterion #1 and
    REQUIREMENTS CICD-01** to read "Python 3.12" (both currently say "3.11 and
    3.12").
- **D-09 EXTENDED — modern docs toolchain.** Use the modern set mirroring
  PCHandler: `docs = ["sphinx ~= 8.1", "myst-parser ~= 4.0", "sphinx-rtd-theme ~= 3.0"]`,
  pinned against a resolved `pip install -e .[docs]` before committing. Docs build
  on 3.12.
- **D-05/D-07 EXTENDED — release-please-action bumped v4 → v5.0.0** (SHA-pinned
  `45996ed1f6d02564a971a2fa1b5860e934307cf7`) to match PCHandler; same call shape.
- **Optional hardening — ALL THREE INCLUDED:**
  - Port PCHandler's `check_publish_gate.py` into the lint job (assert publish
    steps live only in `publish-pypi.yml` / `publish-testpypi.yml`).
  - `Docs build` as a **blocking PR check** (`sphinx-build -W --keep-going`) — but
    **NOT** a D-08 required status check until RTD activates post-public.
  - Add an **`actionlint`** workflow-lint step to catch Actions YAML/expression errors.
</planning_amendments>

---

*Phase: 5-ci-cd-release*
*Context gathered: 2026-06-27*
*Amended: 2026-06-27 (plan-phase, post-research)*
