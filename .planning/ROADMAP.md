# Roadmap: geodispbench3d — Publication Readiness

## Overview

This milestone takes the existing, already-working `geodispbench3d` codebase from "works for
us" to publication-ready on public PyPI. The work sequences strictly: an audit produces a
findings report; targeted fixes are scoped from that report; CLI surfaces are hardened and the
F2S3 adapter is showcased as the canonical `CliToolAdapter` example; licensing, metadata, and
packaging are reconciled for public distribution; and finally CI/CD automation and trusted
publishing close the loop.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Code-Health Audit** - Read-only audit producing a written findings report that gates all subsequent work
- [ ] **Phase 2: Targeted Fixes** - Apply audit-scoped fixes until the full test and quality-tool suite passes
- [ ] **Phase 3: CLI Hardening** - Harden all three CLI surfaces; document F2S3 as the canonical CliToolAdapter example
- [ ] **Phase 4: Licensing, Metadata & Packaging** - Reconcile license, drop Private classifier, untangle packaging deps; resolve open iof3d/pchandler decisions
- [ ] **Phase 5: CI/CD & Release** - Automate lint/type/test gates, wheel+sdist build, and trusted-publishing release to public PyPI

## Phase Details

### Phase 1: Code-Health Audit

**Goal**: A structured findings report exists that classifies every code-health concern and authorises (or defers) each fix before any code changes land
**Depends on**: Nothing (first phase)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04
**Success Criteria** (what must be TRUE):

  1. A written report enumerates all bloat, dead code, and duplication found across `src/`
  2. Each of the three architecture-flagged anti-patterns (untyped `SuiteConfig`, duplicated `SweepParameter` coercion, duplicated `_parser_fn_repr`) is evaluated and given a disposition
  3. The three CLI surfaces (`cli.py`, `CliToolAdapter`, F2S3 `conda-run`) each have a focused risk assessment in the report
  4. Every finding carries a severity rating and one of: fix / defer / accept

**Plans**: 2 plans
**Wave 1**

- [ ] 01-01-PLAN.md — Run the locked detector set (vulture/coverage/deptry/radon) via the conda env, capture reproducible evidence, and distill EVIDENCE.md

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-02-PLAN.md — Reasoned manual file:line review (incl. design-sensibility D-07 + CONCERNS re-verify) and assemble the single severity-classified, disposition-recommended REPORT.md

### Phase 2: Targeted Fixes

**Goal**: All audit-mandated fixes are applied, dead code is removed, and the full quality-tool suite (ruff, pyright, pytest) passes cleanly
**Depends on**: Phase 1
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04
**Success Criteria** (what must be TRUE):

  1. Every finding tagged "fix" in the audit report is resolved in an atomic, reviewed commit
  2. Dead code and unused bloat identified by the audit is absent from `src/`
  3. `SweepParameter` construction is handled by a single source (e.g. `from_mapping` classmethod); `_parser_fn_repr` lives in one shared location, not two
  4. `ruff`, `pyright`, and the full `pytest` suite (core, iof3d, f2s3) pass without errors after every fix lands

**Plans**: TBD

### Phase 3: CLI Hardening

**Goal**: All three CLI surfaces handle failures predictably and F2S3 is documented as the canonical CliToolAdapter example (subprocess + conda-run pattern)
**Depends on**: Phase 2
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):

  1. The package CLI (`run` / `rescore` / `analyze` / `dashboard` / `list-metrics`) validates arguments and exits with documented non-zero codes on error
  2. `CliToolAdapter` has a written subprocess contract covering: nonzero tool exit, missing output files, and timeout — all surface as clear failures, not silent data corruption
  3. The F2S3 `conda-run` integration detects a missing env or missing binary and emits an actionable error message
  4. Tests cover the hardened CLI behaviours: invalid arguments, exit codes, adapter failure modes
  5. F2S3 is documented as the canonical `CliToolAdapter` example, including a "how to obtain F2S3" note sourced from the gseg-ethz F2S3 repo for the case where F2S3 is not bundled in-env

**Open question for Phase 3 discussion:** F2S3 binary in-env vs subprocess/`conda-run` — decided here; subprocess favours the CLI-adapter showcase but the alternative should be evaluated.
**Plans**: TBD

### Phase 4: Licensing, Metadata & Packaging

**Goal**: The package is legally and structurally ready for public PyPI distribution — license statements consistent, Private classifier removed, and the F2S3 extra installable without the iof3d extra
**Depends on**: Phase 2
**Requirements**: LIC-01, LIC-02, LIC-03, LIC-04, PKG-01, PKG-02, PKG-03
**Success Criteria** (what must be TRUE):

  1. README, `pyproject.toml`, and `LICENSE` are consistent: all say BSD-3-Clause; no "Proprietary" language and no `Private :: Do Not Upload` classifier remain
  2. Package metadata (description, project URLs, authors, supported-Python classifiers) is complete and accurate for a public release
  3. `CITATION.cff` and any docs reflect the public BSD-3-Clause status
  4. Installing `geodispbench3d[f2s3]` resolves `pchandler` correctly without depending on the `iof3d` extra; `pchandler`'s new PyPI release is confirmed non-breaking (or the usage is adapted)

**Open questions for Phase 4 discussion:**

- Resolve `pchandler` for the F2S3 parser via the `f2s3` extra vs a `pchandler`-free example parser
- Ship `geodispbench3d_iof3d` and the `iof3d-ax` script in the public distribution, or exclude them

**Plans**: TBD

### Phase 5: CI/CD & Release

**Goal**: An automated pipeline validates code quality on every push and publishes verified releases to public PyPI via trusted publishing
**Depends on**: Phase 4
**Requirements**: CICD-01, CICD-02, CICD-03, CICD-04
**Success Criteria** (what must be TRUE):

  1. CI runs ruff (lint), pyright (type check), and the full test matrix across Python 3.11 and 3.12 on every push and pull request
  2. CI builds wheel + sdist and the distribution passes `twine check` before any publish step can proceed
  3. A tagged release triggers OIDC trusted publishing to public PyPI — no stored long-lived tokens are used
  4. release-please is wired end-to-end so version bumps, changelog entries, and PyPI publishes flow automatically from a git tag

**Plans**: TBD

## Progress

**Execution Order:** 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Code-Health Audit | 0/? | Not started | - |
| 2. Targeted Fixes | 0/? | Not started | - |
| 3. CLI Hardening | 0/? | Not started | - |
| 4. Licensing, Metadata & Packaging | 0/? | Not started | - |
| 5. CI/CD & Release | 0/? | Not started | - |
