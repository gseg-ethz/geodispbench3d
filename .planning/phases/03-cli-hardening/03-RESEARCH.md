# Phase 3: CLI Hardening - Research

**Researched:** 2026-06-27
**Domain:** Python CLI / subprocess hardening, argparse, OmegaConf config loading, pytest stub-executable testing
**Confidence:** HIGH (codebase-grounded; every claim carries `file:line` evidence)

## Summary

This is a pure CLI/subprocess/config-hardening phase on an existing, mature,
tool-agnostic benchmark framework. All twelve product decisions are already
locked in `03-CONTEXT.md` (D-01…D-12). The job here was **not** to re-decide
anything but to resolve the four concrete technical unknowns the context defers
to research, and to ground every routed audit finding (F-06, F-07, F-16, F-32)
in current file:line evidence so the planner can write precise tasks.

The four unknowns resolve cleanly and favorably:

1. **Preflight mechanics** — `shutil.which()` + `conda env list` parsing is the
   right, fast, stdlib-only approach. The `entry` is already `shlex.split` at
   `cli_adapter.py:168`, so the leading token(s) are trivially inspectable.
2. **`--timeout` precedence** — CLI flag overrides YAML; the existing
   `args.max_trials or suite.search.max_trials` pattern (`cli.py:141`) is the
   template, with one important correction (use `is not None`, not truthiness).
3. **Test env split** — the D-12 stub-executable tests run **fully** in
   `iof3d_cosicorr3d-dev312` with no F2S3/conda dependency; `tests/f2s3` keeps
   its `pchandler` self-skip gate (`tests/f2s3/conftest.py:15`).
4. **OmegaConf parse of new optional fields** — **the JSON schema is NOT
   enforced at runtime** (no `jsonschema` import anywhere). The loader reads a
   plain dict via `.get()`, so unknown/extra keys are silently ignored. Adding
   `timeout_seconds` / `remediation` / `help_url` cannot reject any existing
   YAML. `f2s3.yaml` round-trips today even though its `execution:` block
   (`f2s3.yaml:15`) is **already silently ignored** by the loader.

**Primary recommendation:** Implement the timeout + empty-glob failures by
reusing the existing `success=False` / `TrialResult.error` shape
(`cli_adapter.py:115-140`) and the `PassDiagnostics` counter
(`diagnostics.py`); implement the preflight in `CliToolAdapter.prepare()` using
stdlib `shutil`/`subprocess`; wrap config-load in `main()` for clean exit-1
errors; promote `rescore` to its own argparse subcommand; deprecate
`stdout_json` via an error stub (noting it is currently the *default*).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Argument parsing / usage errors (exit 2) | CLI dispatcher (`cli.py`) | — | argparse owns structural validation; exit 2 is argparse-native |
| Clean config-load errors (exit 1, no traceback) | CLI dispatcher (`main()`) | suite/tool loaders (raise) | Loaders raise eagerly; `main()` is the single catch point (D-11) |
| Exit-code taxonomy (0/1/2) | CLI handlers (`cli.py`) | rescore/analyze summaries | Handlers translate summary counters → exit code (F-06) |
| Subprocess invocation contract (exit, missing output, timeout) | `CliToolAdapter` (`cli_adapter.py`) | `ToolResult` shape (`base.py`) | Adapter is the only place that spawns the tool |
| Env/binary preflight (fail-fast) | `CliToolAdapter.prepare()` | `runner.py` (invokes prepare) | `prepare()` runs once before trial 0 (D-10); sweep-path only |
| Timeout-as-failed-trial reporting | `runner.py` (Ax loop) | `cli_adapter.py` (raises/returns) | Runner already maps `success=False` → Ax failed trial |
| Non-fatal failure counting | `PassDiagnostics` (`diagnostics.py`) | CLI summary lines | Existing Phase-2 plumbing (F-08) |
| Tool-config field parsing (new optional fields) | `tool/loader.py` `_build_cli_adapter` | OmegaConf (plain dict) | Loader picks keys explicitly; no schema enforcement |
| F2S3 showcase + remediation hint | `f2s3.yaml` + `docs/tools/f2s3.md` | generic adapter error | F2S3 supplies the specific message into a generic mechanism (D-02) |

## Standard Stack

No new external packages are required. **Every hardening behavior in this phase
is implementable with the Python standard library already in use.**

### Core (all stdlib, already imported in the touched modules)
| Module | Used for | Where it already lives |
|--------|----------|------------------------|
| `subprocess` | `subprocess.run(timeout=…)` raises `TimeoutExpired` | `cli_adapter.py:23,108` `[VERIFIED: codebase]` |
| `shutil` | `shutil.which(exe)` to resolve `conda` / a bare binary on PATH | new import in `cli_adapter.py` `[ASSUMED]` (stdlib) |
| `shlex` | already splits `entry` into tokens for preflight inspection | `cli_adapter.py:22,168` `[VERIFIED: codebase]` |
| `argparse` | subcommand split + native usage exit 2 | `cli.py:14,24` `[VERIFIED: codebase]` |
| `logging` | warning on timeout / degraded path | throughout `[VERIFIED: codebase]` |
| `time` | `time.perf_counter()` duration already captured | `cli_adapter.py:24,106` `[VERIFIED: codebase]` |

### Supporting (existing project modules to reuse)
| Module | Purpose | When to use |
|--------|---------|-------------|
| `geodispbench3d.diagnostics.PassDiagnostics` | count non-fatal timeout/empty-glob failures | D-05/D-07 plug in via `diag.add("timeout")` / `diag.add("empty_glob")` `[VERIFIED: codebase]` |
| `geodispbench3d.tool.base.TrialResult` | `success=False, error=…` failure shape | timeout + empty-glob follow the existing `FileNotFoundError`/`exit=N` shape `[VERIFIED: codebase]` |

**Installation:** None. This phase adds zero dependencies.

## Package Legitimacy Audit

**Not applicable** — this phase installs no external packages. All behavior uses
the Python standard library and existing in-repo modules. No npm/PyPI/crates
package additions to audit.

## Architecture Patterns

### System Architecture Diagram

```text
                         geodispbench3d <subcommand> <args>
                                      │
                                      ▼
                       ┌──────────────────────────────┐
   argparse usage  ◄───┤  main(argv)  (cli.py:24)      │
   error → exit 2      │  subparser dispatch (:91-102) │
                       └───────────────┬──────────────┘
                                       │  D-11: wrap load+dispatch
                                       ▼  catch FileNotFoundError/ValueError
                  ┌────────────────────────────────────────┐
   clean "error:  │  _cmd_run / _cmd_rescore / _cmd_analyze │
   <msg>"  ◄──────┤  _cmd_dashboard / _cmd_list_metrics     │
   exit 1         └───────┬───────────────────────┬─────────┘
                          │ run (sweep)           │ rescore / analyze
                          ▼                        ▼  (no tool invoked)
              ┌───────────────────────┐   exit code keyed off
              │ load_suite            │   genuine errors (parser_misses),
              │ (suite/loader.py:86)  │   NOT skipped_failed  (F-06, D-08)
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────────────────┐
              │ AxSweepRunner.run_with_suite       │
              │ (runner.py:214)                    │
              │   adapter.prepare()  ◄── D-10 PREFLIGHT (env/binary)
              │     │  preflight fails → raise → main() → exit 1
              │     ▼  per trial, per case:
              │   adapter.run_trial(request)       │
              └───────────┬───────────────────────┘
                          ▼
              ┌───────────────────────────────────────────┐
              │ CliToolAdapter.run_trial (cli_adapter.py:98)│
              │   subprocess.run(argv, timeout=T)           │
              │     ├─ FileNotFoundError → success=False     │ (exists :115)
              │     ├─ TimeoutExpired   → success=False ◄── F-32/D-05 NEW
              │     ├─ returncode != 0  → success=False     │ (exists :127)
              │     └─ ok → _collect_outputs (:188)          │
              │            ├─ glob matches 0 preds → fail ◄── F-07/D-07 NEW
              │            └─ stdout_json → DEPRECATE ◄────── F-07/D-06
              └───────────┬───────────────────────────────┘
                          ▼  success=False reported to Ax as failed trial
              runner: complete_trial / log_trial_failure (:268/:271)
              + PassDiagnostics.add(...) → "N non-fatal failures" CLI line
```

File-to-implementation mapping is in the Component Responsibilities table of
`CLAUDE.md`; this diagram traces the failure-handling data flow only.

### Pattern 1: Fail-soft, countable degradation (reuse, do not reinvent)
**What:** Non-fatal problems are caught, narrowed, logged at `warning`, counted
in `PassDiagnostics`, and surfaced as the aggregate "N non-fatal failures" CLI
line — never made interactive, never silently swallowed.
**When to use:** Timeout expiry (D-05) and empty `predictions_glob` (D-07).
**Example (existing shape the new branches must match):**
```python
# Source: src/geodispbench3d/tool/cli_adapter.py:115-123 (FileNotFoundError branch)
except FileNotFoundError as exc:
    duration = time.perf_counter() - start
    return TrialResult(
        outputs=TrialOutputs(run_dir=run_dir or Path.cwd()),
        scalar_metrics={"runtime_seconds": duration},
        duration_seconds=duration,
        success=False,
        error=f"Tool entry not found: {exc}",
    )
# The TimeoutExpired branch follows the same shape with error="timeout".
```

### Pattern 2: Fail-fast preflight in `prepare()` (D-10)
**What:** `ToolAdapter.prepare()` (`base.py:87`) is a no-op hook already invoked
once before the trial loop (`runner.py:251`, also `:192` in the legacy `run`).
Implementing the env/binary check there means a missing env raises **before Ax
launches trial 0**.
**When to use:** Sweep path only — `rescore`/`analyze` never invoke the tool
(D-10), so they need no preflight.
**Example:**
```python
# Target: CliToolAdapter.prepare() — new override
def prepare(self) -> None:
    tokens = shlex.split(self._invocation.entry)  # already how argv[0] is built
    if not tokens:
        raise ToolPreflightError("tool entry is empty", remediation=self._remediation)
    exe = tokens[0]
    if shutil.which(exe) is None:
        raise ToolPreflightError(f"executable {exe!r} not found on PATH", ...)
    # conda run -n ENV BIN  → verify the named env resolves
    if exe == "conda" and tokens[:2] == ["conda", "run"]:
        env_name = _parse_conda_env(tokens)   # -n ENV / --name ENV
        if env_name and env_name not in _conda_env_names():
            raise ToolPreflightError(f"conda env {env_name!r} not found", remediation=...)
```

### Pattern 3: Subcommand split with shared handler (D-09)
**What:** `_cmd_rescore` already exists (`cli.py:188`) and is reached via
`_cmd_run` branching on `args.rescore` (`cli.py:121`). Promoting `rescore` to a
top-level subparser (mirroring `analyze` at `cli.py:79`) moves the four
rescore-only flags onto it so argparse **structurally rejects** them on `run`.
**Example:** Add `rescore_p = sub.add_parser("rescore", ...)` with `suite`,
`--reuse-parser-options`, `--use-prediction-cache`, `--pass-id`, `--max-trials`;
remove those four from `run_p` (`cli.py:37-67`); add `if args.command ==
"rescore": return _cmd_rescore(...)` to dispatch (`cli.py:91-102`).

### Anti-Patterns to Avoid
- **Interactive prompt / watchdog thread on timeout.** Explicitly deferred
  (CONTEXT `<deferred>`); Ax sweeps run for hours, often headless on HPC. Use
  blocking `subprocess.run(timeout=…)`, not a `Popen`/poll loop.
- **Truthiness override for `--timeout`.** `args.max_trials or …` (`cli.py:141`)
  is fine for trials but **wrong for timeout**: `--timeout 0` would be discarded.
  Use `args.timeout if args.timeout is not None else <yaml value>`.
- **Deep conda env validation.** Do not invoke the tool, do not `conda run … --help`,
  do not import the tool. The preflight must be fast (runs before every sweep).
  Cap it at "conda resolves + named env exists + leading binary resolvable".

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess timeout | A `Popen` + watchdog-thread + manual kill | `subprocess.run(argv, timeout=T)` → catch `TimeoutExpired` | stdlib kills the child and raises; matches existing blocking call at `cli_adapter.py:108` |
| Executable resolution | Manual `$PATH` split + `os.access` loop | `shutil.which(exe)` | stdlib, handles PATHEXT/permissions/edge cases |
| Conda env enumeration | Parsing `$CONDA_PREFIX`/`envs/` dirs by hand | `conda env list` (parse names) OR `conda env list --json` | authoritative, conda-version-stable; `--json` avoids comment/format parsing |
| Non-fatal failure counting | A new counter | `PassDiagnostics.add(kind, n)` (`diagnostics.py:33`) | already threaded through sweep/rescore/analyze (F-08) |
| Usage/argument validation | Hand-rolled checks | argparse subparsers + `required=True` (`cli.py:26`) | argparse exits 2 natively; D-09 leans on structural rejection |
| Tool-config field parsing | A typed OmegaConf structured schema | existing `raw.get(...)` dict access in `_build_cli_adapter` | no schema is enforced at runtime; extra keys are already ignored |

**Key insight:** Every routed finding has an existing in-repo seam. The phase is
"fill in the no-op hook / add one more `except` branch / move argparse args /
add a `.get()`", not "introduce machinery."

## Runtime State Inventory

This is **not** a rename/refactor/migration phase — it adds failure handling and
moves CLI argument wiring. No stored data, live-service config, OS-registered
state, secrets, or build artifacts embed a string being renamed. One adjacent
note: the `rescore`-subcommand split (D-09) is a **CLI-surface break**, not a
state migration — its ripple is documentation + a migration note, not data:
- `docs/rescoring-and-analysis.md`, `README.md` (Quickstart ~line 43-52),
  `docs/quickstart.md` reference `run --rescore` and must be updated.
- **None** of databases / parquet / predictions-cache / `summary.json`
  provenance change shape — verified: this phase touches no persistence format.

## OmegaConf / Config-Parse Behavior (Unknown #4 — RESOLVED)

**Finding (HIGH):** Adding optional tool-config fields will NOT reject existing
in-repo YAMLs, and `f2s3.yaml` round-trips today.

Evidence:
- `load_tool_config` does `raw = OmegaConf.to_container(OmegaConf.load(path),
  resolve=True)` then asserts it's a `dict` (`tool/loader.py:57-59`). It is a
  **plain Python dict**, not a structured/typed OmegaConf schema — so OmegaConf
  performs **no struct-mode rejection** of unknown keys. `[VERIFIED: codebase]`
- `_build_cli_adapter` reads only specific keys via `.get()`:
  `invocation`, `outputs`, `entry` (`tool/loader.py:98-140`). Any other
  top-level key is retained in `raw` (passed through to `ToolConfig.raw`,
  `:80`) but never validated. `[VERIFIED: codebase]`
- **The JSON schema is documentation-only — NOT enforced.** `grep` for
  `jsonschema` across `src/`, `tests/`, `pyproject.toml` returns **nothing**;
  `tool/loader.py` and `suite/loader.py` never reference the schema file. So
  `src/geodispbench3d/conf/schema/tool.schema.json` (which currently lists only
  `from: [stdout_json, glob, fixed_path]` and an `execution` block with only
  `mode`/`in_process_safe`) does not block new fields at load time.
  `[VERIFIED: codebase]`
- **Proof by existing precedent:** `f2s3.yaml:15-17` already declares an
  `execution: {mode, in_process_safe}` block that `_build_cli_adapter`
  **never reads** — yet f2s3 loads fine. New optional fields behave identically.
  `[VERIFIED: codebase]`

**Planner implications:**
- `execution.timeout_seconds` (D-04) lands under the tool YAML's existing
  (currently-ignored) `execution:` block. The loader must be extended to read
  `raw.get("execution", {}).get("timeout_seconds")` and pass it to
  `CliToolAdapter(... timeout=…)`. **Naming caution:** this tool-level
  `execution` block is **distinct** from the *suite*-level `execution` block
  parsed in `suite/loader.py:118-122` into `ExecutionConfig`
  (`parallel_trials`/`override_tool_mode`). Keep them separate; don't conflate.
- `remediation` / `help_url` (D-02) are new top-level (or under a `preflight:`)
  optional tool keys; read them in `load_tool_config` / `_build_cli_adapter` and
  thread to the adapter for inclusion in the structured preflight error.
- **Update the JSON schema too** (`tool.schema.json`): add `timeout_seconds` to
  the `execution` block, add `remediation`/`help_url`, and (D-06) reconcile the
  `from` enum (deprecate `stdout_json`). The schema is for IDE/docs, but leaving
  it stale would mislead integrators.

## stdout_json Deprecation (F-07 / D-06 — IMPORTANT NUANCE)

**Finding (HIGH):** `stdout_json` is the current **default**, not an opt-in.
- `CliToolAdapter.__init__` defaults `outputs_from="stdout_json"`
  (`cli_adapter.py:81`); the loader defaults `from`, "stdout_json"
  (`tool/loader.py:134`). `[VERIFIED: codebase]`
- The only CLI tool in-repo, `f2s3.yaml:49`, sets `from: glob`. iof3D is a
  `python_callable`/factory adapter, not a CLI tool. So **no in-repo YAML relies
  on `stdout_json`** — confirming D-06's "safe to deprecate." `grep` confirms
  `stdout_json` appears only in `cli_adapter.py`, the loader default, the schema,
  and three docs files. `[VERIFIED: codebase]`

**Planner nuance the executor must handle:** Because `stdout_json` is the
*default*, a naive "raise if `outputs_from == 'stdout_json'`" stub would break
**every** CLI YAML that simply omits `outputs.from`. To deprecate safely:
1. Change the blessed default to `glob` (in both `cli_adapter.py:81` and
   `tool/loader.py:134`), AND
2. Distinguish *explicitly set* `from: stdout_json` (raise the deprecation
   error) from *unset* (now defaults to glob). The loader currently collapses
   both via `outputs_raw.get("from", "stdout_json")` — read the raw value
   **before** defaulting to tell them apart.

This is the friendlier deprecation stub D-06 prefers over a silent hard-remove.

## `--timeout` vs `execution.timeout_seconds` Precedence (Unknown #2 — RESOLVED)

**Finding (HIGH):** CLI flag overrides YAML. Confirmed by the existing override
pattern and the config flow.

How config flows today (argparse → handler → runner → adapter):
- `args` parsed in `main()` (`cli.py:91`), dispatched to `_cmd_run` →
  `_cmd_sweep` (`cli.py:105,127`).
- Override precedent: `max_trials = args.max_trials or suite.search.max_trials`
  (`cli.py:141`). `[VERIFIED: codebase]`
- **Wiring wrinkle:** the adapter is already fully constructed inside
  `load_tool_config` (`tool/loader.py:132`, returning `suite.tool.adapter`)
  *before* the CLI sees `args`. So a `--timeout` override cannot be passed at
  construction. Two viable mechanisms (planner/executor discretion):
  - **(A) Mutate the built adapter in `_cmd_sweep`:** after `load_suite`, if
    `args.timeout is not None` and `isinstance(suite.tool.adapter,
    CliToolAdapter)`, set its `_timeout`. Smallest change; keeps `run_trial`
    signature stable. Recommended.
  - **(B) Thread timeout through `run_with_suite` → `run_trial`:** changes the
    `TrialRequest`/call signature; broader blast radius. Avoid unless a cleaner
    contract is wanted.
- **Resolution rule to document:** effective timeout =
  `args.timeout if args.timeout is not None else <tool execution.timeout_seconds>
  else None (no timeout)`. Use `is not None` (NOT `or`) so `--timeout 0` /
  `timeout_seconds: 0` are not silently dropped — decide whether `0` means "no
  timeout" or "instant"; recommend treating `<= 0` / unset as "no timeout"
  (today's behavior, now explicit per D-04).
- `--timeout` is a `run`-only flag (sweep path invokes the tool). It is one of
  the new argument surfaces D-04/CLI-04 tests must cover.

## Preflight Resolution Mechanics for `conda run -n ENV bin` (Unknown #1 — RESOLVED)

**Finding (HIGH for the mechanism; the depth is a recommendation):**

The `entry` is already tokenized with `shlex.split` (`cli_adapter.py:168`, tested
at `test_cli_adapter.py:69-80` which asserts `conda run -n my-env mytool` splits
to `["conda","run","-n","my-env","mytool"]`). So the preflight can inspect the
leading tokens directly. `[VERIFIED: codebase]`

**Recommended depth (fast, stdlib-only, runs in `prepare()` before every sweep):**
1. `tokens = shlex.split(entry)`; empty → structured error.
2. `shutil.which(tokens[0])` — resolves the leading executable (`conda`, or a
   bare binary for the in-env override of D-01). `None` → structured error +
   remediation. `[ASSUMED]` (stdlib behavior; not exercised in this session)
3. If `tokens[:2] == ["conda", "run"]`: parse the env name from `-n ENV` /
   `--name ENV`; verify it appears in the set of conda env names. Recommended
   source: `conda env list --json` (parse `["envs"]` basenames) for
   format-stable output; fall back to `conda env list` line parsing if `--json`
   is unavailable. `[ASSUMED]`
4. Resolve the trailing binary (`tokens[-1]`, e.g. `f2s3`) only **shallowly** —
   do NOT `conda run … which f2s3` (that spawns the env and defeats "fast").
   Recommended: stop at "conda resolves + named env exists"; treat a missing
   *binary inside the env* as caught by trial 0's existing nonzero-exit /
   FileNotFoundError path. Document this boundary explicitly.

**Depth recommendation:** "conda resolves + leading binary resolvable + named
env exists" is the sweet spot. Going deeper (verifying the in-env binary)
requires spawning the env, which is slow and fragile; leave it to the first
trial's existing failure handling. The structured error from steps 1-3 plus the
F2S3 `remediation` hint (D-02/D-03 → gseg-ethz repo) satisfies CLI-03/F-16.

**Edge cases to handle:** `-n`/`--name` both forms; `conda run -p /path/env`
(prefix instead of name) — recommend recognizing `-p`/`--prefix` and checking
the path exists; a bare-binary entry (no conda) — just step 2.

## Exit-Code Taxonomy & F-06 Fix (CLI-01 / D-08)

Current exit-code logic (the F-06 bug):
- `_cmd_rescore`: `return 0 if summary.succeeded == summary.total else 1`
  (`cli.py:236`). `RescoreSummary.total` increments for *every* run dir,
  including `skipped_failed` (dirs whose **original** trial failed) and
  `skipped_no_summary` (`rescore.py:78-85`). So any sweep containing one failed
  trial makes a *successful* rescore exit non-zero. `[VERIFIED: codebase, REPORT F-06]`
- `_cmd_analyze`: same `succeeded == total` shape (`cli.py:282`).

D-08 fix:
- Base the rescore non-zero code on **genuine** errors — `summary.parser_misses`
  (`rescore.py:82`) — not on the presence of `skipped_failed`/`skipped_no_summary`.
- Taxonomy: `0` = success; `1` = runtime failure (genuine rescore/parser errors,
  real trial-scoring failures, env/preflight failures, config-load failures —
  **NOT** pre-existing `skipped_failed`); `2` = usage/argument error
  (argparse-native only). Document as a table in the CLI reference.

Discretion cleanups (CONTEXT `### Claude's Discretion`) to fold in:
- `_cmd_dashboard` returns `2` when streamlit is missing (`cli.py:301`) — that's
  a missing-runtime-dependency error → should be **exit 1**.
- `_cmd_list_metrics` (`cli.py:310`) returns `0` even on a malformed
  `metrics.yaml`; route its load through the D-11 clean-error/exit-1 handler.

## Clean Config-Load Errors at `main()` (D-11)

Loaders raise eagerly with descriptive messages:
- `load_suite`: `FileNotFoundError` (`suite/loader.py:91`), `ValueError`
  (`:95`, `:103`), plus `_validate_objective` `ValueError` (`:149`).
- `load_tool_config`: `FileNotFoundError`/`ValueError` (`tool/loader.py:54-59,102`).

Today these propagate as full tracebacks out of `_cmd_run`/`_cmd_analyze`. D-11:
wrap load+dispatch in `main()` (around the `cli.py:91-102` dispatch) in a handler
that catches `FileNotFoundError`/`ValueError`, prints `error: <msg>` to stderr
(no traceback), and returns `1`. Keep argparse's exit `2` strictly for usage.
**Optional planner nicety:** a `--traceback` flag (or `--log-level DEBUG`) that
re-raises for developers.

## Common Pitfalls

### Pitfall 1: Deprecation stub breaks the default path
**What goes wrong:** Raising on `outputs_from == "stdout_json"` breaks every CLI
YAML that omits `outputs.from`, because that's the current default.
**How to avoid:** Change default to `glob` AND read the raw `from` value before
defaulting so "explicitly stdout_json" can be told from "unset." (See dedicated
section above.)

### Pitfall 2: `--timeout 0` silently dropped
**What goes wrong:** Copying the `args.max_trials or …` truthiness pattern drops
`--timeout 0`.
**How to avoid:** Use `is not None`. Decide and document `<= 0` semantics.

### Pitfall 3: Preflight that spawns the env
**What goes wrong:** Verifying the in-env binary via `conda run … which` makes
`prepare()` slow (spawns a full env) and fragile on HPC.
**How to avoid:** Cap depth at "conda + env name + leading binary"; let trial 0
surface an in-env-missing binary via existing nonzero-exit handling.

### Pitfall 4: Empty glob conflated with success
**What goes wrong:** Under `from: glob`, zero matched `predictions_glob` files
currently yields empty `predictions` and `success=True` (`cli_adapter.py:202-221`)
— silent "nothing to score" (the missing-output half of the contract).
**How to avoid (D-07):** When `predictions_glob` is set but matches zero files →
`success=False, error="no predictions matched <glob>"`. An empty `figures_glob`
stays non-fatal (figures are auxiliary).

### Pitfall 5: Tool-level vs suite-level `execution` confusion
**What goes wrong:** Two different `execution:` blocks exist — the suite-level
one (`ExecutionConfig`: `parallel_trials`/`override_tool_mode`,
`suite/loader.py:118`) and the tool-level one in `f2s3.yaml:15`. Putting
`timeout_seconds` on the wrong one, or routing it through `ensure_supported()`,
would misbehave.
**How to avoid:** `timeout_seconds` is a **tool**-config field; parse it in
`tool/loader.py`, not `suite/loader.py`.

## Code Examples

### Timeout branch in `run_trial` (follows existing FileNotFoundError shape)
```python
# Target: src/geodispbench3d/tool/cli_adapter.py, alongside :115-123
start = time.perf_counter()
try:
    proc = subprocess.run(
        argv, capture_output=True, text=True, env=self._env,
        check=False, timeout=self._timeout,  # None today; opt-in via D-04
    )
except FileNotFoundError as exc:
    ...  # existing :115-123
except subprocess.TimeoutExpired:
    duration = time.perf_counter() - start
    self._logger.warning("CLI trial timed out after %ss: %s", self._timeout, argv[0])
    return TrialResult(
        outputs=TrialOutputs(run_dir=run_dir or self._run_dir_root or Path.cwd()),
        scalar_metrics={"runtime_seconds": duration},
        duration_seconds=duration,
        success=False, error="timeout",
    )
```
The runner already maps `success=False` to an Ax failed trial via its
`try/except` around `complete_trial` (`runner.py:268-271`), and the
empty-glob/timeout counts feed `PassDiagnostics` → the existing
"N non-fatal failures" line (`cli.py:183`).

### Empty-glob failure in `_collect_outputs`
```python
# Target: src/geodispbench3d/tool/cli_adapter.py:202-221 (glob branch)
predictions = tuple(sorted(effective_run_dir.glob(self._predictions_glob))) \
    if self._predictions_glob else ()
if self._predictions_glob and not predictions:
    # D-07: nothing to score is data corruption, not success.
    # Surface as success=False to run_trial's caller (return a sentinel /
    # raise an internal signal the run_trial wraps into a failed TrialResult).
    ...
```
(Executor decides whether `_collect_outputs` returns a failure signal or
`run_trial` checks emptiness post-collection; the latter keeps `_collect_outputs`
pure.)

## Tests: Env Split & Mechanics (Unknown #3 — RESOLVED; CLI-04 / D-12)

**Finding (HIGH):** The new stub-executable tests run fully in
`iof3d_cosicorr3d-dev312` with **no F2S3/conda dependency**.

Current layout (`tests/conftest.py:1-17`):
- `tests/core/` — framework-only; no tool extras, no self-skip.
- `tests/iof3d/` — `pytest.importorskip("iof3D")` (`tests/iof3d/conftest.py`).
- `tests/f2s3/` — `pytest.importorskip("pchandler")` (`tests/f2s3/conftest.py:15`).
  Note: this gates on the **parser's** `pchandler` dependency, not on a real
  F2S3 binary or the `f2s3-dev312` conda env. `[VERIFIED: codebase]`
- No `pytest.ini`/`tox.ini`/`setup.cfg`; no `[tool.pytest]` or markers in
  `pyproject.toml`. Test selection is by directory (`pytest tests/core`, per
  `AGENTS.md`). `[VERIFIED: codebase]`

**D-12 placement:** new `tests/core/test_cli.py` (net-new — there is no
`main()`-level CLI test today; `tests/core/test_cli_adapter.py` only covers argv
building, `:21-114`). It belongs in `tests/core/` because:
- It uses **tiny stub executables written to `tmp_path`** (a sleep-N script for
  timeout; an exit-code-N script for nonzero exit; a write-or-omit-output script
  for glob), pointed at by a test `tool.yaml` `entry`. No `conda`, no F2S3.
- It drives both `CliToolAdapter.run_trial` and `main(["run", …])` /
  `main(["rescore", …])`, asserting exit codes + clean messages.
- The preflight is tested via a deliberately-missing `entry` (e.g.
  `entry: /nonexistent/tool` or `conda run -n no-such-env tool`) — exercises the
  `shutil.which`/env-name path **without** a real conda env.

**`tests/f2s3` unchanged:** parser tests keep the `pchandler` self-skip and, per
`AGENTS.md`, are exercised via `conda run -n f2s3-dev312 pytest tests/f2s3` for
the end-to-end binary path — but **no new Phase-3 test depends on that env.**

**Stub-script portability note:** stub executables must be `chmod +x` and have a
shebang (`#!/usr/bin/env bash` or `#!/usr/bin/env python3`); on Linux (the WSL2
dev target) this is fine. Faithfulness over speed is the stated D-12 rationale —
real `subprocess`/timeout/glob plumbing is exercised end-to-end.

## State of the Art

| Old Approach | Current Approach | When | Impact |
|--------------|------------------|------|--------|
| `subprocess.run` no timeout (`cli_adapter.py:107`) | `subprocess.run(timeout=…)` + `TimeoutExpired` | Phase 3 | hung tool no longer stalls the sweep (F-32) |
| `stdout_json` reverse-scan heuristic (default) | `glob` blessed; `stdout_json` deprecated stub | Phase 3 | removes silent-data-corruption landmine (F-07) |
| `run --rescore` flag | `rescore` top-level subcommand | Phase 3 | argparse structurally rejects rescore-only flags on `run` (D-09) |
| exit code on `succeeded == total` | exit code on `parser_misses` | Phase 3 | F-06: pre-existing failed trials no longer poison rescore exit code |
| tracebacks on bad config | `error: <msg>` + exit 1 at `main()` | Phase 3 | clean CLI UX (D-11) |
| no env/binary preflight | `prepare()` preflight + remediation | Phase 3 | actionable F2S3 env errors before trial 0 (F-16/CLI-03) |

**Deprecated/outdated:** `outputs_from="stdout_json"` (becomes a deprecation
error stub). JSON schema `tool.schema.json` is stale relative to the new fields
and should be updated (doc/IDE only — not load-enforced).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `shutil.which()` is the right stdlib executable resolver for the preflight | Preflight mechanics | Low — stdlib, universally used; alternative is manual PATH walk |
| A2 | `conda env list --json` is the format-stable env enumeration | Preflight mechanics | Low — if `--json` unsupported on the target conda, fall back to plain-text parse |
| A3 | A shallow preflight (no in-env binary check) is acceptable depth | Preflight mechanics | Low — CONTEXT explicitly wants it FAST; trial 0 catches in-env binary gaps |
| A4 | Mutating the built adapter's `_timeout` in `_cmd_sweep` is the cleanest `--timeout` wiring | Timeout precedence | Low — alternative (thread through run_trial) also works, broader change |
| A5 | Stub executables run reliably under WSL2/Linux dev env with shebang + chmod | Tests | Low — Linux target per env; would matter only on Windows-native runners |
| A6 | `<= 0` timeout should mean "no timeout" | Timeout precedence | Medium — semantics choice; planner/user may prefer 0 = reject. Surface in plan. |

## Open Questions (RESOLVED)

1. **`--timeout 0` / `timeout_seconds: 0` semantics**
   - What we know: D-04 says unset = no timeout (today's behavior, explicit).
   - What was unclear: whether `0` means "no timeout" or "reject immediately."
   - RESOLVED: treat `<= 0`/unset as "no timeout"; document in the CLI
     reference. (Assumption A6.) Adopted in Plan 01 Task 1 (`<= 0` semantics)
     and Plan 02 Task 3 (`--timeout 0` honored via `is not None`).
2. **`conda run -p /prefix` (prefix) entries**
   - What we know: F2S3 uses `-n NAME`; prefix form is possible for other tools.
   - What was unclear: whether to support `-p`/`--prefix` in the preflight now.
   - RESOLVED: recognize `-p`/`--prefix` and check the path exists; cheap
     and avoids a surprise gap. Scoped in — adopted in Plan 01 Task 3 preflight.
3. **Where the subprocess-contract doc lands**
   - `docs/integrating/cli-tool.md` exists and already documents argv building +
     `outputs.from`; the timeout/exit-code/glob contract should extend it.
     F2S3 canonical-example + how-to-obtain → `docs/tools/f2s3.md` (exists).
     Schema reference: `docs/reference/yaml-schemas.md` + `tool.schema.json`.
   - RESOLVED: no new doc files required; extend the existing pages. Adopted in
     Plan 04 (Task 1 extends f2s3.md + cli-tool.md; Task 2 extends
     rescoring-and-analysis.md + yaml-schemas.md).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (conda `iof3d_cosicorr3d-dev312`) | all dev/test/lint | ✓ (mandated, `AGENTS.md`) | 3.12 | none — mandatory |
| pytest | CLI-04 tests | ✓ | ~=8.4 (`pyproject.toml:64`) | none |
| `conda` CLI | F2S3 showcase runtime only; preflight resolution | n/a for tests | — | stub tests need no conda (D-12) |
| `f2s3-dev312` env + F2S3 binary | F2S3 end-to-end only | not needed for Phase 3 tests | — | how-to-obtain doc → gseg-ethz repo (D-03) |
| stdlib `subprocess`/`shutil`/`shlex`/`argparse` | all hardening logic | ✓ | stdlib | none |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** F2S3 env/binary — intentionally not
required for the phase's tests (D-12); the preflight + remediation doc *is* the
deliverable that handles its absence.

## Validation Architecture

> `.planning/config.json` not inspected for an explicit `nyquist_validation:
> false`; treating validation as enabled per default. Planner: confirm.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ~=8.4 (`pyproject.toml:64`) |
| Config file | none (`pytest.ini`/`tox.ini`/`setup.cfg` absent; no `[tool.pytest]`) |
| Quick run command | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q` |
| Full suite command | `conda run -n iof3d_cosicorr3d-dev312 pytest` (extras dirs self-skip) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CLI-01 | argparse usage error → exit 2; bad config → clean exit 1 | unit (main-level) | `pytest tests/core/test_cli.py -k "usage or config_error" -x` | ❌ Wave 0 |
| CLI-01 | rescore/analyze exit code off `parser_misses` not `skipped_failed` (F-06) | unit | `pytest tests/core/test_cli.py -k "rescore_exit" -x` | ❌ Wave 0 |
| CLI-01 | `rescore` subcommand rejects rescore-only flags on `run` (D-09) | unit | `pytest tests/core/test_cli.py -k "subcommand" -x` | ❌ Wave 0 |
| CLI-02 | nonzero exit → success=False | unit (real subprocess) | `pytest tests/core/test_cli.py -k "nonzero_exit" -x` | ❌ Wave 0 |
| CLI-02 | timeout → success=False, error="timeout" (F-32) | unit (real sleep stub) | `pytest tests/core/test_cli.py -k "timeout" -x` | ❌ Wave 0 |
| CLI-02 | empty `predictions_glob` → failure (F-07/D-07) | unit | `pytest tests/core/test_cli.py -k "empty_glob" -x` | ❌ Wave 0 |
| CLI-02 | `stdout_json` deprecation stub raises (F-07/D-06) | unit | `pytest tests/core/test_cli.py -k "stdout_json_deprecated" -x` | ❌ Wave 0 |
| CLI-03 | missing env/binary preflight → structured error + exit 1 (F-16) | unit (missing entry) | `pytest tests/core/test_cli.py -k "preflight" -x` | ❌ Wave 0 |
| CLI-04 | (umbrella) all above are the CLI-04 deliverable | — | `pytest tests/core/test_cli.py` | ❌ Wave 0 |
| CLI-05 | F2S3 doc + how-to-obtain note | doc review (manual) | n/a (docs) | docs/tools/f2s3.md exists, extend |

### Sampling Rate
- **Per task commit:** `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q`
- **Per wave merge:** `conda run -n iof3d_cosicorr3d-dev312 pytest` + `ruff` + `pyright`
- **Phase gate:** full core suite green + ruff + pyright before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/core/test_cli.py` — net-new; covers CLI-01…CLI-04 (no fixture
      file exists yet). Needs stub-executable helpers (sleep / exit-N /
      write-or-omit-output) in `tmp_path`.
- [ ] Possibly a shared stub-script fixture in `tests/core/conftest.py` (does
      not exist today) or inline in `test_cli.py`.
- [ ] Framework install: none new — pytest already in `[dev]`.

## Project Constraints (from CLAUDE.md / AGENTS.md)

- **Conda env mandatory:** all `python`/`pip`/`pytest`/`ruff`/`pyright` go
  through `conda run -n iof3d_cosicorr3d-dev312 …`; bare `python`/`pip`/`pytest`
  are forbidden (`AGENTS.md`). F2S3 e2e via `conda run -n f2s3-dev312`.
- **Branching:** GSD work stays on `develop`/phase branches (current branch
  `gsd/phase-03-cli-hardening`); PRs to `main` only at milestone, `.planning/`
  stripped.
- **Review:** internal phase-plan reviews run through the codex CLI.
- **Code style:** `line-length=100`, ruff select `E,F,B,I,UP,W`, double quotes,
  4-space indent; modern typing (`str | None`, `list[str]`); `from __future__
  import annotations`; return types always annotated incl. `-> None`;
  `@dataclass(frozen=True)` norm for value types; `__all__` in every public
  module; keyword-only public constructors via `*`.
- **Error handling:** `{value!r}` for echoed input; `ValueError` for bad values,
  `TypeError` for shape/contract; chain with `from exc`; fail-soft side effects
  wrapped in broad `except` with `# pragma: no cover - <reason>`; never let
  observability/caching/provenance failures break the primary path.
- **Logging:** lazy `%`-style args (never f-strings) in log calls; `info` for
  milestones, `warning` for skips/degradation. Timeout/empty-glob warnings must
  follow this.
- **Pyright:** basic mode, `pythonVersion=3.11`, strict list/dict/set inference;
  runs whole-project. New CLI/adapter code must keep the gate green.
- **No direct edits outside GSD workflow** (CLAUDE.md GSD enforcement).

## Sources

### Primary (HIGH confidence — codebase, read this session)
- `src/geodispbench3d/cli.py` — argparse, 5 handlers, exit codes, dispatch (full read).
- `src/geodispbench3d/tool/cli_adapter.py` — `run_trial`, subprocess call,
  `_collect_outputs`, `prepare()` hook site (full read).
- `src/geodispbench3d/tool/base.py` — `ToolAdapter` ABC, `prepare`/`teardown`,
  `TrialResult` shape (full read).
- `src/geodispbench3d/tool/loader.py` — `ToolConfig`, `_build_cli_adapter`,
  OmegaConf dict parsing, `from` default (full read).
- `src/geodispbench3d/suite/loader.py` — eager raises, suite-level
  `ExecutionConfig` (full read).
- `src/geodispbench3d/sweep/runner.py` — `prepare()`/`teardown()` invocation,
  Ax failed-trial mapping, `PassDiagnostics` threading (full read).
- `src/geodispbench3d/sweep/rescore.py` — `RescoreSummary` fields
  (`parser_misses`, `skipped_failed`) (read :1-109).
- `src/geodispbench3d/diagnostics.py` — `PassDiagnostics.add` (full read).
- `src/geodispbench3d_f2s3/conf/tool/f2s3.yaml` — entry, ignored `execution`
  block, `from: glob` (full read).
- `src/geodispbench3d/conf/schema/tool.schema.json` — confirmed NOT enforced.
- `tests/conftest.py`, `tests/f2s3/conftest.py`, `tests/iof3d/conftest.py`,
  `tests/core/test_cli_adapter.py` — env-split + existing coverage.
- `.planning/phases/01-code-health-audit/REPORT.md` — F-06/F-07/F-16/F-32
  detail + AUDIT-03 CLI-surface synthesis.
- `AGENTS.md` — conda-env mandate. `CLAUDE.md` — conventions.
- `docs/tools/f2s3.md`, `docs/integrating/cli-tool.md` — doc landing sites.

### Secondary (MEDIUM)
- grep sweeps: `stdout_json` usages, `jsonschema` (absent), `execution`/`timeout`
  references — confirm schema not enforced and stdout_json default.

### Tertiary (LOW / ASSUMED)
- stdlib `shutil.which` / `subprocess.TimeoutExpired` / `conda env list --json`
  behavior — training knowledge, not exercised in this session (A1-A3).

## Metadata

**Confidence breakdown:**
- Standard stack (stdlib-only): HIGH — no external deps; all touch points read.
- Architecture / integration seams: HIGH — every seam confirmed at file:line.
- Unknowns #1-#4: #2/#3/#4 HIGH (codebase-confirmed); #1 mechanism HIGH, depth
  is a reasoned recommendation (MEDIUM).
- Pitfalls: HIGH — derived from confirmed defaults (stdout_json default,
  truthiness override, dual `execution` blocks).

**Research date:** 2026-06-27
**Valid until:** ~2026-07-27 (stable codebase; revisit if `tool/loader.py`,
`cli_adapter.py`, or the test layout changes before planning).
