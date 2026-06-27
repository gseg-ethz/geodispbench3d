"""Glue between a tool's :class:`TrialResult` and the metric registry.

The tool produces raw outputs (a run directory plus possibly a stdout JSON
payload). The dataset provides ground-truth. Metrics declare what they
``need`` (``prediction``, ``ground_truth``, ``trial_meta``, ``case_meta``).
This module assembles those inputs and dispatches each metric's callable,
splitting the results into

* ``scalar_metrics`` — what gets reported back to Ax.
* ``record_rows`` — structured rows persisted to parquet for the dashboard.

Tools whose output is not already in ``{per_point: [...]}`` form attach an
``output_parser`` to their tool config; the parser is invoked here, once per
trial, between the adapter and the metric callables.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from geodispbench3d.dataset.ground_truth import load_ground_truth
from geodispbench3d.dataset.schema import CaseSpec
from geodispbench3d.metrics.registry import (
    MetricDefinition,
    MetricRegistry,
    MetricsConfig,
)
from geodispbench3d.tool.base import TrialResult


@dataclass
class EvaluationOutput:
    """Per-trial evaluation result split by audience.

    ``scalar_metrics`` feeds Ax (only floats survive). ``record_rows`` is a
    flat list of dicts ready to append to a parquet file. ``prediction``
    is the raw phase-2 output from the parser (or ``None`` when the trial
    skipped phase 2 entirely); the runner caches it to disk so future
    ``--rescore`` and ``analyze`` passes can reuse it without re-running
    the parser.

    ``non_fatal_failures`` counts the swallowed (fail-soft) failures inside this
    one evaluation: a parser that raised, a metric callable that raised, and an
    objective metric that returned a non-scalar. Each pass folds this into its
    aggregate non-fatal-failure total (F-08).
    """

    scalar_metrics: Mapping[str, float]
    record_rows: Sequence[Mapping[str, Any]] = field(default_factory=list)
    prediction: Any = None
    non_fatal_failures: int = 0


def evaluate_trial(
    *,
    trial_result: TrialResult,
    parameters: Mapping[str, Any],
    case: CaseSpec,
    metrics: MetricsConfig,
    registry: MetricRegistry,
    output_parser: Callable[..., Any] | None = None,
    output_parser_options: Mapping[str, Any] | None = None,
    prediction_override: Any = None,
    trial_index: int | None = None,
    record_extras: Mapping[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> EvaluationOutput:
    """Run a tool's output through the metric registry for a single case.

    Returns scalar (Ax-bound) metrics and structured record rows. The trial's
    own scalar metrics (e.g. wallclock_runtime from the adapter) are merged
    into ``scalar_metrics`` first; metric callables can override or augment.
    """

    log = logger or logging.getLogger("geodispbench3d.sweep.evaluation")

    # Count of swallowed fail-soft failures within this evaluation (F-08).
    non_fatal_failures = 0

    ground_truth = load_ground_truth(case.ground_truth) if case.ground_truth is not None else None

    # ``prediction_override`` short-circuits phase 2 — the analyze flow
    # passes a cached prediction here instead of re-running the parser.
    if prediction_override is not None:
        prediction: Any = prediction_override
    elif output_parser is not None:
        try:
            prediction = output_parser(
                outputs=trial_result.outputs,
                ground_truth=ground_truth,
                parameters=parameters,
                options=output_parser_options or {},
                logger=log,
            )
        except Exception:
            # Plugin/user callable: a closed exception set is inapplicable (the
            # parser may raise anything). Stay broad so a parser bug degrades to
            # a None prediction instead of crashing the trial (fail-soft, F-08).
            log.exception("Output parser failed for trial in %s", trial_result.outputs.run_dir)
            prediction = None
            non_fatal_failures += 1
    else:
        prediction = None

    trial_meta: dict[str, Any] = {
        "trial_index": trial_index,
        "duration_seconds": trial_result.duration_seconds,
        "success": trial_result.success,
        "run_dir": str(trial_result.outputs.run_dir),
    }
    case_meta: dict[str, Any] = {
        "name": case.name,
        **dict(case.metadata or {}),
    }

    scalar: dict[str, float] = dict(trial_result.scalar_metrics)
    record_rows: list[Mapping[str, Any]] = []

    gt_kind = case.ground_truth.kind if case.ground_truth is not None else None

    for definition in metrics.objective_metrics:
        if not _gt_kind_matches(definition, gt_kind):
            continue
        value, raised = _invoke_metric(
            definition, registry, prediction, ground_truth, trial_meta, case_meta, log
        )
        if raised:
            non_fatal_failures += 1
        if value is None:
            continue
        try:
            scalar[definition.id] = float(value)
        except (TypeError, ValueError):
            log.warning(
                "Objective metric %r returned non-scalar (%r); skipping",
                definition.id,
                value,
            )
            non_fatal_failures += 1

    extras = dict(record_extras or {})

    for definition in metrics.record_metrics:
        if not _gt_kind_matches(definition, gt_kind):
            continue
        value, raised = _invoke_metric(
            definition, registry, prediction, ground_truth, trial_meta, case_meta, log
        )
        if raised:
            non_fatal_failures += 1
        if value is None:
            continue
        rows_for_metric: list[Mapping[str, Any]] = (
            [value] if isinstance(value, Mapping) else [r for r in value if isinstance(r, Mapping)]
        )
        for row in rows_for_metric:
            record_rows.append({**extras, **row, "metric": definition.id})

    return EvaluationOutput(
        scalar_metrics=scalar,
        record_rows=record_rows,
        prediction=prediction,
        non_fatal_failures=non_fatal_failures,
    )


def _gt_kind_matches(definition: MetricDefinition, gt_kind: str | None) -> bool:
    if not definition.gt_kinds:
        return True
    if gt_kind is None:
        return False
    return gt_kind in definition.gt_kinds


def _invoke_metric(
    definition: MetricDefinition,
    registry: MetricRegistry,
    prediction: Any,
    ground_truth: Any,
    trial_meta: Mapping[str, Any],
    case_meta: Mapping[str, Any],
    logger: logging.Logger,
) -> tuple[Any, bool]:
    """Invoke a metric callable, returning ``(value, raised)``.

    ``raised`` is ``True`` only when the callable threw (a fail-soft skip the
    caller counts as a non-fatal failure); a metric that legitimately returns
    ``None`` reports ``(None, False)`` and is not counted (F-08).
    """

    fn = registry.resolve(definition)
    kwargs: dict[str, Any] = dict(definition.params or {})
    needs = set(definition.needs)
    if not needs or "prediction" in needs:
        kwargs["prediction"] = prediction
    if not needs or "ground_truth" in needs:
        kwargs["ground_truth"] = ground_truth
    if not needs or "trial_meta" in needs:
        kwargs["trial_meta"] = trial_meta
    if not needs or "case_meta" in needs:
        kwargs["case_meta"] = case_meta
    try:
        return fn(**kwargs), False
    except Exception:
        # Plugin/user callable: a closed exception set is inapplicable (the
        # metric may raise anything). Stay broad so one metric bug skips that
        # metric instead of crashing the trial (fail-soft, F-08).
        logger.exception("Metric %r raised; skipping", definition.id)
        return None, True


__all__ = ["EvaluationOutput", "evaluate_trial"]
