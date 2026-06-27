# Pyright Baseline — Phase 02 Targeted Fixes (D-08 / D-11 / D-12)

This file records the pyright no-regression **floor** for Phase 02. Later waves
(02-03, 02-04, 02-05, 02-07) do **not** run a raw `pyright && pytest` gate;
they run the machine-checkable diff gate `pyright_gate.py`, which fails only on
**new** errors above the baseline captured here.

## Gate baseline (authoritative — what `pyright_gate.py` diffs against)

The gate baseline is the **dev-env** capture, because every later wave reruns
`pyright_gate.py` in this same env, making the diff reproducible.

| Field | Value |
|-------|-------|
| Environment | conda `iof3d_cosicorr3d-dev312` (framework + **full** `iof3d` extras: iof3D/pchandler/pc2img/torch) |
| Pyright version | **1.1.403** |
| Config | `pyrightconfig.json` (whole-project; `include = ["src","tests"]`; `typeCheckingMode = "basic"`) |
| Exact command | `conda run -n iof3d_cosicorr3d-dev312 pyright --outputjson` |
| Raw capture | `pyright-baseline.json` (verbatim `--outputjson` stdout) |
| Files analyzed | 54 |
| **Total errors** | **21** |
| Total warnings | 9 |

### Per-file error breakdown (gate baseline, 21 errors)

| Errors | File |
|-------:|------|
| 5 | `src/geodispbench3d/dashboard/app.py` |
| 4 | `src/geodispbench3d/sweep/runner.py` |
| 3 | `src/geodispbench3d/tool/loader.py` |
| 4 | `src/geodispbench3d_iof3d/adapter.py` |
| 2 | `src/geodispbench3d_iof3d/factory.py` |
| 1 | `src/geodispbench3d_iof3d/cli.py` |
| 1 | `tests/core/test_loaders.py` |
| 1 | `tests/core/test_rescore.py` |

### Error rules (gate baseline)

| Count | Rule |
|------:|------|
| 12 | `reportArgumentType` |
| 7 | `reportAttributeAccessIssue` |
| 1 | `reportReturnType` |
| 1 | `reportGeneralTypeIssues` |

### Warnings (gate baseline, 9)

| Warnings | File |
|---------:|------|
| 6 | `src/geodispbench3d/__init__.py` |
| 2 | `src/geodispbench3d/dashboard/app.py` |
| 1 | `src/geodispbench3d/cli.py` |

> Note: the two new Wave-0 test files (`tests/core/test_store.py`,
> `tests/core/test_evaluation.py`) contribute **zero** pyright errors —
> `_StubRegistry` subclasses the real `MetricRegistry` precisely so the F-22
> tests do not inflate this floor.

## CI-faithful reference (D-12, doc-only)

A best-effort isolated env was created to record the number CI would actually
produce. CI installs `.[dev]` **only** (no `iof3d`/`f2s3`/`dashboard` extras)
with `pyright==1.1.392` (see `.github/workflows/ci.yml`). This is **reference
only** — the gate above (dev env) remains authoritative for `pyright_gate.py`.

| Field | Value |
|-------|-------|
| Environment | conda `gdb3d-pyright-ci` (named/persistent), `pip install -e '.[dev]' 'pyright==1.1.392'` |
| Python | 3.12.13 |
| Pyright version | **1.1.392** (CI pin) |
| Exact command | `conda run -n gdb3d-pyright-ci pyright --outputjson` |
| Files analyzed | 54 |
| **Total errors** | **16** |
| Total warnings | 22 |

### Per-file error breakdown (CI-faithful, 16 errors)

| Errors | File |
|-------:|------|
| 4 | `src/geodispbench3d/sweep/runner.py` |
| 3 | `src/geodispbench3d/dashboard/app.py` |
| 3 | `src/geodispbench3d/tool/loader.py` |
| 2 | `src/geodispbench3d_iof3d/adapter.py` |
| 1 | `src/geodispbench3d_iof3d/cli.py` |
| 1 | `src/geodispbench3d_iof3d/factory.py` |
| 1 | `tests/core/test_loaders.py` |
| 1 | `tests/core/test_rescore.py` |

The CI count is **lower** (16 vs 21) because, without the `iof3d` extras
installed, the `iof3D`/`pchandler`/`pc2img` imports in `src/geodispbench3d_iof3d/`
are unresolved: several `reportArgumentType` errors there degrade to
`reportMissingImports` **warnings** instead (hence 22 warnings vs 9). The
dev-env gate baseline is therefore a **superset** of the CI error set on the
shared (non-iof3d) source — strictly the safer floor for the gate.

## Phase-2-owned files (any pyright error on a touched line here is a NEW error)

These are the source files Phase 02 actively refactors; an error on a touched
line in any of them is, by construction, a new error and fails the gate (D-11):

- `src/geodispbench3d/cli.py`
- `src/geodispbench3d/sweep/runner.py` (non-shim portions)
- `src/geodispbench3d/sweep/parameters.py`
- `src/geodispbench3d/tool/loader.py`
- `src/geodispbench3d/sweep/trial_record.py`
- `src/geodispbench3d/sweep/rescore.py`
- `src/geodispbench3d/sweep/evaluation.py`
- `src/geodispbench3d/results/store.py`
- `src/geodispbench3d/dataset/schema.py`

## Gate rule (verbatim)

> later waves: current pyright error multiset minus the baseline multiset must
> be empty (no NEW errors); clearing a baseline error is allowed; any error on a
> Phase-2-owned touched line is by construction a NEW error and fails the gate
> (D-11).

The gate signature is **line-number-independent** — `(repo-relative file path,
rule, whitespace-normalized message)` — so refactors that merely shift line
numbers do not register as new errors. Counts are compared as a multiset
(`collections.Counter`), so N identical baseline errors permit exactly N and
fail on the N+1th.

## How later waves run the gate

```bash
conda run -n iof3d_cosicorr3d-dev312 python \
    .planning/phases/02-targeted-fixes/pyright_gate.py
# exit 0 == PASS (no new errors); exit 1 == FAIL (prints each new diagnostic)
```

## Scope guardrails honoured (D-13)

- No `mypy` introduced.
- No `.github/` CI-workflow edits.
- No `pyproject.toml` edits.
