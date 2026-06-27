---
phase: 4
slug: licensing-metadata-packaging
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-06-27
---

# Phase 4 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| repo metadata → public PyPI listing | `pyproject.toml` + README become the public package page and long-description at publish time (Phase 5); whatever is written here ships publicly | classifiers, project URLs, author/description, long-description (no secrets) |
| public `pip install` → dependency resolver | the published wheel's `dependencies`/extras drive what a clean public environment resolves; an unresolvable dep breaks install for everyone | declared dependency + extras graph |
| `import geodispbench3d_iof3d` → optional private deps | the dormant adapter package ships publicly but must not require the private `iof3D`/`pc2img` at import time | module import side effects |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-02-D | Denial of Service | `[project.optional-dependencies]` publishing an unresolvable private dep | high | mitigate | `iof3d` extra commented out (`pyproject.toml:60-71`), not `[]`; iof3D/pc2img verified absent from public PyPI; clean `pip install '.[f2s3]'` proven in-phase via throwaway venv | closed |
| T-04-02-T | Tampering | `Private :: Do Not Upload` classifier removal | medium | mitigate | Guard classifier removed (0 occurrences in `pyproject.toml`); honest maturity set to `Development Status :: 4 - Beta`, not Stable, so consumers are not misled | closed |
| T-04-SC | Tampering | adding `pchandler ~= 2.1` to the `f2s3` extra | medium | mitigate | `f2s3 = ["pchandler ~= 2.1"]` (`pyproject.toml:78`); pchandler is first-party (gseg-ethz/ETH Zurich), 2.1.0 on PyPI, symbol API verified against the actual wheel (Package Legitimacy Audit — Approved; not a slopsquat target) | closed |
| T-04-03-R | Repudiation | lazy `__getattr__` masking a genuine bug as "iof3D missing" | medium | mitigate | `__getattr__` (`__init__.py:59-78`) translates ONLY a `ModuleNotFoundError` whose top-level package is in `_IOF3D_GATED_TOPS = {iof3D, pc2img}`; every other failure re-raises unchanged; translated case chains via `from exc` for diagnosability | closed |
| T-04-04-T | Tampering | guard tricked into importing a private dep on a clean install | medium | mitigate | PEP 562 defers all heavy imports to attribute access (`__init__.py`); module import never pulls iof3D/pc2img eagerly; simulated-absence tests assert `import geodispbench3d_iof3d` succeeds with those imports blocked | closed |
| T-04-01-I | Information Disclosure | `[project.urls]`, README links | low | mitigate | All `[project.urls]` point only at public `github.com/gseg-ethz/geodispbench3d` and `gseg.igp.ethz.ch` — no private-repo paths, tokens, or internal hostnames enter shippable metadata; Task-1 test asserts the public host/path | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

No accepted risks — all six threats were mitigated in implementation.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-27 | 6 | 6 | 0 | /gsd-secure-phase (L1 grep-depth, register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-27
