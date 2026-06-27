# Requirements: geodispbench3d — Publication Readiness

**Defined:** 2026-06-26
**Core Value:** Nothing is published to PyPI until the codebase is demonstrably lean, correct, well-tested, and its CLI-integration story is sound.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Audit

- [x] **AUDIT-01**: A written code-health findings report is produced covering bloat, dead code, and duplication across `src/`
- [x] **AUDIT-02**: The report evaluates the three architecture-flagged anti-patterns (untyped `SuiteConfig`, duplicated `SweepParameter` coercion, duplicated `_parser_fn_repr`)
- [x] **AUDIT-03**: The report includes a focused risk review of the three CLI surfaces (package `cli.py`, `CliToolAdapter`, F2S3 `conda-run`)
- [x] **AUDIT-04**: Each finding is severity-classified and tagged with a recommended disposition (fix / defer / accept)

### Fixes

- [x] **FIX-01**: Findings marked "fix" in the audit are resolved, each as an atomic, reviewed change
- [ ] **FIX-02**: Dead code and unused bloat identified in the audit is removed
- [x] **FIX-03**: Flagged duplication is consolidated to a single source (SweepParameter construction; `_parser_fn_repr`)
- [x] **FIX-04**: The full test suite (core/iof3d/f2s3) plus ruff and pyright pass after the fixes land

### CLI Hardening

- [ ] **CLI-01**: The package CLI (`run`/`rescore`/`analyze`/`dashboard`/`list-metrics`) has validated argument handling and tested error/exit-code paths
- [ ] **CLI-02**: `CliToolAdapter` subprocess invocation has a documented contract and robust failure handling (nonzero exit, missing outputs, timeouts)
- [ ] **CLI-03**: The F2S3 `conda-run` integration verifies env/binary presence and surfaces failures clearly
- [ ] **CLI-04**: The hardened CLI behaviors are covered by tests
- [ ] **CLI-05**: F2S3 is documented/showcased as the canonical `CliToolAdapter` example (subprocess + `conda-run` pattern), including a short "how to obtain/install F2S3" note sourced from the gseg-ethz F2S3 repo when F2S3 is not bundled in-env

### Licensing & Metadata

- [ ] **LIC-01**: The README license statement is reconciled with `pyproject.toml` + `LICENSE` (all BSD-3-Clause; README currently says Proprietary)
- [ ] **LIC-02**: The `Private :: Do Not Upload` classifier is removed; OSI license + supported-Python classifiers confirmed correct
- [ ] **LIC-03**: Package metadata (description, project URLs, authors) verified/completed for public release
- [ ] **LIC-04**: `CITATION.cff` and docs reflect the public BSD-3-Clause status

### Packaging & Dependencies

- [ ] **PKG-01**: The `iof3d` optional dependency is commented out / disabled for the public release (iof3D is not public at go-live)
- [ ] **PKG-02**: The F2S3 path is installable standalone — `pchandler` resolves without the `iof3d` extra (today the `f2s3` extra is empty but the parser imports `pchandler`)
- [ ] **PKG-03**: geodispbench3d's `pchandler` usage is verified against the newly-published `pchandler` on PyPI and confirmed non-breaking (or adapted)

### CI/CD & Release

- [ ] **CICD-01**: CI runs lint (ruff), type-check (pyright), and the full test matrix across supported Python versions (3.11/3.12)
- [ ] **CICD-02**: CI builds wheel + sdist and validates the distribution (e.g. `twine check`)
- [ ] **CICD-03**: A tagged release publishes to public PyPI via trusted publishing (OIDC), with no stored long-lived tokens
- [ ] **CICD-04**: Release automation (release-please) is aligned end-to-end with the publish workflow

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Execution

- **EXEC-01**: Parallel sweep execution (`parallel_trials` wired through to concurrent trial evaluation)

### Integrations

- **INT-01**: Additional tool adapters beyond iof3D / F2S3

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New benchmark features or metrics | Milestone is hardening + publishing, not feature growth |
| Parallel sweep execution | Known future extension; not publish-blocking (deferred to v2) |
| New tool adapters | Adapter contract already proven by iof3D/F2S3 (deferred to v2) |
| Rewriting the legacy `iof3d-ax` CLI | Kept as-is unless the audit flags it; not named as a concern (whether to *ship* it publicly is an open decision, not a rewrite) |
| Publishing iof3D / making it public | Out of this project's control; iof3D stays private at go-live (drives PKG-01) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIT-01 | Phase 1 | Complete |
| AUDIT-02 | Phase 1 | Complete |
| AUDIT-03 | Phase 1 | Complete |
| AUDIT-04 | Phase 1 | Complete |
| FIX-01 | Phase 2 | Complete |
| FIX-02 | Phase 2 | Pending |
| FIX-03 | Phase 2 | Complete |
| FIX-04 | Phase 2 | Complete |
| CLI-01 | Phase 3 | Pending |
| CLI-02 | Phase 3 | Pending |
| CLI-03 | Phase 3 | Pending |
| CLI-04 | Phase 3 | Pending |
| CLI-05 | Phase 3 | Pending |
| LIC-01 | Phase 4 | Pending |
| LIC-02 | Phase 4 | Pending |
| LIC-03 | Phase 4 | Pending |
| LIC-04 | Phase 4 | Pending |
| PKG-01 | Phase 4 | Pending |
| PKG-02 | Phase 4 | Pending |
| PKG-03 | Phase 4 | Pending |
| CICD-01 | Phase 5 | Pending |
| CICD-02 | Phase 5 | Pending |
| CICD-03 | Phase 5 | Pending |
| CICD-04 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 24 total
- Mapped to phases: 24 (all phases)
- Unmapped: 0

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 — traceability populated after roadmap creation*
