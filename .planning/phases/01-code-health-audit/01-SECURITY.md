---
phase: 01
slug: code-health-audit
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-06-26
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| PyPI → dev conda env | Net-new third-party detectors (vulture, deptry, radon) installed into the mandated conda env `iof3d_cosicorr3d-dev312`; untrusted package code crosses here. | Executable Python package code |
| (none new, Plan 01-02) | Plan 01-02 is read-only on the codebase and installs nothing; it introduces no new trust boundary. | — |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-SC | Tampering | pip install of vulture / deptry / radon | high | mitigate | Install-time legitimacy checkpoint verified each package on pypi.org; detectors pinned (vulture==2.16, deptry==0.25.1, radon==6.0.1), installed dev-only into the conda env, never added to `pyproject.toml`. Verified: `grep` of `pyproject.toml` finds none of the three detectors. | closed |
| T-01-01 | Tampering | detectors run against `src/` | low | accept | Detectors are read-only analyzers; the phase makes no `src/` or `pyproject.toml` change. Verified: phase branch diff vs `develop` touches only `.planning/` + `.gitignore`. | closed |
| T-01-02 | Information disclosure | REPORT.md content | low | accept | The report documents (does not exploit) the by-design YAML-executes-code and subprocess surfaces; recording them as findings with an accept/route-forward disposition is the intended audit outcome, not a leak. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-01 | Detectors are read-only; zero source mutation observed in the phase diff. Residual risk of a detector mutating source is negligible and accepted. | Nicholas Meyer | 2026-06-26 |
| AR-02 | T-01-02 | Documenting by-design execution surfaces in REPORT.md is the intended audit deliverable; findings are routed forward, not exploited. | Nicholas Meyer | 2026-06-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-26 | 3 | 3 | 0 | gsd-secure-phase (L1, artifact-derived register) |

Notes: Register authored at plan time (both PLAN files carry `<threat_model>` blocks). ASVS L1, `block_on: high`. `threats_open: 0` with `register_authored_at_plan_time: true` and `asvs_level == 1` — L1 grep-depth verification is sufficient; no deeper auditor pass required per the secure-phase short-circuit rule. Mitigations confirmed by direct tree inspection (`pyproject.toml` clean; phase diff scoped to `.planning/` + `.gitignore`).

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-26
