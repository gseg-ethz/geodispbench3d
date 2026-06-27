"""Typed per-pass diagnostics for fail-soft (non-fatal) degradation.

The framework's fail-soft convention — "never let observability/caching/
provenance failures break the primary path" — means a swept, rescored, or
analyzed run keeps going even when a side effect (a cache write, a provenance
stamp, a corrupt-summary read) fails. Historically those failures were
swallowed and invisible. :class:`PassDiagnostics` makes them *countable*: each
pass holds one instance, every fail-soft site records into it, and the CLI
surfaces an aggregate ``"N non-fatal failures"`` line (F-08 / D-03).

This is an observability counter, not a control-flow signal: recording a
failure never changes whether a trial/run is considered successful.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class PassDiagnostics:
    """Mutable counter of non-fatal (swallowed, fail-soft) failures in one pass.

    ``non_fatal_failures`` is the running total; ``by_kind`` breaks it down by a
    caller-chosen kind string (e.g. ``"evaluation"``, ``"prediction_cache"``,
    ``"provenance_stamp"``, ``"run_hash"``, ``"rescore_log"``). The two are kept
    in lockstep by :meth:`add`.
    """

    non_fatal_failures: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)

    def add(self, kind: str, n: int = 1) -> None:
        """Record ``n`` non-fatal failures of a given ``kind`` (no-op when n<=0)."""

        if n <= 0:
            return
        self.non_fatal_failures += n
        self.by_kind[kind] = self.by_kind.get(kind, 0) + n

    def merge(self, other: PassDiagnostics) -> None:
        """Fold another :class:`PassDiagnostics` into this one."""

        self.non_fatal_failures += other.non_fatal_failures
        for kind, count in other.by_kind.items():
            self.by_kind[kind] = self.by_kind.get(kind, 0) + count


def merge_kind_counts(target: PassDiagnostics, by_kind: Mapping[str, int]) -> None:
    """Convenience: fold a plain ``{kind: count}`` mapping into ``target``."""

    for kind, count in by_kind.items():
        target.add(kind, count)


__all__ = ["PassDiagnostics", "merge_kind_counts"]
