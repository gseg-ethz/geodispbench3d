"""F2S3-specific bench wiring for geodispbench3d.

The package contains only what makes F2S3 *F2S3* — the output parser that
reads the per-tile ASCII files and samples them at GT points. Datasets,
metrics, and suites live in ``/benchmarks/`` so they can be shared with other
tools (e.g. iof3D) on the same Mattertal data.
"""

from __future__ import annotations

from .output_parser import parse_f2s3_output

__all__ = ["parse_f2s3_output"]
