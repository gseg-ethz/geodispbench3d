"""Persist per-trial JSON records alongside a run directory."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any


def trial_record_path(run_dir: Path) -> Path:
    out_dir = Path(run_dir) / "ax_trial"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "summary.json"


def load_trial_record(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def write_trial_record(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    tmp.replace(path)


def update_trial_record(run_dir: Path, updates: Mapping[str, Any]) -> None:
    path = trial_record_path(run_dir)
    payload = load_trial_record(path)
    payload.update(updates)
    write_trial_record(path, payload)


def initialize_trial_record(
    run_dir: Path,
    parameters: Mapping[str, Any],
    run_hash: str | None = None,
) -> None:
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload: dict[str, Any] = {
        "status": "running",
        "parameters": dict(parameters),
        "started_at": timestamp,
    }
    if run_hash is not None:
        payload["run_hash"] = run_hash
    update_trial_record(run_dir, payload)


def store_trial_metadata(
    run_dir: Path,
    parameters: Mapping[str, Any],
    metrics: Mapping[str, float],
    runtime_seconds: float,
    *,
    predictions: Sequence[Path] = (),
    figures: Sequence[Path] = (),
    extras: Mapping[str, Any] | None = None,
) -> None:
    """Persist a JSON summary of a successful trial."""

    completed_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload: dict[str, Any] = {
        "status": "success",
        "parameters": dict(parameters),
        "metrics": dict(metrics),
        "runtime_seconds": runtime_seconds,
        "completed_at": completed_at,
        "predictions": [str(p) for p in predictions],
        "figures": [str(p) for p in figures],
    }
    if extras:
        payload.update(extras)
    update_trial_record(run_dir, payload)


def store_trial_failure(
    run_dir: Path,
    parameters: Mapping[str, Any],
    runtime_seconds: float,
    error: Exception,
    *,
    extras: Mapping[str, Any] | None = None,
) -> None:
    """Persist failure metadata when a trial aborts."""

    completed_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload: dict[str, Any] = {
        "status": "failure",
        "parameters": dict(parameters),
        "runtime_seconds": runtime_seconds,
        "error": str(error),
        "completed_at": completed_at,
    }
    if extras:
        payload.update(extras)
    update_trial_record(run_dir, payload)


__all__ = [
    "initialize_trial_record",
    "load_trial_record",
    "store_trial_failure",
    "store_trial_metadata",
    "trial_record_path",
    "update_trial_record",
    "write_trial_record",
]
