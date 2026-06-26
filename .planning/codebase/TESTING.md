# Testing Patterns

**Analysis Date:** 2026-06-26

## Test Framework

**Runner:**
- `pytest ~= 8.4` (declared in `pyproject.toml` `[project.optional-dependencies].dev`).
- No `[tool.pytest.ini_options]` section exists — pytest uses **default discovery**
  (no `addopts`, `testpaths`, custom markers, or `filterwarnings`). Tests live
  under `tests/` and are discovered by the `test_*.py` / `def test_*` convention.

**Assertion Library:**
- Plain `assert` (pytest rewriting). No `unittest`.
- `pytest.approx(...)` for float scalar comparisons.
- `numpy.testing.assert_allclose(...)` for array/vector comparisons.
- `math.isclose(...)` used occasionally for paired scalar comparison.

**Coverage:**
- `coverage ~= 7.0` is a dev dependency but **no coverage threshold is enforced**
  in config or CI. Coverage is available but not gated.

**Run Commands** (from `AGENTS.md` — this project mandates a dedicated conda env;
never use bare `python`/`pytest`):
```bash
conda run -n iof3d_cosicorr3d-dev312 pytest                 # all (extras self-skip)
conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -v   # framework-only suite
conda run -n iof3d_cosicorr3d-dev312 pytest tests/f2s3 -v   # F2S3 adapter suite
conda run -n iof3d_cosicorr3d-dev312 pytest tests/iof3d -v  # iof3D adapter suite
```
CI runs each directory separately: `pytest tests/<name> -v` per matrix job.

## Test File Organization

**Location:** separate `tests/` tree (not co-located with source). Mirrors the
three install profiles rather than the source package layout:

```
tests/
├── conftest.py            # top-level docs/config (profile explanation)
├── core/                  # framework wheel only, no tool extras
│   ├── __init__.py
│   ├── test_imports.py            # import-isolation invariant
│   ├── test_loaders.py            # YAML loader smoke tests
│   ├── test_metrics_builtins.py
│   ├── test_cli_adapter.py
│   ├── test_predictions_cache.py
│   ├── test_rescore.py
│   └── test_analyze.py
├── f2s3/                  # requires pchandler (F2S3 parser)
│   ├── conftest.py        # importorskip gate
│   └── test_parser.py
└── iof3d/                 # requires the iof3d extra
    ├── conftest.py        # importorskip gate
    └── test_adapter.py
```

**Naming:** files `test_<subject>.py`; functions `test_<behavior_described>`
with long descriptive names (`test_argparse_presence_flags_omit_when_false`,
`test_rescore_with_prediction_cache_hit`, `test_hash_parameters_is_order_invariant`).

**Profile self-skip pattern (important):** the per-extra test directories must
stay green even in a framework-only environment. Each extra dir's `conftest.py`
uses `pytest.importorskip` at module load so the whole directory skips cleanly
when its tool stack is absent:
```python
# tests/iof3d/conftest.py
iof3D = pytest.importorskip("iof3D", reason="install with: pip install 'geodispbench3d[iof3d]'")
```
```python
# tests/f2s3/conftest.py
pytest.importorskip("pchandler", reason="install with: pip install 'geodispbench3d[iof3d]' ...")
```

## Test Structure

Tests are flat module-level functions (no test classes). Shared construction is
done via module-level helper functions (prefixed `_`) and `@pytest.fixture`.

```python
"""Module docstring: states what is exercised and what is NOT (e.g. 'does not
spawn real subprocesses', 'does not invoke the F2S3 binary')."""

from __future__ import annotations

import numpy as np
import pytest

from geodispbench3d.metrics import builtins as mb


def _gt() -> PointDisplacements:        # private builder, returns a fixture-like object
    return PointDisplacements(points=(...))


def test_median_displacement_error_perfect() -> None:
    gt = _gt()
    err = mb.median_displacement_error(prediction=_perfect_prediction(gt), ground_truth=gt)
    assert err == pytest.approx(0.0, abs=1e-12)
```

**Patterns:**
- Every test file opens with `from __future__ import annotations` and a docstring
  describing scope and explicit non-goals.
- Test functions are annotated `-> None`.
- Setup is via private `_helper()` builders returning domain objects, or via
  `@pytest.fixture` returning a `dict[str, Path]` of generated artifacts
  (`tests/core/test_loaders.py::synthetic_bench`).
- No teardown needed — `tmp_path` is auto-cleaned by pytest.

## Mocking

**Framework:** essentially none — there is **no `unittest.mock` usage**. The
strategy is to test against **real objects with synthetic/stubbed inputs**
rather than mocks.

**Patterns observed:**
- **Stub-via-filesystem packages on `sys.path`:** `test_rescore.py` writes a tiny
  parser package into `tmp_path/stub_pkg/__init__.py` and prepends `tmp_path` to
  `sys.path`, then references it by entry-point string `stub_pkg:parse`. This
  exercises the real importlib resolver instead of monkeypatching it.
- **Test internal methods directly to avoid side effects:** `test_cli_adapter.py`
  calls `adapter._build_argv(...)` / `adapter._resolve_run_dir(...)` to validate
  argv assembly and hashed run-dir logic without spawning a subprocess. Entry
  binaries use harmless real paths (`/bin/true`).
- **Synthetic ground-truth + perfect predictions:** parser/metric tests build a
  small `PointDisplacements` GT and a prediction that matches it exactly, then
  assert error metrics are ~0 (`assert_allclose(..., atol=1e-9)`).
- **Fabricated run directories:** rescore/cache tests hand-write `summary.json`
  trial records (`write_trial_record`) to simulate a completed sweep without
  running Ax or the tool.
- **`on_record_rows` capture:** instead of mocking the parquet store, tests pass
  `on_record_rows=lambda rs: rows.extend(rs)` and assert on the captured rows.

**What NOT to mock:** importlib resolution, the metric registry, dataclass
construction, filesystem I/O (use `tmp_path`). Prefer a real stub object.

## Fixtures and Factories

- **`tmp_path`** (pytest builtin) is the primary fixture — used for GT CSVs, YAML
  configs, run dirs, prediction caches, and PLY/ASCII tool outputs.
- **Local `@pytest.fixture`** returns generated artifact paths
  (`synthetic_bench(tmp_path) -> dict[str, Path]`).
- **Module-level `_bootstrap_*` / `_gt` / `_perfect_prediction` helpers** build
  full benchmark layouts (suite + dataset + metrics + tool + run dir) inline using
  `textwrap.dedent` heredoc YAML strings. See `tests/core/test_rescore.py::_bootstrap_bench`.
- No `tests/fixtures/` data directory — all test data is synthesized in-process.

## Coverage

**Requirements:** None enforced (no threshold in `pyproject.toml` or CI).

**View Coverage:**
```bash
conda run -n iof3d_cosicorr3d-dev312 coverage run -m pytest tests/core
conda run -n iof3d_cosicorr3d-dev312 coverage report
```

**`# pragma: no cover`** is applied deliberately in source to exclude defensive /
optional-dependency branches from coverage accounting (optional Ax import fallback,
swallowed cache/provenance exceptions, `if __name__ == "__main__"`). When you add
a broad `except Exception` for a non-fatal side effect, tag it the same way.

## Test Types

**Unit / smoke tests (the dominant type):** loaders, metric builtins, argv
assembly, hashing, registry resolution. Fast, no I/O beyond `tmp_path`, no network.

**Integration-shape tests:** `test_rescore.py` and `test_analyze.py` wire the
loader + rescore/analyze runners + record-row callback together against a
fabricated run-dir layout. `tests/iof3d/test_adapter.py` and
`tests/f2s3/test_parser.py` exercise the full factory→adapter→parser glue against
synthetic tool outputs — without GPU, real subprocesses, or the actual tool binary.

**Invariant tests:** `tests/core/test_imports.py` statically asserts no module under
`geodispbench3d` imports `iof3D` / `pchandler` / `pc2img`, protecting the
framework-installs-without-extras guarantee.

**E2E tests:** none (no real tool binary or pipeline is invoked in the suite).

## Common Patterns

**Float / vector assertions:**
```python
assert err == pytest.approx(0.0, abs=1e-12)
np.testing.assert_allclose(by_label["A"]["vector"], [0.1, 0.0, 0.0], atol=1e-9)
assert math.isclose(row["pred_magnitude_m"], row["gt_magnitude_m"], abs_tol=1e-12)
```

**Skip when a precondition is absent (in addition to conftest gates):**
```python
if not suite_path.exists():
    pytest.skip(f"benchmark suite not present at {suite_path}")
pytest.importorskip("pchandler")   # inline, inside a test that needs it
```

**Resolve repo-relative paths from the test file:**
```python
repo_root = Path(__file__).resolve().parents[2]
suite_path = repo_root / "benchmarks" / "suites" / "iof3d_mattertal.yaml"
```

**Inline YAML config via dedent:**
```python
(tmp_path / "dataset.yaml").write_text(textwrap.dedent("""\
    id: stub-dataset
    cases:
      - name: only-case
        ...
"""))
```

**Error testing:** `pytest.raises` is available but rarely used here — most
negative paths are validated through summary counters (e.g. `summary.parser_misses`,
`summary.skipped_failed`) rather than raised exceptions, because the runners are
designed to degrade gracefully rather than throw.

---

*Testing analysis: 2026-06-26*
