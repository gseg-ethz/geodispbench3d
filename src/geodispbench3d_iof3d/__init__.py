"""iof3D-specific adapter and configs for geodispbench3d.

This is the bridge that lets a generic geodispbench3d sweep target the iof3D
flow pipeline. The package ships:

* :class:`Iof3dCallableAdapter` — in-process adapter (default for iof3D since
  the pipeline is fork-safe and avoids per-trial CUDA reinitialisation).
* ``conf/tool/iof3d.yaml`` — tool config wired to the adapter.
* ``conf/dataset/rothorn.yaml`` plus ``data/`` CSVs — the GT cases that used
  to live as a hardcoded array in ``iof3D_analysis.results.metrics``.
* ``conf/metrics/standard.yaml`` and ``conf/suite/default.yaml`` — defaults
  reproducing the previous ``iof3d-ax`` sweep.

All iof3D imports stay inside this package; ``geodispbench3d`` itself imports
nothing from iof3D.
"""

from __future__ import annotations

from .adapter import Iof3dCallableAdapter, build_app_config_from_parameters
from .factory import build_iof3d_adapter
from .output_parser import parse_iof3d_output

__all__ = [
    "Iof3dCallableAdapter",
    "build_app_config_from_parameters",
    "build_iof3d_adapter",
    "parse_iof3d_output",
]
