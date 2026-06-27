---
status: complete
phase: 02-targeted-fixes
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md, 02-06-SUMMARY.md, 02-07-SUMMARY.md]
started: 2026-06-27T12:00:00Z
updated: 2026-06-27T12:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Runner trial-loop characterization net (02-01 D1)
expected: Trial loop happy path, adapter prepare/teardown lifecycle, get_best_trial passthrough, and the named create_experiment dispatch branch pinned against unmodified runner.py
result: pass
source: automated
coverage_id: 02-01-D1

### 2. _normalize_trial_data shapes (02-01 D2)
expected: (int,dict) tuple, attribute-object, and TypeError-on-unparseable shapes covered
result: pass
source: automated
coverage_id: 02-01-D2

### 3. Cross-case aggregation incl. NaN survivor mean (02-01 D3)
expected: Single-case short-circuit, multi-case finite mean, and partial-failure NaN-ignoring survivor mean (F-05/F-08 regression anchor)
result: pass
source: automated
coverage_id: 02-01-D3

### 4. Provenance stamping into summary.json (02-01 D4)
expected: A healthy run stamps tool/dataset/parser provenance blocks into ax_trial/summary.json
result: pass
source: automated
coverage_id: 02-01-D4

### 5. results/store.py failure paths (02-02 D1)
expected: create-new-parquet, append round-trip, empty-rows short-circuit directly tested (store.py 100% coverage)
result: pass
source: automated
coverage_id: 02-02-D1

### 6. sweep/evaluation.py failure paths (02-02 D2)
expected: parser-fail->None, metric-raise->skip, non-scalar->skip, needs-based kwarg assembly, _gt_kind_matches filtering tested (evaluation.py 100% coverage)
result: pass
source: automated
coverage_id: 02-02-D2

### 7. Runner/CLI typed to SuiteConfig (02-03 D1)
expected: run_with_suite/_evaluate_across_cases/_cmd_sweep/_cmd_rescore typed SuiteConfig; 0 attr-defined ignores in cli.py; no NEW pyright error above baseline (F-01)
result: pass
source: automated
coverage_id: 02-03-D1

### 8. Provenance lookup collapsed (02-03 D2)
expected: Provenance lookup collapsed to suite.tool.source_path; .raw/__source_path__ fallback removed; behavior preserved (F-13)
result: pass
source: automated
coverage_id: 02-03-D2

### 9. Objective-specific finite-case signal off Ax payload (02-03 D3)
expected: objective_cases_finite/total surfaced via log line + trial artifact + SweepRunSummary/CLI line, absent from complete_trial(raw_data), NaN-mean math unchanged (F-05)
result: pass
source: automated
coverage_id: 02-03-D3

### 10. SweepParameter.from_mapping single-sourcing (02-04 D1)
expected: from_mapping single-sources the 11-field coercion; all three duplicated inline blocks route through it; loader behavior identical
result: pass
source: automated
coverage_id: 02-04-D1

### 11. PassDiagnostics model + narrowed excepts (02-05 D1)
expected: PassDiagnostics typed model + non_fatal_failures on five output/summary types; 8 IO sites narrowed, 4 plugin boundaries documented-broad; debug logs -> warning (F-08)
result: pass
source: automated
coverage_id: 02-05-D1

### 12. Counter threaded through passes, fail-soft preserved (02-05 D2)
expected: Counter threaded through sweep/rescore/analyze; readers carry on_non_fatal; fail-soft control flow preserved (no site becomes fatal)
result: pass
source: automated
coverage_id: 02-05-D2

### 13. Aggregate "N non-fatal failures" CLI line (02-05 D3)
expected: Aggregate non-fatal-failures line emitted by each CLI summary (sweep/rescore/analyze), each asserted by a caplog test
result: pass
source: automated
coverage_id: 02-05-D3

### 14. Timezone-aware UTC timestamps (02-06 D1)
expected: All 5 datetime.utcnow() sites use datetime.now(UTC); isoformat sites drop manual "Z", emit offset-aware (+00:00), parse via fromisoformat (F-09)
result: pass
source: automated
coverage_id: 02-06-D1

### 15. In-loop imports hoisted, lazy gating intact (02-06 D2)
expected: runner.py in-loop internal/stdlib imports hoisted to module top without pulling Ax/iof3D/streamlit to module level (F-10)
result: pass
source: automated
coverage_id: 02-06-D2

### 16. Dead _ = asdict hack removed (02-06 D3)
expected: dead `_ = asdict` lint-suppression hack and asdict import removed from rescore.py; ruff clean (F-11)
result: pass
source: automated
coverage_id: 02-06-D3

### 17. Single shared parser_fn_repr, byte-identical key (02-07 D1)
expected: One shared parser_fn_repr in trial_record.py imported by runner+rescore; rendered module:qualname byte-identical across module-level/method/nested callables (F-03)
result: pass
source: automated
coverage_id: 02-07-D1

### 18. Four dead fields deleted, old records still load (02-07 D2)
expected: Four dead config/provenance fields deleted across all code sites; old summary.json with yaml_hash still deserializes; no TypeError (F-30)
result: pass
source: automated
coverage_id: 02-07-D2

### 19. ExecutionConfig.ensure_supported() guard, bypass-proof (02-07 D3)
expected: ensure_supported() raises deterministically on non-default parallel_trials/override_tool_mode, passes on defaults; invoked from both _cmd_sweep and run_with_suite (F-30)
result: pass
source: automated
coverage_id: 02-07-D3

### 20. FIX-04 green-gate, all suites load (02-07 D4)
expected: Inert YAML/schema keys stripped, every shipped suite loads, full baseline-diff gate green (ruff + ruff format + pyright_gate + pytest 77 passed, 0 skipped)
result: pass
source: automated
coverage_id: 02-07-D4

### 21. Pyright baseline-diff gate (02-02 D3)
expected: pyright_gate.py exits 0 with "PASS: no new pyright errors above baseline"; gate file is ruff-clean
result: pass
coverage_id: 02-02-D3

### 22. from_mapping typing clears values-list pyright errors (02-04 D2)
expected: from_mapping typing clears the values-list pyright errors at tool/loader.py and factory.py with no new errors (net -2: total 21 -> 19); verified via pyright_gate.py exit 0
result: pass
coverage_id: 02-04-D2

## Summary

total: 22
passed: 22
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
