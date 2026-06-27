"""Console entrypoint (``iof3d-ax``) for iof3D-flavored geodispbench3d sweeps.

This is a thin, dependency-free launcher. The hydra-decorated implementation
and its heavy ``hydra`` / ``iof3D`` imports live in
:mod:`geodispbench3d_iof3d._sweep_cli`, imported lazily below so the
``iof3d-ax`` entry point resolves on a public install where iof3D is not yet
available. When iof3D is absent, the import failure is converted into a clean
:class:`SystemExit` carrying an actionable message instead of a raw traceback
(D-03).
"""

from __future__ import annotations


def main() -> None:
    try:
        from ._sweep_cli import main as _impl  # imports hydra + iof3D lazily
    except ImportError as exc:
        raise SystemExit(
            "iof3d-ax requires iof3D, which is not yet publicly available. "
            "Install iof3D to enable this command.\n"
            f"(original error: {exc})"
        ) from None
    _impl()


if __name__ == "__main__":  # pragma: no cover
    main()
