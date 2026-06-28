"""Packaging-metadata assertions for the first public PyPI release.

Pins the LIC-01…04 truths and prohibitions reconciled in phase 04:
README, ``pyproject.toml``, ``LICENSE``, and ``CITATION.cff`` must all agree
on BSD-3-Clause, the publish-blocking ``Private :: Do Not Upload`` classifier
must be gone, and the public listing must carry honest maturity/audience/topic
classifiers plus public Documentation/Changelog URLs.

Pure stdlib (``tomllib`` + ``pathlib``); no extras, no network.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

PUBLIC_HOST_PATH = "github.com/gseg-ethz/geodispbench3d"


def _repo_root() -> Path:
    """Walk up from this file until a directory containing pyproject.toml is found."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root (no pyproject.toml found walking up)")


def _pyproject() -> dict:
    return tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))


def _readme_text() -> str:
    return (_repo_root() / "README.md").read_text(encoding="utf-8")


def _readme_section(heading: str, *, to_end: bool = False) -> str:
    """Return README text from ``## {heading}`` to the next ``## `` heading (or EOF)."""
    text = _readme_text()
    marker = f"## {heading}"
    start = text.find(marker)
    assert start != -1, f"README has no '{marker}' section"
    body = text[start + len(marker) :]
    if to_end:
        return body
    next_heading = body.find("\n## ")
    return body if next_heading == -1 else body[:next_heading]


def test_no_private_classifier() -> None:
    classifiers = _pyproject()["project"]["classifiers"]
    assert "Private :: Do Not Upload" not in classifiers


def test_requires_python_is_312_only() -> None:
    # Phase 5 (D-03 SUPERSEDED): the package is Python 3.12-only because
    # pchandler 2.1.0 (the f2s3 extra) declares requires-python >=3.12,<3.13.
    requires_python = _pyproject()["project"]["requires-python"]
    assert requires_python == "~=3.12", f"requires-python is {requires_python!r}, expected '~=3.12'"


def test_no_python_311_classifier() -> None:
    classifiers = set(_pyproject()["project"]["classifiers"])
    assert "Programming Language :: Python :: 3.11" not in classifiers, (
        "3.11 classifier must be absent (package is 3.12-only)"
    )
    assert "Programming Language :: Python :: 3.12" in classifiers, (
        "3.12 classifier must be present"
    )


def test_ruff_target_version_is_py312() -> None:
    target = _pyproject()["tool"]["ruff"]["target-version"]
    assert target == "py312", f"[tool.ruff] target-version is {target!r}, expected 'py312'"


def test_required_maturity_audience_topic_classifiers_present() -> None:
    classifiers = set(_pyproject()["project"]["classifiers"])
    required = {
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
    }
    missing = required - classifiers
    assert not missing, f"missing required classifiers: {sorted(missing)}"


def test_project_urls_documentation_and_changelog_public() -> None:
    urls = {k.lower(): v for k, v in _pyproject()["project"]["urls"].items()}
    doc = urls.get("documentation", "")
    changelog = urls.get("changelog", "")
    assert doc.startswith("https://"), f"Documentation URL not https: {doc!r}"
    assert changelog.startswith("https://"), f"Changelog URL not https: {changelog!r}"
    assert PUBLIC_HOST_PATH in doc, f"Documentation URL not public: {doc!r}"
    assert PUBLIC_HOST_PATH in changelog, f"Changelog URL not public: {changelog!r}"


def test_readme_license_is_bsd_not_proprietary() -> None:
    license_section = _readme_section("License", to_end=True)
    assert "BSD-3-Clause" in license_section
    assert "Proprietary" not in license_section


def test_readme_notes_iof3d_extra_unavailable() -> None:
    install_section = _readme_section("Install").lower()
    # Must flag the [iof3d] extra as not yet available, with NO timeline.
    assert "iof3d" in install_section
    assert (
        "unavailable" in install_section
        or "not yet" in install_section
        or ("until" in install_section and "published" in install_section)
    ), "install section must note the [iof3d] extra is currently unavailable"
    # Must NOT promise a time horizon.
    assert "month" not in install_section, "install note must not state a timeline"
    assert "~6" not in install_section, "install note must not state a timeline"


def test_readme_no_stale_iof3d_extra_references() -> None:
    text = _readme_text()
    # Finding 1a: the combined-extras command must not advertise the dormant iof3d extra.
    assert "[iof3d,f2s3,dashboard]" not in text
    # Finding 1b: repository-layout text must not call the adapter "gated by [iof3d]".
    assert "gated by `[iof3d]`" not in text
    assert "gated by [iof3d]" not in text


def test_citation_and_license_are_bsd() -> None:
    root = _repo_root()
    # CITATION.cff: parse the license value tolerantly of quoting/whitespace (finding 3).
    license_value: str | None = None
    for line in (root / "CITATION.cff").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("license:"):
            license_value = stripped.split(":", 1)[1].strip().strip("'\"")
            break
    assert license_value == "BSD-3-Clause", f"CITATION.cff license: {license_value!r}"
    # LICENSE first line carries the BSD 3-Clause heading.
    first_line = (root / "LICENSE").read_text(encoding="utf-8").splitlines()[0]
    assert "BSD 3-Clause" in first_line, f"LICENSE first line: {first_line!r}"
