"""suite.yaml loader.

A suite is the top-level configuration a user hands to ``geodispbench3d run``.
It references a tool, a dataset, a metrics file, and a search config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

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


@dataclass(frozen=True)
class ResultsConfig:
    parquet_path: Path | None = None
    run_dir_root: Path | None = None


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
        raise ValueError(
            f"Suite {yaml_path} must reference 'tool', 'dataset', and 'metrics'"
        )

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
    results = ResultsConfig(
        parquet_path=_resolve_optional_path(results_raw.get("parquet_path"), base),
        run_dir_root=_resolve_optional_path(results_raw.get("run_dir_root"), base),
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
