"""Top-level pytest configuration.

Each test directory under ``tests/`` runs against a different install
profile:

* ``tests/core/`` — only the framework wheel is required (no tool extras).
* ``tests/iof3d/`` — requires ``pip install geodispbench3d[iof3d]``.
* ``tests/f2s3/`` — requires the F2S3 adapter (no extra Python deps; the
  binary itself isn't needed for adapter-shape tests).

Tests in the per-extra directories self-skip when the underlying tool
package is not importable, so a developer running ``pytest`` in the
framework-only environment still gets a green baseline.
"""

from __future__ import annotations
