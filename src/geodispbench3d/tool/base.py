"""Tool adapter interface for geodispbench3d.

A tool adapter describes how to invoke a tool under test for a single trial.
Adapters are the only place that knows about a specific tool's CLI, config
schema, or in-process entry point. The sweep engine and metric evaluation layer
consume the adapter interface exclusively.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrialRequest:
    """A trial invocation described in adapter-neutral terms.

    ``parameters`` is the raw Ax parameterization for this trial (dotted keys,
    primitive values). ``case`` identifies which dataset case is being
    evaluated; ``None`` means the trial does not depend on a specific case
    (e.g. a pure-runtime sweep).
    """

    parameters: Mapping[str, Any]
    case_name: str | None = None
    work_dir: Path | None = None


@dataclass(frozen=True)
class TrialOutputs:
    """Filesystem outputs produced by a single trial."""

    run_dir: Path
    predictions: Sequence[Path] = ()
    figures: Sequence[Path] = ()
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrialResult:
    """What a trial produced: outputs + runtime-level scalar metrics.

    Scalar metrics reported directly by the adapter (e.g. wallclock runtime)
    are placed in ``scalar_metrics``. Record-level metric evaluation happens
    downstream and is orthogonal to adapter concerns.
    """

    outputs: TrialOutputs
    scalar_metrics: Mapping[str, float]
    duration_seconds: float
    success: bool = True
    error: str | None = None


class ToolAdapter(ABC):
    """Adapter contract for running a tool under test in a sweep.

    Two canonical implementations ship with geodispbench3d:

    * :class:`~geodispbench3d.tool.cli_adapter.CliToolAdapter` — spawns a
      subprocess and passes trial parameters as CLI overrides. Safe default.
    * :class:`~geodispbench3d.tool.callable_adapter.CallableToolAdapter` —
      imports a Python callable and invokes it in-process. Faster but requires
      the tool to be thread/process-safe inside the sweep runner.

    Third-party tools subclass ``ToolAdapter`` to expose custom invocation
    logic (e.g. applying the trial parameters to a domain-specific config
    object, as ``geodispbench3d_iof3d`` does for iof3D's ``AppConfig``).
    """

    #: Human-readable identifier, used in logs.
    id: str = "tool-adapter"

    #: If ``True``, the adapter may be called in-process from the sweep runner
    #: without a subprocess boundary. Adapters that call into CUDA, hold
    #: large in-memory state, or are not fork-safe should leave this ``False``.
    in_process_safe: bool = False

    @abstractmethod
    def run_trial(self, request: TrialRequest) -> TrialResult:
        """Execute a single trial and return its result."""

    def prepare(self) -> None:
        """Hook called once before the sweep starts. Override if needed."""

    def teardown(self) -> None:
        """Hook called once after the sweep finishes. Override if needed."""


__all__ = [
    "ToolAdapter",
    "TrialRequest",
    "TrialResult",
    "TrialOutputs",
]
