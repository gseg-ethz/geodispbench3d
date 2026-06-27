"""suite.yaml loader.

A suite is the top-level configuration a user hands to ``geodispbench3d run``.
It references a tool, a dataset, a metrics file, and a search config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

from geodispbench3d.dataset.schema import DatasetSpec, load_dataset
from geodispbench3d.metrics.registry import MetricsConfig, load_metrics_config
from geodispbench3d.tool.loader import ToolConfig, load_tool_config


@dataclass(frozen=True)
class SearchConfig:
    max_trials: int = 10
    sobol_trials: int = 3
    objective: str = "runtime_seconds"
    minimize: bool = True


@dataclass(frozen=True)
class ExecutionConfig:
    parallel_trials: int = 1
    override_tool_mode: str | None = None  # "subprocess" | "in_process" | None

    def ensure_supported(self) -> None:
        """Raise if this config requests an unimplemented execution feature.

        ``parallel_trials`` and ``override_tool_mode`` are forward-compat seams
        for the tracked v2 EXEC-01 requirement; the current runner evaluates
        trials sequentially using each adapter's declared mode. Rather than
        silently no-op an operator's explicit request (D-09 — "cannot silently
        no-op"), this guard RAISES deterministically. It is the single shared
        guard invoked from both ``cli._cmd_sweep`` and
        ``AxSweepRunner.run_with_suite`` so a programmatic caller of the runner
        cannot bypass it. The fields are retained as the v2 seam, not deleted.
        """

        if self.parallel_trials != 1:
            raise NotImplementedError(
                f"execution.parallel_trials={self.parallel_trials!r} is not yet "
                "supported: the runner evaluates trials sequentially. This is a "
                "v2 EXEC-01 seam — set parallel_trials: 1."
            )
        if self.override_tool_mode is not None:
            raise NotImplementedError(
                f"execution.override_tool_mode={self.override_tool_mode!r} is not "
                "yet supported: the adapter's declared mode is used. This is a "
                "v2 EXEC-01 seam — leave override_tool_mode unset."
            )


@dataclass(frozen=True)
class ResultsConfig:
    parquet_path: Path | None = None
    run_dir_root: Path | None = None
    # Cache for phase-2 output (parser predictions). Kept separate from
    # run_dir_root so old run dirs can be cleaned up without losing the
    # cheap-to-keep predictions; populated by the runner after each
    # successful trial. Defaults to ``<suite-dir>/outputs/predictions/``
    # if the suite YAML omits it.
    predictions_root: Path | None = None


@dataclass(frozen=True)
class SuiteConfig:
    """Composite suite definition with all referenced configs loaded."""

    id: str
    tool: ToolConfig
    dataset: DatasetSpec
    metrics: MetricsConfig
    search: SearchConfig
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    results: ResultsConfig = field(default_factory=ResultsConfig)
    source_path: Path | None = None


def load_suite(path: str | Path) -> SuiteConfig:
    """Load a suite.yaml and all referenced configs."""

    yaml_path = Path(path).resolve()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Suite YAML not found: {yaml_path}")

    raw = OmegaConf.to_container(OmegaConf.load(str(yaml_path)), resolve=True)
    if not isinstance(raw, dict):
        raise ValueError(f"Suite YAML at {yaml_path} must be a mapping")

    base = yaml_path.parent

    tool_ref = raw.get("tool")
    dataset_ref = raw.get("dataset")
    metrics_ref = raw.get("metrics")
    if not (tool_ref and dataset_ref and metrics_ref):
        raise ValueError(f"Suite {yaml_path} must reference 'tool', 'dataset', and 'metrics'")

    tool_cfg = load_tool_config((base / tool_ref).resolve())
    dataset_spec = load_dataset((base / dataset_ref).resolve())
    metrics_cfg = load_metrics_config((base / metrics_ref).resolve())

    search_raw = raw.get("search") or {}
    search = SearchConfig(
        max_trials=int(search_raw.get("max_trials", 10)),
        sobol_trials=int(search_raw.get("sobol_trials", 3)),
        objective=str(search_raw.get("objective", "runtime_seconds")),
        minimize=bool(search_raw.get("minimize", True)),
    )
    _validate_objective(search.objective, metrics_cfg)

    exec_raw = raw.get("execution") or {}
    execution = ExecutionConfig(
        parallel_trials=int(exec_raw.get("parallel_trials", 1)),
        override_tool_mode=_coerce_tool_mode(exec_raw.get("override_tool_mode")),
    )

    results_raw = raw.get("results") or {}
    predictions_root = _resolve_optional_path(results_raw.get("predictions_root"), base)
    if predictions_root is None:
        predictions_root = (base / "outputs" / "predictions").resolve()
    results = ResultsConfig(
        parquet_path=_resolve_optional_path(results_raw.get("parquet_path"), base),
        run_dir_root=_resolve_optional_path(results_raw.get("run_dir_root"), base),
        predictions_root=predictions_root,
    )

    return SuiteConfig(
        id=str(raw.get("id", yaml_path.stem)),
        tool=tool_cfg,
        dataset=dataset_spec,
        metrics=metrics_cfg,
        search=search,
        execution=execution,
        results=results,
        source_path=yaml_path,
    )


def _validate_objective(objective: str, metrics: MetricsConfig) -> None:
    names = {m.id for m in metrics.objective_metrics}
    if objective not in names:
        raise ValueError(
            f"Suite objective {objective!r} is not declared in metrics.yaml "
            f"objective_metrics. Known: {sorted(names)}"
        )


def _coerce_tool_mode(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).lower()
    if value in {"subprocess", "in_process"}:
        return value
    raise ValueError(f"override_tool_mode must be 'subprocess' or 'in_process', got {value!r}")


def _resolve_optional_path(value: Any, base: Path) -> Path | None:
    if value is None:
        return None
    return (base / str(value)).resolve()


__all__ = ["ExecutionConfig", "ResultsConfig", "SearchConfig", "SuiteConfig", "load_suite"]
