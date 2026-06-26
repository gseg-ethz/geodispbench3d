# External Integrations

**Analysis Date:** 2026-06-26

This project is an offline benchmark harness. It has no network APIs, no
hosted databases, no auth providers, and no webhooks. Its "integrations" are
the external displacement/optical-flow tools it benchmarks, plus the local
filesystem artifacts (parquet, run dirs) it produces.

## APIs & External Services

**None (no remote/HTTP services).** No `requests`, `httpx`, `urllib`, cloud
SDKs, or REST clients appear anywhere under `src/`. All interaction with
external systems is via in-process Python calls or local subprocess execution.

## Benchmarked Tool Integrations

The core abstraction is `ToolAdapter` (`src/geodispbench3d/tool/base.py`).
Two adapter strategies ship:

**In-process adapter — iof3D:**
- Package: `src/geodispbench3d_iof3d/` (gated by the `iof3d` extra).
- Mechanism: imports `iof3D.v2.api.pipeline_runner.run_flow_pipeline` and calls
  it in-process per Ax trial (`src/geodispbench3d_iof3d/adapter.py`,
  `Iof3dCallableAdapter`, `in_process_safe = True`).
- Translates Ax trial parameters into an `iof3D` `AppConfig`
  (`build_app_config_from_parameters`).
- Transitive deps when enabled: `iof3D ~= 0.1`, `pchandler`, `pc2img`, and
  iof3D's own stack (torch, ptlflow, opencv).
- Status: CI test job for `iof3d` is **disabled** (`enabled: "false"` in
  `.github/workflows/ci.yml`) until iof3D is published on a reachable index.

**Subprocess adapter — F2S3:**
- Package: `src/geodispbench3d_f2s3/` (gated by the `f2s3` extra, which is
  empty — the Python lib is not required).
- Mechanism: `CliToolAdapter` (`src/geodispbench3d/tool/cli_adapter.py`) launches
  the F2S3 binary via `subprocess.run` once per trial, `in_process_safe = False`.
- Invocation entry (`src/geodispbench3d_f2s3/conf/tool/f2s3.yaml`):
  `conda run -n f2s3-dev312 f2s3` — F2S3 runs in its own Conda env regardless of
  which env geodispbench3d itself runs in.
- Output is parsed from per-tile ASCII files via
  `geodispbench3d_f2s3:parse_f2s3_output` (`src/geodispbench3d_f2s3/output_parser.py`),
  which samples displacements at ground-truth points using a `pchandler`
  `SphereFilter`.

**Adding new tools:**
- Generic CLI adapter (`tool/cli_adapter.py`) supports `hydra_overrides`,
  `argparse`, and `kv_equals` parameter rendering styles, plus optional
  hashed per-trial run directories.
- Generic callable adapter (`tool/callable_adapter.py`) for in-process Python tools.
- Adapters are resolved by `src/geodispbench3d/tool/loader.py` from tool YAML.

## Data Storage

**Databases:**
- None (no server database). DuckDB (`duckdb ~= 1.4`, `dashboard` extra) is
  available for ad-hoc local parquet querying but is optional and embedded.

**Results store:**
- Local Apache Parquet files, append-only (`src/geodispbench3d/results/store.py`).
  Written and read via pandas (`pd.to_parquet` / `pd.read_parquet`).
- Default path: `./outputs/results.parquet` (overridable via
  `$GEODISPBENCH3D_PARQUET` or `--parquet`).

**Predictions cache:**
- Local cache of per-trial predictions (`src/geodispbench3d/results/predictions_cache.py`),
  consumed by `--rescore --use-prediction-cache` to skip re-running tools.

**File Storage:**
- Local filesystem only. Per-trial outputs live under hashed run directories
  (e.g. `/scratch/00_data/geodispbench3d/f2s3/<hash>/` per the F2S3 tool conf).
  Run-dir roots, parquet outputs, and `runs/` are gitignored.

**Caching:**
- Local on-disk only (predictions cache + tool-internal caches). No external
  cache service.

## Authentication & Identity

- None. No auth provider, no credentials, no API keys are read or required by
  the codebase. No `.env`, secrets file, or credential file is present.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry/Rollbar/etc.

**Logs:**
- Python standard `logging` module throughout (e.g. named loggers
  `geodispbench3d.tool.cli`, `geodispbench3d_iof3d.adapter`). Subprocess
  stdout/stderr captured and logged on tool failure (`tool/cli_adapter.py`).

## CI/CD & Deployment

**Hosting:**
- Not a deployed service. Distributed as a Python package (sdist + wheel) with
  console scripts `geodispbench3d` and `iof3d-ax`.

**CI Pipeline:**
- GitHub Actions (`.github/workflows/ci.yml`): `lint` (ruff + pyright) → `test`
  (matrix: `core` enabled, `iof3d` disabled, `f2s3` enabled) → `build`
  (sdist/wheel via `python -m build`, `twine check`, fresh-venv install smoke).
- Release automation: `release-please` (`.github/workflows/release-please.yml`,
  `release-please-config.json`) — conventional-commits driven changelog +
  GitHub releases, `release-type: simple`.
- Triggers: pull_request and push on `main` and `develop`.

## Environment Configuration

**Required env vars:**
- None required for normal operation. `GEODISPBENCH3D_PARQUET` is an optional
  dashboard convenience.

**Secrets location:**
- Not applicable — the project uses no secrets, tokens, or credentials.

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- None (no HTTP). Note: the iof3D adapter passes an internal in-process
  `run_dir_callback` to `run_flow_pipeline` (`src/geodispbench3d_iof3d/adapter.py`)
  — a Python callback, not a network webhook.

---

*Integration audit: 2026-06-26*
