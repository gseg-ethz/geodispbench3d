"""Skip the F2S3 adapter test suite if pchandler isn't importable.

The F2S3 adapter itself is pure-Python (subprocess-driven) and ships with
the framework, but the *output parser* uses ``pchandler.data_io.Csv`` and
``pchandler.filters.SphereFilter``, so adapter-shape tests need pchandler.

Adding a real F2S3 binary check would also gate any subprocess-execution
test, but those aren't part of this scaffolding.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "pchandler",
    reason="install with: pip install 'geodispbench3d[f2s3]' (provides pchandler ~= 2.1)",
)
