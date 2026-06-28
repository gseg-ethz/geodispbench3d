# Phase 05 — paused before Wave 4 (plan 05-06)

**Paused:** 2026-06-28 · **State:** 5/6 plans complete (waves 1–3 done, all committed on `gsd/phase-05-ci-cd-release`).

Plan **05-06** (integration verification) is non-autonomous (`human_verify_mode=end-of-phase`)
and its outward/external steps cannot run until the external prerequisites below are
provisioned. Verified absent on 2026-06-28: no GitHub Environments, no repo secrets.

## What you must provision (external, human-only)

### 1. GitHub Environments — `gseg-ethz/geodispbench3d` → Settings → Environments
- [ ] `pypi`   (production publish target; optional required-reviewer approval gate)
- [ ] `testpypi` (dry-run target)

### 2. Repo secrets (for release-please App token) — Settings → Secrets and variables → Actions
- [ ] `APP_ID`           — gseg-ethz GitHub App, app id
- [ ] `APP_PRIVATE_KEY`  — gseg-ethz GitHub App, private key PEM
  (the App must be installed on `gseg-ethz/geodispbench3d` with contents + PRs write)

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
