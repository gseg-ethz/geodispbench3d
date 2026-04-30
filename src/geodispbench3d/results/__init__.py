"""Generic results persistence for geodispbench3d sweeps."""

from __future__ import annotations

from .store import (
    ResultsStore,
    append_record_rows,
    load_results_dataframe,
)

__all__ = [
    "ResultsStore",
    "append_record_rows",
    "load_results_dataframe",
]
