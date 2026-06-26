<!-- GSD:project-start source:PROJECT.md -->

## Project

**geodispbench3d — Publication Readiness**

`geodispbench3d` is a mature, tool-agnostic benchmark framework for 3D
displacement / optical-flow tools: a YAML-driven front end (suite → tool +
dataset + metrics), Bayesian hyperparameter sweeps via Ax, three execution
modes (`sweep`, `rescore`, `analyze`) over one evaluation core, a pluggable
`ToolAdapter` contract with two shipped integrations (iof3D, F2S3),
provenance-first persistence, and a Streamlit dashboard.

This milestone takes the existing (already BSD-3-Clause) codebase from "works
for us" to **publication-ready for public release on PyPI with CI/CD** — gated
behind a code-health pass that builds confidence in the codebase before
anything ships.

**Core Value:** Confidence: nothing is published to PyPI until the codebase is demonstrably
lean, correct, well-tested, and its CLI-integration story is sound. The audit
comes before the cleanup, and the cleanup comes before the release.

### Constraints

- **Tech stack**: Python ~=3.11/3.12, numpy 2.0 pin, Ax / Hydra / OmegaConf — preserve; transitive tool stacks must stay NumPy-2 compatible.
- **Dev environment**: all python/pip/pytest invocations must go through the mandated conda env per `AGENTS.md`.
- **Process — branching**: GSD work stays on `develop` and phase branches; PRs to `main` happen only at milestone completion and must strip the `.planning/` folder.
- **Process — review**: internal phase-plan reviews are run through the codex CLI.
- **Licensing**: already BSD-3-Clause; the `Private :: Do Not Upload` classifier and the README "Proprietary" line must be removed/reconciled before any public PyPI publish.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python `~=3.11` (declared `requires-python = "~=3.11"` in `pyproject.toml`; classifiers list 3.11 and 3.12) — all source under `src/`.
- YAML — declarative benchmark definitions (`benchmarks/**/*.yaml`, `src/**/conf/**/*.yaml`) for suites, datasets, metrics, analyses, and tool wiring.
- JSON — JSON Schema validation files (`src/geodispbench3d/conf/schema/*.json`).

## Runtime

- CPython 3.11/3.12. Local development is pinned to a Conda env `iof3d_cosicorr3d-dev312` (see `AGENTS.md`); the F2S3 binary runs in a separate Conda env `f2s3-dev312` invoked via `conda run`.
- CI runs on Python 3.12 (`.github/workflows/ci.yml`).
- pip (editable installs, `pip install -e .[extra]`). Conda is used only for environment isolation, not dependency resolution.
- Lockfile: missing. Dependencies are version-range pinned in `pyproject.toml`, not lockfile-pinned. CI pins lint tools (`ruff==0.8.4`, `pyright==1.1.392`) inline.

## Frameworks

- `ax-platform ~= 1.1` — Bayesian hyperparameter optimization engine. Driven via `AxClient` in `src/geodispbench3d/sweep/runner.py` (with a fallback import path for older Ax).
- `hydra-core ~= 1.3` — configuration composition / structured config. Used in `src/geodispbench3d/cli.py` and the iof3D adapter for `AppConfig` assembly.
- `omegaconf ~= 2.3` — config object model underpinning Hydra; used throughout for YAML <-> dataclass translation (`OmegaConf.create`, `OmegaConf.save`).
- `numpy ~= 2.0` — numerical core for displacement/point-cloud math (e.g. `src/geodispbench3d_f2s3/output_parser.py`).
- `pandas` (unpinned) — DataFrame model for the parquet results store (`src/geodispbench3d/results/store.py`).
- `pytest ~= 8.4` (`dev` extra) — test runner. Suites split into `tests/core`, `tests/iof3d`, `tests/f2s3`.
- `coverage ~= 7.0` (`dev` extra) — coverage measurement.
- `setuptools` + `setuptools_scm` — build backend (`build-system.build-backend = "setuptools.build_meta"`); version derived from git tags, written to `src/geodispbench3d/_version.py`.
- `ruff ~= 0.8` — linter + formatter (replaces black/isort/flake8). Config in `pyproject.toml` `[tool.ruff]`.
- `pyright ~= 1.1` — static type checker. Config in `pyrightconfig.json` (basic mode).
- `pre-commit ~= 4.3` — git hook orchestration (`.pre-commit-config.yaml`).
- `sphinx ~= 5.1` (`docs` extra) — documentation builder.

## Key Dependencies

- `ax-platform ~= 1.1` — without it sweep orchestration cannot run (raised as `ImportError` in `sweep/runner.py`).
- `hydra-core` / `omegaconf` — config backbone; every suite/dataset/tool YAML is parsed through them.
- `numpy ~= 2.0` — note the major-version pin; transitive tool stacks must be NumPy-2 compatible.
- `streamlit ~= 1.41` (`dashboard` extra) — results dashboard UI (`src/geodispbench3d/dashboard/app.py`).
- `altair ~= 5.4` (`dashboard` extra) — charting inside the dashboard (optional; guarded import).
- `duckdb ~= 1.4` (`dashboard` extra) — ad-hoc parquet querying. Readers do not require it; pandas is the default reader.
- `iof3d` extra: `iof3D ~= 0.1`, `pchandler`, `pc2img` — pulls iof3D's full pipeline stack (torch, ptlflow, opencv) transitively. Imported at module level only in `src/geodispbench3d_iof3d/`.
- `f2s3` extra: empty (`f2s3 = []`). The F2S3 adapter drives the F2S3 binary via subprocess; the Python lib is not required.

## Configuration

- `GEODISPBENCH3D_PARQUET` — optional env var pointing the dashboard at a results parquet (`src/geodispbench3d/cli.py`, `src/geodispbench3d/dashboard/app.py`). No `.env` file is used; no secrets are read from the environment.
- `pyproject.toml` — single source of build, dependency, extras, ruff, and setuptools_scm config.
- `pyrightconfig.json` — type-checker config.
- `release-please-config.json` + `.release-please-manifest.json` — automated release/changelog config.
- Package data (`conf/**/*.yaml`, `conf/**/*.json`) is bundled via `[tool.setuptools.package-data]`.

## Platform Requirements

- Conda env `iof3d_cosicorr3d-dev312` (mandated by `AGENTS.md`; bare `python`/`pip`/`pytest` forbidden).
- Separate Conda env `f2s3-dev312` required to exercise the F2S3 adapter end-to-end.
- GPU/CUDA implied transitively when the `iof3d` extra is installed (torch/ptlflow stack); the framework core is CPU-only.
- Distributed as an sdist + wheel to a Python package index (currently flagged `Private :: Do Not Upload`; the classifier must be removed before PyPI publish). Console entry points: `geodispbench3d` and `iof3d-ax` (`[project.scripts]`).

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Tooling Baseline

- `line-length = 100`, `target-version = "py311"`.
- Format: `quote-style = "double"`, `indent-style = "space"` (4 spaces).
- Lint select set: `["E", "F", "B", "I", "UP", "W"]` (pycodestyle, pyflakes,
- `E501` (line length) is ignored in lint — the formatter owns wrapping.
- `typeCheckingMode = "basic"`, `pythonVersion = "3.11"`.
- `strictListInference`, `strictDictionaryInference`, `strictSetInference` all on.
- `reportMissingImports = "warning"`, `reportMissingTypeStubs = "none"`.
- Runs whole-project (`pass_filenames: false`) — cross-file type errors are caught.

## Naming Patterns

- snake_case module names: `predictions_cache.py`, `cli_adapter.py`, `trial_record.py`.
- Package dirs are flat single words: `tool/`, `dataset/`, `metrics/`, `sweep/`,
- Tool-adapter packages live as sibling top-level packages prefixed with the
- snake_case: `run_trial`, `evaluate_trial`, `load_suite`, `build_parameter_specs`.
- Private/internal helpers prefixed with a single underscore: `_build_argv`,
- Module-level private helpers (underscore prefix) sit at the bottom of the file,
- snake_case throughout. Instance attributes that are internal use a leading
- PascalCase: `ToolAdapter`, `TrialRequest`, `AxSweepRunner`, `MetricDefinition`,
- Spec/config dataclasses end in `Spec`, `Config`, `Options`, `Definition`,
- Named by dotted module path under the package root:

## Code Style

- Use modern syntax: `str | None`, `list[str]`, `dict[str, Any]`,
- Import abstract container types from `collections.abc`
- `from typing import Any` is the one `typing` import in regular use.
- Return types are always annotated, including `-> None`.
- `@dataclass(frozen=True)` is the norm for value/spec types
- Use `field(default_factory=dict)` for mutable defaults
- Keyword-only constructors via `*` are used for multi-arg classes

## Import Organization

- The CLI (`src/geodispbench3d/cli.py`) imports heavy/optional subsystems
- Optional dependencies are guarded with `try/except ImportError` that re-raises
- Keep `geodispbench3d.*` free of any `iof3D` / `pchandler` / `pc2img` import —

## Error Handling

- Use `{value!r}` (repr) when echoing user/config input.
- `ValueError` for bad values, `TypeError` for shape/contract violations,
- Chain with `from exc` when re-raising on top of a caught exception
- Always annotate these with a `# pragma: no cover - <reason>` comment explaining
- Never let observability/caching/provenance failures break the primary path.

## Logging

- Modules accept an optional `logger: logging.Logger | None = None` parameter and
- Use lazy `%`-style args, never f-strings, in log calls:
- Level usage: `info` for run milestones, `warning` for skips/degradation,
- CLI entrypoints configure the root logger with the format

## Comments

## Function & Module Design

- **Keyword-only public APIs:** multi-argument functions and constructors force
- **Return immutable/plain dicts** from boundary functions (`dict(result.scalar_metrics)`).
- **`__all__` is declared in every public module** (33 of the source files) and
- **Barrel `__init__.py`** re-exports the subpackage's public surface and declares
- **Runtime introspection for forward-compat:** `inspect.signature(...)` is used

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- The core (`geodispbench3d`) is tool-agnostic. It never imports a specific tool; tools enter through the `ToolAdapter` contract and dotted-path callables resolved at load time.
- Configuration is declarative: `suite.yaml` composes a `tool.yaml`, a `dataset.yaml`, and a `metrics.yaml`. All YAML is parsed into frozen dataclasses up front (`OmegaConf.to_container` → dataclass).
- Three execution modes share one evaluation core (`evaluate_trial`): **sweep** (Ax-driven, runs the tool), **rescore** (re-runs metrics over existing run dirs), **analyze** (scores cached predictions, no tool involvement).
- A two-phase trial model: phase 1 = adapter produces raw outputs in a run dir; phase 2 = an `output_parser` turns those into a `prediction = {per_point: [...]}` mapping. Phase 2 output is cached so rescore/analyze can skip it.
- Provenance-first persistence: every run dir carries an `ax_trial/summary.json` recording tool/dataset/parser provenance, enabling reproducible downstream rescoring without the original suite YAML.

## Layers

- Purpose: Argument parsing and command routing; lazy imports keep optional deps (Ax, streamlit) out of the hot path until needed.
- Location: `src/geodispbench3d/cli.py`
- Contains: `main`, `_cmd_run`, `_cmd_sweep`, `_cmd_rescore`, `_cmd_analyze`, `_cmd_dashboard`, `_cmd_list_metrics`.
- Depends on: suite/analysis loaders, sweep runner, results store.
- Used by: console entry point `geodispbench3d = geodispbench3d.cli:main`.
- Purpose: Turn YAML files into validated, frozen dataclasses with resolved paths.
- Location: `src/geodispbench3d/suite/loader.py`, `tool/loader.py`, `dataset/schema.py`, `metrics/registry.py`, `analysis/loader.py`.
- Contains: `SuiteConfig`, `ToolConfig`, `DatasetSpec`, `MetricsConfig`, `AnalysisConfig`, and their `load_*` functions.
- Depends on: `omegaconf`, `importlib` (dotted-path resolution).
- Used by: CLI layer and orchestration layer.
- Purpose: Drive the three execution modes.
- Location: `src/geodispbench3d/sweep/runner.py`, `sweep/rescore.py`, `analysis/runner.py`.
- Contains: `AxSweepRunner`, `rescore_suite`, `analyze`.
- Depends on: `ax-platform` (sweep only), the evaluation glue, the persistence layer.
- Used by: CLI layer.
- Purpose: Single chokepoint that all three modes funnel through; runs the parser and dispatches metrics.
- Location: `src/geodispbench3d/sweep/evaluation.py` (`evaluate_trial`).
- Depends on: metric registry, ground-truth loader.
- Used by: sweep runner, rescore runner, analyze runner.
- Purpose: Encapsulate tool-specific invocation behind a uniform contract.
- Location: `src/geodispbench3d/tool/` and the external plugin packages.
- Contains: `ToolAdapter` ABC, `CliToolAdapter`, `CallableToolAdapter`, and the iof3D/F2S3 plugins.
- Depends on: the tool itself (only the chosen adapter's package imports it).
- Used by: the sweep runner via `adapter.run_trial`.
- Purpose: Durable outputs the dashboard and downstream passes consume.
- Location: `src/geodispbench3d/results/store.py`, `results/predictions_cache.py`, `sweep/trial_record.py`.
- Contains: `ResultsStore` (parquet), predictions cache (JSON), trial summaries (JSON).
- Depends on: `pandas`, `numpy`.
- Used by: orchestration layer.

## Data Flow

### Primary Request Path (`geodispbench3d run suite.yaml`)

### Rescore Flow (`run --rescore`)

### Analyze Flow (`analyze analysis.yaml`)

- No in-process global mutable state. The Ax experiment state lives inside the `AxClient` instance held by `AxSweepRunner`. Durable state is the parquet file, the predictions cache, and per-run `summary.json` files.

## Key Abstractions

- Purpose: The single seam between the tool-agnostic core and a specific tool.
- Examples: `src/geodispbench3d/tool/base.py` (ABC), `cli_adapter.py`, `callable_adapter.py`, `src/geodispbench3d_iof3d/adapter.py`.
- Pattern: Abstract base class with one required method (`run_trial`) and two optional lifecycle hooks (`prepare`/`teardown`); subclasses opt into in-process execution via `in_process_safe`.
- Purpose: Adapter-neutral description of a trial and its results.
- Examples: `TrialRequest`, `TrialOutputs`, `TrialResult` in `src/geodispbench3d/tool/base.py`.
- Pattern: Frozen dataclasses passed across the adapter boundary.
- Purpose: Declarative parameter-space grammar mapped to Ax's spec dicts.
- Examples: `src/geodispbench3d/sweep/parameters.py`.
- Pattern: Frozen dataclass + pure translation function (`build_parameter_specs`), with conditional activation (`activates_on`).
- Purpose: Late-bound, cached resolution of metric callables declared in YAML.
- Examples: `src/geodispbench3d/metrics/registry.py`, implementations in `metrics/builtins.py`.
- Pattern: Dependency-injection by name — the runner injects only the inputs a metric declares it `needs` (`prediction`, `ground_truth`, `trial_meta`, `case_meta`).
- Purpose: Make a run dir self-describing so downstream passes don't need the original suite.
- Examples: `ToolProvenance`, `DatasetProvenance`, `ParserProvenance` in `src/geodispbench3d/sweep/trial_record.py`.
- Pattern: Frozen dataclasses serialized to/from `summary.json`.

## Entry Points

- Location: `src/geodispbench3d/cli.py` (`main`), declared in `pyproject.toml` `[project.scripts]`.
- Triggers: User shell invocation.
- Responsibilities: Route to run/rescore/analyze/dashboard/list-metrics.
- Location: `src/geodispbench3d_iof3d/cli.py` (`main`).
- Triggers: Legacy Hydra-style CLI for iof3D sweeps, kept for backward compatibility with the pre-framework `iof3D_analysis.ax` workflow.
- Responsibilities: Hydra-config-driven iof3D sweep, independent of the generic suite path.
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

### Duplicated hyperparameter-coercion logic

### `_parser_fn_repr` duplicated across modules

## Error Handling

- Config loading raises eagerly with descriptive `ValueError`/`FileNotFoundError` (e.g. `load_suite` validates that `tool`/`dataset`/`metrics` are present and that the objective is declared in metrics).
- Trial execution is defensive: a failing trial is caught, logged via `logger.exception`, and reported to Ax with `log_trial_failure` so the sweep continues (`src/geodispbench3d/sweep/runner.py:159`, `:215`).
- Best-effort side effects (provenance stamping, prediction caching, audit-log appends) are wrapped in broad `except Exception` with debug-level logging so they never fail a trial (`src/geodispbench3d/sweep/runner.py:295`, `:324`).
- Metric callables that raise are caught in `_invoke_metric` and skipped, not propagated (`src/geodispbench3d/sweep/evaluation.py:177`).
- CLI commands return integer exit codes; partial success in rescore/analyze returns `1` when not all targets scored.

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
