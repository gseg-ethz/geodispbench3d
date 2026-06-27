"""Persist per-trial JSON records alongside a run directory.

Layout under each run directory::

    <run_dir>/ax_trial/
        summary.json        # this module — trial provenance + metrics
        config.yaml         # tool-specific (e.g. iof3D writes its
                            # resolved AppConfig there)
        predictions.json    # cached phase-2 output (see
                            # geodispbench3d.results.predictions_cache)

The summary structure is intentionally flat and forward-compatible:
fields added in future versions are written with sensible defaults; old
summaries missing those fields are read with ``None``. ``rescore_log`` is
the one append-only field — every ``rescore`` pass appends one entry
so the audit trail is preserved.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Provenance dataclasses (the new metadata blocks for the enriched record)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolProvenance:
    """Which tool produced this run, and which version of its config."""

    id: str
    yaml_path: str | None = None

    @classmethod
    def from_yaml_path(cls, tool_id: str, yaml_path: Path | None) -> ToolProvenance:
        return cls(
            id=tool_id,
            yaml_path=str(yaml_path) if yaml_path is not None else None,
        )


@dataclass(frozen=True)
class DatasetProvenance:
    """Which dataset case this trial scored against."""

    id: str
    case: str | None = None


@dataclass(frozen=True)
class ParserProvenance:
    """Phase-2 parser configuration that produced the prediction.

    Storing this lets ``rescore --reuse-parser-options`` reproduce the
    exact phase-2 output from a previous trial, while a plain ``rescore``
    pass can override with the suite's current options.
    """

    fn: str | None = None
    options: Mapping[str, Any] = field(default_factory=dict)


def parser_fn_repr(fn: Any) -> str | None:
    """Render a parser callable as a stable ``"package.module:attr"`` string.

    Single source for the provenance/cache key shared by the sweep runner and
    the rescore pass — they must agree byte-for-byte or a rescore would write
    to a different predictions-cache slot than the sweep that produced it.
    Uses ``__module__`` + ``__qualname__`` (not ``__name__``) so the rendering
    is stable across module-level functions, methods, and nested/local
    closures (whose ``__qualname__`` carries a dotted ``<locals>`` path).
    """

    if fn is None:
        return None
    module = getattr(fn, "__module__", None)
    qualname = getattr(fn, "__qualname__", getattr(fn, "__name__", None))
    if module and qualname:
        return f"{module}:{qualname}"
    return None


# ---------------------------------------------------------------------------
# I/O primitives
# ---------------------------------------------------------------------------


def trial_summary_file(run_dir: Path) -> Path:
    """Path to a run dir's trial summary, *without* creating anything.

    Pure path constructor for read/membership checks (e.g. walking a results
    tree to discover real run dirs). Use :func:`trial_record_path` instead when
    you intend to write — it ensures the ``ax_trial/`` parent exists.
    """

    return Path(run_dir) / "ax_trial" / "summary.json"


def trial_record_path(run_dir: Path) -> Path:
    path = trial_summary_file(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_trial_record(
    path: Path,
    *,
    on_non_fatal: Callable[[Exception], None] | None = None,
) -> dict[str, Any]:
    """Load a trial summary, degrading to ``{}`` when absent or unreadable.

    An absent file is normal (returns ``{}`` without calling ``on_non_fatal``).
    A present-but-corrupt summary (bad permissions, malformed JSON) is a
    fail-soft failure: it still degrades to ``{}``, but when ``on_non_fatal`` is
    supplied it is invoked with the caught exception so the caller can count it
    (F-08). Internal callers that read-modify-write (``update_trial_record``,
    ``append_rescore_entry``, ``read_provenance``) leave it at its default.
    """

    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        # UnicodeDecodeError is a sibling of json.JSONDecodeError under
        # ValueError: a present-but-non-UTF-8 file raises it during the
        # decode in fh.read(), before any JSON parsing. Catching it keeps the
        # fail-soft contract (F-08) instead of aborting the whole pass.
        if on_non_fatal is not None:
            on_non_fatal(exc)
        return {}


def write_trial_record(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=str)
    tmp.replace(path)


def trial_summary_path(results_root: Path, trial_index: int) -> Path:
    """Path of the dedicated trial-level summary artifact.

    Distinct from the per-case ``<run_dir>/ax_trial/summary.json``: this is a
    single per-trial JSON under ``<results_root>/trial_summaries/`` carrying the
    post-aggregation finite-case signal (F-05).
    """

    out_dir = Path(results_root) / "trial_summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"trial_{trial_index}.json"


def write_trial_summary(results_root: Path, trial_index: int, payload: Mapping[str, Any]) -> Path:
    """Atomically write the dedicated trial-level summary artifact.

    Stamps ``recorded_at`` (offset-aware UTC) when the caller has not supplied
    it, then writes via the same tmp+replace pattern as ``write_trial_record``.
    """

    path = trial_summary_path(results_root, trial_index)
    record = dict(payload)
    record.setdefault("recorded_at", datetime.now(UTC).isoformat(timespec="seconds"))
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True, default=str)
    tmp.replace(path)
    return path


def update_trial_record(run_dir: Path, updates: Mapping[str, Any]) -> None:
    path = trial_record_path(run_dir)
    payload = load_trial_record(path)
    payload.update(updates)
    write_trial_record(path, payload)


def append_rescore_entry(run_dir: Path, entry: Mapping[str, Any]) -> None:
    """Append a rescore audit entry without clobbering prior runs."""

    path = trial_record_path(run_dir)
    payload = load_trial_record(path)
    log = payload.get("rescore_log") or []
    log.append(dict(entry))
    payload["rescore_log"] = log
    write_trial_record(path, payload)


# ---------------------------------------------------------------------------
# Lifecycle helpers (called by the runner / adapters)
# ---------------------------------------------------------------------------


def initialize_trial_record(
    run_dir: Path,
    parameters: Mapping[str, Any],
    run_hash: str | None = None,
    *,
    tool: ToolProvenance | None = None,
    dataset: DatasetProvenance | None = None,
) -> None:
    """Mark a run dir as "running" and stamp provenance once at trial start."""

    timestamp = _utcnow()
    payload: dict[str, Any] = {
        "status": "running",
        "parameters": dict(parameters),
        "started_at": timestamp,
    }
    if run_hash is not None:
        payload["run_hash"] = run_hash
    if tool is not None:
        payload["tool"] = asdict(tool)
    if dataset is not None:
        payload["dataset"] = asdict(dataset)
    update_trial_record(run_dir, payload)


def store_trial_metadata(
    run_dir: Path,
    parameters: Mapping[str, Any],
    metrics: Mapping[str, float],
    runtime_seconds: float,
    *,
    predictions: Sequence[Path] = (),
    figures: Sequence[Path] = (),
    tool: ToolProvenance | None = None,
    dataset: DatasetProvenance | None = None,
    parser: ParserProvenance | None = None,
    extras: Mapping[str, Any] | None = None,
) -> None:
    """Persist a JSON summary of a successful trial."""

    payload: dict[str, Any] = {
        "status": "success",
        "parameters": dict(parameters),
        "metrics": dict(metrics),
        "runtime_seconds": runtime_seconds,
        "completed_at": _utcnow(),
        "predictions": [str(p) for p in predictions],
        "figures": [str(p) for p in figures],
    }
    if tool is not None:
        payload["tool"] = asdict(tool)
    if dataset is not None:
        payload["dataset"] = asdict(dataset)
    if parser is not None:
        payload["parser"] = _parser_payload(parser)
    if extras:
        payload.update(extras)
    update_trial_record(run_dir, payload)


def store_trial_failure(
    run_dir: Path,
    parameters: Mapping[str, Any],
    runtime_seconds: float,
    error: Exception,
    *,
    tool: ToolProvenance | None = None,
    dataset: DatasetProvenance | None = None,
    extras: Mapping[str, Any] | None = None,
) -> None:
    """Persist failure metadata when a trial aborts."""

    payload: dict[str, Any] = {
        "status": "failure",
        "parameters": dict(parameters),
        "runtime_seconds": runtime_seconds,
        "error": str(error),
        "completed_at": _utcnow(),
    }
    if tool is not None:
        payload["tool"] = asdict(tool)
    if dataset is not None:
        payload["dataset"] = asdict(dataset)
    if extras:
        payload.update(extras)
    update_trial_record(run_dir, payload)


# ---------------------------------------------------------------------------
# Provenance read-back (used by the rescore + analyze passes)
# ---------------------------------------------------------------------------


def read_provenance(
    run_dir: Path,
) -> tuple[ToolProvenance | None, DatasetProvenance | None, ParserProvenance | None]:
    """Return ``(tool, dataset, parser)`` provenance from a run's summary.

    Older records lacking these blocks return ``None`` for the missing
    pieces; callers should be ready for that and fall back to whatever the
    current suite/analysis YAML declares.
    """

    record = load_trial_record(trial_record_path(run_dir))
    return (
        _tool_from_record(record),
        _dataset_from_record(record),
        _parser_from_record(record),
    )


def _tool_from_record(record: Mapping[str, Any]) -> ToolProvenance | None:
    block = record.get("tool")
    if not isinstance(block, Mapping):
        return None
    return ToolProvenance(
        id=str(block.get("id", "")),
        yaml_path=block.get("yaml_path"),
    )


def _dataset_from_record(record: Mapping[str, Any]) -> DatasetProvenance | None:
    block = record.get("dataset")
    if not isinstance(block, Mapping):
        return None
    return DatasetProvenance(id=str(block.get("id", "")), case=block.get("case"))


def _parser_from_record(record: Mapping[str, Any]) -> ParserProvenance | None:
    block = record.get("parser")
    if not isinstance(block, Mapping):
        return None
    return ParserProvenance(
        fn=block.get("fn"),
        options=dict(block.get("options") or {}),
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _parser_payload(parser: ParserProvenance) -> dict[str, Any]:
    return {"fn": parser.fn, "options": dict(parser.options or {})}


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


__all__ = [
    "DatasetProvenance",
    "ParserProvenance",
    "ToolProvenance",
    "append_rescore_entry",
    "initialize_trial_record",
    "load_trial_record",
    "parser_fn_repr",
    "read_provenance",
    "store_trial_failure",
    "store_trial_metadata",
    "trial_record_path",
    "trial_summary_file",
    "trial_summary_path",
    "update_trial_record",
    "write_trial_record",
    "write_trial_summary",
]
