"""Direct failure-path tests for ``sweep/evaluation.py`` (F-22).

These pin the *current* behaviour of ``evaluate_trial`` so the F-08 narrowing
(02-05) — which adds a ``non_fatal_failures`` count to ``EvaluationOutput`` —
has a regression anchor. Assertions therefore check specific fields and never
do a whole-dataclass equality, so an ADDED field stays tolerated.

The covered paths are: parser-raises -> ``prediction=None`` while trial scalars
survive; one metric raises -> it is skipped while the others still produce
values; an objective metric returns a non-scalar -> warning + skip; the
``needs``-based kwarg assembly injects only the declared inputs; and
``_gt_kind_matches`` filters metrics by ground-truth kind.

All metric/parser callables are defined in-test (no plugin install): the
registry is a tiny stub that maps a ``MetricDefinition.id`` to a local
callable, so we exercise the real ``evaluate_trial`` glue without resolving
dotted paths.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from geodispbench3d.dataset.schema import CaseSpec, GroundTruthSpec
from geodispbench3d.metrics.registry import (
    MetricDefinition,
    MetricRegistry,
    MetricsConfig,
)
from geodispbench3d.sweep.evaluation import evaluate_trial
from geodispbench3d.tool.base import TrialOutputs, TrialResult


class _StubRegistry(MetricRegistry):
    """A ``MetricRegistry`` that resolves by definition id, not dotted fn.

    Subclasses the real registry so it is type-compatible with
    ``evaluate_trial(registry=...)`` while letting tests inject in-process
    callables without resolving any dotted-path import.
    """

    def __init__(self, fns: dict[str, Callable[..., Any]]) -> None:
        self._fns = fns

    def resolve(self, definition: MetricDefinition) -> Callable[..., Any]:
        return self._fns[definition.id]


def _trial_result(
    tmp_path: Path,
    *,
    scalar: dict[str, float] | None = None,
    duration: float = 1.0,
    success: bool = True,
) -> TrialResult:
    return TrialResult(
        outputs=TrialOutputs(run_dir=tmp_path),
        scalar_metrics=scalar or {},
        duration_seconds=duration,
        success=success,
    )


def _objdef(
    id_: str,
    *,
    needs: tuple[str, ...] = ("prediction",),
    gt_kinds: tuple[str, ...] = (),
    params: dict[str, Any] | None = None,
) -> MetricDefinition:
    return MetricDefinition(
        id=id_,
        fn=f"stub:{id_}",
        needs=needs,
        gt_kinds=gt_kinds,
        params=params or {},
    )


# --- (a) parser raises -> prediction None, trial scalars survive ------------


def test_parser_failure_yields_none_prediction_and_keeps_trial_scalars(
    tmp_path: Path,
) -> None:
    def boom_parser(**_: Any) -> Any:
        raise RuntimeError("parser exploded")

    out = evaluate_trial(
        trial_result=_trial_result(tmp_path, scalar={"wallclock_runtime": 2.5}),
        parameters={},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(),
        registry=_StubRegistry({}),
        output_parser=boom_parser,
    )

    assert out.prediction is None
    # The adapter-reported trial scalar is still reported despite the parser fail.
    assert out.scalar_metrics["wallclock_runtime"] == 2.5


# --- (b) one metric raises -> skipped, others survive -----------------------


def test_metric_raise_is_skipped_while_others_survive(tmp_path: Path) -> None:
    def good(**_: Any) -> float:
        return 0.5

    def bad(**_: Any) -> float:
        raise ValueError("nope")

    out = evaluate_trial(
        trial_result=_trial_result(tmp_path),
        parameters={},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(objective_metrics=(_objdef("good"), _objdef("bad"))),
        registry=_StubRegistry({"good": good, "bad": bad}),
        prediction_override={"per_point": []},
    )

    assert out.scalar_metrics["good"] == 0.5
    assert "bad" not in out.scalar_metrics


# --- (c) objective metric returns non-scalar -> warning + skip --------------


def test_objective_metric_non_scalar_is_warned_and_skipped(tmp_path: Path, caplog: Any) -> None:
    def listy(**_: Any) -> Any:
        # float([1.0, 2.0]) raises TypeError -> the non-scalar branch.
        return [1.0, 2.0]

    with caplog.at_level(logging.WARNING, logger="geodispbench3d.sweep.evaluation"):
        out = evaluate_trial(
            trial_result=_trial_result(tmp_path),
            parameters={},
            case=CaseSpec(name="c", scans=()),
            metrics=MetricsConfig(objective_metrics=(_objdef("listy"),)),
            registry=_StubRegistry({"listy": listy}),
            prediction_override={},
        )

    assert "listy" not in out.scalar_metrics
    assert "non-scalar" in caplog.text


# --- (d) needs-based kwarg assembly -----------------------------------------


def test_needs_controls_injected_kwargs(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def capture(**kwargs: Any) -> float:
        captured.update(kwargs)
        return 1.0

    evaluate_trial(
        trial_result=_trial_result(tmp_path),
        parameters={},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(
            objective_metrics=(_objdef("cap", needs=("prediction",), params={"radius": 5}),)
        ),
        registry=_StubRegistry({"cap": capture}),
        prediction_override={"p": True},
    )

    # Only the declared input plus the static param are injected.
    assert set(captured) == {"prediction", "radius"}
    assert captured["prediction"] == {"p": True}
    assert captured["radius"] == 5


def test_empty_needs_injects_all_inputs(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def capture(**kwargs: Any) -> float:
        captured.update(kwargs)
        return 1.0

    evaluate_trial(
        trial_result=_trial_result(tmp_path),
        parameters={},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(objective_metrics=(_objdef("cap", needs=()),)),
        registry=_StubRegistry({"cap": capture}),
        prediction_override="P",
    )

    assert set(captured) == {"prediction", "ground_truth", "trial_meta", "case_meta"}


# --- (e) _gt_kind_matches filtering -----------------------------------------


def test_gt_kind_filter_runs_matching_and_skips_nonmatching(tmp_path: Path) -> None:
    def one(**_: Any) -> float:
        return 1.0

    case = CaseSpec(
        name="c",
        scans=(),
        ground_truth=GroundTruthSpec(
            kind="point_displacements",
            inline={"points": [{"label": "A", "xyz_epoch1": [0, 0, 0], "xyz_epoch2": [0.1, 0, 0]}]},
        ),
    )

    out = evaluate_trial(
        trial_result=_trial_result(tmp_path),
        parameters={},
        case=case,
        metrics=MetricsConfig(
            objective_metrics=(
                _objdef("match", gt_kinds=("point_displacements",)),
                _objdef("nomatch", gt_kinds=("dense_flow",)),
            ),
            # A record metric whose gt_kind does not match is also filtered out.
            record_metrics=(_objdef("rec_nomatch", gt_kinds=("dense_flow",)),),
        ),
        registry=_StubRegistry({"match": one, "nomatch": one, "rec_nomatch": one}),
        prediction_override={},
    )

    assert out.scalar_metrics["match"] == 1.0
    assert "nomatch" not in out.scalar_metrics
    # The non-matching record metric produced no rows.
    assert out.record_rows == []


def test_gt_kinds_required_but_case_has_no_gt_is_skipped(tmp_path: Path) -> None:
    out = evaluate_trial(
        trial_result=_trial_result(tmp_path),
        parameters={},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(
            objective_metrics=(_objdef("needs_gt", gt_kinds=("point_displacements",)),)
        ),
        registry=_StubRegistry({"needs_gt": lambda **_: 1.0}),
        prediction_override={},
    )

    assert "needs_gt" not in out.scalar_metrics


# --- happy path: parser + objective + record metrics ------------------------


def test_record_metrics_and_parser_happy_path(tmp_path: Path) -> None:
    def parser(
        *, outputs: Any, ground_truth: Any, parameters: Any, options: Any, logger: Any
    ) -> Any:
        return {"per_point": [{"label": "A"}]}

    def obj(**_: Any) -> float:
        return 0.25

    def rec_mapping(**_: Any) -> Any:
        return {"value": 1}

    def rec_seq(**_: Any) -> Any:
        # The non-Mapping entry is filtered out by evaluate_trial.
        return [{"value": 2}, "skip-me", {"value": 3}]

    out = evaluate_trial(
        trial_result=_trial_result(tmp_path, scalar={"wallclock": 1.0}),
        parameters={"alpha": 1},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(
            objective_metrics=(_objdef("obj"),),
            record_metrics=(_objdef("rmap"), _objdef("rseq")),
        ),
        registry=_StubRegistry({"obj": obj, "rmap": rec_mapping, "rseq": rec_seq}),
        output_parser=parser,
        record_extras={"trial": 7},
    )

    assert out.prediction == {"per_point": [{"label": "A"}]}
    assert out.scalar_metrics["obj"] == 0.25
    assert out.scalar_metrics["wallclock"] == 1.0
    # rmap -> 1 row, rseq -> 2 valid rows (the str is filtered).
    assert len(out.record_rows) == 3
    assert all(r["trial"] == 7 for r in out.record_rows)
    assert {r["metric"] for r in out.record_rows} == {"rmap", "rseq"}


def test_metric_returning_none_is_skipped_no_parser_no_override(tmp_path: Path) -> None:
    # No parser and no override -> prediction stays None (the else branch).
    out = evaluate_trial(
        trial_result=_trial_result(tmp_path),
        parameters={},
        case=CaseSpec(name="c", scans=()),
        metrics=MetricsConfig(
            objective_metrics=(_objdef("nobj"),),
            record_metrics=(_objdef("nrec"),),
        ),
        registry=_StubRegistry({"nobj": lambda **_: None, "nrec": lambda **_: None}),
    )

    assert out.prediction is None
    assert out.scalar_metrics == {}
    assert out.record_rows == []
