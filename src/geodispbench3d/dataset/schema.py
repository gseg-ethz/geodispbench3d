"""dataset.yaml schema and loader.

A dataset is a list of cases. Each case has one or more scans (e.g. epoch1 +
epoch2 for a point-cloud pair) and optional ground truth. Paths in a dataset
YAML are resolved relative to the YAML file's directory, or to an explicit
``root`` key if given.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from omegaconf import OmegaConf


@dataclass(frozen=True)
class ScanSpec:
    """A single scan (typically one point cloud) within a case."""

    epoch: str
    path: Path
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GroundTruthSpec:
    """Ground-truth pointer for a case.

    ``kind`` discriminates the GT format. The generic dataset loader does not
    parse GT contents — that happens on demand via
    :func:`geodispbench3d.dataset.ground_truth.load_ground_truth`, which
    dispatches on ``kind``.
    """

    kind: str
    path: Path | None = None
    inline: Mapping[str, Any] | None = None
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseSpec:
    """One evaluable case in a dataset."""

    name: str
    scans: Sequence[ScanSpec]
    ground_truth: GroundTruthSpec | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def scan_by_epoch(self, epoch: str) -> ScanSpec:
        for scan in self.scans:
            if scan.epoch == epoch:
                return scan
        raise KeyError(f"Case {self.name!r} has no scan for epoch {epoch!r}")


@dataclass(frozen=True)
class DatasetSpec:
    """Top-level dataset description."""

    id: str
    root: Path
    cases: Sequence[CaseSpec]
    gt_kinds_supported: Sequence[str] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def case(self, name: str) -> CaseSpec:
        for case in self.cases:
            if case.name == name:
                return case
        raise KeyError(f"Dataset {self.id!r} has no case {name!r}")


def load_dataset(path: str | Path) -> DatasetSpec:
    """Load a dataset.yaml and resolve relative paths."""

    yaml_path = Path(path).resolve()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {yaml_path}")

    raw = OmegaConf.to_container(OmegaConf.load(str(yaml_path)), resolve=True)
    if not isinstance(raw, dict):
        raise ValueError(f"Dataset YAML at {yaml_path} must be a mapping")

    root_raw = raw.get("root")
    if root_raw is None:
        root = yaml_path.parent
    else:
        root = (yaml_path.parent / root_raw).resolve()

    cases_raw = raw.get("cases", [])
    if not isinstance(cases_raw, list):
        raise ValueError(f"Dataset {yaml_path}: 'cases' must be a list")

    cases: list[CaseSpec] = []
    for case_raw in cases_raw:
        cases.append(_load_case(case_raw, root))

    gt_kinds = raw.get("gt_kinds_supported") or ()
    metadata = raw.get("metadata") or {}

    return DatasetSpec(
        id=str(raw.get("id", yaml_path.stem)),
        root=root,
        cases=tuple(cases),
        gt_kinds_supported=tuple(gt_kinds),
        metadata=dict(metadata),
    )


def _load_case(case_raw: Mapping[str, Any], root: Path) -> CaseSpec:
    name = str(case_raw["name"])
    scans_raw = case_raw.get("scans") or []
    # An empty scan list is allowed: some tools discover scan paths from
    # their own configuration (e.g. iof3D resolves PCDs from AppConfig).
    # The dataset entry then carries only the GT and metadata.

    scans: list[ScanSpec] = []
    for scan_raw in scans_raw:
        scan_path = (root / scan_raw["path"]).resolve()
        scans.append(
            ScanSpec(
                epoch=str(scan_raw["epoch"]),
                path=scan_path,
                metadata=dict(scan_raw.get("metadata") or {}),
            )
        )

    gt_raw = case_raw.get("ground_truth")
    gt: GroundTruthSpec | None = None
    if gt_raw is not None:
        gt_path_raw = gt_raw.get("path")
        gt = GroundTruthSpec(
            kind=str(gt_raw["kind"]),
            path=(root / gt_path_raw).resolve() if gt_path_raw else None,
            inline=gt_raw.get("inline"),
            options=dict(gt_raw.get("options") or {}),
        )

    metadata = dict(case_raw.get("metadata") or {})

    return CaseSpec(
        name=name,
        scans=tuple(scans),
        ground_truth=gt,
        metadata=metadata,
    )


__all__ = [
    "CaseSpec",
    "DatasetSpec",
    "GroundTruthSpec",
    "ScanSpec",
    "load_dataset",
]
