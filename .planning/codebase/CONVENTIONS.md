# Coding Conventions

**Analysis Date:** 2026-06-26

This is a Python 3.11+ benchmark framework. Conventions are enforced by `ruff`
(lint + format) and `pyright` (basic type checking), pinned identically in
`.pre-commit-config.yaml` and `.github/workflows/ci.yml`. Match the patterns
below when adding code; CI fails on any ruff/pyright deviation.

## Tooling Baseline

**Formatter / Linter:** `ruff ~= 0.8` (pinned `0.8.4`), config in `pyproject.toml`.
- `line-length = 100`, `target-version = "py311"`.
- Format: `quote-style = "double"`, `indent-style = "space"` (4 spaces).
- Lint select set: `["E", "F", "B", "I", "UP", "W"]` (pycodestyle, pyflakes,
  bugbear, isort, pyupgrade, warnings).
- `E501` (line length) is ignored in lint — the formatter owns wrapping.

**Type Checker:** `pyright ~= 1.1` (pinned `1.1.392`), config in `pyrightconfig.json`.
- `typeCheckingMode = "basic"`, `pythonVersion = "3.11"`.
- `strictListInference`, `strictDictionaryInference`, `strictSetInference` all on.
- `reportMissingImports = "warning"`, `reportMissingTypeStubs = "none"`.
- Runs whole-project (`pass_filenames: false`) — cross-file type errors are caught.

**Run before committing:**
```bash
ruff check .
ruff format --check .
pyright
```

## Naming Patterns

**Files:**
- snake_case module names: `predictions_cache.py`, `cli_adapter.py`, `trial_record.py`.
- Package dirs are flat single words: `tool/`, `dataset/`, `metrics/`, `sweep/`,
  `suite/`, `analysis/`, `results/`, `dashboard/`.
- Tool-adapter packages live as sibling top-level packages prefixed with the
  framework name: `geodispbench3d_iof3d/`, `geodispbench3d_f2s3/`.

**Functions / Methods:**
- snake_case: `run_trial`, `evaluate_trial`, `load_suite`, `build_parameter_specs`.
- Private/internal helpers prefixed with a single underscore: `_build_argv`,
  `_normalize_trial_data`, `_load_defs`, `_cmd_run`, `_parser_fn_repr`.
- Module-level private helpers (underscore prefix) sit at the bottom of the file,
  below the public API (see `src/geodispbench3d/sweep/runner.py`).

**Variables:**
- snake_case throughout. Instance attributes that are internal use a leading
  underscore: `self._adapter`, `self._logger`, `self._trial_log_path`.

**Types / Classes:**
- PascalCase: `ToolAdapter`, `TrialRequest`, `AxSweepRunner`, `MetricDefinition`,
  `CliInvocationSpec`, `RescoreOptions`.
- Spec/config dataclasses end in `Spec`, `Config`, `Options`, `Definition`,
  `Provenance`, `Request`, `Result`, `Outputs`.

**Loggers:**
- Named by dotted module path under the package root:
  `logging.getLogger("geodispbench3d.sweep")`, `"geodispbench3d_iof3d.parser"`,
  `"geodispbench3d.cli"`.

## Code Style

**`from __future__ import annotations`** is the first import in every module
(all 37 source files use it). Always add it — it enables PEP 604 `X | None`
syntax and string-lazy annotations on 3.11.

**Type hints are mandatory** on public function signatures and dataclass fields.
- Use modern syntax: `str | None`, `list[str]`, `dict[str, Any]`,
  `Mapping[str, Any]`, `Sequence[Path]`.
- Import abstract container types from `collections.abc`
  (`Callable`, `Mapping`, `Sequence`), not `typing`.
- `from typing import Any` is the one `typing` import in regular use.
- Return types are always annotated, including `-> None`.

**Dataclasses are the default for structured data.**
- `@dataclass(frozen=True)` is the norm for value/spec types
  (`TrialRequest`, `MetricDefinition`, `CliInvocationSpec`, all of
  `dataset/schema.py`). Mutable `@dataclass` only when a field is accumulated
  in place (e.g. `analysis/runner.py`, `sweep/evaluation.py`).
- Use `field(default_factory=dict)` for mutable defaults
  (`extras: Mapping[str, Any] = field(default_factory=dict)`).
- Keyword-only constructors via `*` are used for multi-arg classes
  (`AxSweepRunner.__init__(self, *, adapter, sweep_config, ...)`).

## Import Organization

ruff's isort (`I`) enforces three groups, blank-line separated:
1. `from __future__ import annotations`
2. Standard library (`argparse`, `logging`, `importlib`, `pathlib`, `math`).
3. Third-party (`numpy`, `pandas`, `omegaconf`, `ax`).
4. First-party (`geodispbench3d.*`).

**Path aliases:** none — absolute package imports only
(`from geodispbench3d.tool.base import ToolAdapter`). Relative imports
(`from .evaluation import evaluate_trial`) are used *within* a subpackage.

**Lazy / deferred imports** are an intentional pattern, not an accident:
- The CLI (`src/geodispbench3d/cli.py`) imports heavy/optional subsystems
  *inside* each `_cmd_*` handler so that `geodispbench3d --help` and unrelated
  subcommands never pay for `ax`, `streamlit`, or adapter stacks.
- Optional dependencies are guarded with `try/except ImportError` that re-raises
  a helpful install hint (see `sweep/runner.py` Ax import block).
- Keep `geodispbench3d.*` free of any `iof3D` / `pchandler` / `pc2img` import —
  this invariant is enforced by `tests/core/test_imports.py`.

## Error Handling

**Raise specific built-ins with f-string context** that echoes the offending value:
```python
raise ValueError(f"Metric fn reference must be 'package.module:function', got {entry!r}")
raise FileNotFoundError(f"Metrics YAML not found: {yaml_path}")
raise TypeError(f"Unable to normalize Ax trial data: {trial_data!r}")
```
- Use `{value!r}` (repr) when echoing user/config input.
- `ValueError` for bad values, `TypeError` for shape/contract violations,
  `FileNotFoundError` for missing paths, `ImportError` for unresolvable refs.
- Chain with `from exc` when re-raising on top of a caught exception
  (`raise ValueError(...) from exc` in `geodispbench3d_iof3d/adapter.py`).

**Defensive `except Exception` is reserved for non-fatal side effects.** Trial
execution, provenance stamping, prediction caching, and trial-log appends all
wrap their bodies in `except Exception` and downgrade to a debug log rather than
failing the run:
```python
except Exception:  # pragma: no cover - cache failure shouldn't fail a trial
    self._logger.debug("Unable to cache prediction for run %s",
                       result.outputs.run_dir, exc_info=True)
```
- Always annotate these with a `# pragma: no cover - <reason>` comment explaining
  why the broad catch is justified.
- Never let observability/caching/provenance failures break the primary path.

## Logging

**Framework:** stdlib `logging` only (no third-party logger).
- Modules accept an optional `logger: logging.Logger | None = None` parameter and
  fall back to a module-named logger:
  `self._logger = logger or logging.getLogger("geodispbench3d.sweep")`.
- Use lazy `%`-style args, never f-strings, in log calls:
  `logger.info("Best trial: %s", best)` — not `logger.info(f"...{best}")`.
- Level usage: `info` for run milestones, `warning` for skips/degradation,
  `debug(..., exc_info=True)` for swallowed exceptions, `exception(...)` for a
  caught-and-logged trial failure.
- CLI entrypoints configure the root logger with the format
  `[%(asctime)s][%(name)s][%(levelname)s] %(message)s`.

## Comments

**Module docstrings are required** and substantial — every source file opens with
a triple-quoted docstring explaining the module's role, often with a `Usage::`
block or an enumerated description of inputs (see `cli.py`, `metrics/registry.py`,
`tool/base.py`).

**Class and public-function docstrings** explain contract and intent, not
mechanics. Dataclass docstrings describe what the fields mean and edge cases
(e.g. what `case_name=None` signifies in `TrialRequest`).

**Inline comments explain *why*, often spanning the design rationale** (e.g. the
multi-branch Ax-version compatibility shim in `runner.py._create_experiment`,
the cache-failure rationale). Comments frequently document trade-offs and future
extension points ("extend later if multi-case sweeps need different aggregation").

**No TSDoc/JSDoc equivalent** — plain Python docstrings, no enforced field tags.

## Function & Module Design

- **Keyword-only public APIs:** multi-argument functions and constructors force
  keyword args with `*` for call-site clarity (`evaluate_trial(*, trial_result,
  parameters, case, metrics, registry, ...)`).
- **Return immutable/plain dicts** from boundary functions (`dict(result.scalar_metrics)`).
- **`__all__` is declared in every public module** (33 of the source files) and
  is kept alphabetically sorted. Update it whenever you add a public symbol.
- **Barrel `__init__.py`** re-exports the subpackage's public surface and declares
  its own sorted `__all__` (see `src/geodispbench3d/tool/__init__.py`). New public
  classes should be wired through the package `__init__`.
- **Runtime introspection for forward-compat:** `inspect.signature(...)` is used
  to adapt to differing third-party (Ax) API signatures rather than pinning a
  single shape — see `runner.py._create_experiment`.

---

*Convention analysis: 2026-06-26*
