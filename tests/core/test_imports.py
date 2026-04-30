"""Framework-only import smoke tests.

Confirms that nothing in ``geodispbench3d`` reaches into iof3D, pchandler,
or pc2img — so a user running ``pip install geodispbench3d`` (no extras)
gets a working framework regardless of whether the tool stacks are
present.
"""

from __future__ import annotations

import importlib


def test_framework_imports_without_tool_extras() -> None:
    importlib.import_module("geodispbench3d")
    importlib.import_module("geodispbench3d.cli")
    importlib.import_module("geodispbench3d.tool")
    importlib.import_module("geodispbench3d.dataset")
    importlib.import_module("geodispbench3d.metrics")
    importlib.import_module("geodispbench3d.metrics.builtins")
    importlib.import_module("geodispbench3d.sweep")
    importlib.import_module("geodispbench3d.suite")
    importlib.import_module("geodispbench3d.results")


def test_framework_has_no_iof3d_or_pchandler_imports(tmp_path) -> None:
    """Static check: no module under ``geodispbench3d`` imports iof3D, pchandler, or pc2img."""

    import geodispbench3d
    from pathlib import Path

    pkg_root = Path(geodispbench3d.__file__).parent
    forbidden = ("from iof3D", "import iof3D", "from pchandler", "import pchandler", "from pc2img", "import pc2img")
    offenders: list[str] = []
    for path in pkg_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in forbidden:
            if needle in text:
                offenders.append(f"{path}: {needle}")
    assert not offenders, "framework imports tool-specific modules:\n" + "\n".join(offenders)
