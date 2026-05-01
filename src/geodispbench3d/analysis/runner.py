"""Analyze runner: score cached predictions against an AnalysisConfig.

Loads each prediction JSON file, picks the matching dataset case from
the analysis config (preferring the case recorded in the prediction's
provenance, falling back to a single-case dataset), and dispatches the
metric registry through :func:`evaluate_trial` with the cached
prediction supplied as ``prediction_override`` so phase 2 is skipped
entirely.

Record rows carry ``mode="analyze"`` plus the prediction's recorded
``tool_id`` / ``dataset_id`` / ``case`` so a single parquet file can
mix runs from multiple tools across multiple analyses without
columns colliding.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from geodispbench3d.dataset.schema import CaseSpec, DatasetSpec
from geodispbench3d.metrics.registry import MetricRegistry
from geodispbench3d.results.predictions_cache import read_prediction
from geodispbench3d.sweep.evaluation import evaluate_trial
from geodispbench3d.tool.base import TrialOutputs, TrialResult

from .loader import AnalysisConfig


@dataclass
class AnalysisSummary:
    """One-line counters returned by :func:`analyze`."""

    total: int = 0
    succeeded: int = 0
    skipped_unreadable: int = 0
    skipped_no_case: int = 0
    rows_emitted: int = 0


def analyze(
    *,
    config: AnalysisConfig,
    on_record_rows: Callable[[Sequence[Mapping[str, Any]]], None] | None = None,
    logger: logging.Logger | None = None,
) -> AnalysisSummary:
    """Score every prediction referenced by ``config`` and emit record rows."""

    log = logger or logging.getLogger("geodispbench3d.analysis")
    summary = AnalysisSummary()
    pass_id = config.pass_id or _utcnow_compact()

    case_index: Mapping[str, CaseSpec] = {c.name: c for c in config.dataset.cases}
    registry = MetricRegistry()

    paths = config.predictions.resolve_all()
    log.info("analyze: %d prediction file(s) to score (pass_id=%s)", len(paths), pass_id)

    for path in paths:
        summary.total += 1
        payload = read_prediction(path)
        if payload is None:
            log.warning("analyze: cannot read %s, skipping", path)
            summary.skipped_unreadable += 1
            continue

        prediction = payload.get("prediction")
        provenance = payload.get("provenance") or {}
        case = _resolve_case(provenance, case_index, config.dataset)
        if case is None:
            log.warning(
                "analyze: cannot map prediction %s to a dataset case (provenance=%s); skipping",
                path,
                provenance.get("dataset"),
            )
            summary.skipped_no_case += 1
            continue

        record_extras = {
            "tool_id": _provenance_id(provenance, "tool"),
            "dataset_id": _provenance_id(provenance, "dataset") or config.dataset.id,
            "case": case.name,
            "trial_index": _provenance_run_hash(provenance, path),
            "mode": "analyze",
            "pass_id": pass_id,
            "prediction_path": str(path),
        }

        trial_result = TrialResult(
            outputs=TrialOutputs(run_dir=Path(provenance.get("run_dir") or path.parent)),
            scalar_metrics={},
            duration_seconds=0.0,
            success=True,
        )

        try:
            evaluation = evaluate_trial(
                trial_result=trial_result,
                parameters={},
                case=case,
                metrics=config.metrics,
                registry=registry,
                output_parser=None,
                output_parser_options=None,
                prediction_override=prediction,
                trial_index=None,
                record_extras=record_extras,
                logger=log,
            )
        except Exception:  # pragma: no cover - defensive
            log.exception("analyze: evaluate_trial raised for %s", path)
            continue

        if on_record_rows and evaluation.record_rows:
            on_record_rows(list(evaluation.record_rows))
            summary.rows_emitted += len(evaluation.record_rows)
        summary.succeeded += 1

    log.info(
        "analyze done: succeeded=%d total=%d unreadable=%d no_case=%d rows=%d",
        summary.succeeded,
        summary.total,
        summary.skipped_unreadable,
        summary.skipped_no_case,
        summary.rows_emitted,
    )
    return summary


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _resolve_case(
    provenance: Mapping[str, Any],
    case_index: Mapping[str, CaseSpec],
    dataset: DatasetSpec,
) -> CaseSpec | None:
    block = provenance.get("dataset")
    if isinstance(block, Mapping):
        name = block.get("case")
        if isinstance(name, str) and name in case_index:
            return case_index[name]
    if len(dataset.cases) == 1:
        return dataset.cases[0]
    return None


def _provenance_id(provenance: Mapping[str, Any], key: str) -> str | None:
    block = provenance.get(key)
    if isinstance(block, Mapping):
        value = block.get("id")
        if isinstance(value, str):
            return value
    return None


def _provenance_run_hash(provenance: Mapping[str, Any], path: Path) -> str:
    """Best-effort identifier for the row's `trial_index` column."""

    run_dir = provenance.get("run_dir")
    if isinstance(run_dir, str) and run_dir:
        return Path(run_dir).name
    return path.stem


def _utcnow_compact() -> str:
    return datetime.utcnow().strftime("analyze-%Y%m%dT%H%M%S")


__all__ = ["AnalysisSummary", "analyze"]
