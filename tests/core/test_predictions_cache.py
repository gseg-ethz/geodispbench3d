"""Predictions cache: round-trip + filter behaviour."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from geodispbench3d.results.predictions_cache import (
    cache_path,
    find_predictions,
    read_prediction,
    write_prediction,
)


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    out = write_prediction(
        tmp_path,
        tool_id="iof3d-v2",
        dataset_id="mattertal",
        case="mattertal-all",
        run_hash="abc1",
        prediction={"per_point": [{"label": "A", "vector": [0.1, 0.0, 0.0]}]},
        provenance={"parser": {"fn": "foo:bar", "options": {"radius": 15.0}}},
    )
    assert out.is_file()
    assert out == cache_path(
        tmp_path,
        tool_id="iof3d-v2",
        dataset_id="mattertal",
        case="mattertal-all",
        run_hash="abc1",
    )

    payload = read_prediction(out)
    assert payload is not None
    assert payload["schema_version"] == 1
    assert payload["prediction"]["per_point"][0]["label"] == "A"
    assert payload["provenance"]["parser"]["options"]["radius"] == 15.0
    assert "cached_at" in payload["provenance"]

    # F-09: the stamped timestamp is offset-aware (+00:00, not a manual "Z")
    # and round-trips through datetime.fromisoformat.
    cached_at = payload["provenance"]["cached_at"]
    assert not cached_at.endswith("Z")
    parsed = datetime.fromisoformat(cached_at)
    assert parsed.tzinfo is not None


def test_find_predictions_filters_by_segment(tmp_path: Path) -> None:
    for tool in ("iof3d-v2", "f2s3"):
        for run_hash in ("a", "b"):
            write_prediction(
                tmp_path,
                tool_id=tool,
                dataset_id="mattertal",
                case="mattertal-all",
                run_hash=run_hash,
                prediction={"per_point": []},
            )
    assert len(find_predictions(tmp_path)) == 4
    assert len(find_predictions(tmp_path, tool_id="iof3d-v2")) == 2
    assert len(find_predictions(tmp_path, tool_id="f2s3", case="mattertal-all")) == 2
    assert find_predictions(tmp_path, tool_id="missing") == []


def test_unsafe_segments_are_sanitised(tmp_path: Path) -> None:
    """tool_id like ``../escape`` must not break out of the cache root."""

    out = write_prediction(
        tmp_path,
        tool_id="../escape",
        dataset_id="x",
        case="y",
        run_hash="z",
        prediction={"per_point": []},
    )
    assert tmp_path in out.parents
    # The dot path got replaced; the file lives under tmp_path/<sanitised>/x/y/z.json
    assert ".." not in out.parts
