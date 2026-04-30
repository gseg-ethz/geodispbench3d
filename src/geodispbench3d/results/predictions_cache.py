"""Predictions cache: phase-2 output stored separately from run dirs.

Phase 2 (parsing the tool's raw outputs into a sampled-at-GT prediction)
is the expensive step that downstream re-scoring and analysis want to
skip. We cache its output as JSON at a path independent of the run dir
itself, so cleaning up old run dirs to free disk doesn't destroy the
cheap-to-keep predictions.

Layout::

    <predictions_root>/
        <tool_id>/<dataset_id>/<case>/<run_hash>.json

A file always carries:

    {
      "schema_version": 1,
      "prediction": { "per_point": [...], "source": {...} },
      "provenance": {
        "tool":    {...},
        "dataset": {...},
        "parser":  {"fn": "...", "options": {...}},
        "run_dir": "..." ,
        "cached_at": "..."
      }
    }

The schema is JSON-serialisable by design — we ``json.dumps(default=str)``
so Path / numpy values survive.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

CACHE_SCHEMA_VERSION = 1


def cache_path(
    predictions_root: Path,
    *,
    tool_id: str,
    dataset_id: str,
    case: str,
    run_hash: str,
) -> Path:
    """Return the canonical cache file path for a trial's prediction."""

    safe_case = _safe_segment(case)
    return (
        Path(predictions_root)
        / _safe_segment(tool_id)
        / _safe_segment(dataset_id)
        / safe_case
        / f"{_safe_segment(run_hash)}.json"
    )


def write_prediction(
    predictions_root: Path,
    *,
    tool_id: str,
    dataset_id: str,
    case: str,
    run_hash: str,
    prediction: Any,
    provenance: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    """Persist a single trial's prediction to the cache.

    Returns the path the file was written to. Atomic via ``.tmp`` + rename.
    """

    out = cache_path(
        predictions_root,
        tool_id=tool_id,
        dataset_id=dataset_id,
        case=case,
        run_hash=run_hash,
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "prediction": _to_jsonable(prediction),
        "provenance": _to_jsonable(
            {
                **(dict(provenance) if provenance else {}),
                "cached_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            }
        ),
    }
    if extra:
        payload["extra"] = _to_jsonable(extra)

    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=str)
    tmp.replace(out)
    return out


def read_prediction(path: Path) -> dict[str, Any] | None:
    """Read a cache file. Returns ``None`` when the file is absent."""

    p = Path(path)
    if not p.is_file():
        return None
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def find_predictions(
    predictions_root: Path,
    *,
    tool_id: str | None = None,
    dataset_id: str | None = None,
    case: str | None = None,
) -> list[Path]:
    """Enumerate cached predictions, optionally filtered by provenance segment.

    Each `None` filter matches any value in that segment. Useful for the
    analyze flow, which walks "every cached prediction for this dataset
    + this case across all tools."
    """

    root = Path(predictions_root)
    if not root.is_dir():
        return []

    tool_glob = _safe_segment(tool_id) if tool_id else "*"
    dataset_glob = _safe_segment(dataset_id) if dataset_id else "*"
    case_glob = _safe_segment(case) if case else "*"

    pattern = f"{tool_glob}/{dataset_glob}/{case_glob}/*.json"
    return sorted(root.glob(pattern))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_segment(value: str) -> str:
    """Sanitize a string for use as a directory segment.

    The cache layout is rooted under a user-controlled directory; we
    don't want a tool_id like "../../etc" to break out. Replace anything
    that isn't ascii alphanumerics, underscore, dash, or dot.
    """

    return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in str(value))


def _to_jsonable(obj: Any) -> Any:
    """Coerce common non-JSON types (numpy arrays, Path, dataclasses) to JSON."""

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    # Fallback: stringify so json.dump's default=str doesn't have to.
    return str(obj)


__all__ = [
    "CACHE_SCHEMA_VERSION",
    "cache_path",
    "find_predictions",
    "read_prediction",
    "write_prediction",
]
