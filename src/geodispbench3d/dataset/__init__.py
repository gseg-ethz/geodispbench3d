"""Dataset schema and ground-truth registry."""

from __future__ import annotations

from .schema import (
    CaseSpec,
    DatasetSpec,
    ScanSpec,
    GroundTruthSpec,
    load_dataset,
)
from .ground_truth import (
    GT_LOADERS,
    PointDisplacement,
    PointDisplacements,
    load_ground_truth,
    register_gt_loader,
)

__all__ = [
    "CaseSpec",
    "DatasetSpec",
    "GT_LOADERS",
    "GroundTruthSpec",
    "PointDisplacement",
    "PointDisplacements",
    "ScanSpec",
    "load_dataset",
    "load_ground_truth",
    "register_gt_loader",
]
