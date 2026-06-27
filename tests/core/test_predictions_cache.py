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


def test_read_prediction_non_utf8_degrades_and_counts(tmp_path: Path) -> None:
    """A present-but-non-UTF-8 cache file raises UnicodeDecodeError during the
    decode; read_prediction must degrade to None AND invoke on_non_fatal so the
    pass-level diagnostics count it rather than the exception aborting the pass
    (CR-01 / F-08)."""

    bad = tmp_path / "bad.json"
    bad.write_bytes(b"\xff\xfe\x00bad")  # invalid UTF-8, not OSError, not JSONDecodeError

    counted: list[Exception] = []
    result = read_prediction(bad, on_non_fatal=counted.append)

    assert result is None
    assert len(counted) == 1
    assert isinstance(counted[0], UnicodeDecodeError)


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


def test_whole_segment_path_specials_are_neutralised(tmp_path: Path) -> None:
    """A segment whose entire value is ``..`` / ``.`` must not climb out of the
    cache root (WR-02). The char filter alone preserves these verbatim, so they
    are explicitly prefixed with ``_``."""

    for special in ("..", "."):
        out = cache_path(
            tmp_path,
            tool_id=special,
            dataset_id="x",
            case="y",
            run_hash="z",
        )
        # No path-special component survives, so the file stays under the root.
        assert ".." not in out.parts
        assert "." not in out.parts
        resolved_root = tmp_path.resolve()
        assert resolved_root in out.resolve().parents
        assert out.resolve().is_relative_to(resolved_root)
