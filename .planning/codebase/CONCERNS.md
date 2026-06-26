# Codebase Concerns

**Analysis Date:** 2026-06-26

## Tech Debt

**Pervasive broad `except Exception` swallowing:**
- Issue: Non-fatal paths (provenance stamping, prediction-cache writes, audit-log appends, run-hash logging, trial-log dir creation) are wrapped in bare `except Exception:` that only `logger.debug(...)` and continue. Many are tagged `# pragma: no cover - defensive`, so they are never exercised by tests. Real failures (corrupt JSON, permission errors, schema drift) become invisible.
- Files: `src/geodispbench3d/sweep/runner.py` (lines 61, 295, 324, 354, 397, 403), `src/geodispbench3d/sweep/rescore.py` (lines 257, 295, 310, 330), `src/geodispbench3d/sweep/evaluation.py` (lines 89, 177), `src/geodispbench3d/results/predictions_cache.py` (line 120), `src/geodispbench3d/sweep/trial_record.py` (line 89).
- Impact: A sweep can complete "successfully" while silently dropping provenance, predictions cache entries, or whole metric values — corrupting downstream `--rescore`/`analyze`/dashboard results with no surfaced error.
- Fix approach: Narrow exception types (`OSError`, `json.JSONDecodeError`, `ImportError`), promote the swallowed failures to `WARNING` with a per-pass failure counter, and surface an aggregate "N non-fatal failures" line in the CLI summary so silent degradation is at least visible.

**`suite` / `config` objects passed as untyped `Any`/`object`:**
- Issue: The CLI and runner accept `suite: object` and reach into it with `# type: ignore[attr-defined]` (12+ ignores in `cli.py` alone). Provenance lookup uses a fragile chain: `getattr(suite.tool, "source_path", None) or getattr(suite.tool.raw, "get", lambda *_: None)("__source_path__")`.
- Files: `src/geodispbench3d/cli.py` (lines 132-157, 192-197), `src/geodispbench3d/sweep/runner.py` (lines 173-346, all `suite: Any`).
- Impact: Pyright cannot catch a typo or a renamed suite field; refactors of the suite schema fail silently at runtime instead of at type-check time.
- Fix approach: Introduce a typed `SuiteConfig` Protocol/dataclass (the loader already builds a structured object) and type the runner/CLI against it, removing the `type: ignore` cluster.

**Deprecated `datetime.utcnow()`:**
- Issue: `datetime.utcnow()` is deprecated as of Python 3.12; the project targets `requires-python ~=3.11` and CI runs on 3.12.
- Files: `src/geodispbench3d/sweep/trial_record.py:272`, `src/geodispbench3d/sweep/rescore.py:304,406`, `src/geodispbench3d/analysis/runner.py:173`, `src/geodispbench3d/results/predictions_cache.py:97`.
- Impact: DeprecationWarnings today; removal in a future CPython. Also produces naive timestamps with a manually appended `"Z"`, which is misleading.
- Fix approach: Replace with `datetime.now(datetime.UTC)` (3.11+) and format with `isoformat()` so the offset is real.

**Dead-code suppression hack:**
- Issue: `rescore.py` imports `asdict` it no longer uses and silences the linter with `_ = asdict  # Suppress an unused-import warning ... kept for future expansion.`
- Files: `src/geodispbench3d/sweep/rescore.py:27,410`.
- Impact: Minor — keeps an unused import alive and trains contributors that the lint gate is negotiable.
- Fix approach: Remove the import and the `_ = asdict` line; re-add when actually needed.

**Lazy imports inside hot loops:**
- Issue: `_evaluate_across_cases` imports `geodispbench3d.sweep.trial_record` (and `dataclasses.asdict`, `predictions_cache`) inside the per-case loop body rather than at module top.
- Files: `src/geodispbench3d/sweep/runner.py:232-282,308`.
- Impact: Negligible runtime cost (imports are cached) but obscures the dependency graph and the circular-import workaround it implies.
- Fix approach: Hoist to module level unless a genuine circular import is being dodged — if so, document the cycle (see Architectural Constraints).

## Known Bugs

**Parquet store is O(n²) and not concurrency-safe:**
- Symptoms: Every `on_record_rows` callback reads the entire existing parquet, concatenates the new rows, and rewrites the whole file.
- Files: `src/geodispbench3d/results/store.py:30-40`.
- Trigger: Any multi-trial sweep — each trial × case × record-metric triggers a full-file read-modify-write. A 5000-row results file is re-read and re-written on every append.
- Workaround: None in code. Two processes appending to the same parquet (e.g. parallel sweeps sharing a results path) will lose rows via the read-modify-write race.
- Fix approach: Append to a partitioned dataset (one parquet fragment per trial/pass under a directory) or buffer rows and flush once at end of sweep; readers already glob/duckdb-query so a directory dataset is transparent.

**Cross-case mean aggregation silently hides partial failures:**
- Symptoms: When a sweep dataset has multiple cases, the objective reported to Ax is the NaN-ignoring mean of each scalar across cases.
- Files: `src/geodispbench3d/sweep/runner.py:334-346`.
- Trigger: A trial where the parser fails (NaN) on some cases but succeeds on others. The failed cases are dropped from the mean, so Ax sees an optimistic objective computed from a subset of cases.
- Workaround: None.
- Fix approach: Track per-trial case coverage and either penalize missing cases or refuse to complete the trial when coverage drops below a threshold; at minimum emit the coverage count alongside the aggregated objective.

**`run --rescore` exit code conflates "failed trial" with "rescore error":**
- Symptoms: `_cmd_rescore` returns `1` whenever `succeeded != total`. But `total` includes run dirs skipped because the original trial had `status != "success"` (`skipped_failed`).
- Files: `src/geodispbench3d/cli.py:214`, `src/geodispbench3d/sweep/rescore.py:112-128,146-147`.
- Trigger: Any sweep that contains at least one failed trial — a subsequent `--rescore` always exits non-zero even though re-scoring itself worked perfectly.
- Workaround: Inspect the logged counters instead of trusting the exit code.
- Fix approach: Base the exit code on `parser_misses` / genuine rescore errors, not on the presence of pre-existing failed trials.

**stdout-JSON output collection is heuristic and order-sensitive:**
- Symptoms: `_collect_outputs` scans stdout bottom-up and parses the first line that starts with `{` as the result payload.
- Files: `src/geodispbench3d/tool/cli_adapter.py:190-201`.
- Trigger: A tool that prints any JSON-object-looking line after its real payload (debug dumps, progress JSON) will have that line misread as the trial result.
- Workaround: Use the glob-based `outputs_from` mode instead of `stdout_json`.
- Fix approach: Require a sentinel prefix (e.g. `GEODISPBENCH3D_RESULT: {...}`) or a dedicated results file rather than scraping stdout.

## Security Considerations

**Arbitrary code execution from YAML config by design:**
- Risk: Tool/metric/parser callables are resolved from `"package.module:attr"` strings in suite/tool/metrics/analysis YAML and imported + called. The `custom` adapter kind instantiates an arbitrary class with YAML-supplied `init_kwargs`; the `factory` kind calls an arbitrary function.
- Files: `src/geodispbench3d/tool/loader.py:152-189,213-221` (`_build_custom_adapter`, `_build_factory_adapter`, `_resolve_callable`), `src/geodispbench3d/metrics/registry.py:63-73` (`resolve_metric_fn`), `src/geodispbench3d/sweep/rescore.py:384-392` (`_resolve_dotted`).
- Current mitigation: None — this is intentional plugin behavior for trusted local configs.
- Recommendations: Document that suite YAML is executable and must be treated as trusted code. Never load a suite/tool/metrics/analysis YAML from an untrusted or network source. If external configs are ever needed, add an allowlist of importable module prefixes.

**Subprocess invocation from YAML `entry`:**
- Risk: `CliToolAdapter` runs `subprocess.run(argv, ...)` where `argv[0]` and `extra_args` come from the tool YAML `entry` (via `shlex.split`), and parameter values are interpolated into argv.
- Files: `src/geodispbench3d/tool/cli_adapter.py:98-114,167-185`.
- Current mitigation: `shell=True` is **not** used (good — no shell metacharacter expansion), and `shlex.split` tokenizes the entry. Parameter values pass through `_format_scalar`/`str()` as separate argv elements, not concatenated into a shell string.
- Recommendations: Already reasonable. Keep `shell=False`. Validate that `presence_flag_params` / param names cannot start with `--` from untrusted sources if config provenance ever loosens.

**Path-traversal guard on the predictions cache (positive note):**
- `_safe_segment` replaces any char outside `[A-Za-z0-9._-]` so a malicious `tool_id` like `../../etc` cannot escape the cache root.
- Files: `src/geodispbench3d/results/predictions_cache.py:155-163`.
- Note: `read_prediction` swallows all exceptions and returns `None`, so a corrupt cache file is silently treated as a miss (acceptable, but means corruption is undetectable from logs).

## Performance Bottlenecks

**Full parquet rewrite per append:**
- Problem: See "Parquet store is O(n²)" above — the dominant scaling cost for any non-trivial sweep.
- Files: `src/geodispbench3d/results/store.py:30-40`.
- Cause: Append implemented as read-all → concat → write-all.
- Improvement path: Partitioned dataset or end-of-sweep flush.

**In-memory tile load + merge in parsers:**
- Problem: Both output parsers load every tile/leaf point cloud and merge them into one in-memory `PointCloudData` before sampling at GT points.
- Files: `src/geodispbench3d_f2s3/output_parser.py:126-145`, `src/geodispbench3d_iof3d/output_parser.py:108-122`.
- Cause: `PointCloudData.merge(*pcds)` materializes the full merged cloud; sampling only needs points within a fixed radius of each GT label.
- Improvement path: Spatially pre-filter per tile (sphere filter before merge) or use a KD-tree index; only relevant for very large outputs.

## Fragile Areas

**Ax API compatibility shims:**
- Files: `src/geodispbench3d/sweep/runner.py:17-28` (import fallback), `:72-136` (`_create_experiment` signature introspection), `:375-409` (`_normalize_trial_data`).
- Why fragile: The runner introspects `AxClient.create_experiment`'s signature and tries `parameters` / `parameter_definitions` / `search_space`, then `objective_name` / `objectives` / `optimization_config`, and guesses the shape of `get_next_trial()`'s return by isinstance/`hasattr` probing. This is defensive scaffolding against an unstable pre-2.0 Ax API (pinned `ax-platform ~= 1.1`).
- Safe modification: Pin Ax to the exact tested version before touching this; add a recorded fixture of the real `get_next_trial`/`create_experiment` shapes so a version bump fails a test rather than silently mis-mapping kwargs.
- Test coverage: None — `runner.py` has no direct test (see Test Coverage Gaps).

**iof3D adapter coupling to upstream internal dataclasses:**
- Files: `src/geodispbench3d_iof3d/adapter.py:128-347` (`build_app_config_from_parameters`).
- Why fragile: This 220-line function is the sole `iof3D.*` import site and reconstructs `AppConfig`/`FlowSettings`/`ImgRes`/`Angle` field-by-field, mirroring a legacy `iof3D_analysis.ax.sweep.apply_parameters`. Any rename or signature change in iof3D's config dataclasses breaks it. It also silently falls back to base-config values on any bad/out-of-range parameter (e.g. invalid `opencv_detector`, ratio outside (0,1)), so a malformed sweep parameter is masked rather than reported.
- Safe modification: Change one parameter mapping at a time and run the iof3d test suite; never refactor the whole function blind. Consider asserting on unknown/invalid parameter values instead of silently coercing to base.
- Test coverage: The iof3d CI job is **disabled** (`enabled: "false"`) and tests self-skip when `iof3D` is unimportable — so this, the single largest and most brittle module (580 lines), is effectively untested in CI.

**Provenance lookup chain in the runner:**
- Files: `src/geodispbench3d/sweep/runner.py:238-241`.
- Why fragile: `getattr(suite.tool, "source_path", None) or getattr(suite.tool.raw, "get", lambda *_: None)("__source_path__")` silently yields `None` if neither attribute exists, and `None` flows into `ToolProvenance.from_yaml_path`.
- Safe modification: Replace with the typed suite interface noted under Tech Debt.

## Scaling Limits

**Single-file parquet results store:**
- Current capacity: Fine for hundreds of rows.
- Limit: Each append re-reads and re-writes the whole file (O(n²) total work) and holds the full frame in memory; thousands of trials × cases × record-metrics degrade sharply and risk a read-modify-write race under any parallelism.
- Scaling path: Partitioned parquet dataset (per pass / per trial fragment) or batched end-of-run flush.

**No sweep checkpoint / resume:**
- Current capacity: A sweep runs to completion in a single process; `AxClient` state lives only in memory.
- Limit: A crash mid-sweep loses all Ax optimization state (the surrogate model and trial history). Only the per-trial run dirs / parquet rows survive, which `--rescore` can re-evaluate but cannot resume the Bayesian search from.
- Scaling path: Persist `AxClient` JSON snapshot between trials and reload on restart.

## Dependencies at Risk

**iof3D — not on a reachable package index:**
- Risk: `iof3D ~= 0.1` is not installable from PyPI; the iof3d CI test job is hard-disabled, and development requires a specific conda env (`iof3d_cosicorr3d-dev312`, per `AGENTS.md`). Installing the `iof3d` extra transitively pulls torch/ptlflow/opencv (heavy stack).
- Impact: The iof3d adapter and parser are untested in CI and can only be exercised on one bespoke machine/env. Upstream changes go undetected until a manual local run.
- Migration plan: Publish iof3D to an index (the project already anticipates this — see the `pyproject.toml` comment and `AGENTS.md` "leaner env" note), then flip the CI job `enabled` flag to `"true"`.

**ax-platform ~1.1 — pre-2.0, unstable API:**
- Risk: The volume of compatibility shims in `runner.py` shows the Ax API surface churns across minor versions.
- Impact: A minor Ax bump can silently change `get_next_trial`/`create_experiment` shapes; the shims may mis-map rather than fail loudly.
- Migration plan: Pin Ax exactly, add fixtures asserting the API shape, and budget for an Ax 2.x migration.

**F2S3 — external binary via subprocess against a separate conda env:**
- Risk: The F2S3 adapter drives the tool by subprocess against a separately managed conda environment; the binary itself is an undocumented external dependency (`f2s3` extra is empty). The parser tests only exercise output-shape parsing, not a real F2S3 run.
- Impact: End-to-end F2S3 behavior is unverified in CI; an output-format change in F2S3 would only surface at runtime.
- Migration plan: F2S3 is installable as a Python library (`gseg-ethz/F2S3_pc_deformation_monitoring`, noted in `pyproject.toml`); consider an in-process adapter to remove the subprocess/env coupling.

## Missing Critical Features

**Only one ground-truth kind is implemented:**
- Problem: `load_ground_truth` documents `dense_flow`, `transformation_matrix`, and `segmentation_mask` kinds, but only `point_displacements` has a registered loader; all others raise `NotImplementedError`.
- Files: `src/geodispbench3d/dataset/ground_truth.py:63-73,118`.
- Blocks: Any benchmark case whose GT is dense flow, a rigid transform, or a segmentation mask cannot be scored without a downstream consumer registering a custom loader.

**No sweep checkpoint/resume:** see Scaling Limits — a crash loses Ax search state.

## Test Coverage Gaps

**Sweep orchestration (`runner.py`) — untested:**
- What's not tested: `AxSweepRunner`, the Ax compatibility shims, `run_with_suite`, cross-case aggregation, provenance stamping, and prediction caching during a live sweep.
- Files: `src/geodispbench3d/sweep/runner.py` (412 lines).
- Risk: The most behavior-dense module — and the one most exposed to Ax API drift — has no direct test. A broken kwarg mapping or trial-data normalization would pass CI.
- Priority: High.

**Metric dispatch glue (`evaluation.py`) — untested:**
- What's not tested: `evaluate_trial`'s `needs`-based kwarg assembly, gt-kind filtering, objective vs record splitting, and the parser-failure → `None` path.
- Files: `src/geodispbench3d/sweep/evaluation.py` (182 lines).
- Risk: Core scoring logic; a regression here silently corrupts every metric.
- Priority: High.

**Parquet store (`store.py`) — untested:**
- What's not tested: `append_record_rows` create/append behavior and the empty-rows short-circuit.
- Files: `src/geodispbench3d/results/store.py`.
- Risk: The persistence layer feeding the dashboard and `analyze` is unverified.
- Priority: Medium.

**iof3D adapter — present but skipped in CI:**
- What's not tested: `build_app_config_from_parameters` (the 220-line parameter translation), failure handling, and metadata stamping. The iof3d CI job is `enabled: "false"` and tests `importorskip("iof3D")`.
- Files: `src/geodispbench3d_iof3d/adapter.py` (580 lines).
- Risk: The largest, most upstream-coupled module is exercised by nothing CI can run.
- Priority: High (gated on iof3D being installable in CI).

**Other modules with no direct test reference:**
- `src/geodispbench3d/analysis/runner.py`, `src/geodispbench3d/tool/callable_adapter.py`, `src/geodispbench3d/metrics/registry.py`.
- Risk: `analyze` end-to-end, the in-process callable adapter, and metric resolution caching are only indirectly covered.
- Priority: Medium.

---

*Concerns audit: 2026-06-26*
