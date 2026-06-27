# Phase 3: CLI Hardening - Pattern Map

**Mapped:** 2026-06-27
**Files analyzed:** 11 (4 modified source, 1 modified config, 1 net-new test, 1 modified test, 1 modified schema, 2 docs)
**Analogs found:** 11 / 11 (all in-repo; this is a hardening phase, every change has an existing seam)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/geodispbench3d/cli.py` | controller (CLI dispatcher) | request-response | *self* — rework against own handlers | exact (in-place) |
| `src/geodispbench3d/tool/cli_adapter.py` | service (subprocess adapter) | request-response (subprocess spawn) | *self* — `FileNotFoundError` branch is the template for the new `TimeoutExpired` / empty-glob branches | exact (in-place) |
| `src/geodispbench3d/tool/base.py` | model (ABC contract) | n/a (interface) | *self* — `prepare()`/`teardown()` no-op hooks already exist; may add a `ToolPreflightError` type | exact (in-place) |
| `src/geodispbench3d/tool/loader.py` | service (config → adapter) | transform (YAML→dataclass) | *self* — `_build_cli_adapter` `.get()` parsing is the pattern for new optional fields | exact (in-place) |
| `src/geodispbench3d/sweep/runner.py` | service (Ax loop) | event-driven (trial loop) | *self* — `prepare()` call site + `success=False`→failed-trial mapping already wired | exact (in-place) |
| `src/geodispbench3d/diagnostics.py` | utility (counter) | n/a | *self* — `PassDiagnostics.add(kind)` consumed as-is (no edit expected) | reuse, no change |
| `src/geodispbench3d_f2s3/conf/tool/f2s3.yaml` | config | n/a | *self* — add `execution.timeout_seconds` + `remediation`/`help_url` | exact (in-place) |
| `src/geodispbench3d/conf/schema/tool.schema.json` | config (doc-only schema) | n/a | *self* — add new fields, reconcile `from` enum | exact (in-place) |
| `tests/core/test_cli.py` | test (net-new) | request-response + real subprocess | `tests/core/test_cli_adapter.py` (adapter fixtures) + `tests/core/test_rescore.py` (run-dir/summary fixtures) | role-match |
| `tests/core/test_cli_adapter.py` | test (extend) | real subprocess | *self* — extend existing fixtures with a real-subprocess layer | exact (in-place) |
| `docs/integrating/cli-tool.md`, `docs/tools/f2s3.md` | doc | n/a | *self* — extend existing pages (no new doc files) | exact (in-place) |

No new modules are introduced. The one optional new symbol is a `ToolPreflightError`
exception class (D-02/D-10); home is `tool/base.py` (alongside the ABC) or
`tool/cli_adapter.py` — planner discretion.

## Pattern Assignments

### `src/geodispbench3d/tool/cli_adapter.py` (service, subprocess)

**Analog:** *self* — the existing `FileNotFoundError` branch is the canonical shape every
new failure branch must mirror.

**Failure-branch pattern to copy** (`cli_adapter.py:115-123`) — the `TimeoutExpired`
branch (D-05) and the empty-`predictions_glob` failure (D-07) must produce this exact
`TrialResult(success=False, error=...)` shape:
```python
except FileNotFoundError as exc:
    duration = time.perf_counter() - start
    return TrialResult(
        outputs=TrialOutputs(run_dir=run_dir or Path.cwd()),
        scalar_metrics={"runtime_seconds": duration},
        duration_seconds=duration,
        success=False,
        error=f"Tool entry not found: {exc}",
    )
```

**Timeout wiring** — add `timeout=self._timeout` to the existing `subprocess.run` call
(`cli_adapter.py:107-114`) and a sibling `except subprocess.TimeoutExpired:` branch.
`subprocess` and `time` are already imported (`:23-24`); `self._timeout` is a new
constructor field defaulting to `None` (no timeout = today's behavior, D-04). Log via the
project's lazy-`%` rule: `self._logger.warning("CLI trial timed out after %ss: %s", self._timeout, argv[0])`.

**Empty-glob failure** (`_collect_outputs`, `cli_adapter.py:202-221`) — the glob branch
currently returns `success`-implying outputs even with zero matches. D-07: when
`self._predictions_glob` is set and matches zero files → surface a failure. Keep
`_collect_outputs` pure if preferred and check emptiness in `run_trial` post-collection
(research §"Empty-glob failure" notes this is executor discretion). `figures_glob`
emptiness stays non-fatal.

**stdout_json deprecation** (`cli_adapter.py:81` default, `:190-201` reverse-scan) — D-06:
change the constructor default `outputs_from` from `"stdout_json"` to `"glob"`; turn the
`if self._outputs_from == "stdout_json":` block into a deprecation error stub. CRITICAL
(research Pitfall 1): `stdout_json` is the current *default*, so distinguishing
*explicitly set* from *unset* happens in the loader (see below), not here.

**Preflight `prepare()` override** (new method on `CliToolAdapter`, ABC hook at
`base.py:87`) — `entry` is already `shlex.split` at `cli_adapter.py:168` (tested at
`test_cli_adapter.py:69-80`), so inspect the leading tokens. Add `import shutil`. Shape
(research Pattern 2):
```python
def prepare(self) -> None:
    tokens = shlex.split(self._invocation.entry)
    if not tokens:
        raise ToolPreflightError("tool entry is empty", remediation=self._remediation)
    if shutil.which(tokens[0]) is None:
        raise ToolPreflightError(f"executable {tokens[0]!r} not found on PATH", ...)
    if tokens[:2] == ["conda", "run"]:
        env_name = _parse_conda_env(tokens)  # -n/--name; also handle -p/--prefix
        if env_name and env_name not in _conda_env_names():  # `conda env list --json`
            raise ToolPreflightError(f"conda env {env_name!r} not found", remediation=...)
```
Depth cap: "conda resolves + named env exists + leading binary resolvable" — do NOT spawn
the env (research Pitfall 3). New constructor field `self._remediation` / `self._help_url`
feed the error message.

---

### `src/geodispbench3d/tool/loader.py` (service, transform)

**Analog:** *self* — `_build_cli_adapter` (`loader.py:98-140`) reads keys via `.get()` on a
plain dict; no schema is enforced at runtime (research Unknown #4). New optional fields
follow the identical `.get()` pattern.

**New-field parsing pattern** (mirror `loader.py:112-140`):
```python
exec_raw = raw.get("execution") or {}                       # tool-level block (f2s3.yaml:15)
timeout_seconds = exec_raw.get("timeout_seconds")           # D-04; None = no timeout
remediation = raw.get("remediation")                        # D-02; or under a preflight: block
help_url = raw.get("help_url")
```
Thread these into the `CliToolAdapter(...)` construction (`loader.py:132-140`).

**stdout_json deprecation — the load-time half** (`loader.py:134`): today
`outputs_raw.get("from", "stdout_json")` collapses "unset" and "explicit stdout_json".
Per research Pitfall 1, read the raw value *before* defaulting so the two can be told
apart; default to `"glob"`; raise the deprecation error only on *explicitly* set
`from: stdout_json`.

**Naming caution** (research Pitfall 5): the tool-level `execution:` block parsed here is
DISTINCT from the suite-level `execution:` parsed in `suite/loader.py:118-122` into
`ExecutionConfig` (`parallel_trials`/`override_tool_mode`). Do not route
`timeout_seconds` through `suite/loader.py` or `ensure_supported()`.

---

### `src/geodispbench3d/cli.py` (controller, request-response)

**Analog:** *self* — the existing `analyze` subparser (`cli.py:79-89`) is the template for
the new `rescore` subparser; the dispatch chain (`cli.py:91-102`) is the template for the
new wrapper + dispatch branch.

**Subparser pattern to mirror** (`cli.py:79-89`, the `analyze` subparser):
```python
analyze_p = sub.add_parser("analyze", help="...")
analyze_p.add_argument("analysis", help="Path to analysis.yaml")
analyze_p.add_argument("--log-level", default="INFO")
analyze_p.add_argument("--pass-id", default=None, help="...")
```
D-09: add a `rescore` subparser carrying `suite`, `--reuse-parser-options`,
`--use-prediction-cache`, `--pass-id`, `--max-trials`; REMOVE those four
flags from `run_p` (`cli.py:37-67`); add `--timeout` (`type=float, default=None`) to
`run_p` (D-04). Add `if args.command == "rescore": return _cmd_rescore(...)` to the
dispatch (`cli.py:91-102`). `_cmd_rescore` already exists (`cli.py:188`) and is reused.

**Clean-error wrapper** (D-11) — wrap the dispatch (`cli.py:91-102`) so the eager raises
from `load_suite`/`load_tool_config`/`load_metrics_config`/`load_analysis` print
`error: <msg>` to stderr (no traceback) and return `1`. Mirror the existing stderr-print
style at `cli.py:296-300`:
```python
print(
    "streamlit is not installed. Install the 'dashboard' extra: ...",
    file=sys.stderr,
)
```
Catch `FileNotFoundError` / `ValueError`. Keep argparse's native exit `2` for usage.
Optional `--traceback` / `--log-level DEBUG` re-raises (research §"Clean Config-Load").

**Timeout precedence** (research Unknown #2) — mirror the existing override at
`cli.py:141` (`max_trials = args.max_trials or suite.search.max_trials`) BUT use
`is not None`, not truthiness (research Pitfall 2 / Anti-Patterns), so `--timeout 0` is
not dropped:
```python
effective_timeout = args.timeout if args.timeout is not None else <tool timeout_seconds>
```
Recommended wiring (A4): in `_cmd_sweep`, after `load_suite`, if `args.timeout is not None`
and `isinstance(suite.tool.adapter, CliToolAdapter)`, set the adapter's `_timeout`.

**Exit-code F-06 fix** (`_cmd_rescore` `cli.py:236`, `_cmd_analyze` `cli.py:282`) — both
currently `return 0 if summary.succeeded == summary.total else 1`. D-08: base the non-zero
code on GENUINE errors (`summary.parser_misses`, `rescore.py:82`), NOT on
`skipped_failed`/`total`. The `RescoreSummary` fields are available
(`rescore.py:78-85`: `total`, `succeeded`, `skipped_failed`, `parser_misses`).

**Discretion cleanups** (CONTEXT §Claude's Discretion / research §Exit-Code):
- `_cmd_dashboard` returns `2` when streamlit missing (`cli.py:301`) → change to `1`
  (missing-runtime-dependency, not usage error).
- `_cmd_list_metrics` (`cli.py:310-320`) returns `0` even on malformed `metrics.yaml` →
  route its `load_metrics_config` through the D-11 clean-error/exit-1 wrapper.

---

### `src/geodispbench3d/sweep/runner.py` (service, event-driven)

**Analog:** *self* — no structural change expected; the seams already exist.

**Preflight call site** — `self._adapter.prepare()` is already invoked once before the
trial loop (`runner.py:192` legacy `run`, `runner.py:251` `run_with_suite`). A
`ToolPreflightError` raised there propagates out of `run_with_suite` → `_cmd_sweep` →
`main()` clean-error wrapper → exit 1 (D-10). The `try/finally` guarantees `teardown()`
(`runner.py:204`, `:273`).

**Failed-trial mapping** — `success=False` TrialResults already flow to Ax as failed
trials via the `try/except` around `complete_trial`/`log_trial_failure`
(`runner.py:268-271`); timeout/empty-glob failures ride this existing path. The
`PassDiagnostics` instance (`runner.py:250`) already rides out on
`SweepRunSummary.non_fatal_failures` (`:280`) → CLI line (`cli.py:182-184`). Verify
timeout/empty-glob failures bump `pass_diag.add(...)` so they surface in the
"N non-fatal failures" line.

---

### `src/geodispbench3d_f2s3/conf/tool/f2s3.yaml` (config)

**Analog:** *self* — the existing (currently loader-ignored, soon-read) `execution:` block
(`f2s3.yaml:15-17`) is where `timeout_seconds` lands; `from: glob` (`:49`) already correct.
```yaml
execution:
  mode: subprocess
  in_process_safe: false
  timeout_seconds: <ceiling>     # D-04 — opt-in; F2S3 author's known runtime ceiling
remediation: "F2S3 runs in the f2s3-dev312 conda env. See https://github.com/gseg-ethz/F2S3_pc_deformation_monitoring"
help_url: https://github.com/gseg-ethz/F2S3_pc_deformation_monitoring   # D-03
```
Keep `entry: conda run -n f2s3-dev312 f2s3` as the canonical default (D-01).

---

### `tests/core/test_cli.py` (test, net-new) + `tests/core/test_cli_adapter.py` (extend)

**Analogs:**
- `tests/core/test_cli_adapter.py` — the adapter-construction + `tmp_path` fixture style
  (`test_cli_adapter.py:21-114`). The `entry="/bin/true"` pattern (`:23`) and the
  `tmp_path` hashed-run-dir tests (`:83-113`) are the base D-12 extends with real
  stub executables.
- `tests/core/test_rescore.py` — for the rescore-summary / run-dir fixtures the F-06
  exit-code tests need (read for the `RescoreSummary`/run-dir-walk fixture shape).

**Stub-executable pattern** (D-12; research §Tests) — write tiny `chmod +x` scripts with a
shebang to `tmp_path`, point a test `tool.yaml` `entry` at them:
```python
def _stub(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text("#!/usr/bin/env bash\n" + body)
    p.chmod(0o755)
    return p
# sleep-N (timeout), exit-code-N (nonzero), write-or-omit-output (glob paths)
```

**main()-level test pattern** — drive `main(["run", str(suite_yaml)])` /
`main(["rescore", str(suite_yaml)])` and assert the returned int exit code + captured
stderr `error: <msg>`. Mirror the construction style of `test_cli_adapter.py` (direct
import from `geodispbench3d`). Coverage targets (research §Phase Requirements → Test Map):
nonzero_exit, timeout, empty_glob, stdout_json_deprecated, preflight (deliberately-missing
`entry` — no real conda needed), usage (exit 2), config_error (exit 1), rescore_exit
(F-06), subcommand (argparse rejects rescore flags on `run`).

**Env split** (research Unknown #3): these tests run fully in `iof3d_cosicorr3d-dev312`
with no F2S3/conda dependency; `tests/f2s3` keeps its `pchandler` self-skip unchanged.
There is no `tests/core/conftest.py` today — a shared stub fixture can go there or inline.

---

## Shared Patterns

### Fail-soft, countable degradation
**Source:** `src/geodispbench3d/diagnostics.py` (`PassDiagnostics.add`, `:33-39`) +
`cli_adapter.py:115-123` (failure-branch shape).
**Apply to:** timeout (D-05) and empty-glob (D-07) failures — `success=False`,
`error=...`, then `pass_diag.add("timeout")` / `add("empty_glob")`. Never interactive,
never silently swallowed.
```python
def add(self, kind: str, n: int = 1) -> None:
    if n <= 0:
        return
    self.non_fatal_failures += n
    self.by_kind[kind] = self.by_kind.get(kind, 0) + n
```

### Eager-raise loaders + single catch point
**Source:** `suite/loader.py:89,93,101` and `tool/loader.py:54-59,101-102` (descriptive
`FileNotFoundError`/`ValueError`).
**Apply to:** the D-11 `main()` clean-error wrapper — loaders keep raising eagerly; `main()`
is the one place that catches and prints `error: <msg>` + exit 1.
```python
if not yaml_path.is_file():
    raise FileNotFoundError(f"Suite YAML not found: {yaml_path}")
if not (tool_ref and dataset_ref and metrics_ref):
    raise ValueError(f"Suite {yaml_path} must reference 'tool', 'dataset', and 'metrics'")
```

### Optional-field config parsing (no schema enforcement)
**Source:** `tool/loader.py:98-140` — every field via `raw.get(...)` on a plain dict.
**Apply to:** `timeout_seconds`, `remediation`, `help_url`. Adding them cannot reject any
existing YAML (research Unknown #4); `tool.schema.json` is doc-only, not load-enforced —
update it for IDE/docs accuracy but it gates nothing.

### Lazy-`%` logging at warning level
**Source:** convention (CLAUDE.md) + `cli.py:183`, `cli_adapter.py:104,128`.
**Apply to:** all new timeout/empty-glob/preflight log lines.
`self._logger.warning("CLI trial timed out after %ss: %s", self._timeout, argv[0])` —
never f-strings in log calls; `warning` for degradation.

### Subprocess `TrialResult(success=False)` → Ax failed trial
**Source:** `runner.py:268-271` (try/except `complete_trial`/`log_trial_failure`).
**Apply to:** timeout/empty-glob — no new runner plumbing; they reuse the existing
`success=False` → failed-trial → sweep-continues path.

## No Analog Found

None. Every file in scope is an in-place hardening of existing code or a test that extends
existing fixtures. The single net-new symbol — a `ToolPreflightError` exception (D-02/D-10)
— is a trivial `Exception` subclass carrying `remediation`/`help_url`; closest precedent is
the stdlib-exception usage throughout `tool/loader.py` (`ValueError`/`TypeError`/
`ImportError`). No external pattern from RESEARCH.md is required; the research itself
confirms a stdlib-only, seam-filling phase.

## Metadata

**Analog search scope:** `src/geodispbench3d/{cli,tool,sweep,suite,diagnostics}`,
`src/geodispbench3d_f2s3/conf/tool/`, `tests/{conftest,core}`, `docs/`.
**Files scanned:** 11 read in full or in targeted ranges (cli.py, cli_adapter.py, base.py,
loader.py, runner.py, diagnostics.py, rescore.py, suite/loader.py, f2s3.yaml,
test_cli_adapter.py, tests/conftest.py) + directory listings.
**Pattern extraction date:** 2026-06-27
</content>
</invoke>
