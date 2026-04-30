"""Built-in metric functions.

Each function takes keyword arguments matching its declared ``needs`` in
metrics.yaml. The runner injects the inputs by name; metrics that do not need
a particular input simply omit it from their signature.

Two categories of metric live here today:

* **Scalar metrics** — return a single ``float``; eligible to be the Ax
  objective. Examples: ``wallclock_runtime``, ``median_displacement_error``.
* **Record metrics** — return a list of dicts (one row per case × GT entry);
  feed the parquet/duckdb/dashboard pipeline.

Both kinds share a uniform signature (kwargs in, JSON-friendly out) so the
sweep runner can dispatch on metrics.yaml entries without adapter-specific
glue.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Scalar metrics
# ---------------------------------------------------------------------------


def wallclock_runtime(*, trial_meta: Mapping[str, Any], **_: Any) -> float:
    """Return the trial wallclock duration in seconds."""

    return float(trial_meta.get("duration_seconds", float("nan")))


def median_displacement_error(
    *,
    prediction: Mapping[str, Any],
    ground_truth: Any,
    **_: Any,
) -> float:
    """Median Euclidean error between predicted and ground-truth displacements.

    ``prediction`` must expose ``per_point`` — a sequence of dicts with
    ``label`` and ``vector`` (3-element). ``ground_truth`` is a
    :class:`~geodispbench3d.dataset.ground_truth.PointDisplacements`-like
    iterable.
    """

    gt_by_label = {p.label: p.movement_vector for p in ground_truth}
    errors: list[float] = []
    for entry in prediction.get("per_point", []):
        label = entry.get("label")
        gt_vec = gt_by_label.get(label)
        if gt_vec is None:
            continue
        pred_vec = np.asarray(entry["vector"], dtype=float)
        errors.append(float(np.linalg.norm(pred_vec - gt_vec)))
    if not errors:
        return float("nan")
    return float(np.nanmedian(errors))


def mean_relative_magnitude_error(
    *,
    prediction: Mapping[str, Any],
    ground_truth: Any,
    **_: Any,
) -> float:
    """Mean of |1 - |pred|/|gt|| across labeled points."""

    gt_by_label = {p.label: p.movement_magnitude for p in ground_truth}
    rels: list[float] = []
    for entry in prediction.get("per_point", []):
        label = entry.get("label")
        gt_mag = gt_by_label.get(label)
        if not gt_mag or gt_mag <= 0:
            continue
        pred_vec = np.asarray(entry["vector"], dtype=float)
        pred_mag = float(np.linalg.norm(pred_vec))
        rels.append(abs(gt_mag - pred_mag) / gt_mag)
    if not rels:
        return float("nan")
    return float(np.nanmean(rels))


def median_angle_error_deg(
    *,
    prediction: Mapping[str, Any],
    ground_truth: Any,
    **_: Any,
) -> float:
    """Median angle (degrees) between predicted and ground-truth vectors.

    Direction-only signal: insensitive to magnitude scaling. Reported in
    degrees; 0 = perfect alignment, 180 = anti-aligned.
    """

    gt_by_label = {p.label: p.movement_vector for p in ground_truth}
    angles: list[float] = []
    for entry in prediction.get("per_point", []):
        label = entry.get("label")
        gt_vec = gt_by_label.get(label)
        if gt_vec is None:
            continue
        pred_vec = np.asarray(entry["vector"], dtype=float)
        denom = float(np.linalg.norm(pred_vec)) * float(np.linalg.norm(gt_vec))
        if denom <= 0:
            continue
        cos = float(np.clip(np.dot(pred_vec, gt_vec) / denom, -1.0, 1.0))
        angles.append(float(np.degrees(np.arccos(cos))))
    if not angles:
        return float("nan")
    return float(np.nanmedian(angles))


def median_relative_vector_error(
    *,
    prediction: Mapping[str, Any],
    ground_truth: Any,
    **_: Any,
) -> float:
    """Median of ||gt - pred|| / ||gt|| across labeled points (RVE).

    Combines magnitude and direction error normalized by the ground-truth
    vector magnitude — scale-invariant, comparable across cases.
    """

    gt_by_label = {p.label: (p.movement_vector, p.movement_magnitude) for p in ground_truth}
    rves: list[float] = []
    for entry in prediction.get("per_point", []):
        label = entry.get("label")
        gt_pair = gt_by_label.get(label)
        if gt_pair is None:
            continue
        gt_vec, gt_mag = gt_pair
        if gt_mag <= 0:
            continue
        pred_vec = np.asarray(entry["vector"], dtype=float)
        rves.append(float(np.linalg.norm(gt_vec - pred_vec) / gt_mag))
    if not rves:
        return float("nan")
    return float(np.nanmedian(rves))


def gt_coverage(
    *,
    prediction: Mapping[str, Any],
    ground_truth: Any,
    **_: Any,
) -> float:
    """Fraction of GT labels for which the tool produced a non-NaN prediction.

    A run that produces sparse output (e.g. heavy filtering) but very accurate
    where it does predict will score well on error metrics; this metric
    surfaces the missing-prediction failure mode.
    """

    gt_labels = {p.label for p in ground_truth}
    if not gt_labels:
        return float("nan")
    covered = 0
    for entry in prediction.get("per_point", []):
        label = entry.get("label")
        if label not in gt_labels:
            continue
        vec = np.asarray(entry["vector"], dtype=float)
        if vec.shape == (3,) and np.all(np.isfinite(vec)):
            covered += 1
    return covered / len(gt_labels)


# ---------------------------------------------------------------------------
# Record metrics (one row per GT label)
# ---------------------------------------------------------------------------


def per_point_displacement_record(
    *,
    prediction: Mapping[str, Any],
    ground_truth: Any,
    case_meta: Mapping[str, Any] | None = None,
    trial_meta: Mapping[str, Any] | None = None,
    **_: Any,
) -> Sequence[Mapping[str, Any]]:
    """Emit one row per labeled GT point with vector + magnitude diagnostics."""

    case_name = (case_meta or {}).get("name", "")
    trial_id = (trial_meta or {}).get("trial_index")

    pred_by_label: dict[str, np.ndarray] = {}
    for entry in prediction.get("per_point", []):
        label = entry.get("label")
        if label is None:
            continue
        pred_by_label[str(label)] = np.asarray(entry["vector"], dtype=float)

    rows: list[Mapping[str, Any]] = []
    for gt in ground_truth:
        label = gt.label
        pred_vec = pred_by_label.get(label)
        gt_vec = gt.movement_vector
        gt_mag = gt.movement_magnitude

        if pred_vec is None:
            rows.append(
                {
                    "case": case_name,
                    "trial_index": trial_id,
                    "gt_label": label,
                    "gt_magnitude_m": gt_mag,
                    "pred_magnitude_m": float("nan"),
                    "magnitude_diff_mm": float("nan"),
                    "angle_deg": float("nan"),
                    "rme": float("nan"),
                    "rve": float("nan"),
                    "cosine_similarity": float("nan"),
                }
            )
            continue

        pred_mag = float(np.linalg.norm(pred_vec))
        denom = gt_mag * pred_mag
        cosine = (
            float(np.clip(np.dot(pred_vec, gt_vec) / denom, -1.0, 1.0))
            if denom > 0
            else float("nan")
        )
        angle_deg = float(np.degrees(np.arccos(cosine))) if denom > 0 else float("nan")
        rme = abs(gt_mag - pred_mag) / gt_mag if gt_mag > 0 else float("nan")
        rve = float(np.linalg.norm(gt_vec - pred_vec)) / gt_mag if gt_mag > 0 else float("nan")

        rows.append(
            {
                "case": case_name,
                "trial_index": trial_id,
                "gt_label": label,
                "gt_magnitude_m": gt_mag,
                "pred_magnitude_m": pred_mag,
                "magnitude_diff_mm": (gt_mag - pred_mag) * 1000.0,
                "angle_deg": angle_deg,
                "rme": rme,
                "rve": rve,
                "cosine_similarity": cosine,
            }
        )
    return rows


__all__ = [
    "gt_coverage",
    "mean_relative_magnitude_error",
    "median_angle_error_deg",
    "median_displacement_error",
    "median_relative_vector_error",
    "per_point_displacement_record",
    "wallclock_runtime",
]
