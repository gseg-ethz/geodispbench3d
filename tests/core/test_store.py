"""Direct tests for the parquet-backed results store (F-21).

Covers the three behaviours of ``results/store.py``: creating a fresh parquet,
appending to an existing one (round-trip), and the empty-rows short-circuit
that writes nothing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from geodispbench3d.results.store import (
    ResultsStore,
    append_record_rows,
    load_results_dataframe,
)


def test_append_creates_new_parquet(tmp_path: Path) -> None:
    path = tmp_path / "results.parquet"
    store = ResultsStore(parquet_path=path)

    store.append([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])

    assert path.exists()
    df = pd.read_parquet(path)
    assert list(df["a"]) == [1, 2]
    assert list(df["b"]) == ["x", "y"]
    # Column order / schema is preserved on the round-trip.
    assert list(df.columns) == ["a", "b"]


def test_append_to_existing_roundtrips_both_batches(tmp_path: Path) -> None:
    path = tmp_path / "results.parquet"
    store = ResultsStore(parquet_path=path)

    store.append([{"a": 1}])
    store.append([{"a": 2}, {"a": 3}])

    df = pd.read_parquet(path)
    # Both batches present, in append order, after the concat path.
    assert list(df["a"]) == [1, 2, 3]


def test_append_empty_rows_is_noop(tmp_path: Path) -> None:
    path = tmp_path / "results.parquet"
    store = ResultsStore(parquet_path=path)

    store.append([])

    # The short-circuit must not write a parquet at all.
    assert not path.exists()


def test_append_record_rows_creates_parent_dirs(tmp_path: Path) -> None:
    # Parent directory does not exist yet -> mkdir(parents=True) path.
    path = tmp_path / "nested" / "dir" / "r.parquet"

    append_record_rows(path, pd.DataFrame([{"a": 1}]))

    assert path.exists()
    assert list(load_results_dataframe(path)["a"]) == [1]


def test_load_results_dataframe_missing_returns_empty(tmp_path: Path) -> None:
    df = load_results_dataframe(tmp_path / "does-not-exist.parquet")
    assert df.empty
