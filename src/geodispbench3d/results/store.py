"""Parquet-backed results store.

Append-only by design: each sweep run writes new rows to the configured
parquet path. Downstream consumers (dashboard, duckdb queries) read the file
directly. We do not assume duckdb is available — readers can use pandas.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class ResultsStore:
    """Append rows to a parquet file."""

    parquet_path: Path

    def append(self, rows: Sequence[Mapping[str, object]]) -> None:
        if not rows:
            return
        df = pd.DataFrame(list(rows))
        append_record_rows(self.parquet_path, df)


def append_record_rows(parquet_path: Path, df: pd.DataFrame) -> None:
    """Append a DataFrame to ``parquet_path`` (creating the file if needed)."""

    parquet_path = Path(parquet_path)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    if parquet_path.exists():
        existing = pd.read_parquet(parquet_path)
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df
    combined.to_parquet(parquet_path, index=False)


def load_results_dataframe(parquet_path: Path | str) -> pd.DataFrame:
    """Read a results parquet into a DataFrame."""

    parquet_path = Path(parquet_path)
    if not parquet_path.exists():
        return pd.DataFrame()
    return pd.read_parquet(parquet_path)


__all__ = [
    "ResultsStore",
    "append_record_rows",
    "load_results_dataframe",
]
