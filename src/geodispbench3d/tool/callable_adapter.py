"""In-process callable tool adapter.

Use this adapter when the tool under test can be safely imported and invoked
inside the sweep runner process. It is faster than the CLI adapter (no fork
per trial) but any segfault or unhandled exception in the tool will crash the
sweep.

Adapters for tools with significant in-process state (CUDA contexts,
large cached models) typically subclass this directly.
"""

from __future__ import annotations

import importlib
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import ToolAdapter, TrialOutputs, TrialRequest, TrialResult


@dataclass(frozen=True)
class CallableSpec:
    """Import target for an in-process callable tool.

    ``entry`` is a dotted path of the form ``"package.module:function"``. The
    function is expected to accept ``(parameters: Mapping[str, Any])`` and
    return either a :class:`TrialResult`, a :class:`TrialOutputs`, or a plain
    mapping understood by :func:`_coerce_callable_return`.
    """

    entry: str


class CallableToolAdapter(ToolAdapter):
    """Runs a Python callable in-process for each trial."""

    id = "callable"
    in_process_safe = True

    def __init__(
        self,
        *,
        spec: CallableSpec,
        logger: logging.Logger | None = None,
    ) -> None:
        self._spec = spec
        self._logger = logger or logging.getLogger("geodispbench3d.tool.callable")
        self._fn: Callable[[Mapping[str, Any]], Any] | None = None

    def prepare(self) -> None:
        self._fn = _resolve_callable(self._spec.entry)

    def run_trial(self, request: TrialRequest) -> TrialResult:
        if self._fn is None:
            self._fn = _resolve_callable(self._spec.entry)

        start = time.perf_counter()
        try:
            raw = self._fn(request.parameters)
        except Exception as exc:  # pragma: no cover - defensive
            duration = time.perf_counter() - start
            self._logger.exception("Callable trial failed: %s", exc)
            return TrialResult(
                outputs=TrialOutputs(run_dir=Path.cwd()),
                scalar_metrics={"runtime_seconds": duration},
                duration_seconds=duration,
                success=False,
                error=repr(exc),
            )

        duration = time.perf_counter() - start
        return _coerce_callable_return(raw, duration)


def _resolve_callable(entry: str) -> Callable[[Mapping[str, Any]], Any]:
    if ":" not in entry:
        raise ValueError(f"CallableSpec.entry must be 'package.module:function', got {entry!r}")
    module_path, attr = entry.split(":", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, attr, None)
    if fn is None or not callable(fn):
        raise ImportError(f"Cannot resolve callable {entry!r}")
    return fn  # type: ignore[return-value]


def _coerce_callable_return(raw: Any, duration: float) -> TrialResult:
    if isinstance(raw, TrialResult):
        return raw
    if isinstance(raw, TrialOutputs):
        return TrialResult(
            outputs=raw,
            scalar_metrics={"runtime_seconds": duration},
            duration_seconds=duration,
        )
    if isinstance(raw, Mapping):
        outputs_payload = raw.get("outputs")
        if isinstance(outputs_payload, TrialOutputs):
            outputs = outputs_payload
        else:
            outputs = TrialOutputs(
                run_dir=Path(raw.get("run_dir", ".")),
                predictions=tuple(Path(p) for p in raw.get("predictions", [])),
                figures=tuple(Path(p) for p in raw.get("figures", [])),
            )
        scalars = raw.get("scalar_metrics", {})
        metrics: dict[str, float] = {}
        if isinstance(scalars, Mapping):
            for k, v in scalars.items():
                try:
                    metrics[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        metrics.setdefault("runtime_seconds", duration)
        return TrialResult(
            outputs=outputs,
            scalar_metrics=metrics,
            duration_seconds=duration,
            success=bool(raw.get("success", True)),
            error=raw.get("error"),
        )
    raise TypeError(
        "Callable tool returned an unsupported value; expected TrialResult, "
        f"TrialOutputs, or Mapping, got {type(raw).__name__}"
    )


__all__ = ["CallableSpec", "CallableToolAdapter"]
