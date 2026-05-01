"""``analysis.yaml`` schema and loader.

An analysis YAML composes a dataset + a metrics file with a set of
*cached predictions*. There is no tool reference: predictions are tool-
agnostic by the time they reach the cache, so the analysis verb can mix
runs from any number of tools in a single parquet output.

Three ways to point at predictions, mix-and-match in any combination:

  predictions:
    - path: <abs/relative.json>          # explicit single file
    - glob: <pattern>                    # any pattern resolved relative
                                         # to the analysis YAML
    - root: <dir>                        # walk the cache layout under
      filter:                            # this root, optionally
        tool_id: iof3d-v2                # filtering by provenance
        dataset_id: mattertal            # segment. Each filter is
        case: mattertal-all              # optional.

Resolution returns a flat list of prediction file paths in the order
declared (with glob results sorted lexicographically).
"""

from __future__ import annotations

import glob as _glob
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

from geodispbench3d.dataset.schema import DatasetSpec, load_dataset
from geodispbench3d.metrics.registry import MetricsConfig, load_metrics_config
from geodispbench3d.results.predictions_cache import find_predictions


@dataclass(frozen=True)
class PredictionFilter:
    """Provenance filter for a ``root:`` entry in ``predictions:``.

    Each ``None`` field matches any value in that segment of the cache
    layout (``<root>/<tool_id>/<dataset_id>/<case>/<run_hash>.json``).
    """

    tool_id: str | None = None
    dataset_id: str | None = None
    case: str | None = None


@dataclass(frozen=True)
class PredictionRef:
    """One source of predictions to consume.

    Exactly one of ``path``, ``glob``, or ``root`` is populated. The
    loader normalises everything to an iterable of resolved Path objects
    via :meth:`resolve`.
    """

    path: Path | None = None
    glob: str | None = None
    root: Path | None = None
    filter: PredictionFilter = field(default_factory=PredictionFilter)

    def resolve(self) -> list[Path]:
        if self.path is not None:
            return [self.path] if self.path.is_file() else []
        if self.glob is not None:
            return sorted(Path(p) for p in _glob.glob(self.glob, recursive=True))
        if self.root is not None:
            return find_predictions(
                self.root,
                tool_id=self.filter.tool_id,
                dataset_id=self.filter.dataset_id,
                case=self.filter.case,
            )
        return []


@dataclass(frozen=True)
class PredictionsConfig:
    """The ``predictions:`` block plus an aggregate resolver."""

    refs: Sequence[PredictionRef] = ()

    def resolve_all(self) -> list[Path]:
        seen: set[Path] = set()
        ordered: list[Path] = []
        for ref in self.refs:
            for path in ref.resolve():
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                ordered.append(resolved)
        return ordered


@dataclass(frozen=True)
class ResultsConfig:
    parquet_path: Path | None = None


@dataclass(frozen=True)
class AnalysisConfig:
    """Composite analysis definition with all referenced configs loaded."""

    id: str
    dataset: DatasetSpec
    metrics: MetricsConfig
    predictions: PredictionsConfig
    results: ResultsConfig = field(default_factory=ResultsConfig)
    pass_id: str | None = None
    source_path: Path | None = None


def load_analysis(path: str | Path) -> AnalysisConfig:
    """Load an ``analysis.yaml`` and resolve its references."""

    yaml_path = Path(path).resolve()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Analysis YAML not found: {yaml_path}")

    raw = OmegaConf.to_container(OmegaConf.load(str(yaml_path)), resolve=True)
    if not isinstance(raw, dict):
        raise ValueError(f"Analysis YAML at {yaml_path} must be a mapping")

    base = yaml_path.parent

    dataset_ref = raw.get("dataset")
    metrics_ref = raw.get("metrics")
    if not (dataset_ref and metrics_ref):
        raise ValueError(f"Analysis {yaml_path} must reference 'dataset' and 'metrics'")

    dataset_spec = load_dataset(_resolve_path(dataset_ref, base))
    metrics_cfg = load_metrics_config(_resolve_path(metrics_ref, base))

    predictions_raw = raw.get("predictions") or []
    if not isinstance(predictions_raw, list):
        raise ValueError(f"Analysis {yaml_path}: 'predictions' must be a list")
    refs = tuple(_load_prediction_ref(entry, base) for entry in predictions_raw)
    if not refs:
        raise ValueError(f"Analysis {yaml_path}: at least one prediction source required")

    results_raw = raw.get("results") or {}
    results = ResultsConfig(
        parquet_path=_resolve_optional_path(results_raw.get("parquet_path"), base),
    )

    return AnalysisConfig(
        id=str(raw.get("id", yaml_path.stem)),
        dataset=dataset_spec,
        metrics=metrics_cfg,
        predictions=PredictionsConfig(refs=refs),
        results=results,
        pass_id=raw.get("pass_id"),
        source_path=yaml_path,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _load_prediction_ref(entry: Mapping[str, Any], base: Path) -> PredictionRef:
    if "path" in entry:
        return PredictionRef(path=_resolve_path(entry["path"], base))
    if "glob" in entry:
        # Resolve relative to the analysis YAML's directory.
        pattern = str(entry["glob"])
        if not Path(pattern).is_absolute():
            pattern = str(base / pattern)
        return PredictionRef(glob=pattern)
    if "root" in entry:
        flt = entry.get("filter") or {}
        return PredictionRef(
            root=_resolve_path(entry["root"], base),
            filter=PredictionFilter(
                tool_id=flt.get("tool_id"),
                dataset_id=flt.get("dataset_id"),
                case=flt.get("case"),
            ),
        )
    raise ValueError(
        f"predictions entry must declare one of 'path', 'glob', or 'root', got {dict(entry)!r}"
    )


def _resolve_path(value: Any, base: Path) -> Path:
    p = Path(str(value))
    return p if p.is_absolute() else (base / p).resolve()


def _resolve_optional_path(value: Any, base: Path) -> Path | None:
    if value is None:
        return None
    return _resolve_path(value, base)


__all__ = [
    "AnalysisConfig",
    "PredictionFilter",
    "PredictionRef",
    "PredictionsConfig",
    "ResultsConfig",
    "load_analysis",
]
