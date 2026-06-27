---
phase: 02-targeted-fixes
plan: 07
subsystem: infra
tags: [dedup, dead-code, provenance, cache-key, forward-compat, guard, F-03, F-30, FIX-04, gate]

# Dependency graph
requires:
  - phase: 02-04
    provides: from_mapping dedup-helper home pattern (single-source a renderer/coercer) this plan mirrors for parser_fn_repr
  - phase: 02-06
    provides: persistence-file hygiene (runner/rescore/trial_record cleanups) this plan's deletions + guard sit alongside
  - phase: 02-02
    provides: pyright baseline-diff gate (pyright_gate.py) — the executable FIX-04 gate
  - phase: 02-01
    provides: F-20 characterization net (FakeAxClient + StubAdapter) covering runner.py
provides:
  - Single shared parser_fn_repr in sweep/trial_record.py (public, in __all__); runner.py + rescore.py both import it; byte-identical module:qualname key locked for module-level, method, and nested/local (<locals>) callables
  - Four dead config/provenance fields deleted across every code site (ToolConfig.outputs_options, CaseSpec.scan_by_epoch, DatasetSpec.gt_kinds_supported, ToolProvenance.yaml_hash); old summary.json records carrying yaml_hash still deserialize
  - ExecutionConfig.ensure_supported() — a shared deterministically-raising guard for the v2 EXEC-01 seam (parallel_trials / override_tool_mode), invoked from BOTH cli._cmd_sweep and run_with_suite (bypass-proof); fields retained
  - Inert gt_kinds_supported keys stripped from the two dataset YAMLs + the advisory dataset.schema.json
  - The FIX-04 green-gate closed — ruff + ruff format + pyright baseline-diff + full pytest (0 skipped) all green
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provenance/cache-key renderers are single-sourced next to the dataclass they serialize (parser_fn_repr beside ParserProvenance in sweep/trial_record.py); byte-identity is locked by a characterization test across __qualname__ shapes so the key cannot drift between sweep and rescore"
    - "Forward-compat config fields that the runtime cannot yet honor are guarded by a deterministically-raising ensure_supported() on the config dataclass, invoked from every entry path (CLI + programmatic) so the no-op cannot be reached silently (D-09); the fields are retained as the future seam, not deleted"
    - "Dead-field deletion is YAML-safe because loaders reconstruct via .get()-based extraction — unknown keys are ignored, so existing on-disk records keep loading"

key-files:
  created: []
  modified:
    - src/geodispbench3d/sweep/trial_record.py
    - src/geodispbench3d/sweep/runner.py
    - src/geodispbench3d/sweep/rescore.py
    - src/geodispbench3d/suite/loader.py
    - src/geodispbench3d/tool/loader.py
    - src/geodispbench3d/dataset/schema.py
    - src/geodispbench3d/cli.py
    - src/geodispbench3d/conf/schema/dataset.schema.json
    - benchmarks/datasets/mattertal.yaml
    - benchmarks/datasets/mattertal_f2s3.yaml
    - tests/core/test_runner.py
    - tests/core/test_rescore.py

key-decisions:
  - "Made the shared renderer public (parser_fn_repr, added to trial_record __all__) rather than importing a private _-prefixed symbol across modules; the rendering body is unchanged (module:qualname via __qualname__), preserving byte-identity"
  - "Retained hash_file as a public __all__ export even though from_yaml_path no longer calls it after the yaml_hash deletion; it is a general-purpose utility, vulture honors __all__, and removing it would be out-of-scope churn"
  - "Placed the execution guard call at the TOP of run_with_suite (before the MetricRegistry import) and at the top of _cmd_sweep — the two real entry paths to the sweep loop — so neither the CLI nor a programmatic runner caller can reach the silent no-op (codex HIGH)"
  - "The dataset.schema.json gt_kinds_supported strip was landed in Task 3 (grouped with the YAML hygiene as mandatory doc hygiene), not Task 2; the schema is a config/doc artifact, not a load-bearing code site, so Task 2's code-site deletions were already complete and TypeError-free"

requirements-completed: [FIX-01, FIX-02, FIX-03, FIX-04]

coverage:
  - id: D1
    description: "F-03 — one shared parser_fn_repr in sweep/trial_record.py; runner.py + rescore.py import it; both byte-identical local defs deleted; rendered module:qualname key is byte-identical to pre-consolidation for module-level, method, AND nested/local callables"
    requirement: "FIX-03"
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_parser_fn_repr_byte_identical_across_callable_shapes (module-level, method, nested <locals> closure)"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_parser_fn_repr_single_source_imported_by_runner_and_rescore (runner.parser_fn_repr is rescore.parser_fn_repr is trial_record.parser_fn_repr)"
        status: pass
      - kind: other
        ref: "grep -rn 'def _parser_fn_repr\\|def parser_fn_repr' src/geodispbench3d returns exactly one definition (trial_record.py)"
        status: pass
    human_judgment: false
  - id: D2
    description: "F-30 — the four genuinely-dead fields deleted across all code sites; an old summary.json carrying yaml_hash still deserializes; no TypeError on import/load"
    requirement: "FIX-02"
    verification:
      - kind: unit
        ref: "tests/core/test_rescore.py#test_old_record_with_yaml_hash_still_deserializes (read_provenance returns ToolProvenance; extra yaml_hash key ignored)"
        status: pass
      - kind: other
        ref: "grep -rn 'outputs_options|scan_by_epoch|gt_kinds_supported|yaml_hash' src/geodispbench3d returns nothing; vulture --min-confidence 60 no longer reports the four fields"
        status: pass
    human_judgment: false
  - id: D3
    description: "F-30 — shared ExecutionConfig.ensure_supported() raises deterministically on non-default parallel_trials/override_tool_mode and passes on defaults; invoked from both _cmd_sweep and run_with_suite (bypass-proof)"
    requirement: "FIX-02"
    verification:
      - kind: unit
        ref: "tests/core/test_runner.py#test_execution_config_ensure_supported_{passes_on_defaults,raises_on_parallel_trials,raises_on_override_tool_mode}"
        status: pass
      - kind: unit
        ref: "tests/core/test_runner.py#test_run_with_suite_invokes_guard_bypass_proof (run_with_suite raises NotImplementedError on parallel_trials=2)"
        status: pass
      - kind: other
        ref: "grep -rn 'ensure_supported' src/geodispbench3d/cli.py src/geodispbench3d/sweep/runner.py shows BOTH call sites"
        status: pass
    human_judgment: false
  - id: D4
    description: "FIX-04 — inert YAML/schema keys stripped, every shipped suite loads, and the full baseline-diff quality gate is green (0 skipped)"
    requirement: "FIX-04"
    verification:
      - kind: other
        ref: "grep -rn 'gt_kinds_supported' benchmarks/ src/geodispbench3d/conf/schema/ returns nothing"
        status: pass
      - kind: other
        ref: "python -c '[load_suite(p) for p in glob(benchmarks/suites/*.yaml)]' loads f2s3_voxel_refine.yaml + iof3d_mattertal.yaml OK"
        status: pass
      - kind: other
        ref: "ruff check . (All checks passed) + ruff format --check . (57 files formatted) + pyright_gate.py (PASS, exit 0) + python -m pytest (77 passed, 0 skipped)"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 07: F-03 Dedup + F-30 Dead-Code Removal & Forward-Compat Guard Summary

**Single-sourced the provenance/cache-key renderer (parser_fn_repr, byte-identity locked across __qualname__ shapes), deleted four genuinely-dead config/provenance fields across every code site (old yaml_hash records still load), and guarded the two v2 EXEC-01 execution fields with a shared deterministically-raising ensure_supported() invoked from both the CLI and the runner — closing the FIX-04 green-gate.**

## Performance

- **Duration:** ~18 min
- **Tasks:** 3 (each TDD RED -> GREEN)
- **Files modified:** 12 (8 source/config, 2 benchmark YAML, 2 test)
- **Base tag:** `wave4-pre-02-07`

## Accomplishments
- **F-03 (FIX-03):** moved the parser-callable renderer to `sweep/trial_record.py` as public `parser_fn_repr` (added to `__all__`), beside `ParserProvenance`. runner.py and rescore.py now import the one symbol; both byte-identical local `_parser_fn_repr` defs are gone. The rendering is unchanged (`f"{module}:{qualname}"`), and a new characterization test locks the exact string for a module-level function, a class method, and a nested/local `<locals>` closure — so the sweep/rescore cache key is structurally drift-proof.
- **F-30 dead fields (FIX-02):** deleted `ToolConfig.outputs_options` (decl + construction), `CaseSpec.scan_by_epoch` (method), `DatasetSpec.gt_kinds_supported` (decl + raw.get + construction), and `ToolProvenance.yaml_hash` (decl + `from_yaml_path` + the `_tool_from_record` deserializer — all three, the third being the audit-undersold site that would otherwise raise TypeError). A new compat test proves an on-disk summary still carrying `yaml_hash` deserializes (loaders use `.get()`-based extraction; unknown keys are ignored).
- **F-30 guard (FIX-02):** added `ExecutionConfig.ensure_supported()` that raises `NotImplementedError` on `parallel_trials != 1` or `override_tool_mode is not None` (D-09: cannot silently no-op), invoked from BOTH `cli._cmd_sweep` (after `load_suite`) and `run_with_suite` (top, before the metric registry) — so a programmatic runner caller cannot bypass the CLI guard. The fields are retained as the v2 EXEC-01 seam.
- **Doc hygiene (FIX-04):** stripped the now-inert `gt_kinds_supported` keys from `mattertal.yaml`, `mattertal_f2s3.yaml`, and the advisory `dataset.schema.json`. Every shipped `benchmarks/suites/*.yaml` still loads via `load_suite`.
- **FIX-04 gate:** ruff + ruff format + pyright baseline-diff (`pyright_gate.py`, exit 0) + full pytest (77 passed, 0 skipped) all green.

## Task Commits

Each task followed TDD (RED test commit -> GREEN impl commit):

1. **Task 1: F-03 consolidate parser_fn_repr** - `281be0c` (test, RED) -> `1af1abc` (refactor, GREEN)
2. **Task 2: F-30 delete four dead fields + compat test** - `c891481` (refactor; deletion + guard test, single commit — the compat test is a deletion guard with no natural RED)
3. **Task 3: F-30 shared guard + YAML/schema strip** - `68299be` (test, RED) -> `2fbf124` (feat, GREEN)

**Plan metadata:** _(final docs commit — SUMMARY + STATE + ROADMAP)_

## Files Created/Modified
- `src/geodispbench3d/sweep/trial_record.py` - added public `parser_fn_repr` (in `__all__`); deleted `ToolProvenance.yaml_hash` decl + `from_yaml_path` assignment + `_tool_from_record` deserializer site
- `src/geodispbench3d/sweep/runner.py` - import `parser_fn_repr` from trial_record; deleted local `_parser_fn_repr`; call `suite.execution.ensure_supported()` at top of `run_with_suite`
- `src/geodispbench3d/sweep/rescore.py` - import `parser_fn_repr` from trial_record; deleted local `_parser_fn_repr`
- `src/geodispbench3d/suite/loader.py` - added `ExecutionConfig.ensure_supported()` (deterministic raise; fields retained)
- `src/geodispbench3d/tool/loader.py` - deleted `ToolConfig.outputs_options` decl + construction
- `src/geodispbench3d/dataset/schema.py` - deleted `CaseSpec.scan_by_epoch` + `DatasetSpec.gt_kinds_supported` (decl + raw.get + construction)
- `src/geodispbench3d/cli.py` - call `suite.execution.ensure_supported()` in `_cmd_sweep`
- `src/geodispbench3d/conf/schema/dataset.schema.json` - removed advisory `gt_kinds_supported` entry
- `benchmarks/datasets/mattertal.yaml`, `benchmarks/datasets/mattertal_f2s3.yaml` - stripped inert `gt_kinds_supported` keys
- `tests/core/test_runner.py` - F-03 byte-identity + single-source nets; F-30 guard nets (defaults pass, non-default raise, run_with_suite bypass-proof)
- `tests/core/test_rescore.py` - old-record `yaml_hash` compatibility test

## Decisions Made
- Shared renderer made public (`parser_fn_repr` in `__all__`) instead of importing a private `_`-prefixed name across modules; body unchanged so byte-identity holds.
- `hash_file` kept as a public `__all__` export even though `from_yaml_path` no longer calls it post-deletion — general-purpose utility; vulture honors `__all__`; removal would be out-of-scope churn.
- Guard placed at both real sweep entry paths (`_cmd_sweep` + `run_with_suite` top) so the silent no-op is unreachable from any caller.
- The `dataset.schema.json` `gt_kinds_supported` strip landed in Task 3 (grouped doc hygiene) rather than Task 2; it is a doc/config artifact, not a load-bearing code site, so Task 2's deletions were complete and TypeError-free before it.

## Deviations from Plan

None — plan executed as written. All Rules 1-4 untriggered; no auto-fixes, no architectural decisions, no authentication gates. The only judgment call (schema-strip task placement, above) is documented as a decision, not a deviation; the final state matches the plan's intended artifacts exactly.

## Coverage Floor (D-05 evidence)

Measured via `coverage run -m pytest tests/core -p no:cov` (the `pytest --cov` path crashes on the torch/pytest-cov early-import conflict in this env, per 02-01):

| Module | Coverage | Floor | Status |
|--------|---------:|------:|:------:|
| sweep/runner.py | 74% | >=60% | pass |
| results/store.py | 100% | >=90% | pass |
| sweep/evaluation.py | 99% | >=95% | pass |
| suite/loader.py | 90% | (no regression) | pass |
| dataset/schema.py | 85% | (no regression) | pass |
| sweep/trial_record.py | 66% | (no regression) | pass |
| tool/loader.py | 58% | (no regression) | pass |
| sweep/rescore.py | 79% | (no regression) | pass |

Touched-module subset TOTAL 77% (well above the >=55% project floor).

## Wave-4 / Phase Gate
- `ruff check .` — All checks passed
- `ruff format --check .` — 57 files already formatted
- `python -m pytest` — 77 passed, 0 skipped (remaining warnings are pre-existing pydantic/timm deprecations)
- `python .planning/phases/02-targeted-fixes/pyright_gate.py` — `PASS: no new pyright errors above baseline` (exit 0)
- `vulture src/geodispbench3d --min-confidence 60` — none of the four deleted fields reported
- Every `benchmarks/suites/*.yaml` loads via `load_suite`

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 2 (targeted-fixes) is complete: all four FIX requirements (FIX-01..FIX-04) satisfied across the wave. The codebase is deduped, dead-code-free for the audited fields, and the forward-compat seam is guarded.
- No blockers. The FIX-04 green-gate is the phase's terminal quality bar and is green.

## Self-Check: PASSED

- All 12 modified files present on disk.
- All 5 task commits verified in git history: `281be0c`, `1af1abc`, `c891481`, `68299be`, `2fbf124`.

---
*Phase: 02-targeted-fixes*
*Completed: 2026-06-27*
