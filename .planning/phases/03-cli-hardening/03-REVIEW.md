---
phase: 03-cli-hardening
reviewed: 2026-06-27T00:00:00Z
depth: deep
files_reviewed: 15
files_reviewed_list:
  - src/geodispbench3d/tool/cli_adapter.py
  - src/geodispbench3d/tool/base.py
  - src/geodispbench3d/tool/loader.py
  - src/geodispbench3d/sweep/runner.py
  - src/geodispbench3d/sweep/rescore.py
  - src/geodispbench3d/sweep/evaluation.py
  - src/geodispbench3d/sweep/trial_record.py
  - src/geodispbench3d/analysis/runner.py
  - src/geodispbench3d/analysis/__init__.py
  - src/geodispbench3d/cli.py
  - src/geodispbench3d/conf/schema/tool.schema.json
  - src/geodispbench3d_f2s3/conf/tool/f2s3.yaml
  - tests/core/test_cli.py
  - tests/core/test_cli_adapter.py
  - tests/core/test_runner_failure.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-27T00:00:00Z
**Depth:** deep
**Files Reviewed:** 15
**Status:** issues_found

## Summary

This phase hardened the CLI surfaces: the subprocess contract in `CliToolAdapter`
(process-group `start_new_session=True` + `os.killpg(SIGKILL)` tree-kill on
timeout, explicit `error_kind` discriminators), the env/binary preflight
(`ToolPreflightError` with remediation/help_url, hermetic conda enumeration), the
central failure-propagation contract (`success=False` → `log_trial_failure` on
both runner entry points via the shared `_raise_if_failed` guard), the typed
timeout/crash/eval failure counters, the `RESOLVED-A` all-failed/no-best-trial
guard, and the `cli.py` 0/1/2 exit taxonomy with a first-class `rescore`
subcommand.

The core hardening targets are **sound and well-tested**. I traced the
failure-propagation contract end to end: a `TrialResult(success=False)` raises
`TrialExecutionError` before any scoring/side-effect on both the suite path
(`_evaluate_across_cases`) and the legacy `_default_executor`, is routed to
`log_trial_failure` (never `complete_trial`), and is correctly split into
`timeouts` (non-exit-driving, D-05) vs `trial_failures` (exit-driving). The
`_resolve_best_trial` guard correctly swallows Ax's no-best-trial throw so an
all-failed sweep returns a valid summary with `best_trial is None`. The exit
taxonomy (`trial_failures or eval_failures or successful_trials == 0`) is
internally consistent with the documented decisions and matches the tests. The
process-group tree-kill is correctly PID-reuse-safe (the unreaped child remains
the group leader, so `os.getpgid` cannot resolve a stale/recycled pid).

No BLOCKER-class defects were found. Three WARNING-level issues remain: an
unintended filesystem-mutation side effect during the rescore directory walk, an
environment-replacement / misplaced-config defect in the CLI adapter env path,
and a residual indefinite-hang window on the post-timeout reap. Details below.

## Structural Findings (fallow)

No structural pre-pass payload was provided with this review.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `rescore` directory walk mutates the filesystem, creating spurious empty `ax_trial/` dirs

**File:** `src/geodispbench3d/sweep/rescore.py:223` (via `src/geodispbench3d/sweep/trial_record.py:94-97`)

**Issue:** `_walk_run_dirs` filters candidate run dirs with
`trial_record_path(p).is_file()`:

```python
return sorted(p for p in root_path.iterdir() if p.is_dir() and trial_record_path(p).is_file())
```

But `trial_record_path` is not a pure path constructor — it unconditionally
creates the directory as a side effect:

```python
def trial_record_path(run_dir: Path) -> Path:
    out_dir = Path(run_dir) / "ax_trial"
    out_dir.mkdir(parents=True, exist_ok=True)   # side effect on every call
    return out_dir / "summary.json"
```

The generator calls `trial_record_path(p)` for **every** immediate child
directory of `results.run_dir_root`, including directories that are not run dirs.
Each such call creates an empty `ax_trial/` subdirectory before the
`summary.json` `.is_file()` check fails and excludes the entry. A documented
read-only "walk every run directory" pass therefore litters the results tree
with empty `ax_trial/` directories under unrelated siblings. This is surprising,
hard to attribute, and pollutes the provenance layout the dashboard/rescore rely
on. (The same mkdir-on-read also fires from `read_provenance` /
`load_trial_record`, but those target real run dirs; the walk is where it leaks
to arbitrary directories.)

**Fix:** Use a non-mutating membership check in the walk, and/or make
`trial_record_path` pure for read paths:

```python
def _trial_summary_file(run_dir: Path) -> Path:
    return Path(run_dir) / "ax_trial" / "summary.json"  # no mkdir

# in _walk_run_dirs:
return sorted(
    p for p in root_path.iterdir()
    if p.is_dir() and _trial_summary_file(p).is_file()
)
```

Keep the `mkdir` only in the write helpers (`update_trial_record`,
`write_trial_record`, `write_trial_summary`) that genuinely need the dir to
exist.

### WR-02: CLI adapter subprocess `env` replaces the whole environment and is read from the wrong YAML block

**File:** `src/geodispbench3d/tool/loader.py:173`, `src/geodispbench3d/tool/cli_adapter.py:104,233`

**Issue:** Two compounding defects on the same path.

1. **Wrong source block.** The loader sources the subprocess environment from the
   `outputs` block:
   ```python
   env=outputs_raw.get("env"),
   ```
   `env` is an execution concern, not an output-collection concern; it is also
   absent from `tool.schema.json`'s `outputs` properties (and from `execution`).
   A user following the schema has no documented place to set it, and anyone who
   guesses `execution.env` is silently ignored.

2. **Full environment replacement.** When `env` is set, the adapter passes it
   straight to `Popen` with no merge against `os.environ`:
   ```python
   self._env = dict(env) if env else None
   ...
   proc = subprocess.Popen(argv, ..., env=self._env, start_new_session=True)
   ```
   `subprocess.Popen(env=...)` *replaces* the child environment entirely. A
   partial dict such as `{ "OMP_NUM_THREADS": "4" }` therefore strips `PATH`,
   `HOME`, `CONDA_*`, `LD_LIBRARY_PATH`, etc., which will break `conda run`
   resolution and most native tools. The failure is loud (tool not found / libs
   missing) rather than silent, and no shipped config sets `env`, so impact is
   latent — but the feature is currently unusable as written.

**Fix:** Read `env` from a documented `execution.env` block (and add it to the
schema), and merge rather than replace:

```python
# loader.py
execution_raw = raw.get("execution") or {}
env_overrides = execution_raw.get("env")
...
# cli_adapter.py
self._env = {**os.environ, **env} if env else None
```

### WR-03: Post-timeout reap can still hang indefinitely if a descendant escapes the process group

**File:** `src/geodispbench3d/tool/cli_adapter.py:247-265`

**Issue:** On timeout the adapter kills the process group, then performs a
*second* `communicate()` with **no timeout** to reap and drain pipes:

```python
except subprocess.TimeoutExpired:
    self._terminate_process_tree(proc)   # os.killpg(pgid, SIGKILL)
    stdout, stderr = proc.communicate()  # no timeout
```

The SIGKILL reliably reaps descendants that stay in the child's process group
(the `conda run` topology the tests cover). But the stated goal also includes not
"orphan[ing] a GPU job." A descendant that daemonizes (`setsid`/double-fork) or a
spawned job that re-parents escapes the group, survives the `killpg`, and keeps
the inherited stdout/stderr pipe fds open. The unbounded second `communicate()`
then blocks until those fds close — potentially forever — re-introducing exactly
the hang the timeout was meant to prevent. This is the same class of risk the
phase brief flagged for scrutiny (process-group signal handling / races).

**Fix:** Bound the reap and degrade gracefully if it does not complete:

```python
self._terminate_process_tree(proc)
try:
    stdout, stderr = proc.communicate(timeout=self._REAP_GRACE_SECONDS)
except subprocess.TimeoutExpired:
    # An escaped descendant still holds the pipes; stop waiting on it.
    self._logger.warning("timed-out trial left an escaped descendant holding stdout/stderr")
    stdout, stderr = "", ""
```

(`proc.communicate()` after the second timeout will still leave the leader reaped
via the earlier SIGKILL; the point is to not block the sweep on a re-parented
grandchild.)

## Info

### IN-01: `tool.schema.json` has drifted from the fields the loader and shipped configs actually use

**File:** `src/geodispbench3d/conf/schema/tool.schema.json:30-69`

**Issue:** The schema omits several fields that `_build_cli_adapter` reads and
that `f2s3.yaml` actually sets, so it does not document the real contract:
`invocation.presence_flag_params` and `invocation.static_params` (used by
`f2s3.yaml:36-43`), `outputs.hashed_run_dir` (used by `f2s3.yaml:63-66`),
`outputs.env` (read at `loader.py:173`), and the `output_parser` block. The
configs validate only because `additionalProperties` is left at its permissive
default — meaning the schema provides no real guardrail for these keys, and a
typo in any of them passes silently.

**Fix:** Add the missing properties (and resolve `outputs.env` per WR-02), and
consider `"additionalProperties": false` on the nested objects so misspelled keys
are caught at load.

### IN-02: Unreachable fallthrough in `main()`

**File:** `src/geodispbench3d/cli.py:208-209`

**Issue:** `sub.add_subparsers(dest="command", required=True)` guarantees one of
the five handled commands is always set (argparse exits 2 otherwise), so the
trailing `parser.print_help(); return 2` after the dispatch `if` chain is
unreachable. Harmless defensive code, but it is dead and slightly obscures the
real exit paths.

**Fix:** Either drop it, or convert the chain to an explicit
`else: parser.print_help(); return 2` so the intent (defensive default) is
clear and lint tools do not flag an implicit `None` return path.

### IN-03: A rescore parser-miss is counted as both `succeeded` and `parser_misses`

**File:** `src/geodispbench3d/sweep/rescore.py:319-321,378-379`

**Issue:** When the parser runs and produces nothing usable
(`evaluation.prediction is None and parser_fn is not None and prediction is None`),
`_rescore_one` sets `outcome.parser_failed = True` but does **not** return early —
it falls through to `outcome.scored = True`. The caller then increments **both**
`summary.parser_misses` and `summary.succeeded` for the same run dir. The exit
code is still correct (the parser miss drives exit 1), but the one-line report
double-counts the run as simultaneously "scored" and "parser_failed", which is
misleading in the operator-facing summary line.

**Fix:** Treat a parser miss as not-scored for reporting purposes, e.g. leave
`outcome.scored = False` (or gate the `scored` assignment on
`not outcome.parser_failed`) so `succeeded` and `parser_misses` stay disjoint.

---

_Reviewed: 2026-06-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
