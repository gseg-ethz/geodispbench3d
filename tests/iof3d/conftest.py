"""Skip the iof3D adapter test suite if the iof3d extra is not installed."""

from __future__ import annotations

import pytest

iof3D = pytest.importorskip("iof3D", reason="install with: pip install 'geodispbench3d[iof3d]'")
