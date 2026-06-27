"""analyze() smoke tests with cached predictions across multiple tools."""

from __future__ import annotations

import argparse
import logging
import textwrap
from pathlib import Path

import pytest

from geodispbench3d.analysis import analyze, load_analysis
from geodispbench3d.results.predictions_cache import write_prediction


def _bootstrap_analysis(tmp_path: Path) -> Path:
    (tmp_path / "gt.csv").write_text("label,x1,y1,z1,x2,y2,z2\nA,0,0,0,0.1,0,0\nB,5,0,0,5.05,0,0\n")
    (tmp_path / "dataset.yaml").write_text(
        textwrap.dedent("""\
        id: stub-dataset
        cases:
          - name: only-case
            scans: []
            ground_truth: {kind: point_displacements, path: gt.csv}
        """)
    )
    (tmp_path / "metrics.yaml").write_text(
        textwrap.dedent("""\
        objective_metrics:
          - id: median_displacement_error
            fn: geodispbench3d.metrics.builtins:median_displacement_error
            needs: [prediction, ground_truth]
            gt_kinds: [point_displacements]
        record_metrics:
          - id: per_point
            fn: geodispbench3d.metrics.builtins:per_point_displacement_record
            needs: [prediction, ground_truth, case_meta, trial_meta]
            gt_kinds: [point_displacements]
        """)
    )

    pcache = tmp_path / "pcache"
    for tool, run_hash in [("iof3d-v2", "iof-run"), ("f2s3", "f2s3-run")]:
        write_prediction(
            pcache,
            tool_id=tool,
            dataset_id="stub-dataset",
            case="only-case",
            run_hash=run_hash,
            prediction={
                "per_point": [
                    {"label": "A", "vector": [0.1, 0.0, 0.0], "source_count": 1},
                    {"label": "B", "vector": [0.05, 0.0, 0.05], "source_count": 1},
                ]
            },
            provenance={
                "tool": {"id": tool},
                "dataset": {"id": "stub-dataset", "case": "only-case"},
                "run_dir": str(tmp_path / "fake-runs" / run_hash),
            },
        )

    analysis_yaml = tmp_path / "analysis.yaml"
    analysis_yaml.write_text(
        textwrap.dedent("""\
        id: postanalysis-stub
        dataset: dataset.yaml
        metrics: metrics.yaml
        predictions:
          - root: pcache
        pass_id: smoke-test
        """)
    )
    return analysis_yaml


def test_analyze_scores_predictions_across_tools(tmp_path: Path) -> None:
    config = load_analysis(_bootstrap_analysis(tmp_path))
    rows: list = []
    summary = analyze(config=config, on_record_rows=lambda rs: rows.extend(rs))

    assert summary.total == 2
    assert summary.succeeded == 2
    assert summary.skipped_unreadable == 0
    assert summary.skipped_no_case == 0

    # 2 GT points * 2 tools = 4 record rows, all tagged mode=analyze.
    assert len(rows) == 4
    assert {row["mode"] for row in rows} == {"analyze"}
    assert {row["tool_id"] for row in rows} == {"iof3d-v2", "f2s3"}
    assert {row["pass_id"] for row in rows} == {"smoke-test"}


def test_analyze_handles_missing_provenance_via_single_case_fallback(
    tmp_path: Path,
) -> None:
    """A prediction with no `dataset.case` provenance should still resolve
    when the analysis dataset has only one case."""

    analysis_yaml = _bootstrap_analysis(tmp_path)
    pcache = tmp_path / "pcache"
    write_prediction(
        pcache,
        tool_id="bare",
        dataset_id="stub-dataset",
        case="only-case",
        run_hash="bare-run",
        prediction={
            "per_point": [
                {"label": "A", "vector": [0.1, 0.0, 0.0], "source_count": 1},
                {"label": "B", "vector": [0.05, 0.0, 0.05], "source_count": 1},
            ]
        },
        # No provenance recorded — analyze should fall back to the
        # dataset's single case.
        provenance=None,
    )

    config = load_analysis(analysis_yaml)
    summary = analyze(config=config)
    assert summary.total == 3  # two from bootstrap, one bare
    assert summary.succeeded == 3


def test_analyze_corrupt_prediction_counted_fail_soft(tmp_path: Path) -> None:
    """A present-but-corrupt prediction JSON is swallowed fail-soft and counted
    in AnalysisSummary.non_fatal_failures while the readable ones still score (F-08)."""

    analysis_yaml = _bootstrap_analysis(tmp_path)
    # A file that exists but is invalid JSON -> read_prediction's on_non_fatal
    # fires (json.JSONDecodeError), the prediction is skipped, and the failure
    # is counted without aborting the pass.
    corrupt_dir = tmp_path / "pcache" / "bad-tool" / "stub-dataset" / "only-case"
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    (corrupt_dir / "corrupt-run.json").write_text("{ this is not valid json", encoding="utf-8")

    config = load_analysis(analysis_yaml)
    summary = analyze(config=config)
    assert summary.total == 3  # two readable + one corrupt
    assert summary.succeeded == 2
    assert summary.skipped_unreadable == 1
    assert summary.non_fatal_failures == 1


def test_cli_analyze_emits_non_fatal_failures_line(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_cmd_analyze surfaces the aggregate non-fatal-failure line (F-08)."""

    from geodispbench3d import cli

    analysis_yaml = _bootstrap_analysis(tmp_path)
    corrupt_dir = tmp_path / "pcache" / "bad-tool" / "stub-dataset" / "only-case"
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    (corrupt_dir / "corrupt-run.json").write_text("{ not valid json", encoding="utf-8")

    args = argparse.Namespace(analysis=str(analysis_yaml), pass_id=None, log_level="INFO")
    with caplog.at_level(logging.INFO, logger="geodispbench3d.cli"):
        cli._cmd_analyze(args)

    assert any(
        "non-fatal failures" in r.getMessage() and "1" in r.getMessage() for r in caplog.records
    )
