#!/usr/bin/env python3
"""Reconcile the rendered ci.yml job names with the branch-protection contexts.

The branch-protection rulesets (``.github/rulesets/protect-main.json`` and
``protect-develop.json``, Plan 04) pin a ``required_status_checks`` list whose
``context`` strings MUST equal the rendered CI job names char-for-char. A
one-character drift (e.g. ``Test (core)`` vs ``Test (core, 3.12)``) silently
makes the merge gate permanently unsatisfiable. This guard catches that drift
DURING the phase — it runs in the CI lint job — rather than at ship-time
ruleset enablement (threat T-05-10).

It asserts three sets are mutually equal AND equal to the canonical four
contexts:

    Lint (ruff + pyright)
    Test (core, 3.12)
    Test (f2s3, 3.12)
    Build wheel + install smoke

  (1) the rendered REQUIRED ci.yml job names — the ``lint`` and ``build`` job
      ``name:`` values plus the ``test`` job's ``name:`` template rendered against
      each ``strategy.matrix.include`` entry. The ``docs`` (Docs build) job is a
      blocking-on-PR check but NOT a required_status_check, so it is excluded.
  (2) ``protect-main.json`` required_status_checks contexts.
  (3) ``protect-develop.json`` required_status_checks contexts.

On any mismatch it prints the offending symmetric difference and exits non-zero;
it exits 0 only on exact three-way agreement with the canonical set.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

__all__ = ["main"]

_CI_WORKFLOW = Path(".github/workflows/ci.yml")
_RULESET_MAIN = Path(".github/rulesets/protect-main.json")
_RULESET_DEVELOP = Path(".github/rulesets/protect-develop.json")

# The job keys whose rendered names are required_status_checks (docs excluded).
_REQUIRED_JOB_KEYS = ("lint", "test", "build")
# The job key handled by matrix rendering rather than a literal name.
_MATRIX_JOB_KEY = "test"

# The canonical interface contract — identical to the Plan 04 ruleset payloads
# and the Task 3 acceptance criteria.
_EXPECTED_CONTEXTS: frozenset[str] = frozenset(
    {
        "Lint (ruff + pyright)",
        "Test (core, 3.12)",
        "Test (f2s3, 3.12)",
        "Build wheel + install smoke",
    }
)

_MATRIX_PLACEHOLDER_RE = re.compile(r"\$\{\{\s*matrix\.(\w+)\s*\}\}")


def _fail(message: str) -> None:
    """Print an actionable failure and exit non-zero."""
    print(f"ci-ruleset: FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    """Render the required CI job names, load both rulesets, assert agreement."""
    rendered = _rendered_required_job_names(_CI_WORKFLOW)
    main_contexts = _ruleset_contexts(_RULESET_MAIN)
    develop_contexts = _ruleset_contexts(_RULESET_DEVELOP)

    if rendered != _EXPECTED_CONTEXTS:
        _fail(
            "rendered ci.yml required job names != the canonical contexts; "
            f"symmetric difference: {sorted(rendered ^ _EXPECTED_CONTEXTS)!r} "
            f"(rendered={sorted(rendered)!r})"
        )
    if main_contexts != _EXPECTED_CONTEXTS:
        _fail(
            f"{_RULESET_MAIN.name} contexts != the canonical contexts; "
            f"symmetric difference: {sorted(main_contexts ^ _EXPECTED_CONTEXTS)!r}"
        )
    if develop_contexts != _EXPECTED_CONTEXTS:
        _fail(
            f"{_RULESET_DEVELOP.name} contexts != the canonical contexts; "
            f"symmetric difference: {sorted(develop_contexts ^ _EXPECTED_CONTEXTS)!r}"
        )

    print(f"ci-ruleset: OK rendered names == both rulesets == {sorted(_EXPECTED_CONTEXTS)!r}")
    return 0


def _rendered_required_job_names(path: Path) -> frozenset[str]:
    """Render the required_status_check job names from ci.yml (docs excluded)."""
    document = _load_yaml(path)
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        _fail(f"{path.name!r} has no jobs mapping")

    names: set[str] = set()
    for key in _REQUIRED_JOB_KEYS:
        job = jobs.get(key)
        if not isinstance(job, dict):
            _fail(f"{path.name!r} is missing required job {key!r}")
        if key == _MATRIX_JOB_KEY:
            names.update(_render_matrix_names(key, job))
        else:
            name = job.get("name")
            if not isinstance(name, str) or not name:
                _fail(f"job {key!r} in {path.name!r} has no string name:")
            names.add(name)
    return frozenset(names)


def _render_matrix_names(key: str, job: dict[str, Any]) -> set[str]:
    """Expand a job's name template over its strategy.matrix.include entries."""
    template = job.get("name")
    if not isinstance(template, str) or not template:
        _fail(f"matrix job {key!r} has no string name: template")

    include = (job.get("strategy") or {}).get("matrix", {}).get("include")
    if not isinstance(include, list) or not include:
        _fail(f"matrix job {key!r} has no strategy.matrix.include list")

    rendered: set[str] = set()
    for entry in include:
        if not isinstance(entry, dict):
            _fail(f"matrix include entry in job {key!r} is not a mapping: {entry!r}")

        def _substitute(match: re.Match[str], _entry: dict[str, Any] = entry) -> str:
            axis = match.group(1)
            if axis not in _entry:
                _fail(f"matrix include entry {_entry!r} has no axis {axis!r}")
            return str(_entry[axis])

        rendered.add(_MATRIX_PLACEHOLDER_RE.sub(_substitute, template))
    return rendered


def _ruleset_contexts(path: Path) -> frozenset[str]:
    """Extract the required_status_checks context strings from a ruleset JSON."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"could not read ruleset {str(path)!r}: {exc}")

    rules = payload.get("rules")
    if not isinstance(rules, list):
        _fail(f"{path.name!r} has no rules list")

    for rule in rules:
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
            checks = (rule.get("parameters") or {}).get("required_status_checks")
            if not isinstance(checks, list):
                _fail(f"{path.name!r} required_status_checks is not a list")
            contexts = {c.get("context") for c in checks if isinstance(c, dict)}
            if not all(isinstance(c, str) for c in contexts):
                _fail(f"{path.name!r} has a non-string context entry")
            return frozenset(contexts)  # type: ignore[arg-type]

    _fail(f"{path.name!r} has no required_status_checks rule")
    return frozenset()  # unreachable; _fail raises


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a mapping or fail."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        _fail(f"could not parse {str(path)!r}: {exc}")
    if not isinstance(document, dict):
        _fail(f"{path.name!r} did not parse to a mapping")
    return document


if __name__ == "__main__":
    raise SystemExit(main())
