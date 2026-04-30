"""Dataset schema and ground-truth registry."""

from __future__ import annotations

from .ground_truth import (
    GT_LOADERS,
    PointDisplacement,
    PointDisplacements,
    load_ground_truth,
    register_gt_loader,
)
from .schema import (
    CaseSpec,
    DatasetSpec,
    GroundTruthSpec,
    ScanSpec,
    load_dataset,
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
