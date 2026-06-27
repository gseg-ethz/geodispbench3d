---
phase: 4
slug: licensing-metadata-packaging
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-27
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ~= 8.4 (`dev` extra), coverage ~= 7.0 — already installed in the mandated conda env |
| **Config file** | `pyproject.toml` (no dedicated `pytest.ini`); `pyrightconfig.json` for types |
| **Quick run command** | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q` |
| **Full suite command** | `conda run -n iof3d_cosicorr3d-dev312 pytest` (extras-aware; iof3d/f2s3 dirs self-skip) |
| **Estimated runtime** | ~10–20 seconds (the two new test files are stdlib-only metadata/import checks) |

All python/pip/pytest invocations MUST route through `conda run -n iof3d_cosicorr3d-dev312` per AGENTS.md.

---

## Sampling Rate

- **After every task commit:** Run `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q`
- **After every plan wave:** Run `conda run -n iof3d_cosicorr3d-dev312 pytest` + `ruff check . && ruff format --check .` + baseline-diff pyright (`pyright_gate.py` — no NEW errors vs `develop`)
- **Before `/gsd-verify-work`:** Full core suite green; both new test files green
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | LIC-01/02/03/04 | T-04-01-I | No private-repo paths/tokens in shippable metadata; URLs are public https | unit (metadata assert, RED-first) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_packaging_metadata.py -x` | ❌ W0 (this task creates it) | ⬜ pending |
| 04-01-02 | 01 | 1 | LIC-02/03 | T-04-02-T | Publish-guard classifier removed deliberately; honest Beta maturity signal | unit | `conda run -n iof3d_cosicorr3d-dev312 python -c "import tomllib,pathlib;..."` (see plan) | ✅ (Task 1) | ⬜ pending |
| 04-01-03 | 01 | 1 | LIC-01/04 | T-04-01-I | README long-description states BSD-3-Clause; no Proprietary | unit | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_packaging_metadata.py -x` | ✅ (Task 1) | ⬜ pending |
| 04-02-01 | 02 | 2 | PKG-01/02 | T-04-04-T | Public import succeeds with iof3D/pc2img blocked; no eager private-dep path | unit (simulated absence, RED-first) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_iof3d_import_guard.py -x` | ❌ W0 (this task creates it) | ⬜ pending |
| 04-02-02 | 02 | 2 | PKG-01 | T-04-03-R / T-04-04-T | Adapter use raises actionable ImportError chaining original; iof3d-ax exits 1 cleanly | unit | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_iof3d_import_guard.py::test_public_import_succeeds_use_fails tests/core/test_iof3d_import_guard.py::test_iof3d_ax_launcher_exits_cleanly -x` | ✅ (Task 1) | ⬜ pending |
| 04-02-03 | 02 | 2 | PKG-01/02/03 | T-04-02-D / T-04-SC | iof3d extra disabled (unresolvable private dep removed); f2s3 pins first-party pchandler ~= 2.1 | unit + integration-deferred | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_iof3d_import_guard.py -x` (unit); fresh-venv resolution gate DEFERRED to Phase 5 CI f2s3 job | ✅ (Task 1) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 = the RED-first test tasks embedded as Task 1 of each plan (task-level TDD; no separate wave needed for this coarse phase):

- [ ] `tests/core/test_packaging_metadata.py` (Plan 01, Task 1) — parses `pyproject.toml` via `tomllib` + reads `README.md`/`CITATION.cff`/`LICENSE`; asserts no `Private ::` classifier, no "Proprietary" in README License section, Beta/audience/topic classifiers present, Documentation/Changelog URLs present, `[iof3d]`-unavailable note present (no timeline). Covers LIC-01/02/03/04.
- [ ] `tests/core/test_iof3d_import_guard.py` (Plan 02, Task 1) — simulated-absence guard test (public import succeeds, adapter use raises actionable ImportError) + `iof3d-ax` clean-SystemExit test + pyproject extras assertion (`iof3d` commented, `f2s3 == ["pchandler ~= 2.1"]`). Covers PKG-01/02.
- [ ] No new framework install needed — pytest/coverage already in the `dev` extra.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh-venv `.[f2s3]` resolution pulls `pchandler 2.1.0` (no iof3D/pc2img) and `pytest tests/f2s3` passes against the installed 2.1.0 | PKG-02/PKG-03 (runtime gate) | The mandated dev env holds an editable `pchandler 2.0.0rc8` that does NOT satisfy `~= 2.1`, so the pinned release cannot be exercised in-env. DEFERRED to Phase 5's already-enabled CI `f2s3` job (session decision 2). Symbol/API compatibility is already VERIFIED against the 2.1.0 wheel in research. | Phase 5 CI: `pip install .[f2s3,dev]` in a clean runner, `pytest tests/f2s3 -v`, `pip list \| grep -iE "iof3d\|pc2img"` empty. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (both RED-first test files are Task 1 of their plans)
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-27
