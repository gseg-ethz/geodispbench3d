"""Loader smoke tests for the four YAML kinds.

Uses an inline synthetic dataset/metrics/tool/suite that exercises the
parameter grammar, the dataset GT loader, the metric resolver, and the
suite composition. Does not require any tool extras.
"""

from __future__ import annotations

import csv
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_bench(tmp_path: Path) -> dict[str, Path]:
    gt_csv = tmp_path / "gt.csv"
    with gt_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["label", "x1", "y1", "z1", "x2", "y2", "z2"])
        writer.writerow(["A", 0.0, 0.0, 0.0, 0.1, 0.0, 0.0])
        writer.writerow(["B", 10.0, 0.0, 0.0, 10.05, 0.0, 0.05])

    dataset = tmp_path / "dataset.yaml"
    dataset.write_text(
        textwrap.dedent("""
        id: synthetic
        cases:
          - name: only-case
            scans: []
            ground_truth:
              kind: point_displacements
              path: gt.csv
    """).strip()
        + "\n"
    )

    metrics = tmp_path / "metrics.yaml"
    metrics.write_text(
        textwrap.dedent("""
        objective_metrics:
          - id: median_displacement_error
            fn: geodispbench3d.metrics.builtins:median_displacement_error
            needs: [prediction, ground_truth]
            gt_kinds: [point_displacements]
          - id: gt_coverage
            fn: geodispbench3d.metrics.builtins:gt_coverage
            needs: [prediction, ground_truth]
            gt_kinds: [point_displacements]
        record_metrics: []
    """).strip()
        + "\n"
    )

    tool = tmp_path / "tool.yaml"
    tool.write_text(
        textwrap.dedent("""
        id: stub
        kind: cli
        entry: /bin/true
        invocation:
          style: argparse
        hyperparameters:
          - { name: alpha, type: choice, value_type: float, values: [0.0, 0.5, 1.0] }
          - { name: beta,  type: range,  value_type: int,   lower: 1, upper: 4 }
    """).strip()
        + "\n"
    )

    suite = tmp_path / "suite.yaml"
    suite.write_text(
        textwrap.dedent("""
        id: synthetic
        tool: tool.yaml
        dataset: dataset.yaml
        metrics: metrics.yaml
        search:
          max_trials: 2
          sobol_trials: 1
          objective: median_displacement_error
          minimize: true
    """).strip()
        + "\n"
    )

    return {"gt_csv": gt_csv, "dataset": dataset, "metrics": metrics, "tool": tool, "suite": suite}


def test_dataset_loader(synthetic_bench: dict[str, Path]) -> None:
    from geodispbench3d.dataset import load_dataset, load_ground_truth

    ds = load_dataset(synthetic_bench["dataset"])
    assert ds.id == "synthetic"
    assert len(ds.cases) == 1
    gt_spec = ds.cases[0].ground_truth
    assert gt_spec is not None
    gt = load_ground_truth(gt_spec)
    assert len(gt) == 2
    assert gt.points[0].label == "A"


def test_metrics_loader_resolves_callables(synthetic_bench: dict[str, Path]) -> None:
    from geodispbench3d.metrics import MetricRegistry, load_metrics_config

    cfg = load_metrics_config(synthetic_bench["metrics"])
    assert {m.id for m in cfg.objective_metrics} == {"median_displacement_error", "gt_coverage"}
    reg = MetricRegistry()
    for definition in cfg.objective_metrics:
        fn = reg.resolve(definition)
        assert callable(fn)


def test_tool_loader_builds_cli_adapter(synthetic_bench: dict[str, Path]) -> None:
    from geodispbench3d.tool import CliToolAdapter
    from geodispbench3d.tool.loader import load_tool_config

    tc = load_tool_config(synthetic_bench["tool"])
    assert tc.id == "stub"
    assert tc.kind == "cli"
    assert isinstance(tc.adapter, CliToolAdapter)
    assert {p.name for p in tc.hyperparameters} == {"alpha", "beta"}


def test_suite_loader_composes_all(synthetic_bench: dict[str, Path]) -> None:
    from geodispbench3d.suite import load_suite

    suite = load_suite(synthetic_bench["suite"])
    assert suite.id == "synthetic"
    assert suite.tool.id == "stub"
    assert suite.dataset.id == "synthetic"
    assert suite.search.objective == "median_displacement_error"
