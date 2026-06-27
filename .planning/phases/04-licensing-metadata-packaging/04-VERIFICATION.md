---
phase: 04-licensing-metadata-packaging
verified: 2026-06-27T22:10:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 4: Licensing, Metadata & Packaging Verification Report

**Phase Goal:** The package is legally and structurally ready for public PyPI distribution — license statements consistent (all BSD-3-Clause), Private classifier removed, and the F2S3 extra installable without the iof3d extra.
**Verified:** 2026-06-27T22:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | README, `pyproject.toml`, `LICENSE` consistent BSD-3-Clause; no "Proprietary"; no `Private :: Do Not Upload` classifier (SC1, LIC-01/02) | ✓ VERIFIED | `pyproject.toml:10,19` license=BSD-3-Clause, no Private classifier present; `README.md:86` "Released under the BSD-3-Clause license"; no "Proprietary" in License section; `LICENSE:1` "BSD 3-Clause License". Pinned by `test_no_private_classifier`, `test_readme_license_is_bsd_not_proprietary` (pass) |
| 2 | Package metadata complete/accurate for public release: description, project URLs, authors, supported-Python classifiers (SC2, LIC-03) | ✓ VERIFIED | `pyproject.toml`: description present (`:7`), authors (`:11`), Python 3.11/3.12 classifiers (`:17-18`), Beta/audience/topic classifiers (`:21-23`), Documentation+Changelog URLs at public host (`:37-38`). Pinned by `test_required_maturity_audience_topic_classifiers_present`, `test_project_urls_documentation_and_changelog_public` (pass) |
| 3 | `CITATION.cff` and docs reflect public BSD-3-Clause status (SC3, LIC-04) | ✓ VERIFIED | `CITATION.cff:10` `license: BSD-3-Clause`; `docs/tools/iof3d.md` legacy-CLI line qualified for dormant wheel. Pinned by `test_citation_and_license_are_bsd` (pass) |
| 4 | `geodispbench3d[f2s3]` resolves `pchandler` without the `iof3d` extra; pchandler PyPI release confirmed non-breaking (SC4, PKG-02/03) | ✓ VERIFIED | `pyproject.toml:78` `f2s3 = ["pchandler ~= 2.1"]`; `iof3d` extra commented out (`:60-64`). `output_parser.py:28-30` imports only `pchandler` (no iof3D/pc2img). pchandler **2.1.0 confirmed live on public PyPI** (independent query) matching the `~= 2.1` pin. In-phase throwaway-venv clean install documented PASS (INSTALL_RC=0, SMOKE_RC=0). Full behavioral `pytest tests/f2s3` legitimately deferred to Phase 5 CI |
| 5 | `import geodispbench3d_iof3d` succeeds without iof3D; gated symbol raises actionable chained `ImportError`; unrelated import errors re-raise unchanged (PKG-01, D-02) | ✓ VERIFIED (behavioral) | PEP 562 `__getattr__` guard in `__init__.py:59-78`; translates only `ModuleNotFoundError` whose top package ∈ `{iof3D,pc2img}`, chained `from exc`. Tests `test_public_import_succeeds_use_fails`, `test_parser_path_resolves_without_iof3d` pass (in-process simulated absence). Dev-env check: real `Iof3dCallableAdapter` still resolves through guard |
| 6 | `iof3d-ax` exits 1 with actionable message and no raw traceback when iof3D absent — in- and out-of-process (PKG-01, D-03) | ✓ VERIFIED (behavioral) | `cli.py:15-24` thin launcher converts `ImportError`→`SystemExit`; `_sweep_cli.py` holds the heavy hydra/iof3D body. Tests `test_iof3d_ax_launcher_exits_cleanly` (in-process SystemExit) and `test_iof3d_ax_subprocess_exits_1_no_traceback` (out-of-process exit 1, actionable stderr, no `Traceback`) pass |
| 7 | Non-gated `parse_iof3d_output` resolves while iof3D/pc2img blocked but pchandler present (PKG-01) | ✓ VERIFIED (behavioral) | `_LAZY` maps `parse_iof3d_output`→`output_parser` (pchandler-only). `test_parser_path_resolves_without_iof3d` passes under simulated iof3D/pc2img block |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tests/core/test_packaging_metadata.py` | Stdlib metadata gate, 7 functions | ✓ VERIFIED | Exists; 7 tests pass; pure tomllib+pathlib |
| `tests/core/test_iof3d_import_guard.py` | 5-test simulated-absence guard + extras gate | ✓ VERIFIED | Exists; 5 tests pass (in-process + subprocess) |
| `src/geodispbench3d_iof3d/_sweep_cli.py` | Relocated hydra-decorated body | ✓ VERIFIED | Exists; holds `main`/`_collect_run_kwargs`/heavy imports |
| `src/geodispbench3d_iof3d/__init__.py` | PEP 562 guard | ✓ VERIFIED | `__getattr__`/`__dir__`/`_LAZY`/`_IOF3D_MISSING_HINT`/`TYPE_CHECKING` block; no eager iof3D import |
| `src/geodispbench3d_iof3d/cli.py` | Thin guarded launcher | ✓ VERIFIED | Lazy `from ._sweep_cli import main`; ImportError→SystemExit |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `__init__.py` | `.adapter`/`.factory`/`.output_parser` | PEP 562 `__getattr__` lazy import | ✓ WIRED | `_LAZY` map + `import_module` on attribute access; dev-env resolves real classes |
| `iof3d-ax` entry point | `cli:main` → `_sweep_cli.main` | lazy import + ImportError→SystemExit | ✓ WIRED | Entry point `iof3d-ax = geodispbench3d_iof3d.cli:main` resolves; launcher delegates |
| README | PyPI long-description | `dynamic = ["readme"]` | ✓ WIRED | `pyproject.toml:111` readme=README.md; License edit reaches public listing |
| `[f2s3]` extra | pchandler | `pchandler ~= 2.1` pin | ✓ WIRED | Only path carrying pchandler after iof3d extra removed; 2.1.0 on public PyPI |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase test files pass | `python -m pytest tests/core/test_packaging_metadata.py tests/core/test_iof3d_import_guard.py -q` | 12 passed | ✓ PASS |
| Full suite no regressions | `python -m pytest -q` | 129 passed | ✓ PASS |
| Guard resolves real adapter in dev env | `python -c "import geodispbench3d_iof3d as m; m.Iof3dCallableAdapter"` | resolves to `adapter.Iof3dCallableAdapter` | ✓ PASS |
| pchandler 2.1 on public PyPI | PyPI JSON query | latest 2.1.0; 2.1.x present | ✓ PASS |
| f2s3 parser import surface | grep imports | pchandler-only, no iof3D/pc2img | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| LIC-01 | 04-01 | README license reconciled to BSD-3-Clause | ✓ SATISFIED | README License section BSD-3-Clause, no Proprietary (test) |
| LIC-02 | 04-01 | `Private :: Do Not Upload` removed | ✓ SATISFIED | Classifier absent (pyproject + test) |
| LIC-03 | 04-01 | Metadata complete for public release | ✓ SATISFIED | classifiers + URLs + authors present (test) |
| LIC-04 | 04-01 | CITATION.cff + docs BSD-3-Clause | ✓ SATISFIED | CITATION.cff:10, docs qualified (test) |
| PKG-01 | 04-02 | iof3d extra disabled + dormant guard | ✓ SATISFIED | extra commented out; PEP 562 guard; 5 guard tests |
| PKG-02 | 04-02 | F2S3 installable standalone, pchandler resolves | ✓ SATISFIED | f2s3 pin; pchandler-only parser; PyPI 2.1.0; in-phase clean-install proof |
| PKG-03 | 04-02 | pchandler usage verified vs new PyPI release | ✓ SATISFIED | `~= 2.1` pin; symbol-compat recorded VERIFIED (research D-07); full behavioral suite deferred to Phase 5 |

All 7 declared requirement IDs are accounted for. No orphaned requirements (REQUIREMENTS.md maps exactly LIC-01..04, PKG-01..03 to Phase 4).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| (phase-modified files) | — | TBD/FIXME/XXX debt markers | ℹ️ none | No debt markers in any phase-modified file |
| `src/geodispbench3d_iof3d/cli.py` | 16-24 | Launcher catches **all** `ImportError`, not just iof3D/pc2img (code-review WR-01) | ⚠️ Warning | Inconsistent with the `__init__` guard's narrow translation; a genuine bug (renamed `AxSweepRunner`, missing `pchandler`) on a machine where iof3D *is* installed would be mislabeled "install iof3D". Does NOT block the phase goal (D-03 actionable-exit behavior holds) |
| `pyproject.toml` | 2,10,19 | Deprecated PEP 639 license shape + unpinned build backend (code-review WR-02) | ⚠️ Warning | `license = {text=...}` table form + `License :: OSI Approved` classifier emit `SetuptoolsDeprecationWarning` on setuptools≥77 (installed 78.1.1); build still succeeds today. Relevant to Phase 5 build/`twine check` (CICD-02) — recommend SPDX migration before publish |
| `src/geodispbench3d_iof3d/_sweep_cli.py` | 36-39,78 | `Mapping` isinstance fragility + `int(None)` on explicit null (code-review WR-03, IN-03) | ℹ️ Info | Moved-verbatim legacy code, not introduced this phase; out of phase scope |

### Deferred Items (documented, not phase gaps)

- `iof3d-ax --help` raises `hydra MissingConfigException` (bundled `conf/` lacks `__init__.py` for Hydra's `pkg://` provider). Confirmed **pre-existing** and regression-neutral across the cli/_sweep_cli split; logged in `deferred-items.md`; candidate for Phase 5. Not part of the dormant-guard deliverable.
- Full behavioral `pytest tests/f2s3` against installed `pchandler==2.1.0` deferred to Phase 5 CI `f2s3` job (needs the separate `f2s3-dev312` binary env). Resolution+import smoke proven in-phase.

### Human Verification Required

None — all observable truths were machine-verifiable and verified (behavioral guard truths covered by passing in-process and out-of-process tests).

### Gaps Summary

No gaps. All four ROADMAP success criteria and all seven requirement IDs (LIC-01..04, PKG-01..03) are satisfied with codebase evidence. The package is legally and structurally ready for public PyPI distribution: license statements are consistently BSD-3-Clause across README/pyproject/LICENSE/CITATION, the `Private :: Do Not Upload` classifier is gone, the `iof3d` extra is disabled (commented out) while the dormant adapter still ships in the wheel behind a correct PEP 562 guard, and `[f2s3]` carries a `pchandler ~= 2.1` pin proven to resolve from public PyPI.

Three non-blocking code-review warnings (WR-01 over-broad launcher except; WR-02 PEP 639 deprecated license shape; WR-03 legacy `_collect_run_kwargs` fragility) are surfaced for Phase 5 attention. WR-02 in particular is worth resolving before the Phase 5 publish build, as setuptools is on track to hard-error on the deprecated license metadata — but it only warns today and does not block the Phase 4 goal.

---

_Verified: 2026-06-27T22:10:00Z_
_Verifier: Claude (gsd-verifier)_
