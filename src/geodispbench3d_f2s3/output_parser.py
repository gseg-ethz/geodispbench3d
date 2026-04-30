"""Parse F2S3 output and sample displacements at ground-truth points.

F2S3 writes one ASCII text file per tile under either
``<run_dir>/output/`` or ``<run_dir>/output/refined_results/`` (depending on
whether ``--refine_results`` was set). Each file has 7 whitespace-separated
columns in scientific notation, with no header::

    X1  Y1  Z1  X2  Y2  Z2  magnitude

Where ``(X1, Y1, Z1)`` is the source-cloud position, ``(X2, Y2, Z2)`` the
predicted target-cloud position, and ``magnitude`` the displacement vector
length. The displacement vector at a point is ``(X2 - X1, Y2 - Y1, Z2 - Z1)``.

Sampling at GT points uses a fixed-radius sphere (default 15 m) around each
GT label's epoch-1 position; the displacement vector is aggregated across
sampled points by component-wise median (the same approach used historically
by ``iof3D_analysis.results.metrics.process_gt_samples``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from pchandler import PointCloudData
from pchandler.data_io import Csv
from pchandler.filters import SphereFilter

from geodispbench3d.dataset.ground_truth import (
    PointDisplacement,
    PointDisplacements,
)
from geodispbench3d.tool.base import TrialOutputs


F2S3_COLUMNS = ["x", "y", "z", "x2", "y2", "z2", "magnitude"]
DEFAULT_SAMPLE_RADIUS_M = 15.0
DEFAULT_AGGREGATION = "median"


def parse_f2s3_output(
    *,
    outputs: TrialOutputs,
    ground_truth: PointDisplacements,
    options: Mapping[str, Any] | None = None,
    logger: logging.Logger | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Read F2S3 outputs and produce a sampled-at-GT prediction object.

    Returns a dict shaped ``{per_point: [{label, vector, source_count}, ...]}``,
    matching what the built-in pointing-error metrics consume. Labels with no
    samples within the search radius emit a NaN vector (counted as missing
    coverage by ``gt_coverage``).
    """

    options = dict(options or {})
    radius = float(options.get("sample_radius_m", DEFAULT_SAMPLE_RADIUS_M))
    aggregation = str(options.get("aggregation", DEFAULT_AGGREGATION)).lower()
    use_refined = bool(options.get("prefer_refined", True))
    log = logger or logging.getLogger("geodispbench3d_f2s3.parser")

    tile_dir = _locate_tile_dir(outputs.run_dir, prefer_refined=use_refined, logger=log)
    if tile_dir is None:
        log.warning(
            "F2S3 output directory not found under %s — returning empty prediction.",
            outputs.run_dir,
        )
        return _empty_prediction(ground_truth)

    merged = _load_and_merge_tiles(tile_dir, log)
    if merged is None or merged.nbPoints == 0:
        log.warning("F2S3 produced no usable output points under %s", tile_dir)
        return _empty_prediction(ground_truth)

    per_point = [
        _sample_at_label(merged, gt_point, radius=radius, aggregation=aggregation)
        for gt_point in ground_truth
    ]

    return {
        "per_point": per_point,
        "source": {
            "tile_dir": str(tile_dir),
            "n_tiles": _tile_count(tile_dir),
            "n_points_total": int(merged.nbPoints),
            "sample_radius_m": radius,
            "aggregation": aggregation,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _locate_tile_dir(
    run_dir: Path,
    *,
    prefer_refined: bool,
    logger: logging.Logger,
) -> Path | None:
    output_dir = Path(run_dir) / "output"
    refined_dir = output_dir / "refined_results"

    candidates: list[Path] = []
    if prefer_refined:
        candidates.extend([refined_dir, output_dir])
    else:
        candidates.extend([output_dir, refined_dir])

    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.txt")):
            logger.debug("F2S3 tile dir resolved to %s", candidate)
            return candidate
    return None


def _tile_count(tile_dir: Path) -> int:
    return len(list(tile_dir.glob("*.txt")))


def _load_and_merge_tiles(tile_dir: Path, logger: logging.Logger) -> PointCloudData | None:
    tile_files = sorted(tile_dir.glob("*.txt"))
    if not tile_files:
        return None

    pcds: list[PointCloudData] = []
    for tile_path in tile_files:
        try:
            pcd = _load_f2s3_tile(tile_path)
        except Exception:
            logger.warning("Skipping unreadable F2S3 tile: %s", tile_path, exc_info=True)
            continue
        if pcd.nbPoints > 0:
            pcds.append(pcd)

    if not pcds:
        return None
    if len(pcds) == 1:
        return pcds[0]
    return PointCloudData.merge(*pcds)


def _load_f2s3_tile(tile_path: Path) -> PointCloudData:
    """Load one F2S3 tile via pchandler's CSV/ASCII handler.

    The first three columns become the canonical XYZ; the remaining four are
    attached as scalar fields ``x2``, ``y2``, ``z2``, ``magnitude``.
    """

    return Csv.load(
        tile_path,
        scalar_fields=F2S3_COLUMNS,
        column_names_row=-1,  # no header line; field names supplied explicitly
        delimiter=None,  # let the sniffer detect whitespace
        comment="//",
    )


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
    if not all(name in sf for name in ("x2", "y2", "z2")):
        return {
            "label": gt.label,
            "vector": [float("nan"), float("nan"), float("nan")],
            "source_count": n,
        }

    src_xyz = np.asarray(sampled.xyz, dtype=float)
    tgt_xyz = np.column_stack(
        [
            np.asarray(sf["x2"], dtype=float),
            np.asarray(sf["y2"], dtype=float),
            np.asarray(sf["z2"], dtype=float),
        ]
    )
    vectors = tgt_xyz - src_xyz
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
        "source": {"n_tiles": 0, "n_points_total": 0},
    }


__all__ = ["parse_f2s3_output", "F2S3_COLUMNS"]
