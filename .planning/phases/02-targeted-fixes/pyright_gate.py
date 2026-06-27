#!/usr/bin/env python3
"""Pyright baseline-diff gate for Phase 02 (D-11).

Runs ``pyright --outputjson`` over the whole project and compares the current
set of ERROR-severity diagnostics against the recorded baseline in the sibling
``pyright-baseline.json``. The gate fails only on NEW errors above the baseline;
clearing a baseline error is allowed and never fails the gate.

Diagnostics are reduced to a line-number-independent signature of
``(repo-relative file path, rule, whitespace-normalized message)`` so that
refactors which merely shift line numbers do not register as new errors. A
multiset (``collections.Counter``) is used so that N identical errors in the
baseline still permit exactly N (and fail on the N+1th).

Stdlib only. Run from any cwd via the project's conda env, e.g.::

    conda run -n iof3d_cosicorr3d-dev312 python \\
        .planning/phases/02-targeted-fixes/pyright_gate.py

Exit code 0 == no new errors (gate passes); exit code 1 == new errors (fails).
"""

from __future__ import annotations

import collections
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# repo root is three levels up: .planning/phases/02-targeted-fixes/ -> repo root
REPO_ROOT = SCRIPT_DIR.parents[2]
BASELINE_PATH = SCRIPT_DIR / "pyright-baseline.json"

Signature = tuple[str, str, str]


def _normalize_path(file_path: str) -> str:
    """Return a repo-root-relative POSIX path, or the input if outside the repo."""

    if not file_path:
        return ""
    candidate = Path(file_path)
    try:
        return candidate.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()


def _signature(diagnostic: dict) -> Signature:
    """Line-number-independent signature of one diagnostic."""

    rule = diagnostic.get("rule", "<no-rule>")
    message = " ".join(str(diagnostic.get("message", "")).split())
    return (_normalize_path(diagnostic.get("file", "")), rule, message)


def _error_signatures(diagnostics: list[dict]) -> collections.Counter[Signature]:
    counter: collections.Counter[Signature] = collections.Counter()
    for diagnostic in diagnostics:
        if diagnostic.get("severity") == "error":
            counter[_signature(diagnostic)] += 1
    return counter


def _run_pyright() -> list[dict]:
    """Run ``pyright --outputjson`` whole-project and return generalDiagnostics."""

    result = subprocess.run(
        ["pyright", "--outputjson"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        sys.stderr.write("pyright produced no JSON output. stderr:\n" + result.stderr + "\n")
        raise SystemExit(2)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Could not parse pyright JSON output: {exc}\n")
        raise SystemExit(2) from exc
    return payload.get("generalDiagnostics", [])


def _load_baseline() -> collections.Counter[Signature]:
    if not BASELINE_PATH.is_file():
        sys.stderr.write(f"Baseline not found: {BASELINE_PATH}\n")
        raise SystemExit(2)
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return _error_signatures(payload.get("generalDiagnostics", []))


def main() -> int:
    baseline = _load_baseline()
    current = _error_signatures(_run_pyright())

    new_errors = current - baseline  # Counter subtraction: current MINUS baseline
    if new_errors:
        total = sum(new_errors.values())
        print("New pyright errors above baseline:")
        for (file_path, rule, message), count in sorted(new_errors.items()):
            for _ in range(count):
                print(f"  {file_path}: [{rule}] {message}")
        print(f"FAIL: {total} new pyright error(s) above baseline")
        return 1

    print("PASS: no new pyright errors above baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
