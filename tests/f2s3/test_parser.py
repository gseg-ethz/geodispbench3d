"""F2S3 output-parser test against a synthetic per-tile ASCII file.

Builds the 7-column F2S3 tile format, runs the parser, and checks the
sampled-at-GT shape. Does not invoke the F2S3 binary.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from geodispbench3d.dataset.ground_truth import (
    PointDisplacement,
    PointDisplacements,
)
from geodispbench3d.tool.base import TrialOutputs
from geodispbench3d_f2s3 import parse_f2s3_output


def test_f2s3_parser_perfect_prediction(tmp_path: Path) -> None:
    gt = PointDisplacements(
        points=(
            PointDisplacement(
                label="A",
                xyz_epoch1=np.array([0.0, 0.0, 0.0]),
                xyz_epoch2=np.array([0.1, 0.0, 0.0]),
            ),
            PointDisplacement(
                label="B",
                xyz_epoch1=np.array([200.0, 0.0, 0.0]),
                xyz_epoch2=np.array([200.05, 0.0, 0.05]),
            ),
        )
    )

    output_dir = tmp_path / "output" / "refined_results"
    output_dir.mkdir(parents=True)
    lines = []
    for p in gt:
        e1 = p.xyz_epoch1
        e2 = p.xyz_epoch2
        mag = p.movement_magnitude
        lines.append(
            f"{e1[0]:.6e} {e1[1]:.6e} {e1[2]:.6e} {e2[0]:.6e} {e2[1]:.6e} {e2[2]:.6e} {mag:.6e}"
        )
    (output_dir / "tile_0.txt").write_text("\n".join(lines) + "\n")

    outputs = TrialOutputs(run_dir=tmp_path)
    prediction = parse_f2s3_output(
        outputs=outputs,
        ground_truth=gt,
        options={"sample_radius_m": 5.0, "aggregation": "median", "prefer_refined": True},
    )

    assert prediction["source"]["n_tiles"] == 1
    by_label = {entry["label"]: entry for entry in prediction["per_point"]}
    assert set(by_label) == {"A", "B"}
    np.testing.assert_allclose(by_label["A"]["vector"], [0.1, 0.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(by_label["B"]["vector"], [0.05, 0.0, 0.05], atol=1e-5)


def test_f2s3_parser_handles_missing_output_dir(tmp_path: Path) -> None:
    gt = PointDisplacements(
        points=(
            PointDisplacement(
                label="A",
                xyz_epoch1=np.array([0.0, 0.0, 0.0]),
                xyz_epoch2=np.array([0.1, 0.0, 0.0]),
            ),
        )
    )

    outputs = TrialOutputs(run_dir=tmp_path)
    prediction = parse_f2s3_output(outputs=outputs, ground_truth=gt)
    assert prediction["per_point"][0]["source_count"] == 0
    assert all(np.isnan(prediction["per_point"][0]["vector"]))
