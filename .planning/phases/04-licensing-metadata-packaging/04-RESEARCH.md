# Phase 4: Licensing, Metadata & Packaging - Research

**Researched:** 2026-06-27
**Domain:** Python packaging / PyPI metadata / lazy-import guarding (no new libraries)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01: Single wheel, ship iof3D adapter *dormant*.** Keep `geodispbench3d_iof3d` in
  `[tool.setuptools] packages` (do NOT drop it). The `packages` list governs both the published
  wheel and editable installs; excluding it breaks the maintainer's local research workflow.
- **D-02: Guard module-level heavy imports** (`iof3D.*`, `pc2img`, `pchandler`) so a public
  `import geodispbench3d_iof3d` *succeeds* without iof3D, and only *using* the adapter raises a
  clear, actionable error. Preferred mechanism: PEP 562 module `__getattr__` lazy re-exports in
  `geodispbench3d_iof3d/__init__.py`. Exact implementation is the planner's call.
- **D-03: The `iof3d` extra is commented out** for public release (`iof3D ~= 0.1` cannot resolve on
  public PyPI). This is PKG-01. The `iof3d-ax` console script stays declared but must fail
  gracefully under the same guard rather than raising a raw `ImportError`.
- **D-04: Re-enablement at iof3D go-live (~6 months) is a deferred later step** — not done now.
- **D-05: Add `pchandler` to the `f2s3` extra** → `f2s3 = ["pchandler ~= 2.1"]`. F2S3 is the
  canonical public `CliToolAdapter` example (Phase 3 CLI-05) and must stay fully runnable; it does
  NOT get the dormant treatment. Satisfies PKG-02.
- **D-06: Pin `pchandler ~= 2.1`** (current PyPI release; `>=2.1, <3.0`).
- **D-07: PKG-03 verification is mandatory before trusting the pin.** Confirm the imported symbols
  still exist at their paths in 2.1: `pchandler.PointCloudData`, `pchandler.data_io.Csv`,
  `pchandler.filters.SphereFilter` (F2S3), and `pchandler.geometry.spherical.Angle` (iof3D, dormant).
- **D-08: LIC-01** — fix `README.md:82` ("Proprietary — see `LICENSE`.") to state BSD-3-Clause.
- **D-09: LIC-02** — remove the `Private :: Do Not Upload` classifier from `pyproject.toml`.
- **D-10: LIC-04** — confirm `CITATION.cff` `license: BSD-3-Clause` (line 10) and docs consistency.
- **D-11: LIC-03 / maturity** — add `Development Status :: 4 - Beta`,
  `Intended Audience :: Science/Research`, `Topic :: Scientific/Engineering`, and `Documentation` +
  `Changelog` entries under `[project.urls]`. Keep existing description/keywords/authors/urls.

### Claude's Discretion
- Exact guard mechanism for D-02 (PEP 562 `__getattr__` vs try/except re-exports) — planner's call,
  provided public `import geodispbench3d_iof3d` succeeds and adapter use fails actionably.
- Precise wording of the actionable "install iof3D" error message.
- Exact `Documentation`/`Changelog` URL targets (sphinx site vs repo docs/ vs CHANGELOG).

### Deferred Ideas (OUT OF SCOPE)
- **iof3D extra re-enablement at go-live (~6 months):** uncomment `iof3d`, set version pins, publish.
- **Plugin-distribution split for `geodispbench3d_iof3d`:** promote to its own distribution the
  `[iof3d]` extra pulls in. Considered and rejected for now; revisit at iof3D go-live.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIC-01 | README license reconciled with pyproject + LICENSE (all BSD-3-Clause) | Only one functional edit: `README.md:82`. `pyproject.toml:10` `license = { text = "BSD-3-Clause" }` and `LICENSE` (BSD 3-Clause, ETH Zurich) already agree. |
| LIC-02 | Remove `Private :: Do Not Upload`; confirm OSI + Python classifiers | Exactly one line: `pyproject.toml:23` (+ its 2-line "remove before publishing" comment at :21-22). OSI/Python classifiers already correct. |
| LIC-03 | Metadata (description, URLs, authors, supported-Python) complete for public release | Add 3 classifiers + 2 `[project.urls]` entries (D-11). Exact valid trove strings + recommended URL targets below. |
| LIC-04 | CITATION.cff + docs reflect public BSD-3-Clause status | `CITATION.cff:10` already `license: BSD-3-Clause` — confirm-only. No other "Proprietary"/"Private" strings exist in shippable files (verified by grep). |
| PKG-01 | `iof3d` extra commented out / disabled for public release | `pc2img` and `iof3D` confirmed ABSENT from public PyPI (live `pip index versions`). Commenting the block is mandatory. Console script must fail gracefully (D-03). |
| PKG-02 | F2S3 path installable standalone — `pchandler` resolves without `iof3d` extra | `f2s3 = []` → `f2s3 = ["pchandler ~= 2.1"]`. F2S3 parser imports `pchandler` at module level (lines 28–31). CI already wires `.[f2s3,dev]` enabled. |
| PKG-03 | `pchandler` usage verified against new PyPI release, non-breaking | **VERIFIED against the actual 2.1.0 wheel** — all four symbol paths + the `Csv.load(...)` kwargs + `SphereFilter`/`PointCloudData` API present. No code adaptation required. |
</phase_requirements>

## Summary

This phase is a **surgical, low-risk packaging/metadata pass over an already-BSD-3-Clause
codebase** — there is no new library to adopt, no architecture to design. The work is six edited
files plus one import-topology refactor confined entirely to `geodispbench3d_iof3d`. The
tool-agnostic core (`geodispbench3d`) imports nothing from any tool, so none of this leaks into it.

The two substantive technical risks were both **resolved by live verification in this session**:
(1) **PKG-03** — all `pchandler` symbols the parsers use are confirmed present in the actual
published **pchandler 2.1.0 wheel** (downloaded and inspected; not just the dev-lineage editable
checkout). No import adaptation is needed for F2S3 or the dormant iof3D side. (2) **PKG-01** —
`pc2img` and `iof3D` are confirmed **absent from public PyPI**, so commenting out the `iof3d` extra
is mandatory, not optional, for a clean install to resolve.

The one genuine *design* task is **D-02's dormant-import guard**. The current
`geodispbench3d_iof3d/__init__.py` eagerly imports `.adapter`/`.factory`/`.output_parser`, and
`.adapter`/`.factory`/`.cli` import `iof3D.*`/`pc2img` at module top — so `import
geodispbench3d_iof3d` hard-`ImportError`s without iof3D today. The recommended fix is a PEP 562
`__getattr__` lazy re-export in `__init__.py` plus a thin guarded launcher for the `iof3d-ax`
console script. Conveniently, **pchandler 2.1.0 itself uses exactly this PEP 562 lazy-export pattern
in its own `__init__.py`** — it is a real, in-tree reference implementation.

**Primary recommendation:** Treat this as two near-independent workstreams the planner can parallelize:
(A) **metadata/licensing** — mechanical edits to `pyproject.toml`, `README.md`, confirm
`CITATION.cff`/`LICENSE` (disjoint files, no code); (B) **packaging/guard** — the `f2s3` extra +
commenting `iof3d` + the `geodispbench3d_iof3d` lazy-import refactor + the `iof3d-ax` guarded
launcher, gated by a fresh-venv resolution test and a simulated-absence import-guard unit test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| License-string reconciliation (LIC-01/02/04) | Package metadata (`pyproject.toml`, `README.md`, `CITATION.cff`, `LICENSE`) | — | Pure distribution metadata; no runtime code involved. README is the PyPI long-description (`dynamic = ["readme"]`), so the LIC-01 edit also corrects the public listing. |
| Public metadata polish (LIC-03) | Package metadata (`pyproject.toml` classifiers + `[project.urls]`) | Docs (`docs/`) for URL targets | Trove classifiers + project URLs are static metadata consumed by the PyPI index. |
| Dependency-graph resolution (PKG-01/02) | Build/packaging config (`[project.optional-dependencies]`) | — | Extras list *distributions*; commenting `iof3d` and populating `f2s3` is the only lever that controls what a public `pip install` resolves. |
| Dormant-adapter import guard (D-02/PKG-01) | Plugin package (`geodispbench3d_iof3d/__init__.py`, `cli.py`) | — | Confined to the iof3D plugin; the core never imports it. Lazy re-export defers heavy imports to attribute access. |
| pchandler symbol compatibility (PKG-03) | Plugin parsers (`geodispbench3d_f2s3/output_parser.py`, `geodispbench3d_iof3d/output_parser.py`/`adapter.py`) | — | The parsers are the only consumers of `pchandler` symbols; verification targets their exact import sites. |

## Standard Stack

This phase adds **no new libraries**. It edits existing packaging configuration and one runtime
package. The relevant "stack" is the packaging toolchain already pinned in the repo.

### Core (already present — unchanged)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| setuptools + setuptools_scm | (build-system) | Build backend; version from git tags | Already the declared backend; `packages` list governs wheel + editable install |
| PEP 621 `[project]` table | pyproject.toml | Canonical static metadata (classifiers, urls, extras) | Standard since pip 21.1 / setuptools 61; the project already uses it |
| PEP 562 module `__getattr__` | stdlib (Py 3.7+) | Lazy attribute-level imports | Stdlib mechanism for "import succeeds, use defers"; **pchandler 2.1.0 itself uses it** |

### The only new dependency string
| Change | From | To | Notes |
|--------|------|----|-------|
| `f2s3` extra | `f2s3 = []` | `f2s3 = ["pchandler ~= 2.1"]` | `~=` matches house style; resolves to 2.1.0 on PyPI |

**Verification commands (run via the mandated conda env or a fresh venv per AGENTS.md):**
```bash
# pchandler is public at 2.1.0; pc2img and iof3D are NOT (verified this session):
conda run -n iof3d_cosicorr3d-dev312 python -m pip index versions pchandler   # -> 2.1.0
conda run -n iof3d_cosicorr3d-dev312 python -m pip index versions pc2img      # -> No matching distribution
conda run -n iof3d_cosicorr3d-dev312 python -m pip index versions iof3D       # -> No matching distribution
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `pchandler` | PyPI 2.1.0 | first-party (gseg-ethz, ETH Zurich house lib) | n/a (niche research lib) | gseg.igp.ethz.ch / gseg-ethz | OK | Approved — first-party maintainer-published, symbols verified against the actual 2.1.0 wheel |
| `iof3D` | PyPI: **ABSENT** | — | — | private (go-live ~6mo) | n/a | Extra commented out (PKG-01); not installed publicly |
| `pc2img` | PyPI: **ABSENT** | — | — | private | n/a | Pulled only by the commented `iof3d` extra; dormant publicly |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none. `pchandler` is the project maintainer's own first-party
library (same ETH Zurich `gseg-ethz` group, homepage `gseg.igp.ethz.ch`), maintainer-confirmed on
PyPI at 2.1.0 (CONTEXT specifics). Not a slopsquat risk. The standard automated legitimacy seam
flags niche first-party research libs as low-download; that signal is expected and not a concern here.

> Provenance note: `pchandler 2.1.0`'s existence and symbol set are `[VERIFIED: PyPI wheel inspected]`
> — the 2.1.0 wheel was downloaded (`pip download pchandler==2.1.0 --no-deps`) and its module tree +
> symbol exports read directly. `iof3D`/`pc2img` absence is `[VERIFIED: pip index versions]`.

## Findings by Focus Area

### Focus 1 — D-02 dormant-iof3D guard (PKG-01)

**Current import topology (verified by reading the files):**

| File | Module-level heavy imports | Triggered today by |
|------|----------------------------|--------------------|
| `geodispbench3d_iof3d/__init__.py` | re-exports `.adapter`, `.factory`, `.output_parser` (lines 20–22) | `import geodispbench3d_iof3d` |
| `geodispbench3d_iof3d/adapter.py` | `iof3D.v2.api.pipeline_runner`, `iof3D.v2.config.settings`, `pc2img.core.ImgRes`, `pchandler.geometry.spherical.Angle` (lines 19–27) | imported by `__init__`, `factory`, `cli` |
| `geodispbench3d_iof3d/factory.py` | `iof3D.v2.cli_hydra._build_app_config` + `from .adapter import …` (lines 18, 23) | imported by `__init__` |
| `geodispbench3d_iof3d/output_parser.py` | `pchandler` (`PointCloudData`, `load_file`), `pchandler.filters.SphereFilter` (lines 24–25) — **no iof3D import** | imported by `__init__` |
| `geodispbench3d_iof3d/cli.py` | `hydra`, `iof3D.v2.cli_hydra`, `from .adapter import …` (lines 15–26); `@hydra.main` decorator at module scope (line 76) | console script `iof3d-ax` |

**Key subtlety:** `output_parser.py` imports **only** `pchandler` (public) + numpy + core — *not*
iof3D. So under a lazy guard, `geodispbench3d_iof3d.parse_iof3d_output` actually imports fine
publicly whenever pchandler is present. The truly-gated symbols (need iof3D/pc2img) are
**`Iof3dCallableAdapter`, `build_app_config_from_parameters`, `build_iof3d_adapter`**, and the
`iof3d-ax` CLI. The guard's actionable error must therefore be asserted against one of *those*
symbols, not `parse_iof3d_output`.

**Recommended design — PEP 562 `__getattr__` lazy re-export in `__init__.py`** (see Code Example 1).
Rationale over try/except re-exports:
- A bare `try/except ImportError` wrapping the three submodule imports in `__init__` would either
  (a) swallow them and leave `__all__` symbols missing (so `geodispbench3d_iof3d.Iof3dCallableAdapter`
  raises a bare `AttributeError`, not an actionable message), or (b) still import `.output_parser`
  eagerly. The `__getattr__` form gives a *per-symbol* import deferral and lets you wrap the failure
  in a tailored message. It is also exactly what pchandler 2.1.0 does (`[VERIFIED: wheel inspected]`).
- A `TYPE_CHECKING` block re-importing the real symbols keeps pyright/IDE resolution intact (matters:
  CI runs pyright project-wide, `pass_filenames: false`).

**iof3d-ax console script (`geodispbench3d_iof3d.cli:main`) graceful failure:** the `__init__` guard
does **not** help here — the entry point imports the `cli` submodule directly, whose `@hydra.main`
decorator and `from iof3D… import …` run at module import. Recommended fix: **split `cli.py`** into
a thin guarded launcher (`main()`, the declared entry point — keeps heavy imports out of module
scope) plus a private implementation module holding the current hydra-decorated body. The launcher
catches `ImportError` and raises `SystemExit(<actionable message>)` → clean exit code 1, no
traceback. See Code Example 2.

**Verification approach ("public import succeeds, use fails actionably" without iof3D):**
1. **Simulated-absence unit test (CI-friendly, runs in the dev env where iof3D *is* installed)** —
   block `iof3D` imports via `builtins.__import__`, assert `import geodispbench3d_iof3d` succeeds and
   `geodispbench3d_iof3d.Iof3dCallableAdapter` raises `ImportError` matching the actionable text. This
   belongs in `tests/core/` (no extra needed). See Code Example 3.
2. **Fresh-venv smoke (mirrors the existing CI `build` job)** — `python -m venv /tmp/clean; /tmp/clean/bin/pip install .`
   (core only), then `python -c "import geodispbench3d_iof3d"` succeeds and
   `python -c "import geodispbench3d_iof3d as m; m.Iof3dCallableAdapter"` exits non-zero with the
   message. The CI `build` job already creates a fresh venv and runs `import geodispbench3d`; adding
   `import geodispbench3d_iof3d` there is a one-line extension (Phase 5 territory, but the test in #1
   is the Phase-4 gate).

### Focus 2 — PKG-03 pchandler 2.1 symbol verification (D-07)

**Status: VERIFIED against the actual published `pchandler 2.1.0` wheel** (downloaded with
`pip download pchandler==2.1.0 --no-deps`, module tree + `__init__` exports read directly). The
dev env's installed pchandler is the editable dev-lineage `2.0.0rc8.post51` from
`/scratch/41_pchandler` — which does **not** satisfy `~= 2.1` — so verifying against the real 2.1.0
wheel (not the editable) was necessary and done.

| Symbol used by code | Import site | Present in 2.1.0? | Mechanism in 2.1.0 |
|---------------------|-------------|-------------------|--------------------|
| `pchandler.PointCloudData` | f2s3 parser:28, iof3d parser:24 | ✅ | `__init__` lazy-map → `core` |
| `pchandler.load_file` | iof3d parser:24 | ✅ | `__init__` lazy-map → `data_io` |
| `pchandler.data_io.Csv` | f2s3 parser:29 | ✅ | `data_io/__init__` lazy alias of `CsvHandler` |
| `pchandler.filters.SphereFilter` | f2s3 parser:30, iof3d parser:25 | ✅ | `filters/__init__` → `cartesian_filters` |
| `pchandler.geometry.spherical.Angle` | iof3d adapter:27 | ✅ | `geometry/spherical/__init__` → `angle` |

**Method-level API (the deeper risk) — also verified against 2.1.0 source in the wheel:**
- `CsvHandler.load(path, *, scalar_fields=None, column_names_row=-1, comment="//", delimiter=None, …)`
  — matches the F2S3 parser's exact call (`Csv.load(tile_path, scalar_fields=…, column_names_row=-1,
  delimiter=None, comment="//")`, parser lines 155–161). ✅
- `PointCloudData.nbPoints` (property), `PointCloudData.merge(…)` (classmethod). ✅
- `SphereFilter(sphere_center, radius)` constructor + `.sample()` (inherited from
  `PointCloudFilter`). The parser calls `SphereFilter(sphere_center=…, radius=…).sample(pcd)`. ✅

**Conclusion:** **No import or call-site adaptation is required** for either F2S3 or the dormant
iof3D side. The `~= 2.1` pin is safe. The only residual confirmation the planner should still task is
a **runtime gate**: run `pytest tests/f2s3` against an environment with `pchandler==2.1.0` actually
installed (the mandated dev env currently has the `2.0.0rc8` editable, so its green f2s3 suite does
*not* exercise the pinned release — see Validation Architecture, Wave 0 gap).

### Focus 3 — LIC-01…04 + LIC-03 metadata

**Exact current state (verified by reading each file):**

| File | Line | Current | Required edit | Req |
|------|------|---------|---------------|-----|
| `README.md` | 82 | `Proprietary — see \`LICENSE\`.` | `BSD-3-Clause — see \`LICENSE\`.` (or fuller BSD wording) | LIC-01 |
| `pyproject.toml` | 21–23 | 2-line "remove before publishing" comment + `"Private :: Do Not Upload",` | delete all three lines | LIC-02 |
| `pyproject.toml` | 15–24 | classifiers (OSI BSD + Py 3.11/3.12 present & correct) | add 3 classifiers (below) | LIC-03 |
| `pyproject.toml` | 33–36 | `[project.urls]` homepage/repository/issues | add `Documentation`, `Changelog` (below) | LIC-03 |
| `CITATION.cff` | 10 | `license: BSD-3-Clause` | confirm-only (already correct) | LIC-04 |
| `LICENSE` | 1–4 | `BSD 3-Clause License`, ETH Zurich 2025–2026 | confirm-only (already correct) | LIC-01/04 |

A repo-wide grep (`*.md`/`*.toml`/`*.cff`/`*.txt`, excluding `.planning/`) found **only two**
functional "Proprietary"/"Private" strings: `pyproject.toml:23` and `README.md:82`. (Mentions in
`.claude/CLAUDE.md` are descriptive project notes, not shipped artifacts — leave them.)

**LIC-03 valid PyPI trove classifier strings** (canonical strings from the official PyPI classifier
list) `[CITED: pypi.org/classifiers]`:
```
"Development Status :: 4 - Beta",
"Intended Audience :: Science/Research",
"Topic :: Scientific/Engineering",
```
All three are exact, currently-valid trove classifiers. (`Topic :: Scientific/Engineering` is the
valid parent topic; more specific children like `:: Image Recognition` exist but are not warranted.)

**`[project.urls]` recommendations (Claude's discretion per CONTEXT):** the repo ships docs as
**plain Markdown under `docs/`** (`docs/index.md` + `tools/`, `integrating/`, `reference/`
subdirs) — there is **no built Sphinx site** (the `docs` extra pins sphinx but there is no
`docs/conf.py`, and no ReadTheDocs/GitHub-Pages config). A changelog does **not yet exist**;
`release-please-config.json` declares `changelog-path: CHANGELOG.md` (release-please creates it on
the first release in Phase 5). Recommended forward-valid targets:
```toml
Documentation = "https://github.com/gseg-ethz/geodispbench3d/blob/main/docs/index.md"
Changelog     = "https://github.com/gseg-ethz/geodispbench3d/blob/main/CHANGELOG.md"
```
`Documentation` and `Changelog` are PyPI-recognized labels (rendered with special icons). Note the
existing keys are lowercase (`homepage`/`repository`/`issues`); PyPI title-cases known labels, so
mixing is cosmetically fine, but the planner may optionally normalize for consistency. `[ASSUMED]`
that the default branch is `main` (CLAUDE.md confirms `main` is the PR target / default branch).

### Focus 4 — PKG-02 f2s3 extra

`geodispbench3d_f2s3/output_parser.py` imports at **module level** (lines 27–31):
`numpy`, `from pchandler import PointCloudData`, `from pchandler.data_io import Csv`,
`from pchandler.filters import SphereFilter`. The package `__init__.py` re-exports
`parse_f2s3_output` eagerly — so `import geodispbench3d_f2s3` requires pchandler at import time.
**F2S3 is NOT dormant** (D-05): it must stay fully runnable for a public user.

**Edits:**
```toml
# [project.optional-dependencies]
f2s3 = ["pchandler ~= 2.1"]          # was: f2s3 = []
# iof3d = [ "iof3D ~= 0.1", "pchandler", "pc2img" ]   # PKG-01: commented out until iof3D publishes (D-03/D-04)
```
Commenting the entire `iof3d = [...]` block means `pip install geodispbench3d[iof3d]` errors with
"extra 'iof3d' not provided" publicly — acceptable per D-03/D-04 (re-enabled at go-live). The
`geodispbench3d_iof3d` *package* still ships in the wheel (D-01); only the dependency *extra* is
gone.

**Resolution-independence verification (fresh venv, no iof3d extra):**
```bash
python -m venv /tmp/f2s3-clean
/tmp/f2s3-clean/bin/pip install '.[f2s3]'                      # pulls pchandler 2.1.0 from PyPI only
/tmp/f2s3-clean/bin/python -c "import geodispbench3d_f2s3; from geodispbench3d_f2s3 import parse_f2s3_output"
/tmp/f2s3-clean/bin/pip install '.[f2s3,dev]' && /tmp/f2s3-clean/bin/pytest tests/f2s3 -v
# Confirm NO iof3D/pc2img dragged in:
/tmp/f2s3-clean/bin/pip list | grep -iE "iof3d|pc2img"        # -> empty
```
Per AGENTS.md, route python/pip through the conda env or an explicitly-created venv; do not use bare
`python`/`pip`. The CI `test` matrix already has the `f2s3` job `enabled: "true"` installing
`.[f2s3,dev]` — once the extra carries `pchandler`, that job exercises the real public install path.

**Docstring consistency (minor):** `tests/f2s3/conftest.py:17` still says pchandler comes from the
`[iof3d]` extra "or `[f2s3]` once F2S3 ships pchandler" — that condition is now satisfied; update the
skip message to reference `[f2s3]` directly. Low priority, same-file-as-tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Defer heavy imports until first use | Custom import-proxy classes / `importlib` wrappers scattered across submodules | PEP 562 module `__getattr__` in one `__init__.py` | Stdlib, single chokepoint, type-checker-friendly via `TYPE_CHECKING`; pchandler 2.1.0 uses this exact pattern |
| Gate an optional adapter behind an install | Runtime feature-flag config / env-var checks | Lazy import + actionable `ImportError`/`SystemExit` | The presence of the dependency *is* the flag; no extra config surface |
| CSV/ASCII point-cloud parsing for F2S3 | numpy/pandas re-implementation of the tile reader (the rejected alternative in D-05) | `pchandler.data_io.Csv` (now public on PyPI) | Diverges from the real research parser; pchandler is public and verified non-breaking |
| Friendly CLI failure when a tool is absent | `print()` + `sys.exit()` with a raw traceback | `raise SystemExit("<message>")` from a thin guarded launcher | Clean exit code 1, no traceback noise; keeps the declared entry point stable |

**Key insight:** every non-mechanical piece of this phase is solved by stdlib import mechanics +
existing first-party libraries. The temptation to "just wrap it in try/except" loses the actionable
error message and the type-checker resolution; PEP 562 gives both for free.

## Common Pitfalls

### Pitfall 1: Guard hides the wrong symbol
**What goes wrong:** Asserting the actionable error against `parse_iof3d_output`.
**Why it happens:** `geodispbench3d_iof3d/output_parser.py` imports only `pchandler` (public), not
iof3D — so it imports fine publicly and never raises the guard error.
**How to avoid:** Assert against `Iof3dCallableAdapter` / `build_iof3d_adapter` (which pull
`iof3D`/`pc2img`). Verification test must block `iof3D` (and optionally `pc2img`), not `pchandler`.
**Warning signs:** A "guard works" test that passes even when iof3D is genuinely installed.

### Pitfall 2: `@hydra.main` runs at import, defeating the cli guard
**What goes wrong:** Leaving the `@hydra.main`-decorated `main` and `from iof3D… import …` at module
scope in `cli.py` — the `iof3d-ax` entry point imports the module and hard-`ImportError`s before any
guard runs.
**How to avoid:** Thin launcher `main()` (the declared entry point) with heavy imports inside it /
in a private impl module; catch `ImportError` → `SystemExit(message)`.
**Warning signs:** `iof3d-ax --help` traceback ending in `ModuleNotFoundError: iof3D`.

### Pitfall 3: Trusting the dev env's green f2s3 suite as PKG-03 proof
**What goes wrong:** The mandated dev env has the editable `pchandler 2.0.0rc8.post51`
(from `/scratch/41_pchandler`), which is `< 2.1` and does **not** satisfy `~= 2.1`. A green
`pytest tests/f2s3` there validates the dev lineage, not the pinned 2.1.0 release.
**How to avoid:** Run the PKG-03 runtime gate in a fresh venv with `pchandler==2.1.0` actually
installed (symbol-level verification against the 2.1.0 wheel is already done in this research).
**Warning signs:** `pip show pchandler` reporting an `rc`/`post` dev version or a `Location` under
`/scratch/41_pchandler`.

### Pitfall 4: Commenting `iof3d` extra but leaving README install instructions advertising it
**What goes wrong:** `README.md:23–27` documents `pip install 'geodispbench3d[iof3d]'`, which will
error publicly once the extra is commented out. README is the PyPI long-description.
**How to avoid:** Add a one-line note that the `[iof3d]` extra is unavailable until iof3D publishes
(see Open Questions — this is a recommended, not locked, edit).
**Warning signs:** Public users filing "extra 'iof3d' not provided" issues.

### Pitfall 5: Breaking pyright by removing eager imports
**What goes wrong:** Moving submodule imports out of `__init__.py` makes pyright (CI gate, run
project-wide) unable to resolve `geodispbench3d_iof3d.Iof3dCallableAdapter` → new errors vs the
`develop` baseline.
**How to avoid:** Add a `if TYPE_CHECKING:` block re-importing the real symbols in `__init__.py`.
**Warning signs:** New pyright errors in the baseline-diff gate (Phases gate on no-new-errors).

## Code Examples

### Code Example 1 — PEP 562 lazy re-export in `geodispbench3d_iof3d/__init__.py`
```python
# Source pattern: PEP 562; mirrors pchandler 2.1.0's own __init__ [VERIFIED: 2.1.0 wheel inspected]
from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "Iof3dCallableAdapter",
    "build_app_config_from_parameters",
    "build_iof3d_adapter",
    "parse_iof3d_output",
]

# symbol -> submodule that defines it
_LAZY: dict[str, str] = {
    "Iof3dCallableAdapter": "adapter",
    "build_app_config_from_parameters": "adapter",
    "build_iof3d_adapter": "factory",
    "parse_iof3d_output": "output_parser",
}

_IOF3D_MISSING_HINT = (
    "The iof3D adapter requires iof3D (and pc2img), which are not yet publicly "
    "available. Install iof3D to enable this adapter; until then "
    "`import geodispbench3d_iof3d` works but its adapter cannot be constructed."
)


def __getattr__(name: str) -> Any:  # PEP 562
    submodule = _LAZY.get(name)
    if submodule is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    try:
        mod = import_module(f".{submodule}", __name__)
    except ImportError as exc:  # iof3D / pc2img absent
        raise ImportError(f"{_IOF3D_MISSING_HINT} (original error: {exc})") from exc
    return getattr(mod, name)


def __dir__() -> list[str]:
    return sorted(__all__)


if TYPE_CHECKING:  # keep pyright / IDE resolution intact
    from .adapter import Iof3dCallableAdapter, build_app_config_from_parameters
    from .factory import build_iof3d_adapter
    from .output_parser import parse_iof3d_output
```

### Code Example 2 — Graceful `iof3d-ax` launcher (`geodispbench3d_iof3d/cli.py`)
```python
# Thin guarded entry point. The hydra-decorated implementation moves to a
# private module (e.g. _sweep_cli.py) whose heavy imports stay out of module scope.
from __future__ import annotations


def main() -> None:
    try:
        from ._sweep_cli import main as _impl  # imports hydra + iof3D lazily
    except ImportError as exc:
        raise SystemExit(
            "iof3d-ax requires iof3D, which is not yet publicly available. "
            "Install iof3D to enable this command.\n"
            f"(original error: {exc})"
        )
    _impl()


if __name__ == "__main__":  # pragma: no cover
    main()
```

### Code Example 3 — Simulated-absence import-guard test (`tests/core/test_iof3d_import_guard.py`)
```python
# Runs in the dev env where iof3D IS installed, by blocking the import.
import builtins
import importlib
import sys

import pytest


def test_public_import_succeeds_use_fails(monkeypatch):
    # Drop cached modules so the guard re-runs against the blocked import.
    for mod in list(sys.modules):
        if mod == "iof3D" or mod.startswith(("iof3D.", "pc2img", "geodispbench3d_iof3d")):
            sys.modules.pop(mod, None)

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "iof3D" or name.startswith("iof3D.") or name == "pc2img" or name.startswith("pc2img."):
            raise ImportError(f"simulated absence: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)

    pkg = importlib.import_module("geodispbench3d_iof3d")  # MUST succeed
    with pytest.raises(ImportError, match="not yet publicly available"):
        _ = pkg.Iof3dCallableAdapter  # MUST fail actionably (pulls iof3D)
```

## Runtime State Inventory

> Rename/refactor-adjacent (the D-02 guard restructures imports). External runtime state is minimal.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified: this phase edits packaging config + import topology; no datastores keyed on any renamed string. | none |
| Live service config | None — no external services hold package metadata. PyPI listing is generated *from* this metadata at publish (Phase 5), not edited here. | none |
| OS-registered state | Console scripts `geodispbench3d` + `iof3d-ax` are entry points installed by pip on `pip install -e .`. After the `cli.py` split, the maintainer's editable install **must be reinstalled** (`pip install -e .`) for the `iof3d-ax` shim to re-point. | reinstall editable after entry-point change |
| Secrets/env vars | None. `GEODISPBENCH3D_PARQUET` is unrelated. No tokens in scope (trusted publishing is Phase 5). | none |
| Build artifacts | `src/geodispbench3d/_version.py` (setuptools_scm-generated, git-ignored from edits) is unaffected. No `.egg-info` rename. Repo has **no git tags** → `fallback_version = 0.1.0` governs the built version (consistent with Beta). | none |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ~= 8.4 (`dev` extra), coverage ~= 7.0 |
| Config file | `pyproject.toml` (no dedicated `pytest.ini`); `pyrightconfig.json` for types |
| Quick run command | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q` |
| Full suite command | `conda run -n iof3d_cosicorr3d-dev312 pytest` (extras-aware; iof3d/f2s3 dirs self-skip) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIC-01/02/04 | No "Proprietary"/"Private" strings remain in shippable files; classifiers correct | unit (metadata assert) | `pytest tests/core/test_packaging_metadata.py -x` | ❌ Wave 0 |
| LIC-03 | Required classifiers + `[project.urls]` Documentation/Changelog present | unit | `pytest tests/core/test_packaging_metadata.py -x` | ❌ Wave 0 |
| PKG-01 | `import geodispbench3d_iof3d` succeeds without iof3D; adapter use raises actionable `ImportError` | unit (simulated absence) | `pytest tests/core/test_iof3d_import_guard.py -x` | ❌ Wave 0 |
| PKG-01 | `iof3d-ax` exits 1 with actionable message when iof3D absent | unit (subprocess/SystemExit) | `pytest tests/core/test_iof3d_import_guard.py -x` | ❌ Wave 0 |
| PKG-02 | `pip install .[f2s3]` resolves `pchandler` with no iof3D/pc2img; parser imports | integration (fresh venv) | fresh-venv script (Focus 4) + `pytest tests/f2s3 -v` | ⚠ tests/f2s3 exist; resolution check is manual |
| PKG-03 | F2S3 parser runs against `pchandler==2.1.0` | integration | fresh venv w/ `pchandler==2.1.0` then `pytest tests/f2s3 -v` | ⚠ suite exists; pin-specific run is a gap |

### Sampling Rate
- **Per task commit:** `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q` (metadata + guard tests are fast, no extras)
- **Per wave merge:** `conda run -n iof3d_cosicorr3d-dev312 pytest` + `ruff check . && ruff format --check .` + baseline-diff pyright (`pyright_gate.py` — no NEW errors vs `develop`)
- **Phase gate:** fresh-venv `.[f2s3]` resolution + `pytest tests/f2s3` against installed `pchandler==2.1.0`; full suite green

### Wave 0 Gaps
- [ ] `tests/core/test_packaging_metadata.py` — parse `pyproject.toml` (tomllib) + read `README.md`; assert
      no `Private ::` classifier, no "Proprietary" in README license section, required Beta/audience/topic
      classifiers present, `Documentation`/`Changelog` URLs present. Covers LIC-01/02/03/04.
- [ ] `tests/core/test_iof3d_import_guard.py` — simulated-absence guard test (Code Example 3) + `iof3d-ax`
      clean-exit test. Covers PKG-01.
- [ ] PKG-02/03 fresh-venv resolution + pin-specific run is **integration, not unit** — cannot run inside the
      dev env (which has the `2.0.0rc8` editable pchandler). Plan it as a documented checkpoint step (fresh
      venv), not a pytest file. The symbol/API verification itself is already complete (this research).
- [ ] No new framework install needed — pytest/coverage already in the `dev` extra.

## Security Domain

> `security_enforcement: true`, ASVS level 1. This is a metadata/packaging phase with **no auth,
> network, session, or untrusted-input surface**. The relevant axis is **supply-chain / dependency
> integrity** (ASVS V14 Config & Dependencies), not application security.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth surface; trusted publishing is Phase 5) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | — (no new runtime input paths; parsers unchanged) |
| V6 Cryptography | no | — (no secrets handled this phase) |
| V14 Config & Dependencies | **yes** | Pin `pchandler ~= 2.1` (first-party, verified); comment unresolvable `iof3d` extra; legitimacy audit above |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dependency confusion / slopsquat on `pchandler` | Tampering / Spoofing | `pchandler` is first-party (gseg-ethz/ETH Zurich), maintainer-confirmed, symbols verified against the real 2.1.0 wheel — not a typo-target generic name |
| Publishing a wheel that pulls a non-resolvable private dep | Denial of Service (install fails) | Comment `iof3d` extra (PKG-01); `pc2img`/`iof3D` confirmed absent from PyPI |
| Lazy `__getattr__` masking a real import error as "iof3D missing" | Repudiation (misleading error) | Chain the original exception (`from exc`) and include it in the message (Code Example 1) so genuine bugs stay diagnosable |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| conda env `iof3d_cosicorr3d-dev312` | all python/pip/pytest (AGENTS.md) | ✓ | Python 3.12 | none (mandated) |
| `pchandler` (PyPI) | F2S3 extra (PKG-02/03) | ✓ | **2.1.0 on PyPI**; dev env has editable `2.0.0rc8.post51` | none — pin to 2.1 |
| `iof3D` (PyPI) | dormant iof3d extra | ✗ (public) | private only | extra commented out (PKG-01) |
| `pc2img` (PyPI) | dormant iof3d adapter | ✗ (public) | private only | inert under the lazy guard |
| `pip download` / fresh venv | PKG-02/03 integration gate | ✓ | — | — |

**Missing dependencies with no fallback:** none blocking. `iof3D`/`pc2img` absence is the *intended*
public state (PKG-01) — handled by the guard, not a blocker.
**Missing dependencies with fallback:** the pinned `pchandler 2.1.0` is not installed in the dev env
(editable `2.0.0rc8` is) → the PKG-03 runtime gate runs in a fresh venv.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Default branch is `main` for the recommended `Documentation`/`Changelog` URLs | Focus 3 | Low — CLAUDE.md confirms `main` is default/PR target; if docs move, update the path |
| A2 | The three trove classifier strings are current/valid on PyPI | Focus 3 | Low — canonical strings; `twine check` (Phase 5) catches an invalid classifier at build |
| A3 | `SphereFilter.sample()` (inherited) is unchanged in 2.1.0 vs the dev lineage | Focus 2 | Low — constructor + core API verified in 2.1.0 wheel; the fresh-venv `pytest tests/f2s3` gate confirms end-to-end |
| A4 | Commenting the whole `iof3d = [...]` block (vs `iof3d = []`) is the intended reading of D-03 "commented out" | Focus 4 | Low — CONTEXT says "commented out"; empty-list would silently accept the extra then fail to install iof3D |

## Open Questions

1. **README `[iof3d]` install instructions vs the commented extra**
   - What we know: `README.md:23–27` advertises `pip install 'geodispbench3d[iof3d]'`; README is the
     PyPI long-description; D-03 comments the extra out so that command errors publicly.
   - What's unclear: CONTEXT D-08 only locks the License-line README edit; the install-section note is
     not explicitly decided.
   - Recommendation: add a one-line note ("the `[iof3d]` extra is unavailable until iof3D is published;
     ~6 months") near the iof3d install snippet. Treat as recommended, surface to the user in planning.

2. **Whether to also update `tests/f2s3/conftest.py:17` skip message**
   - What we know: it still credits pchandler to the `[iof3d]` extra "once F2S3 ships pchandler" — now
     satisfied by D-05.
   - Recommendation: update to reference `[f2s3]` directly. Trivial, same wave as the extra edit.

3. **PKG-03 runtime gate placement (Phase 4 vs deferred to Phase 5 CI)**
   - What we know: symbol/API verification is complete; only the fresh-venv `pchandler==2.1.0` run
     remains, and CI's `f2s3` job (Phase 5) will install `.[f2s3,dev]` from PyPI.
   - Recommendation: do a manual fresh-venv checkpoint in Phase 4 for confidence; rely on the Phase 5
     CI job for the standing gate. Flag for the planner whether to add it as a Phase-4 checkpoint task.

## Sources

### Primary (HIGH confidence)
- `pchandler-2.1.0-py3-none-any.whl` (PyPI, `pip download pchandler==2.1.0 --no-deps`) — module tree,
  `__init__` lazy-export maps, `CsvHandler.load` / `SphereFilter` / `PointCloudData` signatures read
  directly. [VERIFIED: PyPI wheel inspected]
- `pip index versions {pchandler,pc2img,iof3D}` in `iof3d_cosicorr3d-dev312` — pchandler 2.1.0
  present; pc2img and iof3D absent from PyPI. [VERIFIED: pip index]
- Repo files read this session: `pyproject.toml`, `README.md`, `CITATION.cff`, `LICENSE`,
  `src/geodispbench3d_iof3d/{__init__,adapter,factory,output_parser,cli}.py`,
  `src/geodispbench3d_f2s3/{__init__,output_parser}.py`, `tests/{conftest,f2s3/conftest,iof3d/conftest}.py`,
  `.github/workflows/ci.yml`, `release-please-config.json`, `pyrightconfig.json`. [VERIFIED: codebase grep/read]

### Secondary (MEDIUM confidence)
- PyPI trove classifier list — `Development Status :: 4 - Beta`, `Intended Audience :: Science/Research`,
  `Topic :: Scientific/Engineering`. [CITED: pypi.org/classifiers]

### Tertiary (LOW confidence)
- None — all load-bearing claims verified against the live environment or the actual published wheel.

## Metadata

**Confidence breakdown:**
- PKG-03 symbol/API compatibility: HIGH — verified against the actual published 2.1.0 wheel, not the
  dev-lineage editable.
- PKG-01 (iof3D/pc2img absent from PyPI): HIGH — live `pip index versions`.
- D-02 guard design: HIGH — stdlib PEP 562; reference implementation present in pchandler 2.1.0.
- LIC edits: HIGH — exact current file:line state read this session.
- LIC-03 classifier strings: MEDIUM — canonical strings, `twine check` (Phase 5) is the build-time guard.

**Research date:** 2026-06-27
**Valid until:** 2026-07-27 (stable — packaging metadata; re-confirm pchandler version if a 2.x bump
lands before publish)
