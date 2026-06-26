<!-- refreshed: 2026-06-26 -->
# Architecture

**Analysis Date:** 2026-06-26

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                    │
│  `src/geodispbench3d/cli.py`  —  argparse subcommands                     │
│   run · run --rescore · analyze · dashboard · list-metrics               │
└──────┬───────────────────┬────────────────────┬────────────────┬────────┘
       │ run               │ run --rescore       │ analyze        │ dashboard
       ▼                   ▼                     ▼                ▼
┌──────────────┐  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐
│ load_suite   │  │ rescore_suite   │  │ analyze        │  │ streamlit    │
│ (suite/      │  │ (sweep/         │  │ (analysis/     │  │ app.py       │
│  loader.py)  │  │  rescore.py)    │  │  runner.py)    │  │              │
└──────┬───────┘  └────────┬────────┘  └───────┬────────┘  └──────────────┘
       │                   │                    │
       ▼                   │                    │
┌──────────────┐           │                    │
│ AxSweepRunner│           │                    │
│ (sweep/      │           │                    │
│  runner.py)  │           │                    │
└──────┬───────┘           │                    │
       │ per trial         │ per run dir        │ per cached prediction
       ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           evaluate_trial  —  `src/geodispbench3d/sweep/evaluation.py`     │
│   adapter outputs → output_parser → prediction → MetricRegistry dispatch │
└──────┬───────────────────────────────────┬──────────────────────────────┘
       │ scalar_metrics                     │ record_rows / prediction
       ▼                                    ▼
┌──────────────────┐          ┌────────────────────────────────────────────┐
│ AxClient         │          │ Persistence                                │
│ (objective loop) │          │ ResultsStore → parquet  `results/store.py`  │
└──────────────────┘          │ predictions cache       `predictions_cache` │
                              │ summary.json            `sweep/trial_record`│
                              └────────────────────────────────────────────┘
       ▲ adapter contract
┌─────────────────────────────────────────────────────────────────────────┐
│        ToolAdapter plugins  —  `src/geodispbench3d/tool/`                 │
│  CliToolAdapter · CallableToolAdapter · custom · factory                 │
│  External packages: geodispbench3d_iof3d · geodispbench3d_f2s3           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI dispatcher | Parse argv, route to run/rescore/analyze/dashboard/list-metrics | `src/geodispbench3d/cli.py` |
| Suite loader | Parse `suite.yaml`, eagerly load referenced tool/dataset/metrics configs | `src/geodispbench3d/suite/loader.py` |
| Tool loader | Build a `ToolAdapter` from `tool.yaml` (cli/callable/custom/factory) | `src/geodispbench3d/tool/loader.py` |
| Tool adapter contract | Adapter-neutral trial invocation interface | `src/geodispbench3d/tool/base.py` |
| CLI adapter | Run the tool as a subprocess, one process per trial | `src/geodispbench3d/tool/cli_adapter.py` |
| Callable adapter | Run an in-process Python callable per trial | `src/geodispbench3d/tool/callable_adapter.py` |
| Sweep runner | Drive the Ax optimization loop, one trial at a time | `src/geodispbench3d/sweep/runner.py` |
| Parameter grammar | Translate sweep-param YAML into Ax parameter specs | `src/geodispbench3d/sweep/parameters.py` |
| Evaluation glue | Bridge tool outputs → parser → metric registry | `src/geodispbench3d/sweep/evaluation.py` |
| Metric registry | Resolve and cache metric callables from dotted paths | `src/geodispbench3d/metrics/registry.py` |
| Built-in metrics | Reference scalar + record metric implementations | `src/geodispbench3d/metrics/builtins.py` |
| Dataset schema | Parse `dataset.yaml` into cases/scans/ground-truth specs | `src/geodispbench3d/dataset/schema.py` |
| Ground-truth loader | Lazily load GT contents, dispatched on `kind` | `src/geodispbench3d/dataset/ground_truth.py` |
| Trial record | Read/write per-run `ax_trial/summary.json` + provenance | `src/geodispbench3d/sweep/trial_record.py` |
| Rescore runner | Re-score existing run dirs without invoking the tool | `src/geodispbench3d/sweep/rescore.py` |
| Analyze runner | Score cached predictions; no tool, no dataset scan | `src/geodispbench3d/analysis/runner.py` |
| Predictions cache | Persist/read phase-2 parser output keyed by provenance | `src/geodispbench3d/results/predictions_cache.py` |
| Results store | Append record rows to a parquet file | `src/geodispbench3d/results/store.py` |
| Dashboard | Streamlit UI for exploring the results parquet | `src/geodispbench3d/dashboard/app.py` |
| iof3D plugin | Factory + in-process adapter + output parser for iof3D | `src/geodispbench3d_iof3d/` |
| F2S3 plugin | Output parser for F2S3 (driven via the generic CLI adapter) | `src/geodispbench3d_f2s3/` |

## Pattern Overview

**Overall:** Plugin/adapter benchmark framework with a declarative (YAML-driven) configuration front end.

**Key Characteristics:**
- The core (`geodispbench3d`) is tool-agnostic. It never imports a specific tool; tools enter through the `ToolAdapter` contract and dotted-path callables resolved at load time.
- Configuration is declarative: `suite.yaml` composes a `tool.yaml`, a `dataset.yaml`, and a `metrics.yaml`. All YAML is parsed into frozen dataclasses up front (`OmegaConf.to_container` → dataclass).
- Three execution modes share one evaluation core (`evaluate_trial`): **sweep** (Ax-driven, runs the tool), **rescore** (re-runs metrics over existing run dirs), **analyze** (scores cached predictions, no tool involvement).
- A two-phase trial model: phase 1 = adapter produces raw outputs in a run dir; phase 2 = an `output_parser` turns those into a `prediction = {per_point: [...]}` mapping. Phase 2 output is cached so rescore/analyze can skip it.
- Provenance-first persistence: every run dir carries an `ax_trial/summary.json` recording tool/dataset/parser provenance, enabling reproducible downstream rescoring without the original suite YAML.

## Layers

**CLI layer:**
- Purpose: Argument parsing and command routing; lazy imports keep optional deps (Ax, streamlit) out of the hot path until needed.
- Location: `src/geodispbench3d/cli.py`
- Contains: `main`, `_cmd_run`, `_cmd_sweep`, `_cmd_rescore`, `_cmd_analyze`, `_cmd_dashboard`, `_cmd_list_metrics`.
- Depends on: suite/analysis loaders, sweep runner, results store.
- Used by: console entry point `geodispbench3d = geodispbench3d.cli:main`.

**Config/loader layer:**
- Purpose: Turn YAML files into validated, frozen dataclasses with resolved paths.
- Location: `src/geodispbench3d/suite/loader.py`, `tool/loader.py`, `dataset/schema.py`, `metrics/registry.py`, `analysis/loader.py`.
- Contains: `SuiteConfig`, `ToolConfig`, `DatasetSpec`, `MetricsConfig`, `AnalysisConfig`, and their `load_*` functions.
- Depends on: `omegaconf`, `importlib` (dotted-path resolution).
- Used by: CLI layer and orchestration layer.

**Orchestration layer:**
- Purpose: Drive the three execution modes.
- Location: `src/geodispbench3d/sweep/runner.py`, `sweep/rescore.py`, `analysis/runner.py`.
- Contains: `AxSweepRunner`, `rescore_suite`, `analyze`.
- Depends on: `ax-platform` (sweep only), the evaluation glue, the persistence layer.
- Used by: CLI layer.

**Evaluation glue:**
- Purpose: Single chokepoint that all three modes funnel through; runs the parser and dispatches metrics.
- Location: `src/geodispbench3d/sweep/evaluation.py` (`evaluate_trial`).
- Depends on: metric registry, ground-truth loader.
- Used by: sweep runner, rescore runner, analyze runner.

**Adapter layer:**
- Purpose: Encapsulate tool-specific invocation behind a uniform contract.
- Location: `src/geodispbench3d/tool/` and the external plugin packages.
- Contains: `ToolAdapter` ABC, `CliToolAdapter`, `CallableToolAdapter`, and the iof3D/F2S3 plugins.
- Depends on: the tool itself (only the chosen adapter's package imports it).
- Used by: the sweep runner via `adapter.run_trial`.

**Persistence layer:**
- Purpose: Durable outputs the dashboard and downstream passes consume.
- Location: `src/geodispbench3d/results/store.py`, `results/predictions_cache.py`, `sweep/trial_record.py`.
- Contains: `ResultsStore` (parquet), predictions cache (JSON), trial summaries (JSON).
- Depends on: `pandas`, `numpy`.
- Used by: orchestration layer.

## Data Flow

### Primary Request Path (`geodispbench3d run suite.yaml`)

1. Parse argv, route to `_cmd_run` → `_cmd_sweep` (`src/geodispbench3d/cli.py:101`, `:123`).
2. `load_suite` reads `suite.yaml` and eagerly loads the referenced tool/dataset/metrics configs, building the `ToolAdapter` (`src/geodispbench3d/suite/loader.py:60`).
3. Build `SweepConfig` + Ax parameter specs; construct `AxSweepRunner` (`src/geodispbench3d/cli.py:134`, `src/geodispbench3d/sweep/parameters.py:84`).
4. `AxSweepRunner.run_with_suite` opens the Ax loop; per trial `AxClient.get_next_trial` yields a parameterization (`src/geodispbench3d/sweep/runner.py:173`).
5. For each dataset case, `adapter.run_trial(TrialRequest)` produces a `TrialResult` with a run dir (`src/geodispbench3d/sweep/runner.py:248`).
6. `evaluate_trial` runs the `output_parser` into a `prediction`, then dispatches objective + record metrics through `MetricRegistry` (`src/geodispbench3d/sweep/evaluation.py:51`).
7. Scalar metrics (mean-aggregated across cases) flow back via `AxClient.complete_trial`; record rows are appended to parquet through `on_record_rows` (`src/geodispbench3d/sweep/runner.py:214`, `:331`).
8. Provenance is stamped into `ax_trial/summary.json` and the prediction is cached under `predictions_root` (`src/geodispbench3d/sweep/runner.py:284`, `:310`).
9. Return the Ax best trial (`src/geodispbench3d/sweep/runner.py:221`).

### Rescore Flow (`run --rescore`)

1. `_cmd_rescore` builds `RescoreOptions`; the tool is never invoked (`src/geodispbench3d/cli.py:170`).
2. `rescore_suite` walks every child of `results.run_dir_root` that has an `ax_trial/summary.json` (`src/geodispbench3d/sweep/rescore.py:79`, `:173`).
3. Per run dir: resolve the dataset case from recorded provenance, select a parser (suite's current vs. recorded), optionally load a cached prediction, then re-dispatch metrics through `evaluate_trial` (`src/geodispbench3d/sweep/rescore.py:203`).
4. Record rows tagged `mode="rescore"` + `pass_id` go to parquet; a `rescore_log` audit entry is appended to the summary (`src/geodispbench3d/sweep/rescore.py:300`).

### Analyze Flow (`analyze analysis.yaml`)

1. `_cmd_analyze` loads an `AnalysisConfig` (dataset + metrics + prediction refs; no tool) (`src/geodispbench3d/cli.py:217`).
2. `analyze` resolves every referenced cached prediction file and scores it with `prediction_override` so phase 2 is skipped entirely (`src/geodispbench3d/analysis/runner.py:45`, `:101`).
3. Record rows tagged `mode="analyze"` + `pass_id` are appended to parquet.

**State Management:**
- No in-process global mutable state. The Ax experiment state lives inside the `AxClient` instance held by `AxSweepRunner`. Durable state is the parquet file, the predictions cache, and per-run `summary.json` files.

## Key Abstractions

**ToolAdapter:**
- Purpose: The single seam between the tool-agnostic core and a specific tool.
- Examples: `src/geodispbench3d/tool/base.py` (ABC), `cli_adapter.py`, `callable_adapter.py`, `src/geodispbench3d_iof3d/adapter.py`.
- Pattern: Abstract base class with one required method (`run_trial`) and two optional lifecycle hooks (`prepare`/`teardown`); subclasses opt into in-process execution via `in_process_safe`.

**Trial value objects:**
- Purpose: Adapter-neutral description of a trial and its results.
- Examples: `TrialRequest`, `TrialOutputs`, `TrialResult` in `src/geodispbench3d/tool/base.py`.
- Pattern: Frozen dataclasses passed across the adapter boundary.

**SweepParameter / parameter specs:**
- Purpose: Declarative parameter-space grammar mapped to Ax's spec dicts.
- Examples: `src/geodispbench3d/sweep/parameters.py`.
- Pattern: Frozen dataclass + pure translation function (`build_parameter_specs`), with conditional activation (`activates_on`).

**MetricDefinition / MetricRegistry:**
- Purpose: Late-bound, cached resolution of metric callables declared in YAML.
- Examples: `src/geodispbench3d/metrics/registry.py`, implementations in `metrics/builtins.py`.
- Pattern: Dependency-injection by name — the runner injects only the inputs a metric declares it `needs` (`prediction`, `ground_truth`, `trial_meta`, `case_meta`).

**Provenance dataclasses:**
- Purpose: Make a run dir self-describing so downstream passes don't need the original suite.
- Examples: `ToolProvenance`, `DatasetProvenance`, `ParserProvenance` in `src/geodispbench3d/sweep/trial_record.py`.
- Pattern: Frozen dataclasses serialized to/from `summary.json`.

## Entry Points

**`geodispbench3d` console script:**
- Location: `src/geodispbench3d/cli.py` (`main`), declared in `pyproject.toml` `[project.scripts]`.
- Triggers: User shell invocation.
- Responsibilities: Route to run/rescore/analyze/dashboard/list-metrics.

**`iof3d-ax` console script:**
- Location: `src/geodispbench3d_iof3d/cli.py` (`main`).
- Triggers: Legacy Hydra-style CLI for iof3D sweeps, kept for backward compatibility with the pre-framework `iof3D_analysis.ax` workflow.
- Responsibilities: Hydra-config-driven iof3D sweep, independent of the generic suite path.

**Dashboard app:**
- Location: `src/geodispbench3d/dashboard/app.py`.
- Triggers: `geodispbench3d dashboard` shells out to `streamlit run app.py`.
- Responsibilities: Interactive exploration of the results parquet.

## Architectural Constraints

- **Threading / concurrency:** Single-threaded trial loop today. `SearchConfig`/`ExecutionConfig` expose `parallel_trials` but the runner evaluates trials sequentially (`AxSweepRunner.run_with_suite`). Parallelism is a future extension, not current behavior.
- **Process isolation:** Adapters declare `in_process_safe`. `CliToolAdapter` is the safe default (subprocess per trial; tool crashes don't kill the sweep). `CallableToolAdapter` / `Iof3dCallableAdapter` run in-process for speed and must be re-entrant across trials (e.g. iof3D reinitialises CUDA per trial).
- **Optional dependencies gated by extras:** `ax-platform` is imported lazily and only required for the sweep path; `streamlit`/`altair`/`duckdb` only for the dashboard extra; `iof3D`/`pchandler`/`pc2img` only for the `[iof3d]` extra. The `[iof3d]` adapter imports the tool stack at module level, so installing that extra transitively pulls torch/opencv/ptlflow.
- **Global state:** None at module level. State is per-`AxSweepRunner`-instance or on disk.
- **Circular imports:** None observed. `tool/loader.py` imports from `sweep/parameters.py`; `sweep/` imports from `tool/base.py` and `metrics/`; the dependency graph is acyclic with `tool/base.py` and the dataclass schemas at the leaves.
- **Append-only persistence:** `ResultsStore.append` reads the full existing parquet, concatenates, and rewrites. This is O(n) per append and not concurrency-safe (last writer wins).

## Anti-Patterns

### Orchestration code treats `SuiteConfig` as untyped

**What happens:** `AxSweepRunner.run_with_suite`, `_evaluate_across_cases`, and the CLI sweep helpers type the suite as `object` / `Any` and reach into it with `getattr(...)` and `# type: ignore[attr-defined]` (`src/geodispbench3d/sweep/runner.py:173`, `src/geodispbench3d/cli.py:132-156`).
**Why it's wrong:** `SuiteConfig` is a concrete frozen dataclass; the `Any` typing discards the static guarantees pyright could provide and hides field-name drift until runtime.
**Do this instead:** Annotate these parameters as `SuiteConfig` (import from `src/geodispbench3d/suite/loader.py`) and drop the `# type: ignore` markers.

### Duplicated hyperparameter-coercion logic

**What happens:** Near-identical `SweepParameter`-construction code appears in three places: `_load_hyperparameters` (`src/geodispbench3d/tool/loader.py:192`), `load_sweep_config` (`src/geodispbench3d/sweep/parameters.py:45`), and `_coerce_hparam` (`src/geodispbench3d_iof3d/factory.py:137`).
**Why it's wrong:** A new field on `SweepParameter` must be added in three spots; they can silently drift.
**Do this instead:** Extract one `SweepParameter.from_mapping(entry)` classmethod in `sweep/parameters.py` and call it everywhere.

### `_parser_fn_repr` duplicated across modules

**What happens:** The same "render a callable as `module:qualname`" helper exists in both `src/geodispbench3d/sweep/runner.py:363` and `src/geodispbench3d/sweep/rescore.py:395`.
**Why it's wrong:** Two copies of identical serialization logic that must stay byte-compatible (the string is used as a cache/provenance key).
**Do this instead:** Promote it to a shared helper in `sweep/trial_record.py` (alongside the provenance dataclasses that consume it).

## Error Handling

**Strategy:** Fail-soft around side effects, fail-loud around configuration.

**Patterns:**
- Config loading raises eagerly with descriptive `ValueError`/`FileNotFoundError` (e.g. `load_suite` validates that `tool`/`dataset`/`metrics` are present and that the objective is declared in metrics).
- Trial execution is defensive: a failing trial is caught, logged via `logger.exception`, and reported to Ax with `log_trial_failure` so the sweep continues (`src/geodispbench3d/sweep/runner.py:159`, `:215`).
- Best-effort side effects (provenance stamping, prediction caching, audit-log appends) are wrapped in broad `except Exception` with debug-level logging so they never fail a trial (`src/geodispbench3d/sweep/runner.py:295`, `:324`).
- Metric callables that raise are caught in `_invoke_metric` and skipped, not propagated (`src/geodispbench3d/sweep/evaluation.py:177`).
- CLI commands return integer exit codes; partial success in rescore/analyze returns `1` when not all targets scored.

## Cross-Cutting Concerns

**Logging:** Standard-library `logging`, configured in the CLI via `logging.basicConfig` with a bracketed `[time][name][level]` format. Loggers are namespaced (`geodispbench3d.sweep`, `geodispbench3d.tool.cli`, etc.) and threaded through call sites explicitly.
**Validation:** Performed at YAML-load time in the loader/schema modules; JSON Schemas also ship under `src/geodispbench3d/conf/schema/` for external validation of suite/tool/dataset/metrics/analysis files.
**Authentication:** Not applicable (offline benchmarking CLI).
**Provenance / reproducibility:** Cross-cutting concern handled by `sweep/trial_record.py` (summary.json) and `results/predictions_cache.py`, stamped from every mode so results are auditable and re-scorable.

---

*Architecture analysis: 2026-06-26*
