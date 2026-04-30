"""Parse iof3D run outputs and sample displacements at ground-truth points.

iof3D's :func:`run_flow_pipeline` writes a set of leaf-tile PLY files to
``<run_dir>/leaf_pointclouds/`` (and optionally merged PLYs alongside). Each
PLY carries scalar fields ``delta_x``, ``delta_y``, ``delta_z``, ``magnitude``
attached by :mod:`iof3D.v2.integrations.flow.reproject` — i.e. the predicted
3D displacement vector at every reprojected source point.

The parser is symmetric to the F2S3 one: load each PLY via pchandler, merge,
sample within ``sample_radius_m`` of each GT epoch-1 position, and aggregate
the displacement vector across sampled points (component-wise median by
default). The result is the ``{per_point: [...]}`` shape consumed by the
shared pointing-error metrics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from pchandler import PointCloudData, load_file
from pchandler.filters import SphereFilter

from geodispbench3d.dataset.ground_truth import (
    PointDisplacement,
    PointDisplacements,
)
from geodispbench3d.tool.base import TrialOutputs


DEFAULT_SAMPLE_RADIUS_M = 15.0
DEFAULT_AGGREGATION = "median"
LEAF_SUBDIR = "leaf_pointclouds"


def parse_iof3d_output(
    *,
    outputs: TrialOutputs,
    ground_truth: PointDisplacements,
    options: Mapping[str, Any] | None = None,
    logger: logging.Logger | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Read iof3D leaf-pointcloud outputs and sample at GT points.

    The trial's ``outputs.predictions`` already contains the leaf paths
    (populated by the iof3D adapter). If that is empty for any reason, fall
    back to globbing ``<run_dir>/leaf_pointclouds/*.ply``.
    """

    options = dict(options or {})
    radius = float(options.get("sample_radius_m", DEFAULT_SAMPLE_RADIUS_M))
    aggregation = str(options.get("aggregation", DEFAULT_AGGREGATION)).lower()
    log = logger or logging.getLogger("geodispbench3d_iof3d.parser")

    leaf_paths = _collect_leaf_paths(outputs)
    if not leaf_paths:
        log.warning(
            "iof3D produced no leaf PLYs under %s — returning empty prediction",
            outputs.run_dir,
        )
        return _empty_prediction(ground_truth)

    merged = _load_and_merge_leaves(leaf_paths, log)
    if merged is None or merged.nbPoints == 0:
        log.warning("iof3D leaf PLYs contained no usable points (%d files)", len(leaf_paths))
        return _empty_prediction(ground_truth)

    per_point = [
        _sample_at_label(merged, gt, radius=radius, aggregation=aggregation)
        for gt in ground_truth
    ]

    return {
        "per_point": per_point,
        "source": {
            "tool": "iof3d",
            "run_dir": str(outputs.run_dir),
            "n_leaves": len(leaf_paths),
            "n_points_total": int(merged.nbPoints),
            "sample_radius_m": radius,
            "aggregation": aggregation,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_leaf_paths(outputs: TrialOutputs) -> list[Path]:
    """Pull leaf-pointcloud paths from the trial outputs (or fall back to glob)."""

    declared = [Path(p) for p in outputs.predictions if Path(p).suffix.lower() == ".ply"]
    leaf_declared = [p for p in declared if LEAF_SUBDIR in p.parts]
    if leaf_declared:
        return sorted(leaf_declared)
    if declared:
        return sorted(declared)
    leaf_dir = Path(outputs.run_dir) / LEAF_SUBDIR
    if leaf_dir.is_dir():
        return sorted(leaf_dir.glob("*.ply"))
    return []


def _load_and_merge_leaves(
    leaf_paths: list[Path], logger: logging.Logger
) -> PointCloudData | None:
    pcds: list[PointCloudData] = []
    for path in leaf_paths:
        try:
            pcd = load_file(path)
        except Exception:
            logger.warning("Skipping unreadable iof3D leaf: %s", path, exc_info=True)
            continue
        if pcd.nbPoints > 0:
            pcds.append(pcd)
    if not pcds:
        return None
    if len(pcds) == 1:
        return pcds[0]
    return PointCloudData.merge(*pcds)


def _sample_at_label(
    pcd: PointCloudData,
    gt: PointDisplacement,
    *,
    radius: float,
    aggregation: str,
) -> dict[str, Any]:
    sphere = SphereFilter(sphere_center=gt.xyz_epoch1, radius=radius)
    sampled = sphere.sample(pcd)
    n = int(sampled.nbPoints)
    if n == 0:
        return {
            "label": gt.label,
            "vector": [float("nan"), float("nan"), float("nan")],
            "source_count": 0,
        }

    sf = sampled.scalar_fields
    if not all(name in sf for name in ("delta_x", "delta_y", "delta_z")):
        return {
            "label": gt.label,
            "vector": [float("nan"), float("nan"), float("nan")],
            "source_count": n,
        }

    vectors = np.column_stack(
        [
            np.asarray(sf["delta_x"], dtype=float),
            np.asarray(sf["delta_y"], dtype=float),
            np.asarray(sf["delta_z"], dtype=float),
        ]
    )
    aggregated = _aggregate(vectors, aggregation)
    return {
        "label": gt.label,
        "vector": [float(v) for v in aggregated],
        "source_count": n,
    }


def _aggregate(vectors: np.ndarray, mode: str) -> np.ndarray:
    if mode == "median":
        return np.nanmedian(vectors, axis=0)
    if mode == "mean":
        return np.nanmean(vectors, axis=0)
    raise ValueError(f"Unknown aggregation mode {mode!r}; expected 'median' or 'mean'")


def _empty_prediction(ground_truth: PointDisplacements) -> dict[str, Any]:
    return {
        "per_point": [
            {
                "label": gt.label,
                "vector": [float("nan"), float("nan"), float("nan")],
                "source_count": 0,
            }
            for gt in ground_truth
        ],
        "source": {"n_leaves": 0, "n_points_total": 0},
    }


__all__ = ["parse_iof3d_output"]
