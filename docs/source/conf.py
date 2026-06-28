"""Sphinx configuration for the geodispbench3d documentation.

Minimal myst-parser config: the docs are narrative Markdown, so no autodoc or
nitpick tuning is needed. The version is derived from the installed package
metadata (setuptools_scm) via importlib.metadata — never hardcoded.
"""

from importlib.metadata import version as _version

project = "geodispbench3d"
author = "Nicholas Meyer"
copyright = "2026, Nicholas Meyer"

release = _version("geodispbench3d")
version = ".".join(release.split(".")[:2])

extensions = ["myst_parser"]
myst_enable_extensions = ["colon_fence", "deflist"]
# Generate GitHub-style implicit anchors for headings (h1-h3) so the existing
# in-tree `file.md#section` cross-references resolve under -W.
myst_heading_anchors = 3

html_theme = "sphinx_rtd_theme"

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
