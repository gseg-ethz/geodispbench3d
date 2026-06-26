# geodispbench3d — Publication Readiness

## What This Is

`geodispbench3d` is a mature, tool-agnostic benchmark framework for 3D
displacement / optical-flow tools: a YAML-driven front end (suite → tool +
dataset + metrics), Bayesian hyperparameter sweeps via Ax, three execution
modes (`sweep`, `rescore`, `analyze`) over one evaluation core, a pluggable
`ToolAdapter` contract with two shipped integrations (iof3D, F2S3),
provenance-first persistence, and a Streamlit dashboard.

This milestone takes the existing (already BSD-3-Clause) codebase from "works
for us" to **publication-ready for public release on PyPI with CI/CD** — gated
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
- [ ] Harden the three CLI-based workflow surfaces: package CLI (`cli.py`), `CliToolAdapter`, and the F2S3 `conda-run` subprocess integration; showcase F2S3 as the canonical `CliToolAdapter` example
- [ ] Reconcile licensing for public release (README ↔ pyproject/LICENSE, already BSD-3-Clause), drop the `Private :: Do Not Upload` classifier, polish metadata
- [ ] Untangle packaging deps: comment out the `iof3d` extra (iof3D stays private), make the F2S3 path resolve `pchandler` without it, and verify `pchandler` against its newly-published PyPI release
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
- Licensing is already BSD-3-Clause in `pyproject.toml` + `LICENSE` (ETH Zurich, 2025–2026); only the README still says "Proprietary" — a reconciliation, not a license choice.
- **iof3D stays private** at go-live, so the `iof3d` optional dependency cannot resolve on public PyPI and must be commented out. Its CI test job is already disabled pending iof3D publication.
- **F2S3 is already a `CliToolAdapter` integration**: the `geodispbench3d_f2s3` sublib is only an output parser + tool YAML; execution goes through the generic CLI adapter via `conda run -n f2s3-dev312 f2s3`. The `f2s3` extra is empty, yet the parser imports `pchandler` — so F2S3 currently only works because the `iof3d` extra happens to pull `pchandler` in. Commenting out `iof3d` exposes this latent gap.
- `pchandler` (newly published on PyPI, with recent changes) is used in two places: the F2S3 parser and the iof3d adapter; its usage must be verified non-breaking.
- Dev environment is conda-isolated: env `iof3d_cosicorr3d-dev312` is mandated by `AGENTS.md` (bare `python`/`pip`/`pytest` are forbidden); F2S3 runs in a separate env `f2s3-dev312` via `conda run`.
- CI currently targets Python 3.12; package supports 3.11/3.12; numpy is pinned to the 2.0 major.
- Tooling available: `gh` CLI present (for clean PRs to `main`); `codex` CLI installed (v0.142.2) for internal plan reviews.

## Constraints

- **Tech stack**: Python ~=3.11/3.12, numpy 2.0 pin, Ax / Hydra / OmegaConf — preserve; transitive tool stacks must stay NumPy-2 compatible.
- **Dev environment**: all python/pip/pytest invocations must go through the mandated conda env per `AGENTS.md`.
- **Process — branching**: GSD work stays on `develop` and phase branches; PRs to `main` happen only at milestone completion and must strip the `.planning/` folder.
- **Process — review**: internal phase-plan reviews are run through the codex CLI.
- **Licensing**: already BSD-3-Clause; the `Private :: Do Not Upload` classifier and the README "Proprietary" line must be removed/reconciled before any public PyPI publish.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Publish target = public PyPI | Widen use; the goal driving this milestone | — Pending |
| Refactor approach = audit first, then scope fixes | Confidence before churn | — Pending |
| Branching = `develop` + phase branches; `main` PRs only at milestone, `.planning/` stripped via clean PR | Keep `main` clean and release-only | — Pending |
| Internal plan reviews via codex CLI | Cross-AI review to harden plans before execution | — Pending |
| License = BSD-3-Clause (already in `pyproject` + `LICENSE`); reconcile README + drop `Private` classifier | No fresh license choice needed | ✓ Resolved |
| iof3D stays private → comment out the `iof3d` extra for public release | iof3D not publishable at go-live | — Pending |
| OPEN: F2S3 binary in-env vs subprocess/`conda-run` | Decided in the CLI/packaging phase; subprocess favours the CLI-adapter showcase | — Pending |
| OPEN: resolve `pchandler` for F2S3 via the `f2s3` extra vs a `pchandler`-free example parser | Decided in the packaging phase | — Pending |
| OPEN: ship `geodispbench3d_iof3d` + `iof3d-ax` script in the public distribution, or exclude | Decided in the packaging phase | — Pending |
| If F2S3 not bundled in-env → document how to obtain/install it (from gseg-ethz F2S3 repo) | Users need a path to run the F2S3 example | — Pending |

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
