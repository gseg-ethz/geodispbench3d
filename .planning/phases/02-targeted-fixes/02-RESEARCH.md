# Phase 2: Targeted Fixes - Research

**Researched:** 2026-06-27
**Domain:** Python refactor / dead-code removal / test-net construction on a mature benchmark framework, gated by ruff + pyright + pytest in a mandated conda env.
**Confidence:** HIGH — every claim below was verified against HEAD by running the actual tools (pytest collect + run, coverage, ruff, pyright, grep) in `iof3d_cosicorr3d-dev312` per AGENTS.md.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The full 13-finding fix set (`F-01, F-02, F-03, F-05, F-08, F-09, F-10, F-11, F-13, F-20, F-21, F-22, F-30`) is ratified — no findings pulled out. F-05 included with its behavior change accepted.
- **D-02 (F-05):** Fix as the audit recommends — surface partial-case failures rather than letting the NaN-ignoring cross-case mean hide them. At minimum emit the finite-case count alongside the aggregated objective (penalize / threshold-refuse are acceptable stronger options at planner discretion). Objective-reporting change is in-scope hardening.
- **D-03 (F-08):** Apply the full audit approach to the ~10 broad `except Exception` sites (`runner.py:61,295,324,354`; `rescore.py:257,295,310`; `evaluation.py:89,177`; `predictions_cache.py:120`; `trial_record.py:89`): (1) narrow each catch to expected types; (2) promote `logger.debug`→`logger.warning`; (3) add a per-pass non-fatal-failure counter surfaced as an aggregate "N non-fatal failures" line in each CLI summary. Fail-soft control flow is preserved.
- **D-04 (order — tests first):** Characterization tests for `runner.py` (F-20) land BEFORE the `runner.py` refactors (F-01, F-05, F-08, F-13).
- **D-05 (bar):** "Done" judged primarily by whether the specific named behaviors are exercised (runner trial loop + partial-failure path; store create/append; evaluation failure paths), with a coverage floor as a secondary regression guard. Floor numbers at planner discretion, anchored to "no regression below current coverage + meaningful lift on `runner.py`, `store.py`, `evaluation.py`." Do not game a percentage with shallow tests.
- **D-06 (F-22 depth):** Direct tests where a module has real failure-path logic; accept indirect coverage for thin pass-through modules.
- **D-07 (commit grain):** Atomic ID-referencing commits where self-contained; grouped commits where trivially mechanical (e.g. F-09/F-10/F-11 hygiene cluster). Commits SHOULD reference the stable finding ID.
- **D-08 (green gate):** `ruff` + `pyright` + the full `pytest` suite must pass at EVERY wave boundary (not necessarily each commit). Intermediate commits within a wave may be transiently red. **See "Quality-Gate Baseline" below — pyright is NOT currently green at HEAD; this decision needs an operational definition.**
- **D-09 (F-30):** Guard (don't delete) `ExecutionConfig.parallel_trials` and `override_tool_mode` (tracked v2 EXEC-01) with an explicit "not implemented" guard. Delete the genuinely dead `ToolConfig.outputs_options`, `CaseSpec.scan_by_epoch`, `DatasetSpec.gt_kinds_supported`, `ToolProvenance.yaml_hash`. Rule: guard if it maps to a tracked v2 requirement, delete otherwise.
- **D-10 (F-13):** F-13 folds into F-01. Once `SuiteConfig`/`ToolConfig` are typed, replace the `getattr(...) or getattr(...raw...lambda...)` chain at `runner.py:238-241` with direct typed access `suite.tool.source_path`. Behavior-preserving.

### Claude's Discretion
- Mechanical findings F-09 (`datetime.utcnow()`→`datetime.now(UTC)`, 5 sites), F-10 (hoist in-loop internal imports to module top), F-11 (delete the `_ = asdict` hack) — exact form is planner/executor discretion, subject to D-08. **F-10 guardrail:** hoisting must NOT pull any optional/heavy dep (Ax, iof3D, streamlit) to module level — preserve lazy-import gating. (Verified: all F-10 imports are geodispbench3d-internal or stdlib — safe.)
- **F-01 scope:** at minimum retype the suite-consumer cluster (`_cmd_sweep`/`_cmd_rescore`/`run_with_suite`/`_evaluate_across_cases`) to `SuiteConfig` and delete the associated `# type: ignore[attr-defined]` markers; repo-wide `type: ignore` sweeping is executor judgment.

### Deferred Ideas (OUT OF SCOPE)
None surfaced in discussion. Findings the audit dispositioned `defer`/`accept`/`route-forward` (F-04, F-06, F-07, F-12, F-14, F-15, F-16, F-17, F-18, F-19, F-23, F-24, F-25, F-26, F-27, F-28, F-29, F-31, F-32) are excluded by D-01's scope statement.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIX-01 | Findings marked "fix" in the audit are resolved, each as an atomic, reviewed change | Per-finding anchor map below confirms all 13 anchors against HEAD (with drift notes); sequencing recommendation provides wave structure. |
| FIX-02 | Dead code and unused bloat identified in the audit is removed | F-09/F-10/F-11/F-30 anchors confirmed; F-30 deletion-safety proven (see Primary Answer 2) — all four field deletions are YAML-safe. |
| FIX-03 | Flagged duplication consolidated to a single source (SweepParameter construction; `_parser_fn_repr`) | F-02 three coercion sites confirmed byte-identical; F-03 two `_parser_fn_repr` copies confirmed; consolidation target `trial_record.py` validated. |
| FIX-04 | Full test suite (core/iof3d/f2s3) + ruff + pyright pass after the fixes land | Primary Answer 1 establishes the exact green-gate command set; Quality-Gate Baseline documents the current ruff=green / pytest=green / pyright=RED state that FIX-04 must reconcile. |
</phase_requirements>

## Summary

This is a fix phase against a green-on-tests, already-functional codebase. The risk is not "can we build it" but "can we change behaviour-dense code (`runner.py`, 13% coverage) without silent regression, and is the green-gate actually well-defined." Both primary research questions resolved with direct evidence:

1. **Env→suite matrix:** The full 32-test suite (core + iof3d + f2s3) runs in the SINGLE env `iof3d_cosicorr3d-dev312` with **0 skips** — `f2s3-dev312` has no pytest/geodispbench3d/pchandler and is NOT a test env (it is only where the F2S3 *binary* executes during a live subprocess sweep, which no Phase-2 test exercises). The objective's hypothesis that "the F2S3 suite needs `conda run -n f2s3-dev312`" is incorrect; AGENTS.md itself runs `tests/f2s3` in the dev env.
2. **F-30 deletion safety:** All four field deletions are **safe against in-repo YAML — no coordinated YAML edit is required.** Every loader uses `OmegaConf.to_container` → explicit `.get()` extraction → dataclass construction with only known keys; unknown YAML keys are silently ignored (tolerant, NOT strict structured-config). The `conf/schema/*.json` files are advisory (no `jsonschema.validate` runs at load). The required edits are all in loader *code* (same-file, same-commit).

The one genuinely unexpected finding: **pyright is RED at HEAD (21 errors, 9 warnings)**, several of them rooted in DEFERRED findings (F-14 Ax shims in `runner.py:395/401`; F-12/F-15 iof3D coupling; the Streamlit dashboard). D-08's "pyright passes at every wave boundary" therefore cannot mean "0 errors" without doing deferred work — it must be operationalized as a no-regression baseline. This needs user confirmation (Assumption A1).

**Primary recommendation:** Run F-20 characterization tests first (Wave 0), establish the CI-faithful pyright baseline as Wave-0 work, then land the `runner.py` cluster (F-01→F-13→F-05→F-08) against the green net, then the mechanical hygiene cluster (F-09/F-10/F-11/F-30), with `conda run -n iof3d_cosicorr3d-dev312 pytest` (all 32, 0 skipped) + ruff + pyright-no-regression as the wave gate.

## Project Constraints (from CLAUDE.md / AGENTS.md)

- **Mandated env:** ALL `python`/`pip`/`pytest`/`ruff`/`pyright` go through `conda run -n iof3d_cosicorr3d-dev312 ...`. Bare `python`/`pip`/`pytest` forbidden; never use `base`.
- **No source edits outside GSD workflow** (this research is read-only).
- **Lazy optional-import gating is invariant:** `geodispbench3d.*` core must never import `iof3D`/`pchandler`/`pc2img`/`streamlit`/Ax at module level. F-10 hoisting must respect this (verified safe — see F-10 anchor).
- **NumPy-2 pin** preserved; transitive tool stacks must stay NumPy-2 compatible (not touched by this phase).
- **Modern typing** (`str | None`, `list[str]`, `collections.abc` imports, `@dataclass(frozen=True)`, keyword-only public APIs, `__all__` in every module). New test/helper code must match.
- **Fail-soft convention:** "never let observability/caching/provenance failures break the primary path" — F-08/D-03 keeps this control flow, only narrowing types + raising visibility.
- **Line length 100, ruff select `[E,F,B,I,UP,W]`, `E501` ignored (formatter owns wrapping), pyright basic mode, `pythonVersion=3.11`, strict list/dict/set inference on.**

---

## PRIMARY ANSWER 1 — Env → Suite Execution Matrix

**Verified by running `pytest --collect-only` and import probes in both envs.** [VERIFIED: conda + pytest collection, this session]

### What exists and what each env can run

| Env | pytest? | geodispbench3d? | pchandler? | iof3D? | Collects which suites | Role |
|-----|---------|-----------------|------------|--------|-----------------------|------|
| `iof3d_cosicorr3d-dev312` | ✓ | ✓ (editable) | ✓ | ✓ | **all 32 tests** (core 28, iof3d 2, f2s3 2), **0 skipped** | THE dev + test + lint env |
| `f2s3-dev312` | ✗ (`No module named pytest`) | ✗ | ✗ | ✗ | none (cannot run pytest at all) | Only the env the **F2S3 binary** runs in (`conda run -n f2s3-dev312 f2s3`, `f2s3.yaml:13`) |

**Collection result in `iof3d_cosicorr3d-dev312`:** `32 tests collected in 10.22s`, full run `32 passed, 35 warnings in 20.07s`. `tests/iof3d` (needs `iof3D`+`pchandler`) and `tests/f2s3` (needs `pchandler`) both *run* here because those packages are present.

**Why `tests/f2s3` does NOT need `f2s3-dev312`:** `tests/f2s3/conftest.py` does `pytest.importorskip("pchandler")` — the F2S3 *parser* uses `pchandler.data_io.Csv` / `pchandler.filters.SphereFilter`; it does NOT invoke the F2S3 binary. `pchandler` lives in `iof3d_cosicorr3d-dev312`, not in `f2s3-dev312`. The `f2s3-dev312` env matters only for *live end-to-end F2S3 subprocess sweeps* (F-16), which are **deferred to Phase 3 and exercised by no Phase-2 test**.

### Operational "wave green" command set (D-08)

A single env covers the entire gate. No second env is needed for the test gate:

```bash
conda run -n iof3d_cosicorr3d-dev312 ruff check .
conda run -n iof3d_cosicorr3d-dev312 ruff format --check .
conda run -n iof3d_cosicorr3d-dev312 pyright            # see pyright caveat in Quality-Gate Baseline
conda run -n iof3d_cosicorr3d-dev312 pytest             # 32 tests, 0 skipped, + Phase-2 new tests
```

For the tight per-task loop, scope pytest to the touched module(s), e.g. `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_runner.py -x` (<10s).

### Important caveat — CI vs. local env divergence

CI's lint job (`.github/workflows/ci.yml`) pins `ruff==0.8.4 pyright==1.1.392` and installs `.[dev]` **only (no `iof3d`/`f2s3`/`dashboard` extras)**. The local conda env has `ruff 0.15.12` + `pyright 1.1.403` + the full iof3D stack. This divergence is the root of the pyright-baseline finding below: the local env surfaces *more* pyright errors (extras installed) than CI's lint job would. The CI `test` matrix runs `pytest tests/<name>` per extra; the `iof3d` job is `enabled: false`. So in CI the framework-only suite is the authoritative green-gate; locally the dev env runs all three because the extras happen to be installed. [VERIFIED: ci.yml + .pre-commit-config.yaml read this session]

---

## PRIMARY ANSWER 2 — F-30 Field-Deletion Safety vs. OmegaConf Parsing

**Verified by reading every loader's parse path + grepping all in-repo YAML for the four keys.** [VERIFIED: source read + grep, this session]

### The structured-config strictness question — answered

Every loader follows the same pattern: `raw = OmegaConf.to_container(OmegaConf.load(path), resolve=True)` → a plain `dict` → **explicit field-by-field `raw.get("key")` extraction** → dataclass construction with ONLY the known keys. There is **no** `DatasetSpec(**raw)` splat and **no** structured/strict OmegaConf merge. Therefore:

- **Unknown keys in YAML are silently ignored** (tolerant parsing). A YAML file may declare a key the dataclass no longer has, and parsing succeeds unchanged.
- The JSON schemas in `src/geodispbench3d/conf/schema/*.json` are **advisory package data — NOT enforced at load time** (no `import jsonschema`, no `.validate()` call anywhere in the loaders; grep returned only `_validate_objective`, an unrelated objective-name check). They have no `additionalProperties: false`. Deleting a dataclass field does not trigger any schema rejection.

**Conclusion: all four deletions are safe as-is. No coordinated YAML edit is REQUIRED.** The coordinated edits are all in loader *code* (same file, same commit).

### Per-field disposition table

| Field (D-09 says) | Declared in in-repo YAML? | Read-back consumer? | Loader-CODE edits required (same commit) | YAML edit required? |
|---|---|---|---|---|
| `ToolConfig.outputs_options` — **delete** | No (the `outputs:` YAML key is read *directly* by `_build_cli_adapter`, NOT via this field) | None | `tool/loader.py:44` (decl) + `:80` (construction) | No |
| `CaseSpec.scan_by_epoch` — **delete** | N/A (it's a *method*, not a parsed field) | None (no caller in src) | `dataset/schema.py:53-57` (remove method) | No |
| `DatasetSpec.gt_kinds_supported` — **delete** | **YES** — `benchmarks/datasets/mattertal.yaml:18`, `benchmarks/datasets/mattertal_f2s3.yaml:14` (+ advisory `conf/schema/dataset.schema.json:43`) | None (field parsed, never read) | `dataset/schema.py:67` (decl) + `:102` (`raw.get`) + `:109` (construction) | No — keys become inert; loader ignores them. **Optional hygiene:** strip the two YAML keys + schema entry for doc consistency. |
| `ToolProvenance.yaml_hash` — **delete** | No (written to `summary.json` provenance, not parsed from suite YAML) | **Round-tripped only** — reconstructed at `trial_record.py:241` (`_tool_from_record`), never consumed downstream | `trial_record.py:40` (decl) + `:47` (`from_yaml_path`) + **`:241` (`_tool_from_record` deserializer)** | No — old `summary.json` files carrying `yaml_hash` still load fine (extra dict keys ignored by `.get()`-based reconstruction). |
| `ExecutionConfig.parallel_trials` — **GUARD** | YES — `benchmarks/suites/iof3d_mattertal.yaml:19`, `f2s3_voxel_refine.yaml:23` | Never read by the runner (loop is sequential) | Field STAYS; add guard (see below) | No (field stays, YAML stays valid) |
| `ExecutionConfig.override_tool_mode` — **GUARD** | YES — same two suite YAMLs (`:20`, `:24`, both `null`) | Never read by the runner | Field STAYS; add guard | No |

### Gotcha the audit undersold

The audit cited `yaml_hash` only at `trial_record.py:40`. There is a **third site** — the `_tool_from_record` deserializer at `trial_record.py:241` reconstructs `ToolProvenance(..., yaml_hash=block.get("yaml_hash"))`. Deleting the field without removing line 241 raises `TypeError: unexpected keyword argument 'yaml_hash'`. The deletion is a **3-site same-file edit**, not one line. The value is never used after reconstruction, so dropping it is behaviour-safe.

### F-30 GUARD placement (parallel_trials / override_tool_mode)

Nothing currently reads `suite.execution` anywhere in src (grep confirms only the loader constructs it). The "not implemented" guard is **net-new code**. Natural home: `cli.py:_cmd_sweep` (or `run_with_suite`) right after `load_suite`, e.g. raise/warn when `suite.execution.parallel_trials != 1` or `suite.execution.override_tool_mode is not None`. Since both shipped suite YAMLs already set `parallel_trials: 1` / `override_tool_mode: null`, a `!= default → raise` guard leaves the in-repo suites valid while preventing silent no-op. `_coerce_tool_mode` (`suite/loader.py:129`) already validates the *value*; the guard adds "declared-but-unsupported" enforcement.

---

## Architectural Responsibility Map

This phase touches only the tool-agnostic core (`geodispbench3d`), never a tool tier.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Suite/tool/dataset config typing (F-01, F-13) | Config/Loader layer | CLI dispatch | `SuiteConfig` is already a frozen dataclass; retype is consumer-side only |
| Sweep orchestration + objective aggregation (F-05, F-08, F-10, F-20) | Orchestration layer (`sweep/runner.py`) | — | Single convergence point; all behavioral refactors land here |
| Parameter coercion dedup (F-02) | Config/Loader layer (`sweep/parameters.py`) | iof3D plugin (call site only) | `SweepParameter` already imported by iof3d factory; no new edge |
| Provenance helper dedup (F-03) | Persistence layer (`sweep/trial_record.py`) | — | STRUCTURE.md nominates `trial_record.py` as the shared-helper home |
| Persistence failure-path tests (F-21/F-22) | Persistence + Eval-glue layer | — | `store.py`, `evaluation.py` |
| Timestamp hygiene (F-09) | Cross-cutting (5 modules) | — | Mechanical, no tier ownership change |

---

## Per-Finding Anchor Map (verified against HEAD)

All anchors re-confirmed this session. Drift from the audit's line numbers is noted explicitly.

### Runner.py convergence cluster (F-01, F-13, F-05, F-08) — `sweep/runner.py`

- **F-01 (typed SuiteConfig):** `run_with_suite(suite: Any)` now at **line 176** (audit said 173, +3 drift), `_evaluate_across_cases(suite: Any)` now at **line 227** (audit said 223, +4 drift). Retype both to `SuiteConfig` (import from `geodispbench3d.suite.loader`). Delete the **15** `# type: ignore[attr-defined]` markers in `cli.py` (`:132,135,137,138,139,145,146,147,149,153,156,157` in `_cmd_sweep`; `:192,193,194` in `_cmd_rescore`) — audit estimated 12, actual 15. **Note:** the 3 `# type: ignore` at `runner.py:18,21,23` are for the optional Ax import — they STAY (not attr-defined). `load_suite` already returns concrete `SuiteConfig` (`suite/loader.py:46-57`), so this is a retype-and-delete-ignores job, no schema change.
- **F-13 (folds into F-01):** the chain at **`runner.py:238-241`** is `getattr(suite.tool, "source_path", None) or getattr(suite.tool.raw, "get", lambda *_: None)("__source_path__")`. `ToolConfig.source_path: Path | None` exists (`tool/loader.py:48`) and is **always populated** (`tool/loader.py:84`), so the `or getattr(...raw...lambda...)` tail is dead. Replace the whole expression with `suite.tool.source_path`. Behavior-preserving. (`suite.tool.raw` IS a real attr — `ToolConfig.raw`, `tool/loader.py:47` — but `source_path` never being `None` means the fallback never fires.) `.raw` is used nowhere else in `sweep/` or `cli.py`.
- **F-05 (partial-failure surfacing):** the NaN-ignoring cross-case mean is at **`runner.py:334-346`** (exact match to audit). `per_case_scalars` accumulates one dict per case (`:247,274`); single-case short-circuits at `:334-335`; multi-case mean over `finite = [v for v in values if ... not isnan]` at `:341-346`. The aggregated dict `out` flows to `complete_trial(raw_data=aggregated)` at `:214`. **Surface point for the finite-case count:** alongside `out[key]`, track `len(finite)` vs `len(cases)` and emit it (e.g. an extra scalar like `cases_finite`/`cases_total`, or a logged + counted signal). D-02 minimum = emit finite-case count; penalize/threshold are optional escalations.
- **F-08 (broad-except sites in runner):** confirmed at **`:61`** (`mkdir` trial-log dir), **`:295`** (provenance stamp), **`:324`** (prediction-cache write), **`:354`** (run-hash append) — all exact matches. NOTE the two `except Exception` at `:159` and `:215` are the *legitimate* trial-failure handlers that call `log_trial_failure` (report to Ax and continue the sweep) — they are NOT in the F-08 list and should be left as-is (or only get the counter, planner judgment).
- **F-10 (hoist in-loop imports):** confirmed at **`:232-236`** (`from ...trial_record import DatasetProvenance, ParserProvenance, ToolProvenance`), **`:280-282`** (`from dataclasses import asdict` + `from ...trial_record import update_trial_record`), **`:308`** (`from ...predictions_cache import write_prediction`), **`:339`** (`import math`). **All are geodispbench3d-internal or stdlib — verified none touch Ax/iof3D/streamlit. Safe to hoist** without breaking lazy-import gating.

### F-08 exception-type guidance (per site)

Two classes of site. **IO/serialization sites narrow cleanly; arbitrary-user-callable boundaries cannot.** This nuance matters for D-03's "narrow each catch."

| Site | What it wraps | Recommended narrow type(s) |
|------|---------------|----------------------------|
| `runner.py:61` | `Path.mkdir(parents, exist_ok)` | `OSError` |
| `runner.py:295` | `asdict(...)` + `update_trial_record` (json load/dump + `Path.replace`) | `(OSError, TypeError)` |
| `runner.py:324` | `write_prediction` (mkdir + `json.dump(default=str)` + replace) | `(OSError, TypeError)` |
| `runner.py:354` | file append | `OSError` |
| `rescore.py:~257` | `evaluate_trial(...)` — **arbitrary parser/metric plugin code** | **Cannot narrow** to a closed set; keep broad, apply warning+counter. `evaluate_trial` already catches inner parser/metric failures, so this outer catch is belt-and-suspenders. FLAG. |
| `rescore.py:~295` | `write_prediction` cache write | `(OSError, TypeError)` |
| `rescore.py:~310` | `append_rescore_entry` (json + file) | `(OSError, json.JSONDecodeError)` |
| `evaluation.py:89` | `output_parser(...)` — **arbitrary plugin callable** | **Cannot narrow**; this IS the parser-failure→`None` path. Keep broad, warning+counter. FLAG. |
| `evaluation.py:177` | metric `fn(**kwargs)` — **arbitrary plugin callable** | **Cannot narrow**; metric-raises→skip path. Keep broad, warning+counter. FLAG. |
| `predictions_cache.py:120` | `json.load` in `read_prediction` | `(OSError, json.JSONDecodeError)` (`JSONDecodeError` ⊂ `ValueError`) |
| `trial_record.py:89` | `json.load` in `load_trial_record` | `(OSError, json.JSONDecodeError)` |

**Recommendation for the planner:** for the 3 arbitrary-callable boundaries (`evaluation.py:89`, `evaluation.py:177`, `rescore.py:~257`), document that narrowing to a closed exception set is *inapplicable* (the callee is user/plugin code) and satisfy D-03 via parts 2 (warning) + 3 (counter) only. Narrowing the other 8 sites to `(OSError, json.JSONDecodeError, TypeError)` is clean.

**"N non-fatal failures" plumbing (D-03 part 3):** the CLI summary lines are emitted in `cli.py` (`_cmd_sweep` returns after the sweep; `_cmd_rescore`/`_cmd_analyze` already print succeeded/total). The rescore/analyze passes already carry summary counters (`rescore.py` `RescoreSummary` with `parser_misses`/`skipped_*`; `analysis/runner.py`). The new non-fatal counter should ride the same summary objects and print one aggregate line. For the sweep path the counter must be threaded out of `_evaluate_across_cases`/`run_with_suite` (currently returns only the best trial) — net-new plumbing the planner must design.

### F-02 — SweepParameter coercion dedup (`from_mapping` classmethod)

Three **byte-identical** 11-field constructions confirmed:
- `sweep/parameters.py:57-72` (`load_sweep_config`)
- `tool/loader.py:194-209` (`_load_hyperparameters`) — audit said `:192`
- `geodispbench3d_iof3d/factory.py:138-150` (`_coerce_hparam`) — audit said `:137`

Fields: `name, kind(=type), value_type, values, lower, upper, log_scale, step, activates_on, is_ordered, sort_values`. Add `SweepParameter.from_mapping(entry: Mapping[str, Any]) -> SweepParameter` in `parameters.py` and call from all three. The iof3d factory already imports `SweepParameter` (`factory.py:21`) — no new dependency edge. **Synergy:** the `list(entry.get("values")) if entry.get("values") is not None else None` line currently produces two of the pyright errors below (`tool/loader.py:200`, `factory.py:142`); a well-typed `from_mapping` can eliminate them (walrus + explicit narrowing).

### F-03 — `_parser_fn_repr` dedup

Two byte-identical defs: `runner.py:363-372` and `rescore.py:395-402`. Call sites: `runner.py:243`, `rescore.py:289`. The string is a **provenance/cache key** (lands in `ParserProvenance.fn` and the predictions-cache path), so the two must stay identical — consolidation guarantees it. Promote one `parser_fn_repr` into `sweep/trial_record.py` (alongside `ParserProvenance`, per STRUCTURE.md) and import in both. Verify the produced string is byte-identical pre/post move (a characterization assertion in `test_runner.py`/`test_rescore.py`).

### F-09 — `datetime.utcnow()` (5 call sites)

- `trial_record.py:272` (`_utcnow`, also called at `:133,168,200`)
- `rescore.py:304` (inline `rescored_at`)
- `rescore.py:406` (`_utcnow_compact`)
- `analysis/runner.py:173` (`_utcnow_compact`)
- `predictions_cache.py:97` (inline `cached_at`)

Replace with `datetime.now(UTC)` (`from datetime import UTC` — 3.11+, available). **Pitfall:** the two `.isoformat(...) + "Z"` sites (`trial_record.py:272`, `rescore.py:304`, `predictions_cache.py:97`) currently emit `...T12:00:00Z`; `datetime.now(UTC).isoformat()` emits `...T12:00:00+00:00`. Drop the hand-appended `"Z"` and check no test/consumer asserts a literal `Z` suffix (verified: `test_rescore.py` uses fixed literal timestamps in fixtures, not generated ones, so safe — but the planner should grep tests for `endswith("Z")`/`"Z"` before landing). The `.strftime("...-%Y%m%dT%H%M%S")` sites (`_utcnow_compact` in rescore/analysis) are ID-format strings — just swap `utcnow()`→`now(UTC)`, strftime output unchanged.

### F-11 — `_ = asdict` hack

`rescore.py:27` (`from dataclasses import asdict, dataclass`) + `:409-410` (`_ = asdict`). Delete the `asdict` import and the `_ = asdict` line. Confirm `dataclass` is still used in `rescore.py` (it is — keep it); only `asdict` is dead there.

---

## Quality-Gate Baseline (the unexpected finding — affects D-08)

Captured this session in `iof3d_cosicorr3d-dev312`. [VERIFIED: ruff/pyright/pytest run this session]

| Gate | Tool (local) | Tool (CI-pinned) | Result at HEAD |
|------|--------------|-------------------|----------------|
| `ruff check .` | ruff 0.15.12 | ruff 0.8.4 | **GREEN** — "All checks passed!" |
| `pytest` (all 32) | pytest 8.4 | pytest 8.4 | **GREEN** — 32 passed, 0 failed, **0 skipped**, 35 warnings (the F-09 `utcnow` DeprecationWarnings + a Pydantic-v2 transitive warning) |
| `pyright` | **1.1.403** + full extras | **1.1.392** + `.[dev]` only | **RED — 21 errors, 9 warnings** |

### pyright errors by file (local, 1.1.403 + extras)

| File | Errors | Phase-2 relevant? |
|------|--------|-------------------|
| `dashboard/app.py` | 5 | No — Streamlit/pandas typing; dashboard is route-forward, and CI's lint job omits the dashboard extra (imports unresolve→warnings, errors mostly vanish) |
| `geodispbench3d_iof3d/adapter.py` | 4 | No — iof3D private-dataclass `Literal[...]` coupling = **F-12/F-15 (DEFERRED)**; CI lint job has no iof3d extra |
| `sweep/runner.py` | 4 | **No** — lines `395,401` (`_normalize_trial_data` duck-typing `int`/`Mapping` attribute access) = **F-14 Ax shims (DEFERRED)** — will REMAIN after Phase 2 |
| `tool/loader.py` | 3 | Partially — `:65,:83` OmegaConf `Dict` typing; `:200` the `list(... .get("values"))` pattern (F-02 can fix `:200`) |
| `geodispbench3d_iof3d/factory.py` | 2 | `:142` is the F-02 pattern (F-02 can fix); `:74` is iof3D-private-fn coupling (deferred) |
| `geodispbench3d_iof3d/cli.py` | 1 | No — legacy `iof3d-ax`, route-forward Phase 4 |
| `tests/core/test_loaders.py` | 1 | `Optional` arg — pre-existing test typing |
| `tests/core/test_rescore.py` | 1 | `Optional` arg — pre-existing test typing |

### The D-08 problem (needs a decision — Assumption A1)

**"pyright passes (0 errors)" is unsatisfiable in Phase 2 without doing deferred work.** At minimum `runner.py:395/401` (F-14), the iof3D adapter (F-12/F-15), and the dashboard are all DEFERRED/route-forward, yet contribute errors. The realistic operationalization of D-08:

1. **Establish a CI-faithful baseline as Wave-0 work:** in the dev env, `pip install pyright==1.1.392` (matching CI) and run `pyright` with `.[dev]`-only resolution — OR accept the local `1.1.403`+extras superset of 21. Record the exact count as the floor.
2. **Define the gate as "no NEW pyright errors above that baseline,"** with the additional requirement that the files Phase 2 *touches* (`cli.py`, `sweep/runner.py` non-shim regions, `sweep/parameters.py`, `tool/loader.py`, `sweep/trial_record.py`, `sweep/rescore.py`, `sweep/evaluation.py`, `results/store.py`, `dataset/schema.py`) reach **0 errors** for the lines Phase 2 owns.
3. **Expect F-01/F-13/F-02 to net-REDUCE the count:** the `cli.py` accesses are currently masked by `# type: ignore[attr-defined]` (so 0 visible errors there today, but the ignores hide nothing wrong after retype); F-02's typed `from_mapping` can clear `tool/loader.py:200` + `factory.py:142`.

**Removing `# type: ignore[attr-defined]` (F-01) caveat:** pyright basic mode does NOT enable `reportUnnecessaryTypeIgnoreComment`, so leftover unnecessary ignores won't error — but if any *removed* ignore exposes a genuine residual error (e.g. an access SuiteConfig doesn't actually type-check), that error becomes visible. The executor MUST re-run pyright after each ignore removal to confirm the access type-checks cleanly. Net should be 0 new errors when the retype is correct.

**ruff version caveat:** local ruff 0.15.12 passes; CI pins 0.8.4. The config (`[E,F,B,I,UP,W]`, `E501` ignored) is conservative; 0.8.4 is expected to also pass, but the wave gate should ideally run the pinned version or at least `ruff format --check .` (CI runs both `ruff check .` and `ruff format --check .`).

---

## Validation Architecture

> `workflow.nyquist_validation: true` — section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4 (+ coverage 7.x), `dev` extra |
| Config file | **none** — no `[tool.pytest.ini_options]` or `[tool.coverage]` in `pyproject.toml`; discovery defaults under `tests/`; `tests/conftest.py` is a docstring only (no shared fixtures); per-extra `conftest.py` do `importorskip` |
| Quick run command | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_<module>.py -x` |
| Full suite command | `conda run -n iof3d_cosicorr3d-dev312 pytest` (32 + new, 0 skipped) |

**Established test pattern to mirror** (`tests/core/test_rescore.py`): build a minimal suite via inline-YAML strings in `tmp_path`, stub a parser package on `sys.path`, fabricate synthetic run dirs with `write_trial_record(trial_record_path(run_dir), {...})`. F-20 characterization reuses this plus a **fake `AxClient`** (a stub exposing `create_experiment`, `get_next_trial`→`(index, params)`, `complete_trial`, `log_trial_failure`, `get_best_trial`) and a **stub `ToolAdapter`** (returns a canned `TrialResult`).

### Phase Requirements → Test Map
| Req | Behavior | Test type | Automated command | File status |
|-----|----------|-----------|-------------------|-------------|
| FIX-01 | Each F-NN resolved, suite stays green | regression | `conda run -n iof3d_cosicorr3d-dev312 pytest` | existing 32 |
| FIX-02 | Dead code gone, no behavior change | regression + vulture | `pytest` + `vulture src/ --min-confidence 60` | existing |
| FIX-03 | `from_mapping` + `parser_fn_repr` single-source, byte-identical key | unit | `pytest tests/core/test_runner.py tests/core/test_rescore.py -k repr_or_from_mapping` | ❌ Wave 0 |
| FIX-04 | Full suite + ruff + pyright green-gate | gate | the 4-command set above | n/a |
| F-20 | Runner trial loop + cross-case aggregation + partial-failure path | characterization→regression | `pytest tests/core/test_runner.py -x` | ❌ Wave 0 |
| F-21 | Store create / append / empty-rows | unit | `pytest tests/core/test_store.py -x` | ❌ Wave 0 |
| F-22 | evaluation.py parser-fail→None, metric-raise→skip, non-scalar coercion | unit | `pytest tests/core/test_evaluation.py -x` | ❌ Wave 0 |

### Wave 0 Gaps (must land BEFORE the runner refactors — D-04)
- [ ] `tests/core/test_runner.py` — **F-20 characterization** (the safety net). Pin, with a fake AxClient + stub adapter:
  - trial loop happy path: `get_next_trial`→executor→`complete_trial` for N trials; `get_best_trial` returned.
  - `_evaluate_across_cases` single-case → returns that case's scalar dict (`:334-335`).
  - `_evaluate_across_cases` multi-case, all finite → mean aggregation (`:341-346`).
  - `_evaluate_across_cases` multi-case **partial failure** (one case yields NaN) → **pin CURRENT behavior** (NaN-ignoring mean over survivors). This test is the F-05 regression anchor; after F-05 lands, extend it to assert the new finite-case-count signal.
  - `_normalize_trial_data` shape coverage: `(int, dict)` tuple; object with `.trial_index`/`.parameters`; the `TypeError` raise on unparseable input (covers F-14-area lines so the refactor net stays green).
  - provenance stamping writes `summary.json` blocks (exercises F-08 site `:295`) on a healthy run.
  - **F-08 counter**: inject an unwritable `predictions_root` → cache write fails → assert the non-fatal counter increments and the surfaced summary line reflects it (pins the NEW F-08 behavior).
- [ ] `tests/core/test_store.py` — **F-21**: create-new-parquet, append-to-existing (round-trip rows), empty-rows short-circuit (`store.py:24-25` returns without writing), schema/columns preserved. (store.py 27 stmts — easily ≥90%.)
- [ ] `tests/core/test_evaluation.py` — **F-22 direct failure paths**: parser raises → `prediction=None`, evaluation still returns trial scalars (`evaluation.py:89-93`); metric raises → that metric skipped, others survive (`:177-179`); metric returns non-float → warning + skip (`:118-122`); `needs`-based kwarg assembly; gt-kind filtering (`_gt_kind_matches`).
- [ ] (Optional, D-06) smoke coverage for thin indirectly-covered modules (`analysis/runner.py`, `tool/callable_adapter.py`, `metrics/registry.py`) — accept indirect; add only where a real failure path exists.
- [ ] No framework install needed (pytest present). Optional: add `[tool.coverage.run] source = ["geodispbench3d"]` to `pyproject.toml` so `--cov` targeting is repeatable.

### Sampling Rate
- **Per task commit:** quick targeted module test (`pytest tests/core/test_<module>.py -x`, <10s).
- **Per wave merge:** full gate — `ruff check .` + `ruff format --check .` + `pyright` (no-regression vs baseline) + `pytest` (all green, 0 skipped).
- **Phase gate:** full suite green + ruff green + pyright ≤ baseline before `/gsd-verify-work`.

### Coverage targets (D-05 floor + lift — anchored to real numbers measured this session)
Current (fresh run, matches EVIDENCE.md): `runner.py` **13%**, `store.py` **44%**, `evaluation.py` **80%**, `trial_record.py` 57%, `predictions_cache.py` 85%, TOTAL **55%**.
- `runner.py` 13% → **≥60%** (trial loop + `_evaluate_across_cases` + `_normalize_trial_data` + provenance are the bulk; the `_create_experiment` Ax-shim span `77-136` is F-14/deferred and may stay uncovered, capping realistic ceiling ~70%). Behavior-anchored: trial loop + partial-failure path + normalize must all be exercised.
- `store.py` 44% → **≥90%** (27 stmts; create/append/empty trivially coverable).
- `evaluation.py` 80% → **≥95%** (only the 3 failure paths remain).
- **Floor (regression guard):** TOTAL must not drop below 55%; no touched module below its current %.

---

## Security Domain

> `security_enforcement: true`, ASVS level 1. This is an internal refactor with no new external/untrusted input surface.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (local CLI/library) |
| V3 Session Management | no | None |
| V4 Access Control | no | None |
| V5 Input Validation | yes (indirectly) | F-05 (finite-case count) + F-08 (narrowed excepts + warning/counter) make silent degradation of trusted-config inputs *visible*; `_coerce_tool_mode`/`_validate_objective` already validate config values |
| V6 Cryptography | no | `hash_file` uses sha256 for provenance integrity only (not security); unchanged |

### Known Threat Patterns for {Python config-driven benchmark, trusted-local YAML}
| Pattern | STRIDE | Standard Mitigation | Phase-2 status |
|---------|--------|---------------------|----------------|
| Arbitrary code execution from YAML dotted-path callables (F-24) | Elevation | By-design plugin behavior for trusted-local configs; documented accepted risk | **OUT OF SCOPE** (accept, documented) |
| Subprocess from YAML `entry` (F-25) | Tampering | `shell=False` + `shlex.split` + per-element argv — positive control | **OUT OF SCOPE** (accept; already safe) |
| Path traversal in predictions cache | Tampering | `_safe_segment` (`predictions_cache.py:155-163`) sanitizes segments — verified effective | unchanged; F-08 narrowing must not weaken the corrupt-cache→miss fallback |

**No new security-relevant surface is introduced.** F-08's purpose is observability (countable silent degradation), not a security boundary change — keep fail-soft control flow.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UTC timestamps (F-09) | naive `datetime.utcnow()` + manual `"Z"` | `datetime.now(UTC).isoformat()` | stdlib offset-aware; `utcnow()` deprecated on 3.12 |
| SweepParameter coercion (F-02) | 3 hand-copied field-extraction blocks | one `SweepParameter.from_mapping` classmethod | single source of truth; new fields can't drift |
| Provenance-key rendering (F-03) | 2 copies of `_parser_fn_repr` | one shared `parser_fn_repr` in `trial_record.py` | cache-key MUST be byte-identical across sweep/rescore |
| Fake Ax for tests (F-20) | a real `AxClient` in unit tests | a minimal stub exposing the 5 methods used | Ax is heavy + nondeterministic; runner already duck-types it |

**Key insight:** this phase *removes* hand-rolled duplication rather than adding libraries — there are **no new third-party dependencies** (see Package Legitimacy).

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** All work is internal refactor + tests using already-declared dev tooling (`pytest`, `coverage`, `ruff`, `pyright`). The only stdlib import additions are `datetime.UTC` (F-09) and possibly `json`/`math` hoisted to module level (F-10). No registry verification required.

## Common Pitfalls

### Pitfall 1: Deleting an F-30 field without its read-back/loader edits
**What goes wrong:** `TypeError: unexpected keyword argument` at import/load. **Why:** `yaml_hash` is reconstructed at `trial_record.py:241` (not just declared at `:40`); `gt_kinds_supported` is read at `schema.py:102` and passed at `:109`. **Avoid:** delete each field's full set of code sites in one commit (table in Primary Answer 2). **Warning sign:** `pytest` collection error or a loader test failing immediately.

### Pitfall 2: F-09 timestamp format change breaks a string assertion
**What goes wrong:** `now(UTC).isoformat()` emits `+00:00`, not `Z`. **Avoid:** drop the manual `"Z"`; grep tests for literal `"Z"`/`endswith("Z")` before landing (verified none today, but a new F-20 test must not assert the old format).

### Pitfall 3: Over-narrowing F-08 at arbitrary-callable boundaries
**What goes wrong:** narrowing `evaluation.py:89/177` or `rescore.py:~257` to `(OSError, json.JSONDecodeError)` lets a plugin's `ValueError`/`KeyError` crash the sweep — violating fail-soft. **Avoid:** keep those 3 broad; satisfy D-03 via warning-promotion + counter only. Narrow the other 8 IO/serialization sites cleanly.

### Pitfall 4: F-10 hoist accidentally lifts a heavy/optional import
**What goes wrong:** breaks lazy-import gating → `import geodispbench3d` pulls Ax/torch. **Avoid:** verified the four F-10 imports are all internal/stdlib; if the work surfaces any other in-loop import, leave heavy/optional ones lazy and document the reason. **Warning sign:** `tests/core/test_imports.py::test_framework_has_no_iof3d_or_pchandler_imports` fails.

### Pitfall 5: Removing a `# type: ignore[attr-defined]` exposes a real residual error
**What goes wrong:** F-01 retype is incomplete and the now-unsuppressed access errors in pyright. **Avoid:** re-run pyright after each ignore removal; confirm the access type-checks against `SuiteConfig`.

### Pitfall 6: Treating "pyright passes" as 0 errors
**What goes wrong:** unachievable — `runner.py:395/401` (F-14), iof3D adapter (F-12/F-15), dashboard all error and are deferred. **Avoid:** operationalize D-08 as no-regression vs. an established baseline + 0 errors in Phase-2-touched lines (Assumption A1).

## State of the Art
| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` (naive) | `datetime.now(UTC)` (aware) | deprecated Python 3.12 | F-09; CI runs 3.12 so it emits DeprecationWarnings today (seen in this session's run) |

## Environment Availability
| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| conda env `iof3d_cosicorr3d-dev312` | all test/lint/coverage | ✓ | py 3.12.12 | — |
| conda env `f2s3-dev312` | live F2S3 binary sweeps only (NOT Phase-2 tests) | ✓ (but no pytest/geodispbench3d) | — | irrelevant to green-gate |
| pytest | test gate | ✓ (in dev env) | 8.4 | — |
| ruff | lint gate | ✓ | 0.15.12 (CI pins 0.8.4) | — |
| pyright | type gate | ✓ | 1.1.403 (CI pins 1.1.392) | install pinned 1.1.392 for CI-faithful baseline |
| iof3D + pchandler | tests/iof3d + tests/f2s3 collection | ✓ (in dev env) | — | suites self-skip if absent |

**Missing dependencies with no fallback:** none — the green-gate runs entirely in `iof3d_cosicorr3d-dev312`.

## Assumptions Log
| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-08 "pyright passes" should be operationalized as **no-regression vs. an established HEAD baseline** (not 0 errors), because F-14/F-12/F-15/dashboard errors are deferred. **Needs user confirmation.** | Quality-Gate Baseline | If user insists on 0 errors, scope balloons into deferred F-14/F-12/F-15 work — a major scope change. |
| A2 | F-05's minimum (emit finite-case count) is satisfied by adding a count signal without changing the mean math; penalize/threshold are optional. | F-05 anchor | If user wants the objective math changed (penalize), more runner + Ax-interaction work + more characterization tests. |
| A3 | Stripping the now-inert `gt_kinds_supported:` keys from the 2 dataset YAMLs (+ schema.json) is optional hygiene, not required for correctness. | Primary Answer 2 | None functionally; only doc-consistency drift if skipped. |
| A4 | The F-08 non-fatal counter for the *sweep* path requires net-new plumbing out of `run_with_suite` (which today returns only the best trial). | F-08 plumbing | If underestimated, F-08 sweep-path work is larger than the rescore/analyze paths (which already carry summary objects). |

## Open Questions
1. **CI-faithful pyright baseline number.**
   - Known: local (1.1.403 + extras) = 21 errors; CI = 1.1.392 + `.[dev]` only.
   - Unclear: the exact CI error count (extras-unresolved → some errors become warnings).
   - Recommendation: Wave 0 installs `pyright==1.1.392` in the dev env (or a throwaway venv) with `.[dev]` only, runs `pyright`, and records the count as the D-08 floor.
2. **Where the sweep-path "N non-fatal failures" line is printed.**
   - Known: rescore/analyze already print summaries; the sweep path returns only the best trial.
   - Recommendation: thread a counter object through `run_with_suite`→`_evaluate_across_cases` and print one aggregate line in `cli.py:_cmd_sweep`.

## Sources

### Primary (HIGH confidence — verified this session)
- `pytest --collect-only` + full run in both envs — env→suite matrix, 32 passed/0 skipped.
- `pytest --cov` fresh run — coverage baseline (runner 13 / store 44 / evaluation 80 / TOTAL 55%).
- `ruff check` (green) + `pyright` (21 errors/9 warnings) in `iof3d_cosicorr3d-dev312`.
- Source reads at HEAD: `runner.py`, `suite/loader.py`, `tool/loader.py`, `dataset/schema.py`, `evaluation.py`, `trial_record.py`, `predictions_cache.py`, `parameters.py`, `iof3d/factory.py`, `rescore.py` (relevant spans).
- `grep` for the four F-30 keys across all in-repo YAML + read-back consumers.
- `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `pyrightconfig.json`, `pyproject.toml` tool config.

### Secondary
- `.planning/phases/01-code-health-audit/REPORT.md` + `EVIDENCE.md` — finding inventory + corroborating detector output (coverage numbers reproduced exactly).

### Tertiary
- None.

## Metadata
**Confidence breakdown:**
- Env→suite matrix: HIGH — directly observed collection + import probes in both envs.
- F-30 deletion safety: HIGH — read every loader's parse path + grepped all YAML + confirmed no jsonschema enforcement.
- Per-finding anchors: HIGH — re-confirmed against HEAD with line-drift noted.
- pyright baseline: HIGH (local) / MEDIUM (CI number is inferred, not yet measured — see Open Q1).
- Validation Architecture: HIGH — grounded in the actual test pattern + measured coverage.

**Research date:** 2026-06-27
**Valid until:** ~2026-07-27 (stable codebase; re-confirm pyright/coverage if HEAD moves before planning).
