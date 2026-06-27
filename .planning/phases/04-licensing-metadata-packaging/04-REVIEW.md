---
phase: 04-licensing-metadata-packaging
reviewed: 2026-06-27T00:00:00Z
depth: deep
files_reviewed: 11
files_reviewed_list:
  - README.md
  - docs/tools/iof3d.md
  - pyproject.toml
  - src/geodispbench3d_iof3d/__init__.py
  - src/geodispbench3d_iof3d/_sweep_cli.py
  - src/geodispbench3d_iof3d/cli.py
  - tests/conftest.py
  - tests/core/test_iof3d_import_guard.py
  - tests/core/test_packaging_metadata.py
  - tests/f2s3/conftest.py
  - tests/iof3d/conftest.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-06-27
**Depth:** deep
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Deep, cross-file review of the publication-readiness changes (PEP 562 dormant-iof3D
import guard, the `iof3d-ax` launcher split, and PyPI packaging metadata).

The three central correctness concerns hold up well:

1. **Import guard (`__init__.py`)** — `__getattr__` relabels a `ModuleNotFoundError`
   into the actionable `ImportError` **only** when the missing top-level package is
   `iof3D` or `pc2img` (`_IOF3D_GATED_TOPS`); a missing `pchandler` or any transitive
   bug re-raises unchanged. Verified against `output_parser.py`, which imports only
   public `pchandler` (`PointCloudData`, `load_file`, `filters.SphereFilter`) and no
   `iof3D`/`pc2img`, so the non-gated parser contract is genuinely satisfiable on the
   `[f2s3]` install profile. This logic is correct and well-tested.
2. **Launcher (`cli.py`/`_sweep_cli.py`)** — does produce a clean `SystemExit`
   (string arg → exit 1, no traceback) when iof3D is absent. Tested in-process and
   out-of-process. The heavy hydra/iof3D body moved verbatim into `_sweep_cli.py`.
3. **Packaging metadata** — `Private :: Do Not Upload` is gone, the `[iof3d]` extra is
   commented out (not `[]`), and `[f2s3]` pins `pchandler ~= 2.1`. README/LICENSE/
   CITATION.cff all agree on BSD-3-Clause.

The defects below are concentrated in over-broad error handling in the launcher (which
undermines the careful relabeling the `__init__` guard takes pains to get right), a
deprecated license-metadata shape that bites exactly on a fresh publish build, and a
documentation-accuracy mismatch. No blockers.

## Warnings

### WR-01: `iof3d-ax` launcher swallows *all* `ImportError`, masking genuine bugs

**File:** `src/geodispbench3d_iof3d/cli.py:16-24`
**Issue:** The launcher catches every `ImportError` from `from ._sweep_cli import main`
and reports "iof3D ... is not yet publicly available. Install iof3D to enable this
command." But `_sweep_cli` imports `.adapter`, `hydra`, `geodispbench3d.sweep.parameters`,
and `geodispbench3d.sweep.runner` — any import-time failure in *any* of those raises
`ImportError` and is mislabeled. Concrete failure mode: on a developer machine where
iof3D **is** installed, a missing `pchandler` (pulled transitively through the adapter)
or a refactor that renames `load_sweep_config`/`AxSweepRunner` would surface as
"install iof3D" — actively misleading, since iof3D is already installed. This is the
exact mislabeling the `__init__.py` guard deliberately avoids (`_IOF3D_GATED_TOPS`
top-name check + re-raise), so the two guards are inconsistent.
**Fix:** Mirror the `__init__` guard — only convert genuine `iof3D`/`pc2img` absence,
re-raise everything else:
```python
def main() -> None:
    try:
        from ._sweep_cli import main as _impl
    except ModuleNotFoundError as exc:
        if (exc.name or "").split(".", 1)[0] not in {"iof3D", "pc2img"}:
            raise  # a real bug / unrelated missing dep — do not mislabel
        raise SystemExit(
            "iof3d-ax requires iof3D, which is not yet publicly available. "
            "Install iof3D to enable this command.\n"
            f"(original error: {exc})"
        ) from None
    _impl()
```
(Narrowing to `ModuleNotFoundError` + top-name check preserves the clean-exit test
while letting real `ImportError`s/`AttributeError`s through.)

### WR-02: Deprecated license metadata + unpinned build backend risk the publish build

**File:** `pyproject.toml:1-3,10,19`
**Issue:** Two publication-readiness concerns compound:
- `license = { text = "BSD-3-Clause" }` (line 10) and the
  `"License :: OSI Approved :: BSD License"` classifier (line 19) are both deprecated
  under PEP 639. setuptools ≥ 77 emits `SetuptoolsDeprecationWarning` for the license
  table form and for license classifiers when building; the installed backend here is
  **78.1.1**, so a build will warn today and is on track to hard-error in a future
  setuptools.
- `build-system.requires = ["setuptools", "setuptools_scm"]` is unpinned (line 2), so
  `python -m build` for the public release picks up whatever setuptools is current —
  i.e. it will ride straight into the above deprecation/removal. For a "demonstrably
  correct, reproducible" first publish this is fragile.
**Fix:** Migrate to the SPDX expression and drop the redundant classifier, and pin a
minimum (and ideally a tested upper bound) on the build backend:
```toml
[build-system]
requires = ["setuptools>=77", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"

[project]
license = "BSD-3-Clause"        # SPDX expression (PEP 639)
# remove "License :: OSI Approved :: BSD License" from classifiers
```
Note: `test_packaging_metadata.py` does not assert the license *shape*, only that the
README says BSD and not "Proprietary", so this change won't break the suite — but it
also means the deprecation is currently untested. Consider asserting the SPDX form once
migrated.

### WR-03: `_collect_run_kwargs` can silently drop the entire `run:` section

**File:** `src/geodispbench3d_iof3d/_sweep_cli.py:36-39`
**Issue:** `if isinstance(cfg, Mapping): getter = cfg.get` else falls back to a stub
that returns the default for every key. `cfg` here is an OmegaConf `DictConfig`
(`main()` passes `cfg.get("run") or {}`). OmegaConf does not register `DictConfig` as a
`collections.abc.Mapping` in all versions, and the author's own `# pragma: no cover -
defensive` comment signals doubt that the branch is unreachable. If the `isinstance`
check is ever False, `pcd_paths`, `features`, `cache_dir`, `work_root`, and
`max_feature_workers` all silently collapse to their defaults — the entire `run:`
section is ignored with no warning, and an `iof3d-ax` sweep would run against the wrong
inputs. (This is moved-verbatim legacy code, not introduced this phase, but it is in
the reviewed launcher path.)
**Fix:** Duck-type on the method actually used instead of relying on ABC registration:
```python
getter = getattr(cfg, "get", None)
if not callable(getter):  # pragma: no cover - defensive
    def getter(_k, default=None):
        return default
```

## Info

### IN-01: README "[iof3d]" install block contradicts its own dormant-extra note

**File:** `README.md:23-31`
**Issue:** The heading "With the iof3D adapter (transitively pulls in iof3D and its
dependencies)" followed by `pip install 'geodispbench3d[iof3d]'` describes behavior the
disabled extra does not have — pip will emit a "does not provide the extra 'iof3d'"
warning and install only the base package. The blockquote Note (lines 29-31) corrects
this, but the imperative command + parenthetical still read as if the extra works today,
which is the kind of thing a reviewer of the PyPI page will flag.
**Fix:** Soften the heading to reflect dormancy (e.g. "Once iof3D is published, the
adapter will be installable via:") or fold the command into the Note so the page never
asserts an install path that currently no-ops.

### IN-02: Launcher body depends on private iof3D API

**File:** `src/geodispbench3d_iof3d/_sweep_cli.py:23`
**Issue:** `from iof3D.v2.cli_hydra import _build_app_config, _to_path` imports two
underscore-prefixed (private) symbols from an external package. These have no stability
contract and can break silently across iof3D releases. Pre-existing, but worth tracking
now that the package is heading for public release where iof3D version skew is more
likely.
**Fix:** Prefer a public iof3D entry point if one exists, or vendor a thin local
equivalent of `_build_app_config`/`_to_path` so the bench wiring owns its config-assembly
contract.

### IN-03: `int(getter("max_feature_workers", 16))` raises on an explicit null

**File:** `src/geodispbench3d_iof3d/_sweep_cli.py:78`
**Issue:** If `run.max_feature_workers` is present but null in the config, `getter`
returns `None` and `int(None)` raises `TypeError` rather than falling back to 16. The
default only applies when the key is absent, not when it is explicitly null.
**Fix:** `int(getter("max_feature_workers") or 16)` or guard for `None` before `int()`.

---

_Reviewed: 2026-06-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
