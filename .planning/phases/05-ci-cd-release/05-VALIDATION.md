---
phase: 5
slug: ci-cd-release
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-27
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> Note: this phase's deliverables are **GitHub Actions workflows + repo/packaging
> config**, not new application code. Validation is largely **observational** (CI run
> status, `twine check`, a TestPyPI dry-run, a docs build) plus the one genuine code
> change — fixing the residual core pyright errors to reach a real exit-0 gate. See
> `05-RESEARCH.md` › Validation Architecture for the full map.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `~= 8.4` (existing) + workflow/YAML validation via `actionlint` and running CI itself |
| **Config file** | `pyproject.toml` (no `[tool.pytest.ini_options]`; tests run by path) |
| **Quick run command** | `conda run -n iof3d_cosicorr3d-dev312 ruff check . && ruff format --check . && pyright` |
| **Full suite command** | `conda run -n iof3d_cosicorr3d-dev312 python -m pytest` (core + f2s3) |
| **Estimated runtime** | ~60–120 seconds (local lint+core); CI matrix longer |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n iof3d_cosicorr3d-dev312 ruff check . && pyright` (fast gate) + `actionlint` on any changed workflow.
- **After every plan wave:** Run `conda run -n iof3d_cosicorr3d-dev312 python -m pytest` + `python -m build && twine check dist/*`.
- **Before `/gsd-verify-work`:** A real branch push exercising the full CI run green; one TestPyPI `workflow_dispatch` dry-run before declaring CICD-03 met.
- **Max feedback latency:** ~120 seconds (local); CI feedback per push.

---

## Per-Task Verification Map

> Populated after planning (tasks are defined by gsd-planner). Requirement→validation
> anchors from research:

| Req | Behavior | Test Type | Automated Command / Observation |
|-----|----------|-----------|----------------------------------|
| CICD-01 | lint + pyright + 3.12 matrix green on push/PR | CI + local | `ruff check . && ruff format --check . && pyright` exits 0 (scoped, genuine); CI `Lint`, `Test (core,3.12)`, `Test (f2s3,3.12)` pass |
| CICD-02 | wheel+sdist pass `twine check` | CI build job + local | `python -m build && twine check dist/*` → PASSED; install-smoke imports + `geodispbench3d --help` |
| CICD-03 | OIDC publish, no tokens | TestPyPI dry-run | `workflow_dispatch` of `publish-testpypi.yml` lands on test.pypi.org via OIDC; confirm no PyPI token secret exists |
| CICD-04 | release-please end-to-end | CI observation | conventional-commit merge to `main` → Release PR → merge cuts `v0.2.0` tag + Release → `publish-pypi.yml` fires on `release: published` |
| PROT-01 | branch protection | `gh api` readback | After `apply-rulesets.sh`: rulesets `protect-main`/`protect-develop` show exact contexts; direct push to `main` rejected |
| DOCS-01 | docs build passes | CI/local build | `sphinx-build -W --keep-going -b html docs/source docs/_build/html` exits 0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **Residual core pyright errors enumerated + fixed** — run the scoped `pyright` locally, enumerate the "few pre-existing type-narrowing errors" the ROADMAP attests, and fix them in code until exit 0. Prerequisite for the genuine 0-error gate (D-01a); size early.
- [ ] `actionlint` available (local binary or pinned CI step) for workflow YAML validation.

*Existing pytest infrastructure (tests/core, tests/f2s3) covers test execution; no new test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OIDC publish to real PyPI | CICD-03 | One-shot, irreversible; depends on external pending publisher + Environment | Confirm external prereqs, then tag `v0.2.0`; observe `publish-pypi.yml` succeed |
| Branch-protection enablement | PROT-01 | Enabled at milestone-ship, not during phase (avoids self-lockout) | Run `.github/scripts/apply-rulesets.sh` at ship; `gh api .../rulesets` readback |
| RTD project import | DOCS-01 | Activates only once repo is public | Import `gseg-ethz/geodispbench3d` on ReadTheDocs post-public |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
