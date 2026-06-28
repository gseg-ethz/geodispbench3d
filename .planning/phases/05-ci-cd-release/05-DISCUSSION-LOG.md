# Phase 5: CI/CD & Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-27
**Phase:** 5-ci-cd-release
**Areas discussed:** Type-check CI policy, Lint→Test→Build coupling, Main/develop branch protection, Publish safety & trigger, release-please ↔ publish wiring, Sphinx/RTD publication, Milestone versioning

---

## Type-check CI policy (Phase 2 D-13)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep pyright, scope to core | Enforce pyright; green it by excluding the iof3D plugin package + ignoring unresolvable plugin imports (iof3D un-installable publicly per Phase 4) | ✓ |
| Keep pyright, baseline-aware | Enforce "no NEW errors vs a committed baseline"; carries a baseline artifact | |
| Demote pyright, adopt strict mypy | pyright informative-only; strict mypy gate pchandler-style | |

**User's choice:** Keep pyright, scope to core.
**Notes:** Resolves D-13 in favour of pyright. The unresolvable-import red is structural (iof3D private at go-live), so scope-away is the only path to a genuine 0-error gate.

---

## Lint→Test→Build coupling

| Option | Description | Selected |
|--------|-------------|----------|
| Parallel lint+test, build needs test | lint/test independent (no masking); build gated behind test | ✓ |
| Keep linear chain | lint→test→build as-is; fail-fast, cheapest minutes | |
| Full decouple | all jobs independent | |

**User's choice:** Parallel lint+test, build needs test.
**Notes:** User correctly challenged the initial "full decouple" recommendation — the linear chain had real intent (fail-fast, quality ladder, don't-build-broken-artifacts). Clarified that the *masking* problem was a symptom of chronic-red lint (fixed by the type-check decision) and that publish safety lives on the release path, not PR CI. Settled on the middle path that keeps the quality-ladder intent and only sheds masking.

---

## Main/develop branch protection (PROT-01, scope addition)

| Option | Description | Selected |
|--------|-------------|----------|
| Required checks + PR-required (minimal-real) | Mirror PCHandler's minimal protection | ✓ |
| Full governance ruleset | + CODEOWNERS, required reviews, signed commits | |
| Document only | Produce ruleset as docs, don't enforce | |

**Timing sub-decision:** Commit artifact now, **enable at ship** (avoids mid-release lockout) — selected over apply-immediately / document-only.

**User's choice:** Mirror PCHandler, enable at ship. **Caveat:** also protect `develop` (PCHandler's was named `develop/gsd`), not just `main`.
**Notes:** Pulled in as a Phase 5 work item (enforcement half of CI/CD), not a separate phase. Mirror PCHandler's `protect-main` (id 18108142) + `protect-develop-gsd` (id 18108143) rulesets: PR-required (0 approvals), required status checks (strict=false), non_fast_forward, deletion, required_linear_history, no bypass. Delivered as committed `gh api` script.

---

## release-please token source

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse gseg-ethz GitHub App | Same App PCHandler uses; org APP_ID/APP_PRIVATE_KEY secrets | ✓ |
| Create a dedicated GitHub App | New App scoped to geodispbench3d | |
| Fine-grained PAT fallback | RELEASE_PLEASE_TOKEN PAT | |

**User's choice:** Reuse gseg-ethz GitHub App.
**Notes:** App token re-triggers workflows and passes required checks on protected `main` — the documented release-please-vs-protection problem PCHandler already solved (its `gsd/phase-8-release-please-fix` branch). Wiring: `on: workflow_run` after CI succeeds on main.

---

## Sphinx/RTD publication (DOCS-01, scope addition)

| Option | Description | Selected |
|--------|-------------|----------|
| Full scaffold + RTD config now | conf.py + myst-parser over existing Markdown + .readthedocs.yaml; RTD activates at go-public | ✓ |
| Config stub only | .readthedocs.yaml + minimal conf.py; content later | |
| Defer docs to its own phase | Keep Phase 5 strictly CI/CD | |

**User's choice:** Full scaffold + RTD config now.
**Notes:** "Wiring that stays red until going public" — RTD project import deferred until repo is public. Existing `docs/` is Markdown (no conf.py), so myst-parser is needed; add to the `docs` extra. Mirror PCHandler's `.readthedocs.yaml`.

---

## Milestone versioning

**User decision (volunteered):** Publish this milestone as **v0.2**, not v1.0. First public release cut = **v0.2.0**; relabel milestone v1.0 → v0.2; seed the release-please manifest (currently `0.0.0`) accordingly.

---

## Claude's Discretion
- Exact `pyrightconfig.json` exclude mechanics + per-job pyright invocation.
- Final CI job names / matrix shape (must match D-08 required-check contexts).
- v0.2.0 seeding mechanism (manifest seed vs `Release-As`).
- Docs build as blocking vs informative CI job.
- Whether to factor a `setup-python-deps` composite action.

## Deferred Ideas
- iof3D re-enablement (extra + CI job) when iof3D publishes publicly (~6mo).
- Full governance ruleset (CODEOWNERS, required reviews, signed commits).
- OS matrix (macOS/Windows).
- GPU/canary workflows (PCHandler's `canary.yml`, `gpu-image-refresh.yml`).
