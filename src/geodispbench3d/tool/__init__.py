"""Tool-adapter interface and built-in adapters."""

from __future__ import annotations

from .base import (
    ToolAdapter,
    TrialOutputs,
    TrialRequest,
    TrialResult,
)
from .callable_adapter import CallableSpec, CallableToolAdapter
from .cli_adapter import (
    CliInvocationSpec,
    CliToolAdapter,
    HashedRunDirSpec,
    hash_parameters,
)

__all__ = [
    "CallableSpec",
    "CallableToolAdapter",
    "CliInvocationSpec",
    "CliToolAdapter",
    "HashedRunDirSpec",
    "ToolAdapter",
    "TrialOutputs",
    "TrialRequest",
    "TrialResult",
    "hash_parameters",
]
