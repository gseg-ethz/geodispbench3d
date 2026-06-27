---
status: complete
phase: 04-licensing-metadata-packaging
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md]
started: 2026-06-27
updated: 2026-06-27
---

## Current Test

[testing complete]

## Tests

### 1. Private :: Do Not Upload classifier removed from pyproject.toml
expected: Publish-blocking `Private :: Do Not Upload` classifier removed (LIC-02)
result: pass
source: automated
coverage_id: 04-01-D1

### 2. Honest first-public-release classifiers present
expected: `Development Status :: 4 - Beta`, `Intended Audience :: Science/Research`, `Topic :: Scientific/Engineering` present (LIC-03)
result: pass
source: automated
coverage_id: 04-01-D2

### 3. Public Documentation and Changelog URLs present
expected: `[project.urls]` carries public `github.com/gseg-ethz/geodispbench3d` Documentation/Changelog URLs (LIC-03)
result: pass
source: automated
coverage_id: 04-01-D3

### 4. README License states BSD-3-Clause (not Proprietary)
expected: README License section states BSD-3-Clause; "Proprietary" removed; PyPI long-description fixed via dynamic readme (LIC-01)
result: pass
source: automated
coverage_id: 04-01-D4

### 5. README notes [iof3d] extra currently unavailable (no timeline)
expected: README install section notes `[iof3d]` is unavailable until iof3D publishes, no timeline (LIC-01)
result: pass
source: automated
coverage_id: 04-01-D5

### 6. README drops stale combined-extras command and gated-by-[iof3d] text
expected: Stale `[iof3d,f2s3,dashboard]` command and "gated by [iof3d]" layout text removed (LIC-01)
result: pass
source: automated
coverage_id: 04-01-D6

### 7. CITATION.cff and LICENSE confirmed BSD-3-Clause
expected: CITATION.cff and LICENSE confirmed BSD-3-Clause (LIC-04)
result: pass
source: automated
coverage_id: 04-01-D7

### 8. Public import succeeds with iof3D/pc2img blocked; adapter use raises chained ImportError
expected: `import geodispbench3d_iof3d` succeeds with iof3D/pc2img blocked; `Iof3dCallableAdapter` access raises actionable, chained ImportError (PKG-01)
result: pass
source: automated
coverage_id: 04-02-D1

### 9. Non-gated parse_iof3d_output resolves under iof3D/pc2img block
expected: Parser path resolves (pchandler present) — not mis-mapped to a gated submodule (PKG-01)
result: pass
source: automated
coverage_id: 04-02-D2

### 10. iof3d-ax exits cleanly in-process when iof3D absent (no traceback)
expected: `iof3d-ax` (cli.main) exits cleanly with actionable message, no raw ImportError traceback (PKG-01)
result: pass
source: automated
coverage_id: 04-02-D3

### 11. Out-of-process iof3d-ax exits 1 with actionable stderr, no traceback
expected: `python -m geodispbench3d_iof3d.cli` under simulated absence exits 1, actionable stderr, no Traceback (PKG-01)
result: pass
source: automated
coverage_id: 04-02-D4

### 12. pyproject has no active iof3d extra; f2s3 pins pchandler ~= 2.1
expected: No active `iof3d` key; `f2s3 == ["pchandler ~= 2.1"]`; `geodispbench3d_iof3d` stays in setuptools packages (PKG-01, PKG-03)
result: pass
source: automated
coverage_id: 04-02-D5

### 13. Clean public install resolves pchandler 2.1.0 without private deps
expected: Throwaway venv `pip install '.[f2s3]'` resolves pchandler 2.1.0 from public PyPI and imports parse_f2s3_output; no iof3d extra / no private deps (PKG-02, PKG-03)
result: pass
source: automated
coverage_id: 04-02-D6

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
