# Technology Stack

**Analysis Date:** 2026-06-26

## Languages

**Primary:**
- Python `~=3.11` (declared `requires-python = "~=3.11"` in `pyproject.toml`; classifiers list 3.11 and 3.12) — all source under `src/`.

**Secondary:**
- YAML — declarative benchmark definitions (`benchmarks/**/*.yaml`, `src/**/conf/**/*.yaml`) for suites, datasets, metrics, analyses, and tool wiring.
- JSON — JSON Schema validation files (`src/geodispbench3d/conf/schema/*.json`).

## Runtime

**Environment:**
- CPython 3.11/3.12. Local development is pinned to a Conda env `iof3d_cosicorr3d-dev312` (see `AGENTS.md`); the F2S3 binary runs in a separate Conda env `f2s3-dev312` invoked via `conda run`.
- CI runs on Python 3.12 (`.github/workflows/ci.yml`).

**Package Manager:**
- pip (editable installs, `pip install -e .[extra]`). Conda is used only for environment isolation, not dependency resolution.
- Lockfile: missing. Dependencies are version-range pinned in `pyproject.toml`, not lockfile-pinned. CI pins lint tools (`ruff==0.8.4`, `pyright==1.1.392`) inline.

## Frameworks

**Core:**
- `ax-platform ~= 1.1` — Bayesian hyperparameter optimization engine. Driven via `AxClient` in `src/geodispbench3d/sweep/runner.py` (with a fallback import path for older Ax).
- `hydra-core ~= 1.3` — configuration composition / structured config. Used in `src/geodispbench3d/cli.py` and the iof3D adapter for `AppConfig` assembly.
- `omegaconf ~= 2.3` — config object model underpinning Hydra; used throughout for YAML <-> dataclass translation (`OmegaConf.create`, `OmegaConf.save`).
- `numpy ~= 2.0` — numerical core for displacement/point-cloud math (e.g. `src/geodispbench3d_f2s3/output_parser.py`).
- `pandas` (unpinned) — DataFrame model for the parquet results store (`src/geodispbench3d/results/store.py`).

**Testing:**
- `pytest ~= 8.4` (`dev` extra) — test runner. Suites split into `tests/core`, `tests/iof3d`, `tests/f2s3`.
- `coverage ~= 7.0` (`dev` extra) — coverage measurement.

**Build/Dev:**
- `setuptools` + `setuptools_scm` — build backend (`build-system.build-backend = "setuptools.build_meta"`); version derived from git tags, written to `src/geodispbench3d/_version.py`.
- `ruff ~= 0.8` — linter + formatter (replaces black/isort/flake8). Config in `pyproject.toml` `[tool.ruff]`.
- `pyright ~= 1.1` — static type checker. Config in `pyrightconfig.json` (basic mode).
- `pre-commit ~= 4.3` — git hook orchestration (`.pre-commit-config.yaml`).
- `sphinx ~= 5.1` (`docs` extra) — documentation builder.

## Key Dependencies

**Critical:**
- `ax-platform ~= 1.1` — without it sweep orchestration cannot run (raised as `ImportError` in `sweep/runner.py`).
- `hydra-core` / `omegaconf` — config backbone; every suite/dataset/tool YAML is parsed through them.
- `numpy ~= 2.0` — note the major-version pin; transitive tool stacks must be NumPy-2 compatible.

**Infrastructure:**
- `streamlit ~= 1.41` (`dashboard` extra) — results dashboard UI (`src/geodispbench3d/dashboard/app.py`).
- `altair ~= 5.4` (`dashboard` extra) — charting inside the dashboard (optional; guarded import).
- `duckdb ~= 1.4` (`dashboard` extra) — ad-hoc parquet querying. Readers do not require it; pandas is the default reader.

**Tool-adapter extras (gated, not installed by default):**
- `iof3d` extra: `iof3D ~= 0.1`, `pchandler`, `pc2img` — pulls iof3D's full pipeline stack (torch, ptlflow, opencv) transitively. Imported at module level only in `src/geodispbench3d_iof3d/`.
- `f2s3` extra: empty (`f2s3 = []`). The F2S3 adapter drives the F2S3 binary via subprocess; the Python lib is not required.

## Configuration

**Environment:**
- `GEODISPBENCH3D_PARQUET` — optional env var pointing the dashboard at a results parquet (`src/geodispbench3d/cli.py`, `src/geodispbench3d/dashboard/app.py`). No `.env` file is used; no secrets are read from the environment.

**Build:**
- `pyproject.toml` — single source of build, dependency, extras, ruff, and setuptools_scm config.
- `pyrightconfig.json` — type-checker config.
- `release-please-config.json` + `.release-please-manifest.json` — automated release/changelog config.
- Package data (`conf/**/*.yaml`, `conf/**/*.json`) is bundled via `[tool.setuptools.package-data]`.

## Platform Requirements

**Development:**
- Conda env `iof3d_cosicorr3d-dev312` (mandated by `AGENTS.md`; bare `python`/`pip`/`pytest` forbidden).
- Separate Conda env `f2s3-dev312` required to exercise the F2S3 adapter end-to-end.
- GPU/CUDA implied transitively when the `iof3d` extra is installed (torch/ptlflow stack); the framework core is CPU-only.

**Production:**
- Distributed as an sdist + wheel to a Python package index (currently flagged `Private :: Do Not Upload`; the classifier must be removed before PyPI publish). Console entry points: `geodispbench3d` and `iof3d-ax` (`[project.scripts]`).

---

*Stack analysis: 2026-06-26*
