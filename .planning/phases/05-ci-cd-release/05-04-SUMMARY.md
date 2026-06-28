---
phase: 05-ci-cd-release
plan: 04
subsystem: ci-cd-release
tags: [branch-protection, rulesets, gh-api, idempotent-apply, preflight, self-lockout]

requires:
  - phase: 05-ci-cd-release
    plan: 01
    provides: "name:CI workflow + rendered CI job names (lint/test/build) the ruleset contexts pin against"
provides:
  - "protect-main.json — ruleset on refs/heads/main pinning the four CI contexts (enforcement:active, bypass_actors:[])"
  - "protect-develop.json — sibling ruleset on refs/heads/develop, identical rule body"
  - "apply-rulesets.sh — idempotent create-or-update applier (PUT/POST by name) with --dry-run + preflight; deliverable only, NOT run this phase"
  - "rulesets/README.md — ship-time-only enablement, self-lockout rationale, idempotency model, strict:false tradeoff"
affects: [05-05 ci.yml (must render job names matching these contexts char-for-char), 05-06 integration verification (apply at ship)]

tech-stack:
  added: []
  patterns:
    - "Branch protection delivered as version-controlled JSON ruleset payloads + a gh-api applier, enabled at milestone-ship (never during phase execution) to avoid self-lockout"
    - "Idempotent create-or-update: match ruleset by name, PUT if present else POST (no duplicate rulesets on re-run)"
    - "Write-guarded preflight: gh auth, repo identity, App install, and recent-context observation gate every POST/PUT (incl. --dry-run)"
    - "required_status_checks contexts as a char-for-char interface contract with ci.yml rendered job names"

key-files:
  created:
    - .github/rulesets/protect-main.json
    - .github/rulesets/protect-develop.json
    - .github/scripts/apply-rulesets.sh
    - .github/rulesets/README.md
  modified: []

key-decisions:
  - "allowed_merge_methods is [squash, rebase] only — merge dropped because required_linear_history rejects merge commits (review MEDIUM 05-04)"
  - "apply-rulesets.sh is idempotent create-or-update (match by name → PUT/POST) with --dry-run + a write-guarding preflight (auth, repo identity, App install, recent contexts), so re-runs never duplicate rulesets and activation cannot lock out maintainers (review MEDIUM 05-04 / T-05-09 / T-05-14)"
  - "strict_required_status_checks_policy kept false — a deliberate solo-maintainer choice (merging against a slightly out-of-date base is allowed); documented in README (review LOW 05-04)"
  - "Repo path parameterized as REPO in the script; the literal gseg-ethz/geodispbench3d/rulesets retained in a readback-hint comment so the interface string is greppable and reviewable"

requirements-completed: [PROT-01]

coverage:
  - id: PROT-01
    description: "Branch-protection rulesets for main + develop pin the green CI gate as required status checks; delivered as reviewable artifacts enabled at ship"
    requirement: "PROT-01"
    verification:
      - kind: integration
        ref: "Both payloads json.load cleanly; contexts == the four rendered CI job names; ref includes main vs develop; allowed_merge_methods == {squash, rebase}; enforcement active; bypass_actors empty; strict policy false"
        status: pass
      - kind: integration
        ref: "apply-rulesets.sh passes bash -n; greps confirm rulesets endpoint, --method PUT, --dry-run; README documents ship + strict; script never executed (only bash -n + --help)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-06-28
status: complete
---

# Phase 5 Plan 04: Branch-Protection Rulesets (main + develop) Summary

**Authored the branch-protection enforcement layer as committed, reviewable artifacts: two ruleset payloads (`protect-main` on `refs/heads/main`, `protect-develop` on `refs/heads/develop`) that pin the four rendered CI job names as required status checks with `[squash, rebase]` merges and linear history, plus an idempotent `apply-rulesets.sh` (create-or-update by name, `--dry-run`, write-guarding preflight) and a README that mandates ship-time-only enablement — the rulesets are NOT applied during this phase, avoiding self-lockout of the in-flight milestone PR.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-06-28T07:49Z
- **Completed:** 2026-06-28T07:55Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- **Two ruleset payloads (PROT-01 / T-05-05).** `protect-main.json` and `protect-develop.json` share one rule body — `pull_request` (`required_approving_review_count:0`, all review-friction flags false, `allowed_merge_methods:["squash","rebase"]`), `required_status_checks` (`strict_required_status_checks_policy:false`, `do_not_enforce_on_create:false`) with the four exact contexts, plus `non_fast_forward` + `deletion` + `required_linear_history`; `bypass_actors:[]`; `enforcement:"active"`. The only delta is `conditions.ref_name.include` (`refs/heads/main` vs `refs/heads/develop`).
- **`merge` dropped from allowed merges (review MEDIUM 05-04).** Because `required_linear_history` rejects merge commits, the merge button would always fail — so only `squash` and `rebase` are offered.
- **Idempotent applier (review MEDIUM 05-04 / T-05-14).** `apply-rulesets.sh` GETs `repos/gseg-ethz/geodispbench3d/rulesets`, matches each payload by its `name` (jq), and `--method PUT repos/.../rulesets/<id>` when present else `--method POST repos/.../rulesets` — printing the returned ruleset id. Re-running never creates duplicates.
- **`--dry-run` + write-guarding preflight (review MEDIUM 05-04 / T-05-09).** A preflight runs before any write (including in `--dry-run`): `gh auth status`, repo identity resolves to `gseg-ethz/geodispbench3d`, a GitHub App installation is visible, and every required context has *recently* appeared as a check run on each target branch's HEAD (`commits/<sha>/check-runs`). `--dry-run` prints the intended POST/PUT + target id and writes nothing.
- **Ship-time README (T-05-09 / LOW 05-04).** Documents what the rulesets enforce, why enablement is deferred to milestone-ship (self-lockout — the milestone PR to `main` must be green and the App token wired first), the idempotent create-or-update model, the `--dry-run` workflow, and the deliberate `strict:false` tradeoff (merging against a slightly out-of-date base is allowed; the right call for a solo maintainer).
- **Not applied this phase.** The script was only `bash -n`'d and `--help`'d; no `gh api` ruleset POST/PUT was executed, so no protection was activated.

## Task Commits

1. **Task 1: protect-main.json + protect-develop.json with the four exact CI contexts** — `7e24be6` (feat)
2. **Task 2: idempotent apply-rulesets.sh (create-or-update + dry-run + preflight) + ship-time README** — `0a5ec83` (feat)

## Files Created

- `.github/rulesets/protect-main.json` — ruleset on `refs/heads/main`; four contexts; `[squash, rebase]`; linear history; active; no bypass.
- `.github/rulesets/protect-develop.json` — sibling on `refs/heads/develop`; identical rule body.
- `.github/scripts/apply-rulesets.sh` — `set -euo pipefail`; banner; arg parse (`--dry-run`/`--help`); `require_tools` (gh + jq); `preflight`; `apply_one` (name-match PUT/POST); ship-only banner.
- `.github/rulesets/README.md` — enforcement summary, strict:false tradeoff, ship-time-only apply workflow, idempotency + preflight docs.

## Decisions Made

- **`[squash, rebase]` only.** PCHandler's template carried `[merge, squash, rebase]`; with `required_linear_history` on, `merge` is incoherent, so it was removed in both payloads (the in-phase verify asserts the merge-method set is exactly `{squash, rebase}`).
- **Idempotency over a bare POST.** The RESEARCH delivery block showed a bare `POST`; a re-run of that creates duplicate rulesets. The script instead queries by `name` and create-or-updates, recording the returned id — the deterministic behavior the review asked for.
- **Preflight guards activation.** Making a never-run context required would block all merges. The preflight refuses to write unless each required context has recently produced a check run on the target branch, plus auth/identity/App checks — failing safe (a missing context or unreachable branch aborts rather than proceeds).
- **`strict:false` retained intentionally.** Kept off to avoid forcing a re-run of every open PR's checks on each base advance; documented as a conscious solo-maintainer tradeoff, flip to `true` when concurrent contributors arrive.
- **Greppable interface string.** The repo is a `REPO` variable in the script for single-sourcing; the literal `gseg-ethz/geodispbench3d/rulesets` is kept in a readback-hint comment so the endpoint stays reviewable and the plan's grep contract holds.

## Deviations from Plan

None — both tasks landed exactly per their `<action>` blocks. No Rule 1/2/3 auto-fixes and no Rule 4 architectural pauses. (One micro-adjustment within scope: the script parameterizes the repo as `REPO`, so the plan's `grep "gseg-ethz/geodispbench3d/rulesets"` contract is satisfied via a literal readback-hint comment rather than an inlined API path — same interface string, kept greppable.)

## Interface Contract — ACTION REQUIRED in Plan 05 (ci.yml)

The contexts in both payloads are pinned **char-for-char** to the canonical CI job names per the plan and `05-PATTERNS.md` (line 234):

```
Lint (ruff + pyright)
Test (core, 3.12)
Test (f2s3, 3.12)
Build wheel + install smoke
```

**The current `.github/workflows/ci.yml` does NOT yet render `Test (core, 3.12)` / `Test (f2s3, 3.12)`.** Its test job is `name: Test (${{ matrix.job.name }})` with `matrix.job.name ∈ {core, iof3d, f2s3}`, so today it renders `Test (core)` / `Test (f2s3)` (no `, 3.12` suffix). The lint and build job names (`Lint (ruff + pyright)`, `Build wheel + install smoke`) already match exactly.

This is the planned direction, not a defect in this deliverable: these payloads define the canonical contexts, and **Plan 05 owns reconciliation** — it must update the ci.yml matrix job `name` to include the Python version (e.g. `Test (${{ matrix.job.name }}, 3.12)`) and machine-verify equality via `check_ci_ruleset_contexts.py` (renders ci.yml job names, asserts equality with these contexts — T-05-10). If Plan 05 instead chooses to keep `Test (core)` as the rendered name, it must update these two contexts in lockstep. **Do not enable the rulesets until that equality holds**, or the gate is unsatisfiable.

## Verification Evidence

- Both payloads `json.load` cleanly; contexts `== ["Lint (ruff + pyright)", "Test (core, 3.12)", "Test (f2s3, 3.12)", "Build wheel + install smoke"]`; `ref_name.include` is `["refs/heads/main"]` / `["refs/heads/develop"]`; `allowed_merge_methods` set `== {squash, rebase}`; `enforcement == "active"`; `bypass_actors == []`; `strict_required_status_checks_policy is False`.
- `apply-rulesets.sh`: `bash -n` clean; greps confirm the `rulesets` endpoint, `--method PUT`, and `--dry-run`; `--help` exits 0 with usage. README greps confirm `ship` and `strict` are documented.
- **Not run during the phase:** no `gh api` ruleset POST/PUT executed (only `bash -n` + `--help`), so no branch protection was activated — exactly as required (avoids self-lockout).
- **Not verifiable locally (deferred to ship):** the live `gh api` create-or-update, the App-installation probe, and the recent-context check all require an authenticated `gh` against `gseg-ethz/geodispbench3d` with the pipeline green; these run at milestone-ship per the README.

## Threat Surface

No new security surface beyond the plan's `<threat_model>`. All four mitigations are implemented: required_status_checks pinned to the exact contexts + empty bypass_actors + non_fast_forward/linear history (T-05-05); apply-script-as-deliverable + ship-time README + write-guarding preflight + `--dry-run` (T-05-09); contexts as an interface contract for Plan 05's machine check (T-05-10); name-match create-or-update recording returned IDs (T-05-14). No `## Threat Flags` to report.

## Known Stubs

None. The four artifacts are complete; no placeholder values, empty data sources, or TODO/FIXME markers were introduced. The only intentionally-deferred action is *running* the applier, which is a ship-time human step by design (documented in the README), not a code stub.

## Next Phase Readiness

- **Plan 05 (ci.yml + composite + publish-gate)** must render test job names matching `Test (core, 3.12)` / `Test (f2s3, 3.12)` (or update these contexts in lockstep) and add `check_ci_ruleset_contexts.py` to machine-verify equality — see the Interface Contract section above. This is the one open coordination item.
- **Plan 06 (integration verification)** owns the live apply: at milestone-ship, after CI is green and the gseg-ethz App token is wired, run `apply-rulesets.sh --dry-run` then `apply-rulesets.sh`.
- No code blockers; the only gating item is the Plan 05 context reconciliation before the rulesets are ever enabled.

## Self-Check: PASSED

- All 4 created files present on disk (`protect-main.json`, `protect-develop.json`, `apply-rulesets.sh`, `README.md`).
- Both task commits found in git history (`7e24be6`, `0a5ec83`).

---
*Phase: 05-ci-cd-release*
*Completed: 2026-06-28*
