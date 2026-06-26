# geodispbench3d — Publication Readiness

## What This Is

`geodispbench3d` is a mature, tool-agnostic benchmark framework for 3D
displacement / optical-flow tools: a YAML-driven front end (suite → tool +
dataset + metrics), Bayesian hyperparameter sweeps via Ax, three execution
modes (`sweep`, `rescore`, `analyze`) over one evaluation core, a pluggable
`ToolAdapter` contract with two shipped integrations (iof3D, F2S3),
provenance-first persistence, and a Streamlit dashboard.

This milestone takes the existing codebase from "works for us" to
**publication-ready for a public, open-source PyPI release with CI/CD** — gated
behind a code-health pass that builds confidence in the codebase before
anything ships.

## Core Value

Confidence: nothing is published to PyPI until the codebase is demonstrably
lean, correct, well-tested, and its CLI-integration story is sound. The audit
comes before the cleanup, and the cleanup comes before the release.

## Requirements

### Validated

<!-- Inferred from existing code via .planning/codebase/ map (2026-06-26). -->

- ✓ YAML-driven suite configuration (suite composes tool + dataset + metrics) — existing
- ✓ Bayesian hyperparameter sweeps via Ax (`AxSweepRunner`) — existing
- ✓ Three execution modes (`sweep`, `rescore`, `analyze`) sharing one `evaluate_trial` core — existing
- ✓ Pluggable `ToolAdapter` contract (cli / callable / custom / factory) — existing
- ✓ Two shipped tool integrations: iof3D (in-process callable) and F2S3 (CLI subprocess) — existing
- ✓ Provenance-first persistence: parquet results store, predictions cache, per-run `summary.json` — existing
- ✓ Streamlit results dashboard — existing
- ✓ Quality tooling in place: pytest suites (core/iof3d/f2s3), ruff, pyright, pre-commit, release-please — existing

### Active

<!-- This milestone. Building toward these. -->

- [ ] Code-health audit producing a written findings report (bloat, dead code, the flagged anti-patterns, CLI risk areas)
- [ ] Resolve audit findings — de-bloat and fixes scoped *from* the report, not pre-committed
- [ ] Harden the three CLI-based workflow surfaces: package CLI (`cli.py`), `CliToolAdapter`, and the F2S3 `conda-run` subprocess integration
- [ ] Re-license from Proprietary to an OSS license; update classifiers, package metadata, and README accordingly
- [ ] CI/CD: lint + type + test gates, build (wheel + sdist), and trusted-publishing release automation to public PyPI
- [ ] Wire internal plan reviews through the codex CLI

### Out of Scope

- New tool adapters beyond iof3D / F2S3 — not needed for publish readiness; adapter contract already proven
- New benchmark features or metrics — this milestone is hardening + publishing, not feature growth
- Parallel sweep execution — a known future extension (`parallel_trials` exists but is sequential today); not publish-blocking
- Rewriting the legacy `iof3d-ax` CLI — kept as-is unless the audit flags it (not named as a concern)

## Context

- Brownfield: full codebase map exists at `.planning/codebase/` (refreshed 2026-06-26).
- The architecture map already flags three anti-patterns to feed the audit: `SuiteConfig` typed as `Any` in orchestration, duplicated `SweepParameter`-coercion logic across three modules, and a duplicated `_parser_fn_repr` helper.
- Dev environment is conda-isolated: env `iof3d_cosicorr3d-dev312` is mandated by `AGENTS.md` (bare `python`/`pip`/`pytest` are forbidden); F2S3 runs in a separate env `f2s3-dev312` via `conda run`.
- CI currently targets Python 3.12; package supports 3.11/3.12; numpy is pinned to the 2.0 major.
- Tooling available: `gh` CLI present (for clean PRs to `main`); `codex` CLI installed (v0.142.2) for internal plan reviews.

## Constraints

- **Tech stack**: Python ~=3.11/3.12, numpy 2.0 pin, Ax / Hydra / OmegaConf — preserve; transitive tool stacks must stay NumPy-2 compatible.
- **Dev environment**: all python/pip/pytest invocations must go through the mandated conda env per `AGENTS.md`.
- **Process — branching**: GSD work stays on `develop` and phase branches; PRs to `main` happen only at milestone completion and must strip the `.planning/` folder.
- **Process — review**: internal phase-plan reviews are run through the codex CLI.
- **Licensing**: current Proprietary license + `Private :: Do Not Upload` classifier must be replaced before any public PyPI publish.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Publish target = public PyPI (open-source) | Widen use; the goal driving this milestone | — Pending |
| Refactor approach = audit first, then scope fixes | Confidence before churn | — Pending |
| Branching = `develop` + phase branches; `main` PRs only at milestone, `.planning/` stripped via clean PR | Keep `main` clean and release-only | — Pending |
| Internal plan reviews via codex CLI | Cross-AI review to harden plans before execution | — Pending |
| OSS license = TBD (MIT / Apache-2.0 / BSD-3) | Required to drop Proprietary for public release; decided in the licensing phase | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-26 after initialization*
