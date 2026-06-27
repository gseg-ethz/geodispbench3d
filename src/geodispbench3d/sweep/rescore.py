"""``--rescore`` mode: re-evaluate existing run dirs without invoking the tool.

The flow walks every run directory under a suite's ``results.run_dir_root``
that carries an ``ax_trial/summary.json`` and, per run:

  1. Resolve a parser to call. By default this is the suite's current
     ``output_parser:`` configuration; with ``reuse_parser_options=True``
     the parser identity / options recorded in the run's summary win
     instead (useful when the suite YAML has drifted away from what
     produced the run).
  2. Resolve a prediction. With ``use_prediction_cache=True`` and a cache
     hit, the cached prediction is loaded directly and phase 2 is
     skipped. Otherwise the parser runs against the run dir.
  3. Dispatch the suite's metrics through :func:`evaluate_trial`. Scalar
     metrics go nowhere (Ax is not involved); record rows are forwarded
     to the caller's ``on_record_rows`` callback (typically the parquet
     appender) tagged with ``mode="rescore"`` and an audit ``pass_id``.
  4. Append a ``rescore_log`` entry to the trial's summary so each pass
     is auditable.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from geodispbench3d.dataset.schema import CaseSpec, DatasetSpec
from geodispbench3d.diagnostics import PassDiagnostics
from geodispbench3d.metrics.registry import MetricRegistry
from geodispbench3d.results.predictions_cache import (
    cache_path as predictions_cache_path,
)
from geodispbench3d.results.predictions_cache import (
    read_prediction,
    write_prediction,
)
from geodispbench3d.sweep.evaluation import evaluate_trial
from geodispbench3d.sweep.trial_record import (
    DatasetProvenance,
    ParserProvenance,
    ToolProvenance,
    append_rescore_entry,
    load_trial_record,
    parser_fn_repr,
    read_provenance,
    trial_record_path,
)
from geodispbench3d.tool.base import TrialOutputs, TrialResult


@dataclass(frozen=True)
class RescoreOptions:
    """User-facing flags for a rescore pass."""

    reuse_parser_options: bool = False
    use_prediction_cache: bool = False
    pass_id: str | None = None  # appears in the parquet `pass_id` column

    def resolved_pass_id(self) -> str:
        return self.pass_id or _utcnow_compact()


@dataclass
class RescoreSummary:
    """Aggregate counters returned to the CLI for a one-line report.

    ``non_fatal_failures`` totals the swallowed fail-soft failures across the
    pass (corrupt trial-record / cache reads, per-run evaluation skips, cache
    writes, and rescore-log appends), surfaced as the CLI's aggregate
    "N non-fatal failures" line (F-08).

    ``eval_failures`` (03-01) is the genuine-parser/metric subset — the
    ``"evaluation"`` diag kind — separated from the benign cache/append
    degradation that also rides in ``non_fatal_failures``. Plan 02 keys the
    rescore exit-1 condition off ``parser_misses`` OR ``eval_failures``, never
    the collapsed ``non_fatal_failures`` total.
    """

    total: int = 0
    succeeded: int = 0
    skipped_no_summary: int = 0
    skipped_failed: int = 0
    parser_misses: int = 0
    cache_hits: int = 0
    rows_emitted: int = 0
    non_fatal_failures: int = 0
    eval_failures: int = 0


def rescore_suite(
    *,
    suite: Any,
    options: RescoreOptions,
    on_record_rows: Callable[[Sequence[Mapping[str, Any]]], None] | None = None,
    run_dirs: Iterable[Path] | None = None,
    logger: logging.Logger | None = None,
) -> RescoreSummary:
    """Re-score every existing trial under the suite's run-dir root.

    ``run_dirs`` overrides the directory walk for tests / programmatic
    re-scoring of a curated subset. When omitted, every immediate child
    of ``suite.results.run_dir_root`` containing
    ``ax_trial/summary.json`` is processed.
    """

    log = logger or logging.getLogger("geodispbench3d.sweep.rescore")
    summary = RescoreSummary()
    pass_id = options.resolved_pass_id()

    case_index: Mapping[str, CaseSpec] = {c.name: c for c in suite.dataset.cases}
    registry = MetricRegistry()

    # One PassDiagnostics for the whole pass: suite-level corrupt reads record
    # here directly; each run's internal fail-soft failures (evaluation,
    # cache write, rescore-log append) ride on its _RescoreOutcome and are
    # folded in below (F-08).
    diag = PassDiagnostics()

    targets = list(run_dirs) if run_dirs is not None else _walk_run_dirs(suite, log)
    log.info("rescore: %d run dir(s) to evaluate (pass_id=%s)", len(targets), pass_id)

    for run_dir in targets:
        summary.total += 1
        record = load_trial_record(
            trial_record_path(run_dir),
            on_non_fatal=lambda _exc: diag.add("trial_record_read"),
        )
        if not record:
            log.warning("rescore: no summary.json under %s, skipping", run_dir)
            summary.skipped_no_summary += 1
            continue
        if record.get("status") != "success":
            log.info(
                "rescore: skipping %s (status=%r)",
                run_dir,
                record.get("status", "<unknown>"),
            )
            summary.skipped_failed += 1
            continue

        case = _resolve_case(record, case_index, suite.dataset)
        if case is None:
            log.warning(
                "rescore: cannot map %s to a dataset case; skipping",
                run_dir,
            )
            summary.skipped_failed += 1
            continue

        outcome = _rescore_one(
            run_dir=run_dir,
            record=record,
            case=case,
            suite=suite,
            options=options,
            registry=registry,
            pass_id=pass_id,
            log=log,
            on_cache_read_failure=lambda _exc: diag.add("prediction_cache_read"),
        )
        summary.cache_hits += int(outcome.cache_hit)
        summary.parser_misses += int(outcome.parser_failed)
        # Record genuine parser/metric errors under the "evaluation" kind and
        # benign cache/append degradation under a distinct kind, so eval_failures
        # is a true subset readout and non_fatal_failures stays the aggregate.
        diag.add("evaluation", outcome.eval_failures)
        diag.add("rescore_degradation", outcome.degradation_failures)
        if outcome.rows:
            summary.rows_emitted += len(outcome.rows)
            if on_record_rows:
                on_record_rows(outcome.rows)
        if outcome.scored:
            summary.succeeded += 1

    summary.non_fatal_failures = diag.non_fatal_failures
    summary.eval_failures = diag.by_kind.get("evaluation", 0)
    log.info(
        "rescore done: succeeded=%d total=%d cache_hits=%d parser_failed=%d rows=%d "
        "non_fatal_failures=%d",
        summary.succeeded,
        summary.total,
        summary.cache_hits,
        summary.parser_misses,
        summary.rows_emitted,
        summary.non_fatal_failures,
    )
    return summary


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


@dataclass
class _RescoreOutcome:
    scored: bool = False
    cache_hit: bool = False
    parser_failed: bool = False
    rows: list[Mapping[str, Any]] | None = None
    # 03-01: typed apart at the source so genuine parser/metric errors are never
    # summed with benign observability degradation. ``eval_failures`` is the
    # parser-failed eval + the inner evaluation non-fatals; ``degradation_failures``
    # is the cache-write + rescore-log-append degradation.
    eval_failures: int = 0
    degradation_failures: int = 0


def _walk_run_dirs(suite: Any, log: logging.Logger) -> list[Path]:
    root: Path | None = getattr(suite.results, "run_dir_root", None)
    if root is None:
        log.warning("rescore: suite has no results.run_dir_root configured; nothing to walk")
        return []
    root_path = Path(root)
    if not root_path.is_dir():
        log.warning("rescore: run_dir_root %s does not exist", root_path)
        return []
    return sorted(p for p in root_path.iterdir() if p.is_dir() and trial_record_path(p).is_file())


def _resolve_case(
    record: Mapping[str, Any],
    case_index: Mapping[str, CaseSpec],
    dataset: DatasetSpec,
) -> CaseSpec | None:
    """Best-effort case lookup from a trial summary."""

    block = record.get("dataset")
    if isinstance(block, Mapping):
        name = block.get("case")
        if isinstance(name, str) and name in case_index:
            return case_index[name]
    # Fall back: single-case datasets are unambiguous.
    if len(dataset.cases) == 1:
        return dataset.cases[0]
    return None


def _rescore_one(
    *,
    run_dir: Path,
    record: Mapping[str, Any],
    case: CaseSpec,
    suite: Any,
    options: RescoreOptions,
    registry: MetricRegistry,
    pass_id: str,
    log: logging.Logger,
    on_cache_read_failure: Callable[[Exception], None] | None = None,
) -> _RescoreOutcome:
    outcome = _RescoreOutcome(rows=[])

    recorded_tool, recorded_dataset, recorded_parser = read_provenance(run_dir)
    parser_fn, parser_options, parser_source = _select_parser(
        suite=suite,
        recorded=recorded_parser,
        options=options,
        log=log,
    )

    prediction: Any = None
    if options.use_prediction_cache:
        prediction = _try_cache_lookup(
            suite,
            recorded_tool,
            recorded_dataset,
            case,
            run_dir,
            on_non_fatal=on_cache_read_failure,
        )
        if prediction is not None:
            outcome.cache_hit = True
            log.debug("rescore: cache hit for %s", run_dir)

    trial_result = _fabricate_trial_result(record, run_dir)

    record_extras = {
        "tool_id": (recorded_tool.id if recorded_tool else suite.tool.id),
        "dataset_id": (recorded_dataset.id if recorded_dataset else suite.dataset.id),
        "case": case.name,
        "trial_index": record.get("run_hash") or run_dir.name,
        "mode": "rescore",
        "pass_id": pass_id,
        "parser_source": parser_source,
    }

    try:
        evaluation = evaluate_trial(
            trial_result=trial_result,
            parameters=record.get("parameters") or {},
            case=case,
            metrics=suite.metrics,
            registry=registry,
            output_parser=parser_fn if prediction is None else None,
            output_parser_options=parser_options if prediction is None else None,
            prediction_override=prediction,
            trial_index=None,
            record_extras=record_extras,
            logger=log,
        )
    except Exception:
        # Plugin/user callable boundary: evaluate_trial runs arbitrary
        # parser/metric code, so a closed exception set is inapplicable. Stay
        # broad (belt-and-suspenders — inner parser/metric failures are already
        # caught) so a plugin bug skips this run instead of aborting the pass
        # (fail-soft, F-08).
        log.exception("rescore: evaluate_trial failed for %s", run_dir)
        outcome.parser_failed = True
        outcome.eval_failures += 1
        return outcome

    outcome.eval_failures += evaluation.non_fatal_failures

    if evaluation.prediction is None and parser_fn is not None and prediction is None:
        # Parser was supposed to run and produced nothing usable.
        outcome.parser_failed = True

    # Update the cache opportunistically if we just freshly produced a
    # prediction (and a cache root is configured).
    if (
        evaluation.prediction is not None
        and not outcome.cache_hit
        and getattr(suite.results, "predictions_root", None) is not None
    ):
        try:
            tool_prov = recorded_tool or ToolProvenance(id=suite.tool.id)
            dataset_prov = recorded_dataset or DatasetProvenance(
                id=suite.dataset.id, case=case.name
            )
            write_prediction(
                Path(suite.results.predictions_root),
                tool_id=tool_prov.id,
                dataset_id=dataset_prov.id,
                case=case.name,
                run_hash=run_dir.name,
                prediction=evaluation.prediction,
                provenance={
                    "tool": tool_prov,
                    "dataset": dataset_prov,
                    "parser": ParserProvenance(
                        fn=parser_fn_repr(parser_fn), options=dict(parser_options or {})
                    ),
                    "run_dir": str(run_dir),
                    "cached_by": "rescore",
                },
            )
        except (OSError, TypeError):  # cache write failures shouldn't fail rescoring
            log.warning("rescore: cache write failed for %s", run_dir, exc_info=True)
            outcome.degradation_failures += 1

    # Audit log appended to the trial summary.
    try:
        append_rescore_entry(
            run_dir,
            {
                "pass_id": pass_id,
                "rescored_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "parser_source": parser_source,
                "parser_options": dict(parser_options or {}),
                "metrics": dict(evaluation.scalar_metrics),
            },
        )
    except (OSError, AttributeError, TypeError):
        # append_rescore_entry: trial_record mkdir + load_trial_record (which
        # swallows JSONDecodeError, returning {}) + payload['rescore_log'].append
        # + write_trial_record (json.dump + Path.replace). A malformed-but-valid
        # summary whose rescore_log is a non-list truthy yields AttributeError on
        # .append; OSError/TypeError cover the I/O + serialization paths. Stays
        # fail-soft (the rescore itself already succeeded).
        log.warning("rescore: append_rescore_entry failed for %s", run_dir, exc_info=True)
        outcome.degradation_failures += 1

    outcome.scored = True
    outcome.rows = list(evaluation.record_rows)
    return outcome


def _select_parser(
    *,
    suite: Any,
    recorded: ParserProvenance | None,
    options: RescoreOptions,
    log: logging.Logger,
) -> tuple[Callable[..., Any] | None, Mapping[str, Any], str]:
    """Pick which parser configuration the rescore pass should use."""

    if options.reuse_parser_options and recorded is not None and recorded.fn:
        try:
            fn = _resolve_dotted(recorded.fn)
        except Exception:  # pragma: no cover - clear error path
            log.warning(
                "rescore: cannot resolve recorded parser %r; falling back to suite parser",
                recorded.fn,
            )
            return suite.tool.output_parser, dict(suite.tool.output_parser_options or {}), "suite"
        return fn, dict(recorded.options or {}), "recorded"

    return (
        suite.tool.output_parser,
        dict(suite.tool.output_parser_options or {}),
        "suite",
    )


def _try_cache_lookup(
    suite: Any,
    recorded_tool: ToolProvenance | None,
    recorded_dataset: DatasetProvenance | None,
    case: CaseSpec,
    run_dir: Path,
    *,
    on_non_fatal: Callable[[Exception], None] | None = None,
) -> Any:
    root = getattr(suite.results, "predictions_root", None)
    if root is None:
        return None
    tool_id = recorded_tool.id if recorded_tool else suite.tool.id
    dataset_id = recorded_dataset.id if recorded_dataset else suite.dataset.id
    path = predictions_cache_path(
        Path(root),
        tool_id=tool_id,
        dataset_id=dataset_id,
        case=case.name,
        run_hash=run_dir.name,
    )
    payload = read_prediction(path, on_non_fatal=on_non_fatal)
    if payload is None:
        return None
    return payload.get("prediction")


def _fabricate_trial_result(record: Mapping[str, Any], run_dir: Path) -> TrialResult:
    """Build a TrialResult that points at the existing run dir for the parser."""

    predictions = tuple(Path(p) for p in record.get("predictions") or ())
    figures = tuple(Path(p) for p in record.get("figures") or ())
    duration = float(record.get("runtime_seconds") or 0.0)
    return TrialResult(
        outputs=TrialOutputs(run_dir=Path(run_dir), predictions=predictions, figures=figures),
        scalar_metrics=dict(record.get("metrics") or {}),
        duration_seconds=duration,
        success=record.get("status") == "success",
    )


def _resolve_dotted(entry: str) -> Callable[..., Any]:
    if ":" not in entry:
        raise ValueError(f"parser fn must be 'package.module:function', got {entry!r}")
    module_name, attr = entry.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, attr, None)
    if not callable(fn):
        raise ImportError(f"cannot resolve callable {entry!r}")
    return fn


def _utcnow_compact() -> str:
    return datetime.now(UTC).strftime("rescore-%Y%m%dT%H%M%S")


__all__ = [
    "RescoreOptions",
    "RescoreSummary",
    "rescore_suite",
]
