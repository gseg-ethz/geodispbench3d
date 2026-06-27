# Phase 4: Licensing, Metadata & Packaging - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `geodispbench3d` legally and structurally ready for a **public PyPI release**:
license statements consistent (BSD-3-Clause everywhere), the `Private :: Do Not Upload`
classifier removed, public metadata completed, and the dependency graph made to resolve
correctly **when iof3D is not publicly installable**.

The driving constraint: **iof3D stays private at go-live** (publishes publicly in ~6 months),
yet the maintainer's own research env keeps iof3D installed from the private repo, so the
integration must keep working locally while never breaking a clean public install.

In scope: README/pyproject/LICENSE/CITATION reconciliation (LIC-01…04), classifier + metadata
polish (LIC-03), and the iof3d / F2S3 / pchandler packaging untangle (PKG-01…03).
Out of scope: CI/CD, build, and trusted-publishing automation (Phase 5); any new features.

</domain>

<decisions>
## Implementation Decisions

### iof3D in the public distribution (open question — RESOLVED)
- **D-01: Single wheel, ship iof3D adapter dormant.** Keep `geodispbench3d_iof3d` as a
  subpackage listed in `[tool.setuptools] packages` (do **not** drop it from the package list).
  Rationale: the `packages` list governs *both* the published wheel and editable installs, so
  excluding it would break the maintainer's local research workflow. Nothing is stripped from
  the repo.
- **D-02: Guard the module-level heavy imports** (`iof3D.*`, `pc2img`, `pchandler`) so that a
  public `import geodispbench3d_iof3d` **succeeds** without iof3D installed, and only *using* the
  adapter raises a clear, actionable error (e.g. "iof3D is not yet publicly available; install
  iof3D to enable this adapter"). Today these imports are eager at package top
  (`__init__.py` → `.adapter`/`.factory`/`.output_parser`), so they hard-`ImportError` without
  iof3D. Preferred mechanism: lazy re-exports via module `__getattr__` (PEP 562) in
  `geodispbench3d_iof3d/__init__.py` so submodules are imported on attribute access, not at
  package import. Exact implementation is the planner/researcher's call.
- **D-03: The `iof3d` extra is commented out** for the public release (forced — `iof3D ~= 0.1`
  cannot resolve on public PyPI). This is PKG-01. The `iof3d-ax` console script
  (`geodispbench3d_iof3d.cli:main`) stays declared but must fail gracefully under the same guard
  rather than raising a raw `ImportError`.
- **D-04: Re-enablement at iof3D go-live (~6 months) is a deliberate later step** — uncomment the
  `iof3d` extra, set its version pins (incl. `pchandler`/`pc2img`), and publish. Tracked as a
  deferred item, not done now.
- **Rejected alternative:** promoting `geodispbench3d_iof3d` to a *separate plugin distribution*
  that the `[iof3d]` extra pulls in. This is the only way an extra can truly gate a package (extras
  list *distributions*, never in-wheel subpackages), and it yields the cleanest core wheel — but it
  adds a second build target + version to maintain, is a heavier change now, and does **not**
  shorten the iof3D-private timeline. Kept as a Deferred Idea to revisit at go-live.

### F2S3 pchandler resolution (open question — RESOLVED)
- **D-05: Add `pchandler` to the `f2s3` extra** → `f2s3 = ["pchandler ~= 2.1"]`. The
  `geodispbench3d_f2s3.output_parser` imports `pchandler` (`PointCloudData`, `Csv`, `SphereFilter`)
  at module level and runs **in the main env** (the F2S3 tool itself runs via `conda run` subprocess
  per Phase 3 D-01, but its output parser is in-process). F2S3 is the **canonical public
  `CliToolAdapter` example** (Phase 3 CLI-05), so it must stay fully runnable by a public user — it
  does **not** get the dormant treatment. This satisfies PKG-02.
- **Rejected alternative:** a `pchandler`-free example parser (rewrite to numpy/pandas CSV reading).
  More work, diverges from the real research parser, and unnecessary now that `pchandler` is public.

### pchandler pinning + compatibility (PKG-03)
- **D-06: Pin `pchandler ~= 2.1`** (the current PyPI release; post-1.0 so two-component compatible-
  release matches house style — `>=2.1, <3.0`).
- **D-07: PKG-03 verification is mandatory before trusting the pin.** `pchandler` 2.x is a *major*
  line; confirm the symbols the code imports still exist at their paths in 2.1:
  `pchandler.PointCloudData`, `pchandler.data_io.Csv`, `pchandler.filters.SphereFilter`
  (F2S3 parser) and `pchandler.geometry.spherical.Angle` (iof3D adapter, dormant). If any moved/
  renamed, adapt the import (F2S3) before release; the iof3D side can be adapted now or at go-live.

### Licensing & metadata (LIC-01…04 — mechanical, default disposition)
- **D-08: LIC-01** — fix `README.md:82` ("Proprietary — see `LICENSE`.") to state BSD-3-Clause,
  matching `pyproject.toml`, `LICENSE`, and `CITATION.cff`.
- **D-09: LIC-02** — remove the `Private :: Do Not Upload` classifier from `pyproject.toml`.
- **D-10: LIC-04** — `CITATION.cff` already declares `license: BSD-3-Clause` (line 10); confirm it
  and any docs consistently reflect public BSD-3-Clause status.
- **D-11: LIC-03 / maturity** — add `Development Status :: 4 - Beta` (honest first-public-release
  signal for a tool mature in-house but new to outside users). Also add
  `Intended Audience :: Science/Research` and `Topic :: Scientific/Engineering` classifiers, and
  `Documentation` + `Changelog` entries under `[project.urls]`. Existing description/keywords/
  authors/homepage/repo/issues are kept.

### Claude's Discretion
- Exact guard mechanism for D-02 (PEP 562 `__getattr__` vs try/except re-exports) — planner's call,
  provided public `import geodispbench3d_iof3d` succeeds and adapter use fails with an actionable
  message.
- Precise wording of the actionable "install iof3D" error message.
- Exact `Documentation`/`Changelog` URL targets (sphinx site vs repo docs/ vs CHANGELOG).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & decisions
- `.planning/REQUIREMENTS.md` — LIC-01…04, PKG-01…03 (acceptance criteria for this phase)
- `.planning/ROADMAP.md` — Phase 4 goal, success criteria, the two open questions (now resolved here)
- `.planning/PROJECT.md` §Key Decisions / §Context — iof3D-stays-private constraint, BSD-3-Clause
  already in pyproject+LICENSE, pchandler newly on PyPI
- `.planning/phases/03-cli-hardening/03-CONTEXT.md` — Phase 3 D-01 (F2S3 defaults to `conda run`
  subprocess; F2S3 is the canonical `CliToolAdapter` showcase that must stay runnable)

### Artifacts edited in this phase
- `pyproject.toml` — classifiers (drop `Private`, add Beta/audience/topic), `[project.optional-
  dependencies]` (comment `iof3d`, set `f2s3 = ["pchandler ~= 2.1"]`), `[project.urls]`,
  `[project.scripts]` (`iof3d-ax`)
- `README.md` §License (line ~80–82) — Proprietary → BSD-3-Clause
- `LICENSE`, `CITATION.cff` — confirm BSD-3-Clause consistency
- `src/geodispbench3d_f2s3/output_parser.py` (lines 28–30, 149) — pchandler import sites (PKG-03)
- `src/geodispbench3d_iof3d/__init__.py` — guard target (lazy re-exports for dormant shipping)
- `src/geodispbench3d_iof3d/adapter.py` (imports `iof3D.*`, `pc2img`, `pchandler.geometry.spherical`)
- `src/geodispbench3d_iof3d/cli.py` — `iof3d-ax` entry; must fail gracefully when iof3D absent
- `src/geodispbench3d_iof3d/output_parser.py` — also imports `pchandler`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- House dependency-pin convention is compatible-release `~=` throughout `pyproject.toml`
  (`numpy ~= 2.0`, `omegaconf ~= 2.3`, `ax-platform ~= 1.1`, `ruff ~= 0.15`) — `pchandler ~= 2.1`
  and the F2S3 extra follow the same style.
- `dynamic = ["version", "readme"]` with `readme = { file = ["README.md"] }` — the README *is* the
  PyPI long description, so the LIC-01 fix also corrects the public listing text.

### Established Patterns
- **Architecture boundary holds:** core `geodispbench3d` imports nothing from iof3D (verified — only
  a doc comment in `tool/base.py`). Guarding work is confined to `geodispbench3d_iof3d`; it cannot
  leak into the tool-agnostic core.
- **setuptools `packages` list is the single lever** governing both the published wheel and editable
  installs — the reason D-01 keeps `geodispbench3d_iof3d` listed rather than excluding it.
- The self-documenting "remove before publishing" comment already sits on the `Private` classifier
  in `pyproject.toml` — LIC-02 is a known, pre-flagged edit.

### Integration Points
- Commenting out the `iof3d` extra (D-03) removes the only path that currently drags `pchandler`
  into a default install — which is exactly why D-05 must add `pchandler` to the `f2s3` extra, or
  F2S3 breaks on a clean public install.
- The dormant iof3D adapter still imports `pchandler` (and `pc2img`); once guarded, those are
  inert publicly. When the `iof3d` extra is re-enabled at go-live, keep its `pchandler` consistent
  with the F2S3 `~= 2.1` pin.

</code_context>

<specifics>
## Specific Ideas

- pchandler is published on PyPI at **version 2.1** (maintainer-confirmed) → pin `~= 2.1`.
- iof3D is expected to go **public in ~6 months**; the maintainer needs the integration working
  locally throughout (it is, via the private repo in `iof3d_cosicorr3d-dev312`).
- Maturity presented as **Beta**, not Production/Stable — a deliberate first-public-release signal.

</specifics>

<deferred>
## Deferred Ideas

- **iof3D extra re-enablement at go-live (~6 months):** uncomment the `iof3d` extra, set version
  pins (`iof3D`, `pchandler`, `pc2img`), and publish. A future-milestone task, not Phase 4.
- **Plugin-distribution split for `geodispbench3d_iof3d`:** promote it to its own distribution that
  the `[iof3d]` extra pulls in (cleanest core wheel; the only way an extra can truly gate a
  package). Considered and rejected for now (heavier maintenance, no timeline benefit). Natural time
  to revisit is iof3D go-live, alongside the re-enablement above.

</deferred>

---

*Phase: 4-Licensing, Metadata & Packaging*
*Context gathered: 2026-06-27*
