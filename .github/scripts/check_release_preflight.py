#!/usr/bin/env python3
"""Production-publish preflight guard for ``publish-pypi.yml``.

Blocks the real-PyPI upload unless the release event and the built
distributions satisfy every gate:

    (a) the release tag matches ``vX.Y.Z`` (a plain release, no pre/dev/local
        suffix);
    (b) every built wheel/sdist in ``dist/`` carries that exact ``X.Y.Z``;
    (c) the GitHub Release is neither a draft nor a prerelease;
    (d) the tag commit is reachable from ``origin/main``.

Any failing check prints an actionable message naming the gate and exits
non-zero, which fails the workflow step before ``gh-action-pypi-publish``
runs (review MEDIUM 05-03 / threat T-05-13). It is designed to run inside the
``publish-to-pypi`` job after the dist artifact is downloaded and the
repository is checked out with full history.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

__all__ = ["main"]

_TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
_SDIST_SUFFIX = ".tar.gz"


def _fail(check: str, detail: str) -> NoReturn:
    """Print an actionable failure for a named check and exit non-zero."""
    print(f"preflight: FAIL [{check}] {detail}", file=sys.stderr)
    raise SystemExit(1)


def _load_release(event_path: str | None) -> dict[str, Any]:
    """Read the ``release`` object from the GitHub event payload."""
    if not event_path:
        _fail("event", "GITHUB_EVENT_PATH is unset; not running in a release event")
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    release = payload.get("release")
    if not isinstance(release, dict):
        _fail("event", f"event payload has no release object: {event_path!r}")
    return release


def _tag_version(release: dict[str, Any]) -> str:
    """Validate the release tag is ``vX.Y.Z`` and return the bare ``X.Y.Z``."""
    tag = release.get("tag_name")
    if not isinstance(tag, str):
        _fail("tag-format", f"release has no string tag_name: {release.get('tag_name')!r}")
    match = _TAG_RE.match(tag)
    if match is None:
        _fail("tag-format", f"tag {tag!r} does not match the required vX.Y.Z form")
    return match.group(1)


def _assert_not_prerelease(release: dict[str, Any]) -> None:
    """Reject draft or prerelease GitHub Releases."""
    if release.get("draft"):
        _fail("not-draft", "release is a draft; refusing to publish to production PyPI")
    if release.get("prerelease"):
        _fail("not-prerelease", "release is marked prerelease; refusing production publish")


def _dist_versions(dist_dir: Path) -> set[str]:
    """Parse the version token from every wheel/sdist in ``dist_dir``."""
    versions: set[str] = set()
    files = sorted(p for p in dist_dir.glob("*") if p.is_file())
    if not files:
        _fail("built-version", f"no distribution files found in {str(dist_dir)!r}")
    for path in files:
        name = path.name
        if name.endswith(".whl"):
            # PEP 427: name-version-pytag-abitag-platformtag.whl; the project
            # name carries no hyphen, so field [1] is the version.
            versions.add(name[: -len(".whl")].split("-")[1])
        elif name.endswith(_SDIST_SUFFIX):
            versions.add(name[: -len(_SDIST_SUFFIX)].rsplit("-", 1)[1])
    if not versions:
        _fail("built-version", f"no wheel/sdist version parsed from {str(dist_dir)!r}")
    return versions


def _assert_tag_reachable_from_main(tag: str) -> None:
    """Fail unless the tag commit is an ancestor of ``origin/main``."""
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if resolved.returncode != 0:
        _fail("tag-reachable", f"cannot resolve a commit for tag {tag!r}")
    tag_sha = resolved.stdout.strip()
    # Populate FETCH_HEAD with the current main tip; fail-safe if this errors.
    subprocess.run(["git", "fetch", "--quiet", "origin", "main"], check=False)
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", tag_sha, "FETCH_HEAD"],
        check=False,
    )
    if ancestry.returncode != 0:
        _fail("tag-reachable", f"tag commit {tag_sha!r} is not reachable from origin/main")


def main() -> int:
    """Run every preflight gate; return 0 only when all pass."""
    release = _load_release(os.environ.get("GITHUB_EVENT_PATH"))
    tag_version = _tag_version(release)
    _assert_not_prerelease(release)

    built = _dist_versions(Path("dist"))
    mismatched = sorted(v for v in built if v != tag_version)
    if mismatched:
        _fail(
            "built-version",
            f"built versions {mismatched!r} do not equal the tag version {tag_version!r}",
        )

    _assert_tag_reachable_from_main(str(release["tag_name"]))
    print(f"preflight: OK tag=v{tag_version} built={sorted(built)!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
