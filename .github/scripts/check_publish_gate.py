#!/usr/bin/env python3
"""Supply-chain guard: publish mechanisms may live only in the publish workflows.

Scans every ``.github/workflows/*.yml`` and asserts that any step which can push
a distribution to a package index appears ONLY in the two allowed publish
workflows (``publish-pypi.yml`` / ``publish-testpypi.yml``). An accidental
``pypa/gh-action-pypi-publish`` or ``twine upload`` slipping into ``ci.yml`` (or
any other workflow) would let an untrusted PR/push reach PyPI; this gate fails
the lint job before that can happen (threat T-05-03).

Recognized publish mechanisms (hardened beyond a literal ``twine upload`` match,
review MEDIUM 05-05):

  * a ``uses:`` referencing ``pypa/gh-action-pypi-publish`` at ANY ref;
  * a ``run:`` line invoking ``twine ... upload`` in any spelling —
    ``twine upload``, ``python -m twine upload``, ``python3 -m twine upload``,
    and shell-indirection forms such as ``sh -c "twine upload"``.

Documented limitations (printed in the failure message): a fully variable-hidden
invocation (``TW=twine; $TW upload``) and a reusable-workflow call
(``uses: ./.github/workflows/...`` that itself publishes) are out of scope for
this static scan — they would need call-graph analysis.

Exit status: 0 when no publish mechanism appears outside the allowed files;
non-zero (with an actionable, file/step-named message) otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

__all__ = ["main"]

# Publish mechanisms outside these files are a gate violation.
ALLOWED_PUBLISH_FILES: frozenset[str] = frozenset({"publish-pypi.yml", "publish-testpypi.yml"})

_WORKFLOWS_DIR = Path(".github/workflows")
_PUBLISH_ACTION = "pypa/gh-action-pypi-publish"
# `twine ... upload` on one logical command line; catches `python -m twine upload`,
# `python3 -m twine upload`, and `sh -c "twine upload ..."` indirection.
_TWINE_UPLOAD_RE = re.compile(r"\btwine\b[^\n]*\bupload\b")

_LIMITATION_NOTE = (
    "note: this scan does not catch fully variable-hidden twine calls "
    "(e.g. TW=twine; $TW upload) or reusable-workflow indirection "
    "(uses: ./.github/workflows/...); review those by hand."
)


def main() -> int:
    """Scan the workflows and report any out-of-bounds publish mechanism."""
    if not _WORKFLOWS_DIR.is_dir():
        print(
            f"publish-gate: FAIL no workflows directory at {str(_WORKFLOWS_DIR)!r}",
            file=sys.stderr,
        )
        return 1

    violations: list[str] = []
    for path in sorted(_WORKFLOWS_DIR.glob("*.yml")):
        if path.name in ALLOWED_PUBLISH_FILES:
            continue
        violations.extend(_scan_workflow(path))

    if violations:
        print("publish-gate: FAIL publish mechanism(s) outside the allowed files", file=sys.stderr)
        print(
            f"  allowed files: {sorted(ALLOWED_PUBLISH_FILES)!r}",
            file=sys.stderr,
        )
        for line in violations:
            print(f"  - {line}", file=sys.stderr)
        print(f"  {_LIMITATION_NOTE}", file=sys.stderr)
        return 1

    print(f"publish-gate: OK no publish mechanism outside {sorted(ALLOWED_PUBLISH_FILES)!r}")
    return 0


def _scan_workflow(path: Path) -> list[str]:
    """Return human-readable violation descriptions for one workflow file."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"could not parse workflow {str(path)!r}: {exc}") from exc
    if not isinstance(document, dict):
        return []

    found: list[str] = []
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return found

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        # A job may itself be a reusable-workflow call (out of scope; flag softly).
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            mechanism = _step_publish_mechanism(step)
            if mechanism is not None:
                found.append(
                    f"{path.name}: job {job_name!r} step #{index} "
                    f"({_step_label(step)!r}) -> {mechanism}"
                )
    return found


def _step_publish_mechanism(step: dict[str, Any]) -> str | None:
    """Return a description if the step is a publish mechanism, else None."""
    uses = step.get("uses")
    if isinstance(uses, str) and _PUBLISH_ACTION in uses:
        return f"uses {uses!r}"

    run = step.get("run")
    if isinstance(run, str):
        for raw_line in run.splitlines():
            line = raw_line.strip()
            if _TWINE_UPLOAD_RE.search(line):
                return f"run line {line!r}"
    return None


def _step_label(step: dict[str, Any]) -> str:
    """Best-effort human label for a step (name, else id, else uses/run head)."""
    for key in ("name", "id", "uses"):
        value = step.get(key)
        if isinstance(value, str) and value:
            return value
    run = step.get("run")
    if isinstance(run, str) and run:
        return run.splitlines()[0]
    return "<unnamed step>"


if __name__ == "__main__":
    raise SystemExit(main())
