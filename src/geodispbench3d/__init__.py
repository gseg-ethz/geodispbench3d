"""geodispbench3d: a generic benchmark framework for 3D displacement / optical-flow tools.

The package is tool-agnostic: any tool that can be described by a
:class:`~geodispbench3d.tool.base.ToolAdapter` can be swept, evaluated against a
dataset, and scored with configurable metrics.

Public surface is intentionally small; see the submodule docstrings for details.
"""

from __future__ import annotations

__all__ = [
    "tool",
    "dataset",
    "metrics",
    "sweep",
    "suite",
    "results",
]
