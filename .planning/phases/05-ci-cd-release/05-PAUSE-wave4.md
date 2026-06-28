# Phase 05 — paused before Wave 4 (plan 05-06)

**Paused:** 2026-06-28 · **State:** 5/6 plans complete (waves 1–3 done, all committed on `gsd/phase-05-ci-cd-release`).

Plan **05-06** (integration verification) is non-autonomous (`human_verify_mode=end-of-phase`)
and its outward/external steps cannot run until the external prerequisites below are
provisioned. Verified absent on 2026-06-28: no GitHub Environments, no repo secrets.

## What you must provision (external, human-only)

### 1. GitHub Environments — `gseg-ethz/geodispbench3d` → Settings → Environments
- [x] `pypi`   (production publish target) — created 2026-06-28 via gh
- [x] `testpypi` (dry-run target) — created 2026-06-28 via gh
- [ ] **`pypi` required-reviewer approval gate (NixtonM) — DEFERRED to repo-go-public.**
      Environment protection rules (required reviewers) are unavailable for *private*
      repos on the current gseg-ethz billing plan (GitHub returns HTTP 422). The gate
      becomes free the moment the repo is public. **At ship-time, after making the repo
      public, run:**
      `gh api --method PUT repos/gseg-ethz/geodispbench3d/environments/pypi --input - <<<'{"reviewers":[{"type":"User","id":49650019}]}'`
      Until then the production publish is guarded by `check_release_preflight.py` only.

### 2. Secrets (for release-please App token) — repo OR org level
`release-please.yml` reads `secrets.APP_ID` + `secrets.APP_PRIVATE_KEY` (the
`gseg-release-please` App). App installed on the repo ✓ (user, 2026-06-28), but the
App id + private key still need to exist as Actions secrets.
- [x] `APP_ID`           — set repo-level 2026-06-28
- [x] `APP_PRIVATE_KEY`  — set repo-level 2026-06-28
  (org-level had nothing; registered as repo secrets. App installed on repo ✓)

### (note) Codecov — not wired in CI
The Codecov App was installed, but `ci.yml` has **no coverage-upload step**, so Codecov
receives no data. Out of scope for publishing; add a `codecov/codecov-action` step (and
`CODECOV_TOKEN` while the repo is private) later if coverage reporting is wanted.

### 3. PyPI / TestPyPI pending trusted publishers (OIDC, no stored token)
Register both as **pending publishers** for project `geodispbench3d`:

| Index    | Project name    | Owner      | Repository      | Workflow              | Environment |
|----------|-----------------|------------|-----------------|-----------------------|-------------|
| PyPI     | geodispbench3d  | gseg-ethz  | geodispbench3d  | `publish-pypi.yml`    | `pypi`      |
| TestPyPI | geodispbench3d  | gseg-ethz  | geodispbench3d  | `publish-testpypi.yml`| `testpypi`  |

- PyPI:     https://pypi.org/manage/account/publishing/
- TestPyPI: https://test.pypi.org/manage/account/publishing/

## Resume

Once the three sections above are done:

```
/gsd-execute-phase 5 --wave 4
```

That runs 05-06 fully end-to-end:
- **Task 1** — push branch + open a PR against `develop`; observe CI green across
  Lint, Test (core, 3.12), Test (f2s3, 3.12), Build wheel + install smoke, Docs build.
- **Task 2** — confirm prereqs; `workflow_dispatch` the TestPyPI OIDC dry-run
  (skip-existing disabled / unique version); assert built version; confirm newly
  created on test.pypi.org; names-only secret readback shows no PyPI token.
- **Task 3** — CICD-04 release-please gate (wiring + deterministic-0.2.0 seed proof;
  ship-time release→tag→publish procedure recorded). *(Task 3 is local-only and could
  also be run independently if you want CICD-04 closed before provisioning.)*

Real PyPI publish, the first `v0.2.0` tag, and ruleset enablement remain **ship-time**
human actions (handled at `/gsd-ship`), not part of 05-06.
