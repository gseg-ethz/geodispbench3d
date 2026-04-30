"""iof3D adapter integration test (no actual flow pipeline run).

Builds an Iof3dCallableAdapter via the factory and exercises the output
parser against a synthetic leaf PLY whose displacements match the GT
exactly. Confirms the parser shape and metric dispatch glue, without
requiring a GPU or the full iof3D pipeline to run.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def test_factory_loads_iof3d_tool_yaml() -> None:
    from geodispbench3d.suite.loader import load_suite

    repo_root = Path(__file__).resolve().parents[2]
    suite_path = repo_root / "benchmarks" / "suites" / "iof3d_mattertal.yaml"
    if not suite_path.exists():
        pytest.skip(f"benchmark suite not present at {suite_path}")
    suite = load_suite(suite_path)
    assert suite.tool.id == "iof3d-v2"
    assert suite.tool.adapter.in_process_safe is True
    assert suite.tool.output_parser is not None


def test_iof3d_parser_perfect_prediction(tmp_path: Path) -> None:
    pytest.importorskip("pchandler")
    from pchandler import PointCloudData
    from pchandler.data_io import Ply

    from geodispbench3d.dataset.ground_truth import (
        PointDisplacement,
        PointDisplacements,
    )
    from geodispbench3d.tool.base import TrialOutputs
    from geodispbench3d_iof3d import parse_iof3d_output

    gt = PointDisplacements(
        points=(
            PointDisplacement(
                label="A",
                xyz_epoch1=np.array([0.0, 0.0, 0.0]),
                xyz_epoch2=np.array([0.1, 0.0, 0.0]),
            ),
            PointDisplacement(
                label="B",
                xyz_epoch1=np.array([100.0, 0.0, 0.0]),
                xyz_epoch2=np.array([100.05, 0.0, 0.05]),
            ),
        )
    )

    xyz = np.array([p.xyz_epoch1 for p in gt], dtype=np.float64)
    deltas = np.array([p.movement_vector for p in gt], dtype=np.float64)
    pcd = PointCloudData(xyz=xyz)
    pcd.scalar_fields["delta_x"] = deltas[:, 0]
    pcd.scalar_fields["delta_y"] = deltas[:, 1]
    pcd.scalar_fields["delta_z"] = deltas[:, 2]
    pcd.scalar_fields["magnitude"] = np.linalg.norm(deltas, axis=1)

    leaf_dir = tmp_path / "leaf_pointclouds"
    leaf_dir.mkdir()
    Ply.save(pcd, leaf_dir / "leaf_0.ply")

    outputs = TrialOutputs(run_dir=tmp_path)
    prediction = parse_iof3d_output(
        outputs=outputs,
        ground_truth=gt,
        options={"sample_radius_m": 5.0, "aggregation": "median"},
    )
    by_label = {entry["label"]: entry for entry in prediction["per_point"]}
    assert set(by_label) == {"A", "B"}
    np.testing.assert_allclose(by_label["A"]["vector"], [0.1, 0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(by_label["B"]["vector"], [0.05, 0.0, 0.05], atol=1e-9)
