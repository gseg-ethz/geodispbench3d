"""Ax-backed sweep runner, tool-agnostic.

The runner consumes a :class:`~geodispbench3d.tool.base.ToolAdapter` and a
:class:`SweepConfig`. It does not know anything about how a specific tool
turns parameters into a configuration — that lives in the adapter.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Mapping, Sequence
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
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

from geodispbench3d.tool.base import ToolAdapter, TrialRequest

from .evaluation import evaluate_trial
from .parameters import SweepConfig


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
    """

    best_trial: Any
    objective_name: str
    objective_cases_finite: int = 0
    objective_cases_total: int = 0


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
            except Exception:
                self._logger.debug(
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

        return self._ax.get_best_trial()

    def _default_executor(self, parameters: Mapping[str, Any]) -> Mapping[str, float]:
        request = TrialRequest(parameters=parameters)
        result = self._adapter.run_trial(request)
        self._record_run_hash(result.outputs.run_dir.name)
        return dict(result.scalar_metrics)

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

        from geodispbench3d.metrics.registry import MetricRegistry

        registry = MetricRegistry()
        cases = list(suite.dataset.cases)
        if not cases:
            raise ValueError(f"Suite dataset {suite.dataset.id!r} has no cases")

        total_objective_cases_finite = 0
        total_objective_cases = 0
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
                    )
                    total_objective_cases_finite += cases_finite
                    total_objective_cases += cases_total
                    self._ax.complete_trial(trial_index=ax_trial_index, raw_data=aggregated)
                except Exception as exc:  # pragma: no cover - defensive
                    self._logger.exception("Trial %s failed: %s", ax_trial_index, exc)
                    self._ax.log_trial_failure(trial_index=ax_trial_index)
        finally:
            self._adapter.teardown()

        return SweepRunSummary(
            best_trial=self._ax.get_best_trial(),
            objective_name=self._objective_name,
            objective_cases_finite=total_objective_cases_finite,
            objective_cases_total=total_objective_cases,
        )

    def _evaluate_across_cases(
        self,
        parameters: Mapping[str, Any],
        cases: Sequence[Any],
        suite: SuiteConfig,
        registry: Any,
        ax_trial_index: int,
        on_record_rows: Callable[[Sequence[Mapping[str, Any]]], None] | None,
    ) -> tuple[Mapping[str, float], int, int]:
        from geodispbench3d.sweep.trial_record import (
            DatasetProvenance,
            ParserProvenance,
            ToolProvenance,
        )

        # source_path is always populated by load_tool_config (tool/loader.py),
        # so the typed field fully replaces the old getattr/.raw fallback chain.
        tool_yaml = suite.tool.source_path
        tool_prov = ToolProvenance.from_yaml_path(suite.tool.id, tool_yaml)
        parser_prov = ParserProvenance(
            fn=_parser_fn_repr(suite.tool.output_parser),
            options=dict(suite.tool.output_parser_options or {}),
        )

        per_case_scalars: list[dict[str, float]] = []
        for case in cases:
            request = TrialRequest(parameters=parameters, case_name=case.name)
            result = self._adapter.run_trial(request)
            self._record_run_hash(result.outputs.run_dir.name)

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

            # Stamp provenance into the run's summary.json so downstream
            # --rescore / analyze invocations can find tool, dataset, and
            # parser context without consulting the original suite YAML.
            try:
                from dataclasses import asdict

                from geodispbench3d.sweep.trial_record import update_trial_record

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
            except Exception:  # pragma: no cover - never fail a trial on provenance
                self._logger.debug(
                    "Unable to stamp provenance for run %s",
                    result.outputs.run_dir,
                    exc_info=True,
                )

            # Cache phase-2 output so future --rescore / analyze passes
            # can skip re-parsing. Failures here are non-fatal; the trial
            # itself succeeded and Ax already has its scalar.
            predictions_root = getattr(suite.results, "predictions_root", None)
            if predictions_root is not None and evaluation.prediction is not None:
                try:
                    from geodispbench3d.results.predictions_cache import write_prediction

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
                except Exception:  # pragma: no cover - cache failure shouldn't fail a trial
                    self._logger.debug(
                        "Unable to cache prediction for run %s",
                        result.outputs.run_dir,
                        exc_info=True,
                    )

            if on_record_rows and evaluation.record_rows:
                on_record_rows(list(evaluation.record_rows))

        import math

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
    ) -> None:
        """Make objective-specific partial-case failure visible (F-05).

        Emits a per-trial log line and writes a dedicated trial-level summary
        artifact — both OFF the Ax objective payload. The artifact write is
        fail-soft: it can never fail a trial (02-05 adds the non-fatal counter
        to this site).
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
            from geodispbench3d.sweep.trial_record import write_trial_summary

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
        except Exception:  # pragma: no cover - never fail a trial on summary write
            self._logger.warning(
                "Unable to write trial-level summary for trial %s",
                ax_trial_index,
                exc_info=True,
            )

    def _record_run_hash(self, run_hash: str) -> None:
        if self._trial_log_path is None:
            return
        try:
            with self._trial_log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{run_hash}\n")
        except Exception:
            self._logger.debug(
                "Unable to append run hash %s to %s",
                run_hash,
                self._trial_log_path,
                exc_info=True,
            )


def _parser_fn_repr(fn: Any) -> str | None:
    """Render a parser callable as a stable ``"package.module:attr"`` string."""

    if fn is None:
        return None
    module = getattr(fn, "__module__", None)
    qualname = getattr(fn, "__qualname__", getattr(fn, "__name__", None))
    if module and qualname:
        return f"{module}:{qualname}"
    return None


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


__all__ = ["AxSweepRunner", "SweepRunSummary"]
