"""Ground-truth loaders.

The GT system is a simple registry keyed by ``GroundTruthSpec.kind``. Built-in
loaders handle ``point_displacements``. Additional kinds
(``dense_flow``, ``transformation_matrix``, ``segmentation_mask``, ...) can be
registered by downstream consumers via :func:`register_gt_loader`.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from .schema import GroundTruthSpec


@dataclass(frozen=True)
class PointDisplacement:
    """A single labeled 3D displacement (epoch1 → epoch2)."""

    label: str
    xyz_epoch1: NDArray
    xyz_epoch2: NDArray

    @property
    def movement_vector(self) -> NDArray:
        return self.xyz_epoch2 - self.xyz_epoch1

    @property
    def movement_magnitude(self) -> float:
        return float(np.linalg.norm(self.movement_vector))


@dataclass(frozen=True)
class PointDisplacements:
    """A set of labeled 3D point displacements."""

    points: Sequence[PointDisplacement]

    def __iter__(self):
        return iter(self.points)

    def __len__(self) -> int:
        return len(self.points)


GTLoader = Callable[[GroundTruthSpec], Any]
GT_LOADERS: dict[str, GTLoader] = {}


def register_gt_loader(kind: str, loader: GTLoader) -> None:
    """Register a loader for a new ground-truth kind."""

    GT_LOADERS[kind] = loader


def load_ground_truth(spec: GroundTruthSpec) -> Any:
    """Dispatch to the registered loader for ``spec.kind``."""

    loader = GT_LOADERS.get(spec.kind)
    if loader is None:
        raise NotImplementedError(
            f"No ground-truth loader registered for kind {spec.kind!r}. "
            f"Call register_gt_loader({spec.kind!r}, ...) or pick a supported kind: "
            f"{sorted(GT_LOADERS)}"
        )
    return loader(spec)


# ---------------------------------------------------------------------------
# Built-in: point_displacements
# ---------------------------------------------------------------------------


def _load_point_displacements(spec: GroundTruthSpec) -> PointDisplacements:
    if spec.inline:
        raw = spec.inline.get("points", [])
    elif spec.path is not None:
        raw = _read_point_displacements_csv(spec.path)
    else:
        raise ValueError("point_displacements ground truth requires 'path' or 'inline'")

    points: list[PointDisplacement] = []
    for entry in raw:
        points.append(
            PointDisplacement(
                label=str(entry["label"]),
                xyz_epoch1=np.asarray(entry["xyz_epoch1"], dtype=float),
                xyz_epoch2=np.asarray(entry["xyz_epoch2"], dtype=float),
            )
        )
    return PointDisplacements(points=tuple(points))


def _read_point_displacements_csv(path: Path) -> list[Mapping[str, Any]]:
    """Read a CSV with columns ``label, x1, y1, z1, x2, y2, z2``."""

    out: list[Mapping[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            out.append(
                {
                    "label": row["label"],
                    "xyz_epoch1": [float(row["x1"]), float(row["y1"]), float(row["z1"])],
                    "xyz_epoch2": [float(row["x2"]), float(row["y2"]), float(row["z2"])],
                }
            )
    return out


register_gt_loader("point_displacements", _load_point_displacements)


__all__ = [
    "GT_LOADERS",
    "GTLoader",
    "PointDisplacement",
    "PointDisplacements",
    "load_ground_truth",
    "register_gt_loader",
]
