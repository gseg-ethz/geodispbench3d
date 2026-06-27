"""Top-level CLI for geodispbench3d.

Usage::

    geodispbench3d run <suite.yaml> [--timeout SECONDS]
    geodispbench3d rescore <suite.yaml> [flags]
    geodispbench3d analyze <analysis.yaml>
    geodispbench3d dashboard [--parquet PATH]
    geodispbench3d list-metrics <metrics.yaml>

The config-loading subcommands (run / rescore / analyze / list-metrics) accept
``--traceback`` placed AFTER the subcommand
(e.g. ``geodispbench3d run <suite.yaml> --traceback``) to surface the full stack
for a config-load or tool-preflight error instead of the default one-line
``error: <msg>``. This is the single canonical placement for the flag.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import Any

    from geodispbench3d.suite.loader import SuiteConfig

    # The optional results sink: ResultsStore.append, or None when no parquet
    # path is configured. Matches rescore_suite / run_with_suite's parameter.
    OnRecordRows = Callable[[Sequence[Mapping[str, Any]]], None] | None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geodispbench3d")
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared parent parser carrying --traceback. Subcommands that load config
    # inherit it via parents=[...], so the single canonical placement is
    # ``geodispbench3d <subcommand> ... --traceback`` (review LOW: do NOT also
    # wire a bare pre-subcommand flag — one unambiguous form only).
    traceback_parent = argparse.ArgumentParser(add_help=False)
    traceback_parent.add_argument(
        "--traceback",
        action="store_true",
        help=(
            "On a config-load or tool-preflight error, print the full traceback "
            "instead of the default one-line 'error: <msg>'."
        ),
    )

    run_p = sub.add_parser(
        "run",
        parents=[traceback_parent],
        help="Run a sweep described by a suite.yaml",
    )
    run_p.add_argument("suite", help="Path to suite.yaml")
    run_p.add_argument("--log-level", default="INFO")
    run_p.add_argument(
        "--max-trials",
        type=int,
        default=None,
        help="Override suite.search.max_trials",
    )
    run_p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "Override the tool's execution.timeout_seconds (seconds). "
            "0 means no timeout. Applies only to CLI-subprocess tools."
        ),
    )

    rescore_p = sub.add_parser(
        "rescore",
        parents=[traceback_parent],
        help=(
            "Skip the tool: walk every existing run dir under "
            "results.run_dir_root and re-evaluate metrics against the suite"
        ),
    )
    rescore_p.add_argument("suite", help="Path to suite.yaml")
    rescore_p.add_argument("--log-level", default="INFO")
    rescore_p.add_argument(
        "--reuse-parser-options",
        action="store_true",
        help=(
            "Reproduce the parser configuration recorded in each trial's "
            "summary.json instead of using the suite's current output_parser "
            "options."
        ),
    )
    rescore_p.add_argument(
        "--use-prediction-cache",
        action="store_true",
        help=(
            "Load predictions from the predictions cache when available, "
            "skipping phase 2 entirely."
        ),
    )
    rescore_p.add_argument(
        "--pass-id",
        default=None,
        help="Tag this rescore pass in the parquet rows.",
    )
    rescore_p.add_argument(
        "--max-trials",
        type=int,
        default=None,
        help=(
            "Accepted for symmetry but ignored: rescore walks existing run "
            "dirs, so there is no trial budget to cap."
        ),
    )

    dash_p = sub.add_parser("dashboard", help="Launch the Streamlit dashboard")
    dash_p.add_argument(
        "--parquet",
        default=None,
        help="Path to the results parquet file (default: $GEODISPBENCH3D_PARQUET or ./outputs/results.parquet)",
    )

    list_p = sub.add_parser(
        "list-metrics",
        parents=[traceback_parent],
        help="List metrics declared in a metrics.yaml",
    )
    list_p.add_argument("metrics", help="Path to metrics.yaml")

    analyze_p = sub.add_parser(
        "analyze",
        parents=[traceback_parent],
        help="Score cached predictions against a metrics set (no tool involvement)",
    )
    analyze_p.add_argument("analysis", help="Path to analysis.yaml")
    analyze_p.add_argument("--log-level", default="INFO")
    analyze_p.add_argument(
        "--pass-id",
        default=None,
        help="Override the analysis YAML's pass_id (auto-generated otherwise).",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "rescore":
        return _cmd_rescore(args)
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "dashboard":
        return _cmd_dashboard(args)
    if args.command == "list-metrics":
        return _cmd_list_metrics(args)
    parser.print_help()
    return 2


def _prepare_suite_run(
    args: argparse.Namespace,
) -> tuple[SuiteConfig, OnRecordRows, logging.Logger]:
    """Shared prelude for ``run`` (sweep) and ``rescore``.

    Configures logging, loads the suite, and builds the optional results sink.
    Both subcommands reuse it so the sweep / rescore split lives only in their
    handlers, not in duplicated setup.
    """

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    )
    from geodispbench3d.results import ResultsStore
    from geodispbench3d.suite.loader import load_suite

    suite = load_suite(args.suite)
    logger = logging.getLogger("geodispbench3d.cli")

    on_record_rows = None
    if suite.results.parquet_path is not None:
        store = ResultsStore(parquet_path=suite.results.parquet_path)
        on_record_rows = store.append

    return suite, on_record_rows, logger


def _cmd_run(args: argparse.Namespace) -> int:
    """``run``: drive an Ax sweep over the suite (sweep-only; see ``rescore``)."""

    suite, on_record_rows, logger = _prepare_suite_run(args)
    return _cmd_sweep(args, suite, on_record_rows, logger)


def _cmd_sweep(
    args: argparse.Namespace,
    suite: SuiteConfig,
    on_record_rows,
    logger: logging.Logger,
) -> int:
    from geodispbench3d.sweep.parameters import SweepConfig, build_parameter_specs
    from geodispbench3d.sweep.runner import AxSweepRunner

    # Shared guard for the v2 EXEC-01 seam: raise deterministically rather than
    # silently no-op an unsupported parallel_trials / override_tool_mode (D-09).
    # run_with_suite enforces the same guard, so neither path can bypass it.
    suite.execution.ensure_supported()

    max_trials = args.max_trials or suite.search.max_trials

    sweep_cfg = SweepConfig(
        parameters=suite.tool.hyperparameters,
        max_trials=max_trials,
        sobol_trials=suite.search.sobol_trials,
        objective_name=suite.search.objective,
        minimize=suite.search.minimize,
    )
    parameter_specs = build_parameter_specs(sweep_cfg)

    logger.info(
        "Running suite %s (tool=%s, dataset=%s, trials=%d, objective=%s)",
        suite.id,
        suite.tool.id,
        suite.dataset.id,
        max_trials,
        suite.search.objective,
    )

    runner = AxSweepRunner(
        adapter=suite.tool.adapter,
        sweep_config=sweep_cfg,
        parameter_specs=parameter_specs,
        objective_name=suite.search.objective,
        minimize=suite.search.minimize,
        logger=logger,
    )

    result = runner.run_with_suite(
        suite=suite,
        max_trials=max_trials,
        on_record_rows=on_record_rows,
    )
    logger.info("Best trial: %s", result.best_trial)
    logger.info(
        "Objective %s: %d/%d cases finite across the sweep",
        result.objective_name,
        result.objective_cases_finite,
        result.objective_cases_total,
    )
    logger.info(
        "%d non-fatal failures (swallowed, fail-soft) during the sweep", result.non_fatal_failures
    )
    return 0


def _cmd_rescore(args: argparse.Namespace) -> int:
    """``rescore``: skip the tool, re-run metrics over existing run dirs."""

    suite, on_record_rows, logger = _prepare_suite_run(args)

    from geodispbench3d.sweep.rescore import RescoreOptions, rescore_suite

    if args.max_trials is not None:
        logger.warning("--max-trials has no effect in rescore mode")

    options = RescoreOptions(
        reuse_parser_options=bool(args.reuse_parser_options),
        use_prediction_cache=bool(args.use_prediction_cache),
        pass_id=args.pass_id,
    )

    logger.info(
        "Rescoring suite %s (tool=%s, dataset=%s, "
        "reuse_parser_options=%s, use_prediction_cache=%s, pass_id=%s)",
        suite.id,
        suite.tool.id,
        suite.dataset.id,
        options.reuse_parser_options,
        options.use_prediction_cache,
        options.resolved_pass_id(),
    )

    summary = rescore_suite(
        suite=suite,
        options=options,
        on_record_rows=on_record_rows,
        logger=logger,
    )
    logger.info(
        "Rescore done: %d/%d run dirs scored (cache_hits=%d, parser_failed=%d, rows=%d)",
        summary.succeeded,
        summary.total,
        summary.cache_hits,
        summary.parser_misses,
        summary.rows_emitted,
    )
    logger.info(
        "%d non-fatal failures (swallowed, fail-soft) during the rescore",
        summary.non_fatal_failures,
    )
    return 0 if summary.succeeded == summary.total else 1


def _cmd_analyze(args: argparse.Namespace) -> int:
    """``analyze``: score cached predictions; no tool involvement."""

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    )
    from dataclasses import replace

    from geodispbench3d.analysis import analyze, load_analysis
    from geodispbench3d.results import ResultsStore

    config = load_analysis(args.analysis)
    if args.pass_id:
        config = replace(config, pass_id=args.pass_id)

    logger = logging.getLogger("geodispbench3d.cli")
    logger.info(
        "Analyzing %s (dataset=%s, predictions sources=%d, pass_id=%s)",
        config.id,
        config.dataset.id,
        len(config.predictions.refs),
        config.pass_id or "<auto>",
    )

    on_record_rows = None
    if config.results.parquet_path is not None:
        store = ResultsStore(parquet_path=config.results.parquet_path)
        on_record_rows = store.append

    summary = analyze(config=config, on_record_rows=on_record_rows, logger=logger)
    logger.info(
        "Analyze done: %d/%d predictions scored (unreadable=%d, no_case=%d, rows=%d)",
        summary.succeeded,
        summary.total,
        summary.skipped_unreadable,
        summary.skipped_no_case,
        summary.rows_emitted,
    )
    logger.info(
        "%d non-fatal failures (swallowed, fail-soft) during the analyze",
        summary.non_fatal_failures,
    )
    return 0 if summary.succeeded == summary.total else 1


def _cmd_dashboard(args: argparse.Namespace) -> int:
    import os

    parquet = args.parquet or os.environ.get(
        "GEODISPBENCH3D_PARQUET", str(Path.cwd() / "outputs" / "results.parquet")
    )
    os.environ["GEODISPBENCH3D_PARQUET"] = parquet

    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print(
            "streamlit is not installed. Install the 'dashboard' extra: "
            "pip install 'geodispbench3d[dashboard]'",
            file=sys.stderr,
        )
        return 2

    from geodispbench3d import dashboard as dashboard_pkg

    app_path = Path(dashboard_pkg.__file__).parent / "app.py"
    sys.argv = ["streamlit", "run", str(app_path)]
    return int(stcli.main())


def _cmd_list_metrics(args: argparse.Namespace) -> int:
    from geodispbench3d.metrics.registry import load_metrics_config

    cfg = load_metrics_config(args.metrics)
    print("Objective metrics:")
    for m in cfg.objective_metrics:
        print(f"  - {m.id} ({m.fn})")
    print("Record metrics:")
    for m in cfg.record_metrics:
        print(f"  - {m.id} ({m.fn})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
