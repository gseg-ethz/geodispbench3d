"""Skip the iof3D adapter test suite if the iof3d extra is not installed."""

from __future__ import annotations

import pytest

iof3D = pytest.importorskip(
    "iof3D",
    reason="iof3D must be installed from its (currently private) source; "
    "the public [iof3d] extra is disabled until iof3D publishes",
)
