"""Ax-backed sweep runner, tool-agnostic.

The runner consumes a :class:`~geodispbench3d.tool.base.ToolAdapter` and a
:class:`SweepConfig`. It does not know anything about how a specific tool
turns parameters into a configuration — that lives in the adapter.
"""

from __future__ import annotations

import inspect
import logging
import math
from collections.abc import Callable, Mapping, Sequence
from collections.abc import Mapping as MappingABC
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from geodispbench3d.suite.loader import SuiteConfig

try:  # Ax 1.1+
    from ax.service.ax_client import AxClient, ObjectiveProperties  # type: ignore
except ImportError:  # pragma: no cover - optional dep or older Ax
    try:
        from ax.service.ax_client import AxClient  # type: ignore

        ObjectiveProperties = None  # type: ignore
    except ImportError as ax_exc:  # pragma: no cover - optional dependency missing
        raise ImportError(
            "ax-platform is required for sweep orchestration. Install the 'sweep' extra: "
            "pip install 'geodispbench3d[sweep]'"
        ) from ax_exc

from geodispbench3d.diagnostics import PassDiagnostics
from geodispbench3d.results.predictions_cache import write_prediction
from geodispbench3d.sweep.trial_record import (
    DatasetProvenance,
    ParserProvenance,
    ToolProvenance,
    parser_fn_repr,
    update_trial_record,
    write_trial_summary,
)
from geodispbench3d.tool.base import ToolAdapter, TrialRequest, TrialResult

from .evaluation import evaluate_trial
from .parameters import SweepConfig


class TrialExecutionError(Exception):
    """Signals a failed trial (an adapter ``TrialResult`` with ``success=False``).

    Raised by the shared :func:`_raise_if_failed` guard so a failed adapter
    result is routed to Ax via ``log_trial_failure`` (a genuine failed trial)
    instead of being scored. Carries the adapter's ``error_kind`` so the
    per-trial handler classifies a timeout (non-exit-driving, D-05) apart from a
    genuine crash (exit-driving).
    """

    def __init__(self, message: str, *, error_kind: str | None = None) -> None:
        super().__init__(message)
        self.error_kind = error_kind


def _raise_if_failed(result: TrialResult) -> None:
    """Shared success guard (RESOLVED-B): raise on ``success=False``.

    Called from BOTH the suite path (``_evaluate_across_cases``) and the legacy
    ``_default_executor`` so a failed result is never scored on either entry
    point — it is reported to Ax as a failed trial instead.
    """

    if not result.success:
        raise TrialExecutionError(
            result.error or "trial failed", error_kind=result.error_kind
        )


@dataclass(frozen=True)
class SweepRunSummary:
    """Outcome of a suite sweep.

    Carries the best trial plus the objective-specific finite-case signal
    (F-05), aggregated across every trial in the sweep. The finite-case fields
    live here — and on the per-trial log line + trial-level summary artifact —
    so partial-case degradation is visible WITHOUT touching the Ax objective
    payload handed to ``complete_trial``.

    Extended additively by 02-05 (which appends ``non_fatal_failures``); keep
    the field order so the existing defaults stay valid.

    ``non_fatal_failures`` is the count of swallowed fail-soft failures across
    the whole sweep (per-case evaluation skips, provenance-stamp / prediction-
    cache / run-hash / trial-summary write failures), surfaced as the CLI's
    aggregate "N non-fatal failures" line (F-08).

    Extended additively by 03-01 with the typed failure counters that separate
    timeouts (non-exit-driving per D-05) from genuine tool crashes and
    parser/eval failures, plus a ``successful_trials`` count. Plan 02 derives
    exit 1 from ``trial_failures`` + ``eval_failures`` (NOT ``timeouts``), and
    treats ``successful_trials == 0`` (paired with ``best_trial is None``) as the
    all-failed-sweep exit-1 trigger — even a timeouts-only sweep that optimized
    nothing (RESOLVED-A). The new fields keep their position AFTER
    ``non_fatal_failures`` so existing positional/keyword constructors stay valid.

    * ``timeouts`` — trials killed at the wall-clock timeout (D-05: NON-FATAL for
      the exit code; its own visible category, not folded into other counters).
    * ``trial_failures`` — genuine tool/runtime crashes (nonzero exit, missing
      output, entry-not-found, or an unexpected runner bug). Exit-driving.
    * ``eval_failures`` — parser/metric failures (the ``"evaluation"`` diag kind).
      Exit-driving.
    * ``successful_trials`` — trials that reached ``complete_trial``. ``0`` is the
      zero-successful-trial exit-1 trigger Plan 02 consumes.
    """

    best_trial: Any
    objective_name: str
    objective_cases_finite: int = 0
    objective_cases_total: int = 0
    non_fatal_failures: int = 0
    timeouts: int = 0
    trial_failures: int = 0
    eval_failures: int = 0
    successful_trials: int = 0


class AxSweepRunner:
    """Drive Ax optimization using a :class:`ToolAdapter` for trial execution."""

    def __init__(
        self,
        *,
        adapter: ToolAdapter,
        sweep_config: SweepConfig,
        parameter_specs: Sequence[Mapping[str, Any]],
        objective_name: str,
        minimize: bool,
        logger: logging.Logger | None = None,
        trial_log_path: Path | None = None,
        experiment_name: str = "geodispbench3d_sweep",
    ) -> None:
        self._adapter = adapter
        self._param_defs = list(sweep_config.parameters)
        self._objective_name = objective_name
        self._minimize = minimize
        self._sobol_trials = max(1, min(sweep_config.sobol_trials, sweep_config.max_trials))
        self._logger = logger or logging.getLogger("geodispbench3d.sweep")
        self._trial_log_path = Path(trial_log_path) if trial_log_path is not None else None
        if self._trial_log_path is not None:
            try:
                self._trial_log_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                self._logger.warning(
                    "Unable to create trial log directory %s",
                    self._trial_log_path.parent,
                    exc_info=True,
                )
                self._trial_log_path = None

        self._ax = AxClient(verbose_logging=False)
        self._create_experiment(parameter_specs, experiment_name)

    def _create_experiment(
        self,
        parameter_specs: Sequence[Mapping[str, Any]],
        experiment_name: str,
    ) -> None:
        sig = inspect.signature(self._ax.create_experiment)
        param_names = set(sig.parameters)
        specs = [dict(spec) for spec in parameter_specs]
        self._logger.debug("AxClient.create_experiment parameters: %s", sorted(param_names))

        exp_kwargs: dict[str, Any] = {}

        if "parameters" in param_names:
            exp_kwargs["parameters"] = specs
        elif "parameter_definitions" in param_names:
            exp_kwargs["parameter_definitions"] = specs
        elif "search_space" in param_names:
            exp_kwargs["search_space"] = {"parameters": specs}
        else:
            raise TypeError(
                "AxClient.create_experiment signature unsupported: expects one of "
                "parameters, parameter_definitions, or search_space"
            )

        if "name" in param_names:
            exp_kwargs["name"] = experiment_name
        elif "experiment_name" in param_names:
            exp_kwargs["experiment_name"] = experiment_name

        if "objective_name" in param_names:
            exp_kwargs["objective_name"] = self._objective_name
            if "minimize" in param_names:
                exp_kwargs["minimize"] = self._minimize
        elif "objectives" in param_names:
            if ObjectiveProperties is not None:
                exp_kwargs["objectives"] = {
                    self._objective_name: ObjectiveProperties(minimize=self._minimize)
                }
            else:
                exp_kwargs["objectives"] = {self._objective_name: {"minimize": self._minimize}}
        elif "optimization_config" in param_names:
            if ObjectiveProperties is not None:
                exp_kwargs["optimization_config"] = {
                    "objectives": {
                        self._objective_name: ObjectiveProperties(minimize=self._minimize)
                    }
                }
            else:
                exp_kwargs["optimization_config"] = {
                    "objectives": {self._objective_name: {"minimize": self._minimize}}
                }
        else:
            self._logger.debug(
                "AxClient.create_experiment does not expose objective_name/objectives; "
                "falling back to bare minimize flag"
            )
            if "minimize" in param_names:
                exp_kwargs["minimize"] = self._minimize

        if "choose_generation_strategy_kwargs" in param_names:
            exp_kwargs["choose_generation_strategy_kwargs"] = {
                "num_initialization_trials": self._sobol_trials,
            }

        self._ax.create_experiment(**exp_kwargs)

    def run(
        self,
        *,
        max_trials: int,
        trial_executor: Callable[[Mapping[str, Any]], Mapping[str, float]] | None = None,
    ) -> Any:
        """Execute up to ``max_trials`` evaluations.

        ``trial_executor`` overrides the adapter-driven default. It receives the
        raw Ax parameterization and must return a scalar metric dict.
        """

        executor = trial_executor or self._default_executor
        self._adapter.prepare()
        try:
            for _ in range(max_trials):
                trial_data = self._ax.get_next_trial()
                trial_index, parameters = _normalize_trial_data(trial_data)
                try:
                    metrics = executor(parameters)
                    self._ax.complete_trial(trial_index=trial_index, raw_data=metrics)
                except Exception as exc:  # pragma: no cover - defensive
                    self._logger.exception("Trial %s failed: %s", trial_index, exc)
                    self._ax.log_trial_failure(trial_index=trial_index)
        finally:
            self._adapter.teardown()

        return self._resolve_best_trial()

    def _default_executor(self, parameters: Mapping[str, Any]) -> Mapping[str, float]:
        request = TrialRequest(parameters=parameters)
        result = self._adapter.run_trial(request)
        # RESOLVED-B: honor success=False on the legacy path too. The raise
        # propagates to run()'s per-trial except handler, which calls
        # log_trial_failure — so a failed result becomes a real failed Ax trial
        # (reported, not scored) on the iof3d-ax CLI path as well.
        _raise_if_failed(result)
        self._record_run_hash(result.outputs.run_dir.name)
        return dict(result.scalar_metrics)

    def _resolve_best_trial(self) -> Any:
        """Return Ax's best trial, or ``None`` when no trial completed.

        RESOLVED-A: an all-failed / all-timeout sweep leaves Ax with no completed
        trial, and ``get_best_trial`` can raise in that state. This shared guard
        (called from BOTH ``run()`` and ``run_with_suite()``) never lets a raw Ax
        exception escape the trial loop — it returns ``None`` so the runner can
        report a valid summary with ``best_trial is None``.
        """

        try:
            return self._ax.get_best_trial()
        except Exception:  # pragma: no cover - Ax has no completed/best trial
            self._logger.info(
                "No best trial available (no successful trials in this sweep)"
            )
            return None

    def run_with_suite(
        self,
        *,
        suite: SuiteConfig,
        max_trials: int,
        on_record_rows: Callable[[Sequence[Mapping[str, Any]]], None] | None = None,
    ) -> SweepRunSummary:
        """Run the sweep, evaluating each trial through the suite's metric set.

        For each trial, the adapter produces a :class:`TrialResult`; the suite's
        tool config may attach an output parser that turns raw outputs into a
        ``prediction`` mapping; metric definitions are then dispatched via
        :func:`evaluate_trial`. Scalar metrics flow back to Ax; record rows
        are forwarded to ``on_record_rows`` (typically a parquet appender).

        Iterates over the suite's dataset cases per trial and aggregates
        scalar metrics across cases by mean (a reasonable default — extend
        later if multi-case sweeps need different aggregation).
        """

        # Shared, deterministically-raising guard for the v2 EXEC-01 seam
        # (parallel_trials / override_tool_mode). Invoked here AND in
        # cli._cmd_sweep so a programmatic caller cannot bypass it (F-30).
        suite.execution.ensure_supported()

        from geodispbench3d.metrics.registry import MetricRegistry

        registry = MetricRegistry()
        cases = list(suite.dataset.cases)
        if not cases:
            raise ValueError(f"Suite dataset {suite.dataset.id!r} has no cases")

        total_objective_cases_finite = 0
        total_objective_cases = 0
        # Typed failure tallies (review HIGH #2 + Warning 1). ``timeouts`` is
        # NON-FATAL for the exit code (D-05); ``trial_failures`` (crashes) and
        # the ``"evaluation"`` diag kind (parser/metric) are exit-driving in
        # Plan 02. ``successful_trials`` counts completions (zero => RESOLVED-A
        # all-failed exit-1 trigger).
        timeouts = 0
        trial_failures = 0
        successful_trials = 0
        # One PassDiagnostics for the whole sweep; every fail-soft site records
        # into it and the total rides out on SweepRunSummary (F-08).
        pass_diag = PassDiagnostics()
        self._adapter.prepare()
        try:
            for _ in range(max_trials):
                trial_data = self._ax.get_next_trial()
                ax_trial_index, parameters = _normalize_trial_data(trial_data)
                try:
                    aggregated, cases_finite, cases_total = self._evaluate_across_cases(
                        parameters,
                        cases,
                        suite,
                        registry,
                        ax_trial_index,
                        on_record_rows,
                        diagnostics=pass_diag,
                    )
                    total_objective_cases_finite += cases_finite
                    total_objective_cases += cases_total
                    self._ax.complete_trial(trial_index=ax_trial_index, raw_data=aggregated)
                    successful_trials += 1
                except TrialExecutionError as exc:
                    # A failed adapter result (success=False): report it to Ax as
                    # a genuine failed trial (NOT complete_trial) and continue the
                    # sweep. Classify on the explicit error_kind so a timeout is
                    # split off from a crash (D-05 / Warning 1).
                    if exc.error_kind == "timeout":
                        timeouts += 1
                        self._logger.warning(
                            "Trial %s timed out; recorded as a timeout (non-fatal)",
                            ax_trial_index,
                        )
                    else:
                        trial_failures += 1
                        self._logger.warning(
                            "Trial %s failed (%s); recorded as a trial failure",
                            ax_trial_index,
                            exc,
                        )
                    self._ax.log_trial_failure(trial_index=ax_trial_index)
                except Exception as exc:  # pragma: no cover - defensive: a real bug
                    # An unexpected (non-TrialExecutionError) exception is a
                    # genuine runner bug -> exit-driving trial_failures.
                    self._logger.exception("Trial %s failed unexpectedly: %s", ax_trial_index, exc)
                    trial_failures += 1
                    self._ax.log_trial_failure(trial_index=ax_trial_index)
        finally:
            self._adapter.teardown()

        return SweepRunSummary(
            best_trial=self._resolve_best_trial(),
            objective_name=self._objective_name,
            objective_cases_finite=total_objective_cases_finite,
            objective_cases_total=total_objective_cases,
            non_fatal_failures=pass_diag.non_fatal_failures,
            timeouts=timeouts,
            trial_failures=trial_failures,
            eval_failures=pass_diag.by_kind.get("evaluation", 0),
            successful_trials=successful_trials,
        )

    def _evaluate_across_cases(
        self,
        parameters: Mapping[str, Any],
        cases: Sequence[Any],
        suite: SuiteConfig,
        registry: Any,
        ax_trial_index: int,
        on_record_rows: Callable[[Sequence[Mapping[str, Any]]], None] | None,
        *,
        diagnostics: PassDiagnostics | None = None,
    ) -> tuple[Mapping[str, float], int, int]:
        # ``diagnostics`` is the sweep-wide non-fatal counter (F-08). Direct
        # callers (tests) may omit it; a throwaway then keeps the recording
        # sites uniform without changing behavior.
        diag = diagnostics if diagnostics is not None else PassDiagnostics()

        # source_path is always populated by load_tool_config (tool/loader.py),
        # so the typed field fully replaces the old getattr/.raw fallback chain.
        tool_yaml = suite.tool.source_path
        tool_prov = ToolProvenance.from_yaml_path(suite.tool.id, tool_yaml)
        parser_prov = ParserProvenance(
            fn=parser_fn_repr(suite.tool.output_parser),
            options=dict(suite.tool.output_parser_options or {}),
        )

        per_case_scalars: list[dict[str, float]] = []
        for case in cases:
            request = TrialRequest(parameters=parameters, case_name=case.name)
            result = self._adapter.run_trial(request)
            # THE CENTRAL CONTRACT (review HIGH #1, F-32/F-07): a failed adapter
            # result is NOT scored. Raise BEFORE evaluate_trial / provenance /
            # cache side effects so the case loop unwinds and the per-trial
            # handler reports a failed Ax trial (log_trial_failure). The guard is
            # shared with the legacy path (RESOLVED-B).
            if not result.success:
                self._logger.warning(
                    "Trial %s case %s failed (%s); skipping scoring, reporting failure to Ax",
                    ax_trial_index,
                    case.name,
                    result.error,
                )
                _raise_if_failed(result)
            if not self._record_run_hash(result.outputs.run_dir.name):
                diag.add("run_hash")

            dataset_prov = DatasetProvenance(id=suite.dataset.id, case=case.name)
            record_extras = {
                "tool_id": tool_prov.id,
                "dataset_id": dataset_prov.id,
                "case": case.name,
                "trial_index": ax_trial_index,
                "mode": "sweep",
            }

            evaluation = evaluate_trial(
                trial_result=result,
                parameters=parameters,
                case=case,
                metrics=suite.metrics,
                registry=registry,
                output_parser=suite.tool.output_parser,
                output_parser_options=suite.tool.output_parser_options,
                trial_index=ax_trial_index,
                record_extras=record_extras,
                logger=self._logger,
            )
            per_case_scalars.append(dict(evaluation.scalar_metrics))
            diag.add("evaluation", evaluation.non_fatal_failures)

            # Stamp provenance into the run's summary.json so downstream
            # rescore / analyze invocations can find tool, dataset, and
            # parser context without consulting the original suite YAML.
            try:
                update_trial_record(
                    result.outputs.run_dir,
                    {
                        "tool": asdict(tool_prov),
                        "dataset": asdict(dataset_prov),
                        "parser": {
                            "fn": parser_prov.fn,
                            "options": dict(parser_prov.options),
                        },
                    },
                )
            except (OSError, TypeError):  # never fail a trial on provenance
                self._logger.warning(
                    "Unable to stamp provenance for run %s",
                    result.outputs.run_dir,
                    exc_info=True,
                )
                diag.add("provenance_stamp")

            # Cache phase-2 output so future rescore / analyze passes
            # can skip re-parsing. Failures here are non-fatal; the trial
            # itself succeeded and Ax already has its scalar.
            predictions_root = getattr(suite.results, "predictions_root", None)
            if predictions_root is not None and evaluation.prediction is not None:
                try:
                    write_prediction(
                        Path(predictions_root),
                        tool_id=tool_prov.id,
                        dataset_id=dataset_prov.id,
                        case=case.name,
                        run_hash=result.outputs.run_dir.name,
                        prediction=evaluation.prediction,
                        provenance={
                            "tool": tool_prov,
                            "dataset": dataset_prov,
                            "parser": parser_prov,
                            "run_dir": str(result.outputs.run_dir),
                        },
                    )
                except (OSError, TypeError):  # cache failure shouldn't fail a trial
                    self._logger.warning(
                        "Unable to cache prediction for run %s",
                        result.outputs.run_dir,
                        exc_info=True,
                    )
                    diag.add("prediction_cache")

            if on_record_rows and evaluation.record_rows:
                on_record_rows(list(evaluation.record_rows))

        # Objective-specific finite-case signal (F-05), computed AFTER the loop
        # for self._objective_name only — each objective key may be absent/NaN
        # in different cases, so a single metric-agnostic count would mislead.
        # Computed regardless of the single-case short-circuit below.
        objective = self._objective_name
        objective_cases_total = len(per_case_scalars)
        objective_cases_finite = sum(
            1
            for d in per_case_scalars
            if objective in d
            and isinstance(d[objective], (int, float))
            and not math.isnan(float(d[objective]))
        )

        if len(per_case_scalars) == 1:
            aggregated: Mapping[str, float] = per_case_scalars[0]
        else:
            # Aggregate across cases by mean of each scalar metric, ignoring NaN.
            keys = {k for d in per_case_scalars for k in d.keys()}
            out: dict[str, float] = {}
            for key in keys:
                values = [d[key] for d in per_case_scalars if key in d]
                finite = [
                    v for v in values if isinstance(v, (int, float)) and not math.isnan(float(v))
                ]
                if finite:
                    out[key] = float(sum(finite) / len(finite))
            aggregated = out

        self._surface_finite_case_signal(
            suite,
            ax_trial_index,
            objective,
            objective_cases_finite,
            objective_cases_total,
            aggregated.get(objective),
            diagnostics=diag,
        )
        return aggregated, objective_cases_finite, objective_cases_total

    def _surface_finite_case_signal(
        self,
        suite: SuiteConfig,
        ax_trial_index: int,
        objective: str,
        objective_cases_finite: int,
        objective_cases_total: int,
        aggregated_objective: float | None,
        *,
        diagnostics: PassDiagnostics,
    ) -> None:
        """Make objective-specific partial-case failure visible (F-05).

        Emits a per-trial log line and writes a dedicated trial-level summary
        artifact — both OFF the Ax objective payload. The artifact write is
        fail-soft: it can never fail a trial, and a swallowed write failure is
        recorded into the pass-wide ``diagnostics`` as ``"trial_summary"`` so it
        rides out on ``SweepRunSummary.non_fatal_failures`` (F-08).
        """

        if objective_cases_finite < objective_cases_total:
            self._logger.warning(
                "Trial %s objective %s: only %d/%d cases finite (partial failure)",
                ax_trial_index,
                objective,
                objective_cases_finite,
                objective_cases_total,
            )
        else:
            self._logger.info(
                "Trial %s objective %s: %d/%d cases finite",
                ax_trial_index,
                objective,
                objective_cases_finite,
                objective_cases_total,
            )

        run_dir_root = suite.results.run_dir_root
        if run_dir_root is None:
            return
        try:
            write_trial_summary(
                Path(run_dir_root),
                ax_trial_index,
                {
                    "trial_index": ax_trial_index,
                    "objective_name": objective,
                    "objective_cases_finite": objective_cases_finite,
                    "objective_cases_total": objective_cases_total,
                    "aggregated_objective": aggregated_objective,
                },
            )
        except Exception:  # never fail a trial on summary write
            self._logger.warning(
                "Unable to write trial-level summary for trial %s",
                ax_trial_index,
                exc_info=True,
            )
            diagnostics.add("trial_summary")

    def _record_run_hash(self, run_hash: str) -> bool:
        """Append a run hash to the trial log; return ``False`` on a write failure.

        No configured log path is not a failure (returns ``True``): there is
        simply nothing to record. Only an actual ``OSError`` on the append is a
        fail-soft failure the caller counts (F-08).
        """

        if self._trial_log_path is None:
            return True
        try:
            with self._trial_log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{run_hash}\n")
        except OSError:
            self._logger.warning(
                "Unable to append run hash %s to %s",
                run_hash,
                self._trial_log_path,
                exc_info=True,
            )
            return False
        return True


def _normalize_trial_data(trial_data: Any) -> tuple[int, dict[str, Any]]:
    """Coerce ``AxClient.get_next_trial`` return into ``(index, params)``."""

    if isinstance(trial_data, tuple):
        items = list(trial_data)
    else:
        items = [trial_data]

    trial_index: int | None = None
    params: dict[str, Any] | None = None

    for item in items:
        if isinstance(item, int) and trial_index is None:
            trial_index = item
            continue
        if isinstance(item, MappingABC) and params is None:
            params = dict(item)
            continue
        if hasattr(item, "trial_index") and trial_index is None:
            try:
                trial_index = int(item.trial_index)
                continue
            except Exception:  # pragma: no cover
                pass
        if hasattr(item, "parameters") and params is None:
            try:
                params = dict(item.parameters)
                continue
            except Exception:  # pragma: no cover
                pass

    if trial_index is None or params is None:
        raise TypeError(f"Unable to normalize Ax trial data: {trial_data!r}")

    return trial_index, params


__all__ = ["AxSweepRunner", "SweepRunSummary", "TrialExecutionError"]
