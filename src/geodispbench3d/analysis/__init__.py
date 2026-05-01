"""Tool-agnostic analysis: re-score cached predictions across tools.

Where a suite's ``run --rescore`` is bound to one tool's run directories
and runs phase 2 against tool-specific outputs, an analysis YAML works
purely from the predictions cache. Predictions live in the common
``{per_point: [...]}`` shape, so an analysis can mix iof3D and F2S3
results in one parquet output, with the metric set as the only knob.
"""

from __future__ import annotations

from .loader import (
    AnalysisConfig,
    PredictionFilter,
    PredictionRef,
    PredictionsConfig,
    ResultsConfig,
    load_analysis,
)

__all__ = [
    "AnalysisConfig",
    "PredictionFilter",
    "PredictionRef",
    "PredictionsConfig",
    "ResultsConfig",
    "load_analysis",
]
