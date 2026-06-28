---
phase: 05-ci-cd-release
plan: 03
subsystem: ci-cd-release
tags: [github-actions, oidc, trusted-publishing, release-please, pypi, testpypi, sha-pinning, preflight]

requires:
  - phase: 05-ci-cd-release
    plan: 01
    provides: Python 3.12-only baseline, name:CI interface string, setuptools_scm fallback_version 0.1.0
provides:
  - OIDC trusted-publishing path to real PyPI (publish-pypi.yml, env pypi, no stored token)
  - Manual TestPyPI dry-run (publish-testpypi.yml, env testpypi, workflow_dispatch)
  - Production-publish preflight guard (check_release_preflight.py) blocking non-conforming releases
  - release-please on workflow_run [CI] + gseg-ethz App token (replaces on:push:main + GITHUB_TOKEN/PAT)
  - Durable 0.1.0 manifest baseline + committed Release-As: 0.2.0 footer forcing the first cut to v0.2.0
affects: [05-04 branch protection (contexts), 05-06 integration verification (CICD-03/04 gates)]

tech-stack:
  added: []
  patterns:
    - "OIDC trusted publishing (id-token:write) instead of stored PyPI tokens (CICD-03)"
    - "Per-job least privilege: contents:read on build, id-token/attestations only on publish, write scopes only on release-please"
    - "Every action SHA-pinned with a trailing # vX.Y.Z comment (D-07)"
    - "\"on\": key quoted in every workflow to avoid the PyYAML 1.1 boolean-key trap"
    - "release-please via workflow_run after CI + short-lived GitHub App token (protected-main fix)"
    - "Version seeding as durable committed state (manifest 0.1.0) plus a verifiable Release-As footer, not an unchanged 0.0.0 + unverified future footer"

key-files:
  created:
    - .github/workflows/publish-pypi.yml
    - .github/workflows/publish-testpypi.yml
    - .github/scripts/check_release_preflight.py
  modified:
    - .github/workflows/release-please.yml
    - .release-please-manifest.json

key-decisions:
  - "Durable v0.2.0 seeding: manifest set to 0.1.0 (aligned with setuptools_scm fallback) AND a committed Release-As: 0.2.0 footer; both are real git state, not a documented-but-unverified future footer (review HIGH 05-03)"
  - "Production-publish preflight (check_release_preflight.py) added so any published GitHub Release that is not a clean vX.Y.Z tag matching the built version, reachable from main, and non-draft/prerelease cannot reach real PyPI (review MEDIUM 05-03 / T-05-13)"
  - "Publish workflows use INLINE setup-python, not the Plan 05 setup-python-deps composite, so they verify independently in Wave 2 before the composite exists (review MEDIUM 05-05)"
  - "release-please-action bumped v4 -> v5.0.0 (SHA-pinned) for PCHandler mirror fidelity; same call shape (token/config-file/manifest-file, outputs release_created/major/minor)"

bootstrap-commit: ce1dcfccfe3ea8c8a1cf271bfe0ea107aa1c4c6b  # carries the Release-As: 0.2.0 footer

requirements-completed: []  # advances CICD-03 + CICD-04 wiring; end-to-end proof (TestPyPI dry-run + first real cut) is Plan 06's gate

coverage:
  - id: D-04
    description: "Two OIDC publish workflows: publish-pypi.yml (env pypi, release:published) and publish-testpypi.yml (env testpypi, workflow_dispatch)"
    requirement: "CICD-03"
    verification:
      - kind: integration
        ref: "yaml.safe_load both files; on-key intact (not coerced to bool True); pypi env + id-token/attestations write; testpypi env + test.pypi.org/legacy + attestations:false + skip-existing:true + id-token only"
        status: pass
    human_judgment: false
  - id: D-13
    description: "Production-publish preflight blocks bad publishes (tag vX.Y.Z, built version==tag, not draft/prerelease, tag reachable from main) and runs before the publish step"
    requirement: "CICD-03"
    verification:
      - kind: integration
        ref: "py_compile + ruff clean; functional test fires all four gates on crafted events; step ordering preflight(3) < publish(4) in publish-pypi.yml"
        status: pass
    human_judgment: false
  - id: D-05
    description: "release-please on workflow_run [CI] completed on main, gated on conclusion==success, authenticated by the gseg-ethz App token; no GITHUB_TOKEN/PAT line"
    requirement: "CICD-04"
    verification:
      - kind: integration
        ref: "yaml.safe_load: on.workflow_run.workflows==[CI], branches==[main]; RELEASE_PLEASE_TOKEN absent; release-please-action v5.0.0 SHA-pinned"
        status: pass
    human_judgment: false
  - id: D-06
    description: "First public cut is deterministically v0.2.0: durable manifest 0.1.0 + committed Release-As: 0.2.0 footer reachable in git history; no sticky release-as in config"
    requirement: "CICD-04"
    verification:
      - kind: other
        ref: "manifest['.']=='0.1.0'; 'release-as' not in config packages['.']; git log --grep 'Release-As: 0.2.0' finds commit ce1dcfc"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-06-28
status: complete
---

# Phase 5 Plan 03: Release Path — OIDC Publish + release-please + v0.2.0 Seed Summary

**Wired the full release path: two OIDC trusted-publishing workflows (real PyPI on Release, manual TestPyPI dry-run), a production-publish preflight that blocks non-conforming releases, a rewritten release-please that cuts from a protected main via the gseg-ethz App token after CI succeeds, and a durable 0.1.0 manifest plus a committed Release-As: 0.2.0 footer that forces the first public cut to exactly v0.2.0 — all actions SHA-pinned, no stored PyPI tokens.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-28T07:38Z
- **Completed:** 2026-06-28T07:45Z
- **Tasks:** 3
- **Files created/modified:** 5

## Accomplishments
- **OIDC trusted publishing (CICD-03).** `publish-pypi.yml` triggers on `release: published`: a `build` job (checkout `fetch-depth:0 + fetch-tags:true`, `python -m build --wheel --sdist`, `twine check dist/*`, upload `dist-${{ github.run_id }}`) feeds a `publish-to-pypi` job bound to GitHub Environment `pypi` with `id-token: write + attestations: write` and no `repository-url` (defaults to real PyPI). No stored token crosses the runner→PyPI boundary.
- **TestPyPI dry-run.** `publish-testpypi.yml` is the `workflow_dispatch` sibling: Environment `testpypi`, `repository-url: https://test.pypi.org/legacy/`, `attestations: false` (PEP 740 is inconsistent on TestPyPI), `skip-existing: true`, `id-token: write` only, no preflight (it never reaches production).
- **Production-publish preflight (review MEDIUM 05-03 / T-05-13).** `check_release_preflight.py` runs *before* `gh-action-pypi-publish` and exits non-zero — blocking the upload — unless (a) the release tag matches `^v\d+\.\d+\.\d+$`, (b) every built wheel/sdist version equals the tag's `X.Y.Z`, (c) the release is neither draft nor prerelease, and (d) the tag commit is an ancestor of `origin/main`. Each failed gate prints an actionable `preflight: FAIL [check] detail` message.
- **release-please rewrite (CICD-04 / D-05).** Trigger replaced with `workflow_run: workflows: [CI]: types: [completed]: branches: [main]`, gated `if: workflow_run.conclusion == 'success'`. A short-lived `actions/create-github-app-token` (gseg-ethz App, `APP_ID`/`APP_PRIVATE_KEY`) drives both checkout and the `release-please-action` (bumped to **v5.0.0**, SHA-pinned). The old `secrets.RELEASE_PLEASE_TOKEN || secrets.GITHUB_TOKEN` wiring is removed. A `release_created`-gated floating-tag step force-moves `vX`/`vX.Y` only, with an inline tag-protection caveat.
- **Deterministic v0.2.0 (review HIGH 05-03 / D-06).** `.release-please-manifest.json` set to `{".": "0.1.0"}` — a durable committed baseline aligned with `setuptools_scm` `fallback_version = "0.1.0"`, not the prior placeholder `0.0.0`. A committed `Release-As: 0.2.0` footer (commit `ce1dcfc`) forces the first cut to exactly v0.2.0 (otherwise `bump-patch-for-minor-pre-major` would cut 0.1.1 from 0.1.0). No sticky `release-as` was added to the config.

## Task Commits

Each task was committed atomically:

1. **Task 1: OIDC publish workflows + production-publish preflight** — `f52639c` (feat)
2. **Task 2: Rewrite release-please (workflow_run + GitHub App token)** — `0e530cb` (feat)
3. **Task 3: Durable 0.1.0 manifest + verifiable Release-As: 0.2.0 footer** — `ce1dcfc` (chore; carries the bootstrap footer)

## Files Created/Modified
- `.github/workflows/publish-pypi.yml` (new) — `"on": release: published` → build (twine check) → preflight → OIDC publish, env `pypi`, id-token+attestations write, default PyPI URL.
- `.github/workflows/publish-testpypi.yml` (new) — `"on": workflow_dispatch` → env `testpypi`, test.pypi.org/legacy, attestations:false, skip-existing:true, id-token only.
- `.github/scripts/check_release_preflight.py` (new) — production-publish guard; `NoReturn` `_fail()` per gate; parses the GitHub event payload + `dist/*` filenames + git ancestry.
- `.github/workflows/release-please.yml` (rewritten) — workflow_run [CI] + App token; v5.0.0 action; floating-tag move with explicit force semantics.
- `.release-please-manifest.json` (modified) — `0.0.0` → `0.1.0` durable baseline.

## Decisions Made
- **Durable AND verifiable v0.2.0 seed.** The original plan left the manifest at `0.0.0` and relied on a documented-but-unverified future footer. This plan makes both pieces real git state: the manifest is `0.1.0` (matching the setuptools_scm fallback) and the `Release-As: 0.2.0` footer is committed now and verified present via `git log --grep` (commit `ce1dcfc`). The end-to-end proof that the cut actually lands 0.2.0 remains Plan 06's CICD-04 gate.
- **Preflight defends the highest-risk boundary.** Because *any* published GitHub Release fires `publish-pypi.yml`, an unintended or hand-made Release (wrong tag, draft promoted, version skew) would otherwise reach real PyPI. The preflight makes the release tag + built artifact + branch reachability a hard gate, failing safe (a missing tag or a failed `git fetch origin main` blocks rather than allows).
- **Inline setup-python in the publish workflows.** They deliberately do not use the Plan 05 `setup-python-deps` composite (which does not exist yet in Wave 2) so they are independently verifiable now; the composite's scope is CI jobs only.

## Deviations from Plan

None — plan executed as written. All three tasks landed exactly per their `<action>` blocks; no Rule 1/2/3 auto-fixes and no Rule 4 architectural pauses were needed. (One over-strict assertion I added during Task 2's local check — asserting the literal string `GITHUB_TOKEN` was absent — tripped because the explanatory comments mention `GITHUB_TOKEN`; this was my extra check, not the plan's. The plan's actual verify, `RELEASE_PLEASE_TOKEN` absent, passes, and no `GITHUB_TOKEN` appears in any token wiring — only in comments explaining why it was removed.)

## Verification Evidence
- All three workflows `yaml.safe_load` cleanly with the `"on":` key intact (never coerced to boolean `True`); `d.get(True)` is `None` for each.
- `check_release_preflight.py`: `py_compile` clean, `ruff check`/`ruff format --check` clean, and a functional test fired all four gates (tag-format, prerelease, version-mismatch, tag-reachable) on crafted event payloads.
- Step ordering in `publish-pypi.yml`: preflight (index 3) runs before `gh-action-pypi-publish` (index 4).
- `release-please.yml`: `on.workflow_run.workflows == ["CI"]`, `branches == ["main"]`, `RELEASE_PLEASE_TOKEN` absent, action SHA `45996ed1…` (v5.0.0).
- Manifest is `{".": "0.1.0"}`; config has no `release-as`; `git log --grep='Release-As: 0.2.0'` returns commit `ce1dcfc`.
- **Not verified locally (deferred to Plan 06 / CI):** `actionlint` (not installed in the local toolchain — relied on `conda run … python -m yaml` parse instead), the live OIDC exchange, the first real tag, and the end-to-end release-please cut. These require GitHub-hosted runners + the external prerequisites below.

## Threat Surface
No new security surface beyond the plan's `<threat_model>`. The plan's mitigations are all implemented: OIDC-only publish (T-05-02), SHA-pinned actions (T-05-01), CI-success-gated release-please (T-05-05), the preflight guard (T-05-13), per-job least privilege (T-05-04), and `fetch-tags`+durable-manifest+preflight version fidelity (T-05-08). No `## Threat Flags` to report.

## Known Stubs
None. No placeholder values, empty data sources, or TODO/FIXME markers were introduced; the deliverables are complete workflow/config/script files.

## User Setup Required (external prerequisites — block the first real publish, not this plan)
- **PyPI + TestPyPI trusted publishers** — register pending publishers for project `geodispbench3d`: workflow `publish-pypi.yml` / env `pypi` on pypi.org, and `publish-testpypi.yml` / env `testpypi` on test.pypi.org → Publishing → pending publishers.
- **gseg-ethz GitHub App** — share `APP_ID` and `APP_PRIVATE_KEY` as repo secrets so release-please can authenticate against a protected main.
- **GitHub Environments** `pypi` and `testpypi` must exist on the repo.

## Next Phase Readiness
- 05-04 (branch protection) consumes the workflow/job-name interface strings; the `name: CI` ↔ `workflow_run.workflows: [CI]` contract is preserved.
- 05-06 (integration verification) owns the live proof: a TestPyPI `workflow_dispatch` dry-run for CICD-03 and the first end-to-end release-please cut to v0.2.0 for CICD-04.
- No blockers in code; the only gating items are the user-provisioned external prerequisites above.

## Self-Check: PASSED

- All 5 created/modified files present on disk (`publish-pypi.yml`, `publish-testpypi.yml`, `check_release_preflight.py`, `release-please.yml`, `.release-please-manifest.json`).
- All three task commits found in git history (`f52639c`, `0e530cb`, `ce1dcfc`); the Release-As: 0.2.0 footer commit is `ce1dcfc`.

---
*Phase: 05-ci-cd-release*
*Completed: 2026-06-28*
