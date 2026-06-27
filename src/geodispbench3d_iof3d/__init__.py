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

The public symbols are re-exported lazily via PEP 562 ``__getattr__`` so that
``import geodispbench3d_iof3d`` succeeds on a public install where iof3D (and
pc2img) are not yet available (D-02). The heavy iof3D imports only fire when a
gated symbol is actually accessed; if iof3D/pc2img are absent at that point the
failure is translated into an actionable :class:`ImportError`. The parser
symbol (:func:`parse_iof3d_output`) imports only public ``pchandler``, so it
keeps working even while iof3D/pc2img are blocked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "Iof3dCallableAdapter",
    "build_app_config_from_parameters",
    "build_iof3d_adapter",
    "parse_iof3d_output",
]

# Public symbol -> the submodule that defines it. Resolved lazily on first
# attribute access (PEP 562) so module import never pulls iof3D/pc2img eagerly.
_LAZY: dict[str, str] = {
    "Iof3dCallableAdapter": "adapter",
    "build_app_config_from_parameters": "adapter",
    "build_iof3d_adapter": "factory",
    "parse_iof3d_output": "output_parser",
}

# Top-level packages whose absence is translated into the actionable hint. A
# missing ``pchandler`` is deliberately NOT here: the non-gated parser path
# depends on public pchandler, so its absence must surface as its own genuine
# ModuleNotFoundError rather than being mislabelled "iof3D missing" (finding 5).
_IOF3D_GATED_TOPS = frozenset({"iof3D", "pc2img"})

_IOF3D_MISSING_HINT = (
    "The iof3D adapter requires iof3D (and pc2img), which are not yet publicly "
    "available. Install iof3D to enable this adapter; until then "
    "`import geodispbench3d_iof3d` works but its adapter cannot be constructed."
)


def __getattr__(name: str) -> Any:  # PEP 562 module-level lazy re-export
    submodule = _LAZY.get(name)
    if submodule is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    try:
        mod = import_module(f".{submodule}", __name__)
    except ModuleNotFoundError as exc:
        # Translate ONLY a genuine iof3D/pc2img absence into the actionable
        # hint, chaining the original error for diagnosability. Any other
        # failure (a transitive bug, a missing pchandler, a regression inside a
        # target module) re-raises unchanged so it is never mislabelled as
        # "iof3D missing" (review 04-02 finding 5; threat T-04-03-R).
        top = (exc.name or "").split(".", 1)[0]
        if top in _IOF3D_GATED_TOPS:
            raise ImportError(f"{_IOF3D_MISSING_HINT} (original error: {exc})") from exc
        raise
    return getattr(mod, name)


def __dir__() -> list[str]:
    return sorted(__all__)


if TYPE_CHECKING:  # keep pyright / IDE resolution intact (Pitfall 5)
    from .adapter import Iof3dCallableAdapter, build_app_config_from_parameters
    from .factory import build_iof3d_adapter
    from .output_parser import parse_iof3d_output
