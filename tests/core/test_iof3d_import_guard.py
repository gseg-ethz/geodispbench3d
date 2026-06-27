"""Guard tests for the dormant iof3D adapter (PKG-01, D-02/D-03).

These run in the dev env (where iof3D *is* installed) by *simulating* its
absence: a monkeypatched ``builtins.__import__`` (in-process) or a
``sys.meta_path`` finder (out-of-process) raises ``ModuleNotFoundError`` for
the ``iof3D`` / ``pc2img`` top-level packages, leaving everything else
importable.

The contract under test:

* ``import geodispbench3d_iof3d`` MUST succeed even when iof3D/pc2img are
  absent (PEP 562 lazy re-export — no eager private-dep import).
* Accessing a *gated* symbol (``Iof3dCallableAdapter``) MUST raise an
  ``ImportError`` carrying an actionable message that chains the original.
* The *non-gated* parser symbol (``parse_iof3d_output``, which imports only
  public ``pchandler``) MUST still resolve under the same block (finding 9).
* ``iof3d-ax`` (``geodispbench3d_iof3d.cli.main``) MUST exit cleanly with the
  actionable message, in-process and out-of-process, with no raw traceback
  (findings 10).
* ``pyproject.toml`` extras MUST disable ``iof3d`` and pin ``f2s3`` pchandler.

Module-cache hygiene: cached ``iof3D*`` / ``pc2img*`` / ``geodispbench3d_iof3d*``
entries are removed via ``monkeypatch.delitem(..., raising=False)`` so pytest
auto-restores them and no state leaks into later real-iof3D tests (finding 8 —
never bare-``pop``).
"""

from __future__ import annotations

import builtins
import importlib
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_GATED_TOPS = ("iof3D", "pc2img")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _clear_cached_iof3d_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop cached modules so the guard re-runs against the blocked import.

    Uses ``monkeypatch.delitem(..., raising=False)`` (finding 8) so the real
    modules are restored after the test and later iof3D tests are unaffected.
    """

    for name in list(sys.modules):
        top = name.split(".", 1)[0]
        if top in _GATED_TOPS or name.startswith("geodispbench3d_iof3d"):
            monkeypatch.delitem(sys.modules, name, raising=False)


def _install_import_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch ``builtins.__import__`` to raise for iof3D/pc2img only."""

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.split(".", 1)[0] in _GATED_TOPS:
            raise ModuleNotFoundError(f"simulated absence: {name}", name=name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)


def test_public_import_succeeds_use_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_cached_iof3d_modules(monkeypatch)
    _install_import_block(monkeypatch)

    pkg = importlib.import_module("geodispbench3d_iof3d")  # MUST succeed

    with pytest.raises(ImportError, match="not yet publicly available"):
        _ = pkg.Iof3dCallableAdapter  # gated symbol — pulls iof3D, MUST fail


def test_parser_path_resolves_without_iof3d(monkeypatch: pytest.MonkeyPatch) -> None:
    # finding 9: the non-gated parser symbol imports only public pchandler, so
    # it MUST resolve even while iof3D/pc2img are blocked. Guards against a
    # regression that maps parse_iof3d_output to a gated submodule.
    _clear_cached_iof3d_modules(monkeypatch)
    _install_import_block(monkeypatch)

    pkg = importlib.import_module("geodispbench3d_iof3d")
    parser = pkg.parse_iof3d_output  # MUST NOT raise
    assert callable(parser)


def test_iof3d_ax_launcher_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_cached_iof3d_modules(monkeypatch)
    _install_import_block(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        cli = importlib.import_module("geodispbench3d_iof3d.cli")
        cli.main()

    assert "not yet publicly available" in str(excinfo.value)


def test_iof3d_ax_subprocess_exits_1_no_traceback() -> None:
    # finding 10: an out-of-process launch under simulated iof3D absence must
    # exit 1, print the actionable message to stderr, and show NO traceback.
    preamble = (
        "import sys, runpy\n"
        "class _Blocker:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.', 1)[0] in ('iof3D', 'pc2img'):\n"
        "            raise ModuleNotFoundError('blocked: ' + name, name=name)\n"
        "        return None\n"
        "sys.meta_path.insert(0, _Blocker())\n"
        "runpy.run_module('geodispbench3d_iof3d.cli', run_name='__main__')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", preamble],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )

    assert proc.returncode == 1, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "not yet publicly available" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_extras_iof3d_commented_f2s3_pinned() -> None:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())
    optional = data["project"]["optional-dependencies"]

    assert "iof3d" not in optional, "the iof3d extra must be commented out, not present"
    assert optional["f2s3"] == ["pchandler ~= 2.1"]
