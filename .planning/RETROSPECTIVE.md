# Retrospective

## Milestone: v0.2 — Publication Readiness

**Shipped:** 2026-06-28 — `geodispbench3d 0.2.0` on PyPI (OIDC trusted publishing)
**Phases:** 5 | **Plans:** 21

### What Was Built
Took an already-working benchmark framework to a public, CI/CD-gated PyPI release: a
code-health audit (Phase 1) gated targeted fixes (Phase 2), CLI surfaces were hardened
(Phase 3), licensing/metadata/packaging reconciled to BSD-3-Clause public-ready (Phase 4),
and a full CI/CD + trusted-publishing pipeline shipped (Phase 5) — 3.12-only baseline,
genuine 0-error pyright, lint/test-matrix/build/docs CI, OIDC publish, release-please,
branch-protection rulesets, and Sphinx/RTD docs.

### What Worked
- **Audit-first gating** (no fixes before the dispositioned report) kept Phase 2 scoped.
- **Wave-based parallel execution** with per-plan SUMMARY/verification kept each phase auditable.
- **Opening a real CI PR before declaring done** (Phase 5, Wave 4) caught four latent
  publish-blockers the fat local dev env had masked — the single highest-value moment.
- **Deterministic release seed** (manifest 0.1.0 + `Release-As: 0.2.0` footer) made
  release-please cut exactly 0.2.0 on the first try.
- **Gated irreversible steps** (merge-to-main, go-public, publish) behind explicit human
  confirmation + the `pypi` environment approval gate.

### What Was Inefficient
- The lean-vs-fat environment gap meant CI surfaced dependency defects (pyarrow, Ax 1.3.x)
  only at the very end; an isolated-env smoke earlier could have caught them sooner.
- `apply-rulesets.sh` depended on `jq`, which wasn't installed — applied rulesets via
  `gh api` directly instead.

### Patterns Established
- Public `main` is rebuilt clean from `develop` (`.planning` stripped via `filter-branch`,
  commit messages + `Release-As` footer preserved) — never a direct `develop→main` merge.
- Environments + trusted publishers + approval gate are external, human-provisioned prereqs.

### Key Lessons
- A "done" phase isn't done until CI runs on a real PR in the lean target environment.
- GitHub *repository rulesets* with empty `bypass_actors` bind admins too — verify bypass
  intent before enabling on a solo-maintainer repo.

### Cost Observations
- Sessions: 1 (continuous execute→ship→milestone).
- Notable: most wall-clock was CI runs (torch/CUDA build smoke ~5 min) and human approval gates.
