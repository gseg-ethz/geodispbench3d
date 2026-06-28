"""Streamlit dashboard for exploring sweep results.

Parquet path resolution order:

1. ``--parquet`` CLI flag passed by ``geodispbench3d dashboard`` (sets
   ``$GEODISPBENCH3D_PARQUET``).
2. ``$GEODISPBENCH3D_PARQUET`` environment variable.
3. ``./outputs/results.parquet`` relative to the current working directory.

Users can also override interactively in the sidebar.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import cast

try:
    import streamlit as st
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "streamlit is required for the dashboard. Install with "
        "'pip install geodispbench3d[dashboard]'"
    ) from exc

try:
    import altair as alt
except ImportError:  # pragma: no cover - optional dependency
    alt = None  # type: ignore[assignment]

import pandas as pd

from geodispbench3d.results import load_results_dataframe


def _default_parquet() -> Path:
    return Path(
        os.environ.get(
            "GEODISPBENCH3D_PARQUET",
            str(Path.cwd() / "outputs" / "results.parquet"),
        )
    )


_PANDAS_AGG_MAP = {
    "AVG": "mean",
    "MEDIAN": "median",
    "MIN": "min",
    "MAX": "max",
    "STD": "std",
}


def _available_metrics(df: pd.DataFrame) -> list[str]:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    preferred = [col for col in df.columns if col.endswith("]") or col.endswith(" [m]")]
    seen: set[str] = set()
    ordered: list[str] = []
    for col in preferred + numeric_cols:
        if col in df.columns and col not in seen:
            ordered.append(col)
            seen.add(col)
    return ordered


def _apply_filters(df: pd.DataFrame, filters: dict[str, Iterable[str]]) -> pd.DataFrame:
    filtered = df.copy()
    for column, selected in filters.items():
        if selected:
            mask = cast("pd.Series", filtered[column]).isin(list(selected))
            filtered = filtered.loc[mask]
    return cast("pd.DataFrame", filtered)


def _sanitize_alias(value: str) -> str:
    alias = re.sub(r"[^0-9a-zA-Z_]+", "_", value).strip("_")
    return alias or "value"


def _summarise(
    df: pd.DataFrame, metric: str, group_by: list[str], aggregations: list[str]
) -> pd.DataFrame:
    if not group_by:
        group_by = ["dummy"]
        df = df.assign(dummy="all")
    ops = [
        (_sanitize_alias(f"{agg.lower()}_{metric}"), _PANDAS_AGG_MAP[agg]) for agg in aggregations
    ]
    return df.groupby(group_by)[metric].agg(ops).reset_index()


def _render_chart(summary: pd.DataFrame, metric: str, group_by: list[str]) -> None:
    if alt is None or summary.empty or len(group_by) != 1:
        return
    y_columns = [col for col in summary.columns if col not in group_by]
    melted = summary.melt(
        id_vars=group_by, value_vars=y_columns, var_name="stat", value_name="value"
    )
    chart = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X(f"{group_by[0]}:N", sort="-y"),
            y=alt.Y("value:Q"),
            color="stat:N",
            tooltip=[group_by[0], "stat", "value"],
        )
        .properties(height=400)
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="geodispbench3d Sweep Explorer", layout="wide")
    st.title("geodispbench3d Sweep Explorer")

    parquet_input = st.sidebar.text_input("Parquet file", str(_default_parquet()))
    parquet_path = Path(parquet_input)
    if not parquet_path.exists():
        st.error(f"Parquet file not found: {parquet_path}")
        return

    df = load_results_dataframe(parquet_path)
    st.caption(f"Loaded {len(df)} records from {parquet_path}")

    metrics = _available_metrics(df)
    if not metrics:
        st.error("No numeric metrics available in the dataset.")
        return

    metric = st.sidebar.selectbox("Metric", metrics, index=0)

    filter_columns = [
        col for col in df.columns if df[col].dtype == object and df[col].nunique() <= 50
    ]
    filters: dict[str, Iterable[str]] = {}
    for col in filter_columns:
        options = sorted(df[col].dropna().unique())
        selected = st.sidebar.multiselect(f"Filter by {col}", options)
        if selected:
            filters[col] = selected

    filtered_df = _apply_filters(df, filters)
    st.subheader("Filtered Results")
    st.dataframe(filtered_df, width="stretch")

    group_options = [col for col in filter_columns if col in df.columns]
    group_by = st.sidebar.multiselect("Group by", options=group_options, default=group_options[:1])

    agg_choices = list(_PANDAS_AGG_MAP.keys())
    aggregations = st.sidebar.multiselect(
        "Aggregations", options=agg_choices, default=["AVG", "MEDIAN"]
    )
    if not aggregations:
        st.warning("Select at least one aggregation function.")
        return

    summary = _summarise(filtered_df, metric=metric, group_by=group_by, aggregations=aggregations)
    st.subheader("Aggregated Metrics")
    st.dataframe(summary, width="stretch")

    _render_chart(summary, metric, group_by)

    csv_bytes = summary.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download summary (CSV)",
        data=csv_bytes,
        file_name="geodispbench3d_summary.csv",
        mime="text/csv",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
