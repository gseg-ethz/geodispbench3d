"""analyze() smoke tests with cached predictions across multiple tools."""

from __future__ import annotations

import textwrap
from pathlib import Path

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
