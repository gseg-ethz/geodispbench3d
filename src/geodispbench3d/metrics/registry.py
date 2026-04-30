"""metrics.yaml schema, loader, and function resolver.

A metrics.yaml has two top-level lists:

* ``objective_metrics`` — scalar metrics eligible to be the Ax objective.
* ``record_metrics`` — structured-row metrics that feed the results
  persistence layer (parquet / duckdb / dashboard).

Each entry references a Python callable via an entry-point-style path
(``package.module:function``), declares what inputs it ``needs``
(``prediction``, ``ground_truth``, ``trial_meta``, ``case_meta``), and may
constrain itself to specific GT kinds via ``gt_kinds``.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from omegaconf import OmegaConf


@dataclass(frozen=True)
class MetricDefinition:
    """One entry from metrics.yaml."""

    id: str
    fn: str  # "package.module:function"
    needs: Sequence[str] = ()
    gt_kinds: Sequence[str] = ()
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricsConfig:
    """Composite metrics.yaml content."""

    objective_metrics: Sequence[MetricDefinition] = ()
    record_metrics: Sequence[MetricDefinition] = ()

    def all(self) -> Sequence[MetricDefinition]:
        return tuple(self.objective_metrics) + tuple(self.record_metrics)


class MetricRegistry:
    """Cached resolver for metric callables.

    Keeps imported callables around so repeated trials don't re-import.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Callable[..., Any]] = {}

    def resolve(self, definition: MetricDefinition) -> Callable[..., Any]:
        if definition.fn not in self._cache:
            self._cache[definition.fn] = resolve_metric_fn(definition.fn)
        return self._cache[definition.fn]


def resolve_metric_fn(entry: str) -> Callable[..., Any]:
    """Resolve a ``"package.module:function"`` string to a callable."""

    if ":" not in entry:
        raise ValueError(
            f"Metric fn reference must be 'package.module:function', got {entry!r}"
        )
    module_path, attr = entry.split(":", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, attr, None)
    if fn is None or not callable(fn):
        raise ImportError(f"Cannot resolve metric callable {entry!r}")
    return fn  # type: ignore[return-value]


def load_metrics_config(path: str | Path) -> MetricsConfig:
    """Load a metrics.yaml."""

    yaml_path = Path(path).resolve()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Metrics YAML not found: {yaml_path}")

    raw = OmegaConf.to_container(OmegaConf.load(str(yaml_path)), resolve=True)
    if not isinstance(raw, dict):
        raise ValueError(f"Metrics YAML at {yaml_path} must be a mapping")

    return MetricsConfig(
        objective_metrics=tuple(_load_defs(raw.get("objective_metrics") or [])),
        record_metrics=tuple(_load_defs(raw.get("record_metrics") or [])),
    )


def _load_defs(raw_list: Sequence[Mapping[str, Any]]) -> list[MetricDefinition]:
    out: list[MetricDefinition] = []
    for entry in raw_list:
        out.append(
            MetricDefinition(
                id=str(entry["id"]),
                fn=str(entry["fn"]),
                needs=tuple(entry.get("needs") or ()),
                gt_kinds=tuple(entry.get("gt_kinds") or ()),
                params=dict(entry.get("params") or {}),
            )
        )
    return out


__all__ = [
    "MetricDefinition",
    "MetricRegistry",
    "MetricsConfig",
    "load_metrics_config",
    "resolve_metric_fn",
]
