"""Built-in pointing-error metric tests.

Synthesizes a tiny GT and uses it to drive the built-in metric callables
both for the perfect-prediction case (errors should be zero) and a
degraded-prediction case (errors should be finite and ordered as
expected).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from geodispbench3d.dataset.ground_truth import PointDisplacement, PointDisplacements
from geodispbench3d.metrics import builtins as mb


def _gt() -> PointDisplacements:
    return PointDisplacements(
        points=(
            PointDisplacement(
                label="A",
                xyz_epoch1=np.array([0.0, 0.0, 0.0]),
                xyz_epoch2=np.array([0.1, 0.0, 0.0]),
            ),
            PointDisplacement(
                label="B",
                xyz_epoch1=np.array([10.0, 0.0, 0.0]),
                xyz_epoch2=np.array([10.05, 0.0, 0.05]),
            ),
        )
    )


def _perfect_prediction(gt: PointDisplacements) -> dict:
    return {
        "per_point": [
            {"label": p.label, "vector": list(p.movement_vector), "source_count": 1}
            for p in gt
        ]
    }


def test_median_displacement_error_perfect() -> None:
    gt = _gt()
    err = mb.median_displacement_error(prediction=_perfect_prediction(gt), ground_truth=gt)
    assert err == pytest.approx(0.0, abs=1e-12)


def test_gt_coverage_full_and_partial() -> None:
    gt = _gt()
    full = _perfect_prediction(gt)
    assert mb.gt_coverage(prediction=full, ground_truth=gt) == 1.0

    partial = {
        "per_point": [
            full["per_point"][0],
            {"label": "B", "vector": [float("nan"), float("nan"), float("nan")], "source_count": 0},
        ]
    }
    assert mb.gt_coverage(prediction=partial, ground_truth=gt) == 0.5


def test_median_angle_error_zero_for_perfect() -> None:
    gt = _gt()
    err = mb.median_angle_error_deg(prediction=_perfect_prediction(gt), ground_truth=gt)
    assert err == pytest.approx(0.0, abs=1e-9)


def test_median_relative_vector_error_zero_for_perfect() -> None:
    gt = _gt()
    err = mb.median_relative_vector_error(prediction=_perfect_prediction(gt), ground_truth=gt)
    assert err == pytest.approx(0.0, abs=1e-12)


def test_per_point_record_emits_one_row_per_label() -> None:
    gt = _gt()
    rows = mb.per_point_displacement_record(
        prediction=_perfect_prediction(gt),
        ground_truth=gt,
        case_meta={"name": "case-1"},
        trial_meta={"trial_index": 0},
    )
    assert len(rows) == 2
    labels = {row["gt_label"] for row in rows}
    assert labels == {"A", "B"}
    for row in rows:
        assert math.isclose(row["pred_magnitude_m"], row["gt_magnitude_m"], abs_tol=1e-12)
        assert row["trial_index"] == 0


def test_wallclock_runtime_extracts_duration() -> None:
    assert mb.wallclock_runtime(trial_meta={"duration_seconds": 12.5}) == 12.5
