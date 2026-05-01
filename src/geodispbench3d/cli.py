"""Top-level CLI for geodispbench3d.

Usage::

    geodispbench3d run <suite.yaml>
    geodispbench3d run <suite.yaml> --rescore [flags]
    geodispbench3d dashboard [--parquet PATH]
    geodispbench3d list-metrics <metrics.yaml>
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geodispbench3d")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a sweep described by a suite.yaml")
    run_p.add_argument("suite", help="Path to suite.yaml")
    run_p.add_argument("--log-level", default="INFO")
    run_p.add_argument(
        "--max-trials",
        type=int,
        default=None,
        help="Override suite.search.max_trials",
    )
    run_p.add_argument(
        "--rescore",
        action="store_true",
        help=(
            "Skip the tool: walk every existing run dir under "
            "results.run_dir_root and re-evaluate metrics against the "
            "current suite. Ax is not invoked."
        ),
    )
    run_p.add_argument(
        "--reuse-parser-options",
        action="store_true",
        help=(
            "(--rescore only) reproduce the parser configuration recorded "
            "in each trial's summary.json instead of using the suite's "
            "current output_parser options."
        ),
    )
    run_p.add_argument(
        "--use-prediction-cache",
        action="store_true",
        help=(
            "(--rescore only) load predictions from the predictions cache "
            "when available, skipping phase 2 entirely."
        ),
    )
    run_p.add_argument(
        "--pass-id",
        default=None,
        help="(--rescore only) tag this rescore pass in the parquet rows.",
    )

    dash_p = sub.add_parser("dashboard", help="Launch the Streamlit dashboard")
    dash_p.add_argument(
        "--parquet",
        default=None,
        help="Path to the results parquet file (default: $GEODISPBENCH3D_PARQUET or ./outputs/results.parquet)",
    )

    list_p = sub.add_parser("list-metrics", help="List metrics declared in a metrics.yaml")
    list_p.add_argument("metrics", help="Path to metrics.yaml")

    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "dashboard":
        return _cmd_dashboard(args)
    if args.command == "list-metrics":
        return _cmd_list_metrics(args)
    parser.print_help()
    return 2


def _cmd_run(args: argparse.Namespace) -> int:
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

    if args.rescore:
        return _cmd_rescore(args, suite, on_record_rows, logger)

    return _cmd_sweep(args, suite, on_record_rows, logger)


def _cmd_sweep(
    args: argparse.Namespace,
    suite: object,
    on_record_rows,
    logger: logging.Logger,
) -> int:
    from geodispbench3d.sweep.parameters import SweepConfig, build_parameter_specs
    from geodispbench3d.sweep.runner import AxSweepRunner

    max_trials = args.max_trials or suite.search.max_trials  # type: ignore[attr-defined]

    sweep_cfg = SweepConfig(
        parameters=suite.tool.hyperparameters,  # type: ignore[attr-defined]
        max_trials=max_trials,
        sobol_trials=suite.search.sobol_trials,  # type: ignore[attr-defined]
        objective_name=suite.search.objective,  # type: ignore[attr-defined]
        minimize=suite.search.minimize,  # type: ignore[attr-defined]
    )
    parameter_specs = build_parameter_specs(sweep_cfg)

    logger.info(
        "Running suite %s (tool=%s, dataset=%s, trials=%d, objective=%s)",
        suite.id,  # type: ignore[attr-defined]
        suite.tool.id,  # type: ignore[attr-defined]
        suite.dataset.id,  # type: ignore[attr-defined]
        max_trials,
        suite.search.objective,  # type: ignore[attr-defined]
    )

    runner = AxSweepRunner(
        adapter=suite.tool.adapter,  # type: ignore[attr-defined]
        sweep_config=sweep_cfg,
        parameter_specs=parameter_specs,
        objective_name=suite.search.objective,  # type: ignore[attr-defined]
        minimize=suite.search.minimize,  # type: ignore[attr-defined]
        logger=logger,
    )

    best = runner.run_with_suite(
        suite=suite,
        max_trials=max_trials,
        on_record_rows=on_record_rows,
    )
    logger.info("Best trial: %s", best)
    return 0


def _cmd_rescore(
    args: argparse.Namespace,
    suite: object,
    on_record_rows,
    logger: logging.Logger,
) -> int:
    """``run --rescore``: skip the tool, re-run metrics over existing run dirs."""

    from geodispbench3d.sweep.rescore import RescoreOptions, rescore_suite

    if args.max_trials is not None:
        logger.warning("--max-trials is ignored in --rescore mode")

    options = RescoreOptions(
        reuse_parser_options=bool(args.reuse_parser_options),
        use_prediction_cache=bool(args.use_prediction_cache),
        pass_id=args.pass_id,
    )

    logger.info(
        "Rescoring suite %s (tool=%s, dataset=%s, "
        "reuse_parser_options=%s, use_prediction_cache=%s, pass_id=%s)",
        suite.id,  # type: ignore[attr-defined]
        suite.tool.id,  # type: ignore[attr-defined]
        suite.dataset.id,  # type: ignore[attr-defined]
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
