"""rescore_suite() smoke tests against a stubbed-out tool/parser."""

from __future__ import annotations

import sys
import textwrap
from dataclasses import asdict
from pathlib import Path

from geodispbench3d.results.predictions_cache import write_prediction
from geodispbench3d.suite.loader import load_suite
from geodispbench3d.sweep.rescore import RescoreOptions, rescore_suite
from geodispbench3d.sweep.trial_record import (
    DatasetProvenance,
    ToolProvenance,
    load_trial_record,
    trial_record_path,
    write_trial_record,
)


def _bootstrap_bench(tmp_path: Path) -> Path:
    """Build a minimal suite + run-dir layout. Returns path to suite.yaml."""

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

    # Stub parser package on sys.path
    pkg_dir = tmp_path / "stub_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text(
        "def parse(*, outputs, ground_truth, options=None, **_):\n"
        "    return {'per_point': [\n"
        "        {'label': p.label, 'vector': list(p.movement_vector), 'source_count': 1}\n"
        "        for p in ground_truth\n"
        "    ]}\n"
    )
    if str(tmp_path) not in sys.path:
        sys.path.insert(0, str(tmp_path))

    (tmp_path / "tool.yaml").write_text(
        textwrap.dedent("""\
        id: stub-tool
        kind: cli
        entry: /bin/true
        invocation: {style: argparse}
        output_parser:
          fn: stub_pkg:parse
          options: {radius: 5}
        """)
    )
    suite_yaml = tmp_path / "suite.yaml"
    suite_yaml.write_text(
        textwrap.dedent("""\
        id: stub-suite
        tool: tool.yaml
        dataset: dataset.yaml
        metrics: metrics.yaml
        search:
          max_trials: 1
          sobol_trials: 1
          objective: median_displacement_error
          minimize: true
        results:
          run_dir_root: runs
          predictions_root: pcache
        """)
    )

    # Fabricate a synthetic run dir as if a sweep had completed.
    run_dir = tmp_path / "runs" / "abcdef123456"
    run_dir.mkdir(parents=True)
    write_trial_record(
        trial_record_path(run_dir),
        {
            "status": "success",
            "parameters": {"alpha": 0.5},
            "metrics": {"median_displacement_error": 0.123},
            "runtime_seconds": 1.5,
            "completed_at": "2026-04-30T00:00:00Z",
            "started_at": "2026-04-30T00:00:00Z",
            "run_hash": "abcdef123456",
            "predictions": [],
            "figures": [],
            "tool": asdict(ToolProvenance(id="stub-tool")),
            "dataset": asdict(DatasetProvenance(id="stub-dataset", case="only-case")),
            "parser": {"fn": "stub_pkg:parse", "options": {"radius": 5}},
        },
    )
    return suite_yaml


def test_rescore_default_options(tmp_path: Path) -> None:
    suite = load_suite(_bootstrap_bench(tmp_path))
    rows: list = []
    summary = rescore_suite(
        suite=suite,
        options=RescoreOptions(),
        on_record_rows=lambda rs: rows.extend(rs),
    )

    assert summary.total == 1
    assert summary.succeeded == 1
    assert summary.cache_hits == 0
    assert summary.parser_misses == 0

    assert all(row["mode"] == "rescore" for row in rows)
    assert all(row["parser_source"] == "suite" for row in rows)
    assert all(row["pass_id"] for row in rows)

    record = load_trial_record(trial_record_path(tmp_path / "runs" / "abcdef123456"))
    assert len(record["rescore_log"]) == 1
    assert record["rescore_log"][0]["parser_source"] == "suite"


def test_rescore_with_prediction_cache_hit(tmp_path: Path) -> None:
    suite = load_suite(_bootstrap_bench(tmp_path))
    write_prediction(
        suite.results.predictions_root,
        tool_id="stub-tool",
        dataset_id="stub-dataset",
        case="only-case",
        run_hash="abcdef123456",
        prediction={
            "per_point": [
                {"label": "A", "vector": [0.1, 0.0, 0.0], "source_count": 99},
                {"label": "B", "vector": [0.05, 0.0, 0.05], "source_count": 99},
            ]
        },
    )

    summary = rescore_suite(
        suite=suite,
        options=RescoreOptions(use_prediction_cache=True),
    )
    assert summary.succeeded == 1
    assert summary.cache_hits == 1


def test_rescore_default_options_zero_non_fatal_failures(tmp_path: Path) -> None:
    """A clean rescore pass reports zero non-fatal failures (F-08)."""

    suite = load_suite(_bootstrap_bench(tmp_path))
    summary = rescore_suite(suite=suite, options=RescoreOptions())
    assert summary.succeeded == 1
    assert summary.non_fatal_failures == 0


def test_rescore_malformed_rescore_log_is_counted_fail_soft(tmp_path: Path) -> None:
    """A non-list ``rescore_log`` makes append_rescore_entry raise AttributeError;
    it is swallowed fail-soft, counted in RescoreSummary.non_fatal_failures, and
    the run still scores (F-08, corrected exception set OSError/AttributeError/TypeError)."""

    suite = load_suite(_bootstrap_bench(tmp_path))

    # Corrupt the (valid-JSON) summary so rescore_log is a truthy dict, not a
    # list: append_rescore_entry then does ``{}.append(...)`` -> AttributeError.
    run_dir = tmp_path / "runs" / "abcdef123456"
    record_path = trial_record_path(run_dir)
    record = load_trial_record(record_path)
    record["rescore_log"] = {"unexpectedly": "a-dict"}
    write_trial_record(record_path, record)

    summary = rescore_suite(suite=suite, options=RescoreOptions())

    # Fail-soft: the run was still scored despite the append failure.
    assert summary.total == 1
    assert summary.succeeded == 1
    # F-08: the swallowed AttributeError on the append was counted.
    assert summary.non_fatal_failures == 1


def test_rescore_skips_failed_runs(tmp_path: Path) -> None:
    suite_yaml = _bootstrap_bench(tmp_path)
    suite = load_suite(suite_yaml)

    failed_dir = tmp_path / "runs" / "deadbeef"
    failed_dir.mkdir(parents=True)
    write_trial_record(
        trial_record_path(failed_dir),
        {"status": "failure", "parameters": {}, "error": "boom"},
    )

    summary = rescore_suite(suite=suite, options=RescoreOptions())
    assert summary.total == 2
    assert summary.succeeded == 1
    assert summary.skipped_failed == 1
