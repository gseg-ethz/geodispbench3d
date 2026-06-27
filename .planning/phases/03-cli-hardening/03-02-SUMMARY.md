---
phase: 03-cli-hardening
plan: 02
subsystem: cli
tags: [cli, argparse, subcommand, exit-codes, clean-errors, timeout, traceback]
requires:
  - ToolPreflightError (03-01)
  - CliToolAdapter.set_timeout_override (03-01)
  - SweepRunSummary.timeouts/trial_failures/eval_failures/successful_trials (03-01)
  - RescoreSummary.parser_misses/eval_failures (03-01)
  - AnalysisSummary.skipped_unreadable/eval_failures (03-01)
provides:
  - "rescore: first-class argparse subcommand (suite + 4 rescore-only flags + --log-level)"
  - "run: --timeout (float) flag; LOST the four rescore-only flags + the --rescore store_true"
  - "--traceback: shared parent-parser flag, single canonical placement <subcommand> ... --traceback"
  - "_load_or_clean_exit: narrow config-load clean-error helper (loader-only protected region)"
  - "_CleanExit: internal sentinel translated to exit 1 at main()"
  - "exit-code taxonomy 0/1/2 across all five handlers, INCLUDING sweep exit-1"
affects:
  - Plan 03 (authors the main()-level behavioral tests for these exit/usage/clean-error paths)
  - Plan 04 (documents the final flag layout, the exit-code table, and the --traceback form)
tech-stack:
  added: []
  patterns:
    - "argparse shared parent parser (add_help=False) for a cross-subcommand flag"
    - "narrow exception boundary: catch loader errors AT the load call, not around dispatch"
    - "distinct exception type (ToolPreflightError) safe to catch at the dispatch boundary"
    - "is-not-None precedence (not truthiness) so a 0 override is honored"
key-files:
  created: []
  modified:
    - src/geodispbench3d/cli.py
    - tests/core/test_rescore.py
    - tests/core/test_analyze.py
    - tests/core/test_runner.py
decisions:
  - "Conda env runs pytest/ruff as `python -m` (base shadows the env bin under `conda run`); pyright gated via the phase-02 baseline-diff gate, consistent with 03-01."
  - "Repo-wide `--rescore` token scrub stays Plan 04's scope; this plan scrubs only cli.py (Task 1 contract). Other src/ docstrings still carry the token by design."
metrics:
  duration: 8min
  completed: 2026-06-27
  tasks: 3
  files: 4
status: complete
---

# Phase 3 Plan 02: CLI Hardening — rescore subcommand, clean errors, exit taxonomy Summary

One-liner: restructured `cli.py` so `rescore` is its own subcommand (argparse
structurally rejects the four rescore-only flags on `run`), bad config / tool
preflight produce a one-line `error: <msg>` + exit 1 through a NARROW
loader-only wrapper (runtime ValueErrors keep their traceback), and every
command — sweep included — now derives a 0/1/2 exit code from Plan 01's typed
failure counters instead of an unconditional `return 0`.

## What Was Built

### Task 1 — rescore subcommand split + --timeout + canonical --traceback (53a0aa9)
- New `rescore` subparser mirroring `analyze`: positional `suite`, `--log-level`,
  `--reuse-parser-options`, `--use-prediction-cache`, `--pass-id`, `--max-trials`.
- `--max-trials` on `rescore` is **WARN-AND-IGNORE** (locked D-09): a single
  `logger.warning("--max-trials has no effect in rescore mode")`; no run-dir cap
  implemented (out of phase scope).
- `run` LOST the `--rescore` store_true and the four rescore-only flags; it GAINED
  `--timeout` (`type=float, default=None`). argparse now rejects `run --rescore`
  with `error: unrecognized arguments: --rescore` (exit 2), verified by smoke test.
- `--traceback` is a shared parent parser (`add_help=False`) attached via
  `parents=[...]` to `run` / `rescore` / `analyze` / `list-metrics`. The SINGLE
  canonical form is `geodispbench3d <subcommand> ... --traceback`; no second bare
  pre-subcommand flag (review LOW: avoid dual-placement ambiguity).
- Factored the shared prelude `_prepare_suite_run(args)` (logging.basicConfig +
  load_suite + optional ResultsStore sink) reused by `run` (sweep) and `rescore`;
  removed the dead `if args.rescore:` branch — `run` is sweep-only.
- `_cmd_rescore` is now the dispatch entry `(args)`; `main()` routes
  `args.command == "rescore"` to it.
- **STALE `--rescore` SCRUB:** cli.py contains NO `--rescore` flag token — module
  docstring, `_cmd_rescore` docstring, and the warn string were all rephrased to
  the `rescore` subcommand / "rescore mode". (Repo-wide src/ scrub is Plan 04's.)

### Task 2 — narrow clean-error wrapper + dashboard/list-metrics cleanups (c571faa)
- `_CleanExit(Exception)` internal sentinel + `_load_or_clean_exit(loader, *args,
  traceback)` generic helper. The protected region is EXACTLY the loader call:
  only a `FileNotFoundError`/`ValueError` raised BY the loader is flattened to
  `error: <msg>` (stderr) + exit 1 (review MEDIUM). With `--traceback`, the
  ORIGINAL exception is re-raised for the full stack.
- `main()` dispatch wrapped in a NARROW boundary: `except _CleanExit: return 1`
  and `except ToolPreflightError` (a DISTINCT type, safe to catch at the boundary
  even though `adapter.prepare()` runs deep inside `run_with_suite`) →
  `error: <msg>` + exit 1, re-raised under `--traceback`. An UNEXPECTED runtime
  `ValueError` from Ax / a metric / persistence is NOT caught and keeps its full
  traceback. argparse's `SystemExit` (usage, exit 2) is never swallowed.
- `load_suite` / `load_analysis` / `load_metrics_config` all routed through
  `_load_or_clean_exit`, so a malformed `metrics.yaml` under `list-metrics` now
  exits 1 with a clean message instead of a bare traceback / a stray 0.
- `_cmd_dashboard`: streamlit-missing `return 2` → `return 1` (missing runtime
  dependency is a runtime failure, not a usage error).

### Task 3 — exit-code taxonomy + --timeout precedence (7fab804)
- `_cmd_sweep`: the unconditional `return 0` is GONE. Now
  `return 1 if (result.trial_failures or result.eval_failures or
  result.successful_trials == 0) else 0`. Individual `timeouts` are EXCLUDED
  (locked D-05) but a ZERO-success sweep exits 1 even if every failure was a
  timeout (RESOLVED-A). Added a DEDICATED `"%d trials timed out"` line plus a
  `"%d trial failures, %d evaluation failures"` line, both distinct from the
  aggregate `"N non-fatal failures"` degradation line (review Warning 1).
- `_cmd_rescore`: `return 1 if (summary.parser_misses or summary.eval_failures)
  else 0` — pre-existing `skipped_failed`/`skipped_no_summary` do NOT fail it.
- `_cmd_analyze`: `return 1 if (summary.skipped_unreadable or
  summary.eval_failures) else 0` — benign `skipped_no_case` does NOT fail it.
- `_cmd_sweep` `--timeout` precedence: `if args.timeout is not None and
  isinstance(suite.tool.adapter, CliToolAdapter):
  suite.tool.adapter.set_timeout_override(args.timeout)`. Uses `is not None` (not
  truthiness) so `--timeout 0` is honored (= no timeout per the adapter's `<= 0`
  semantics); writes through the public seam, never `_timeout`.

## Authoritative Surface (for Plan 03 tests + Plan 04 docs)

### Final flag layout
- `run <suite>`: `--log-level`, `--max-trials` (int), `--timeout` (float), `--traceback`.
- `rescore <suite>`: `--log-level`, `--reuse-parser-options`, `--use-prediction-cache`,
  `--pass-id`, `--max-trials` (int, warn-and-ignored), `--traceback`.
- `analyze <analysis>`: `--log-level`, `--pass-id`, `--traceback`.
- `dashboard`: `--parquet` (no `--traceback`).
- `list-metrics <metrics>`: `--traceback`.

### --traceback accepted form
Exactly one: `geodispbench3d <subcommand> ... --traceback` (subcommand-level,
via the shared parent parser). No bare top-level form.

### Exit-code expressions (exact)
- sweep: `1 if (trial_failures or eval_failures or successful_trials == 0) else 0`
- rescore: `1 if (parser_misses or eval_failures) else 0`
- analyze: `1 if (skipped_unreadable or eval_failures) else 0`
- list-metrics: `0` on success; `1` via `_CleanExit` on a bad metrics.yaml.
- dashboard: `1` when streamlit missing; else streamlit's own return.
- Any config-load (`FileNotFoundError`/`ValueError` from a loader) or
  `ToolPreflightError`: clean `error: <msg>` + `1` (full traceback under `--traceback`).
- argparse usage error (incl. `run --rescore`, unknown flag): `2`.

## Deviations from Plan

### Test adaptations (Rule 3 — refactor broke pre-existing internal-API callers)
The plan declared `files_modified: [cli.py]` only, but three pre-existing
`tests/core` tests called the changed internal handlers and had to be adapted to
keep `tests/core` green (the Task verify gate). These are mechanical signature /
namespace updates, no production behavior re-shaped by the tests:

1. **`tests/core/test_rescore.py`** — `test_cli_rescore_emits_non_fatal_failures_line`
   called the OLD `_cmd_rescore(args, suite, on_record_rows, logger)`. Updated to
   the new `_cmd_rescore(args)` entry: pass argv-shaped `args` (`suite` path,
   `log_level`, `traceback=False`, rescore flags) so it runs the shared prelude.
   Commit 53a0aa9.

2. **`tests/core/test_analyze.py`** — `test_cli_analyze_emits_non_fatal_failures_line`
   built a Namespace without `traceback`; `_cmd_analyze` now reads `args.traceback`
   for the clean-error helper. Added `traceback=False`. Commit c571faa.

3. **`tests/core/test_runner.py`** — `test_cli_sweep_emits_non_fatal_failures_line`
   built a Namespace without `timeout` AND asserted `rc == 0` against a fake
   summary with `successful_trials == 0`. Under the NEW RESOLVED-A taxonomy a
   zero-success sweep exits 1, so the fake was changed to a genuine success
   (`successful_trials=1`, `best_trial=object()`) — faithfully representing the
   "exits 0 WITH non-fatal degradation" path the test asserts — and `timeout=None`
   was added. Commit 7fab804.

No Rule 1/2/4 deviations. No architectural changes.

### Verification-command adaptation (not a code deviation)
Per 03-01: under `conda run -n iof3d_cosicorr3d-dev312`, bare `pytest`/`ruff`
resolve to the base env, so verification ran as `python -m pytest` / `python -m
ruff`. `pyright` gated via `.planning/phases/02-targeted-fixes/pyright_gate.py`
(baseline-diff): PASS, no new errors above baseline.

## Verification Evidence
- `python -m pytest tests/core -q` → 79 passed (after each task).
- `python -m pytest` (full, incl. iof3d/f2s3) → 83 passed.
- `python -m ruff check src` → All checks passed.
- pyright baseline gate → PASS: no new errors above baseline.
- Smoke (`main()` argv): `run --rescore` → exit 2 (`unrecognized arguments`);
  `run /nope.yaml` → `error: Suite YAML not found: ...` + exit 1; same with
  `--traceback` → full `FileNotFoundError` stack; `list-metrics /nope.yaml` →
  clean `error:` + exit 1; `rescore -h` / `run -h` show the expected disjoint
  flag sets.

## Known Stubs
None. All flags wire to real handlers; all exit expressions read live counters.

## Threat Flags
None beyond the plan's threat register. The exit-code taxonomy (T-03-07/T-03-08)
and the no-traceback clean-error path (T-03-06) are the mitigations this plan
delivers; no new network/auth/file-access surface introduced.

## Notes for Plan 03 / 04
- Plan 03: assert at `main()` level — `run --rescore` → 2; missing/bad config → 1
  with a clean `error:` line (and `--traceback` → traceback); a sweep with
  `trial_failures`/`eval_failures`/`successful_trials==0` → 1 while a
  some-success timeouts-only sweep → 0; rescore over only `skipped_failed` → 0;
  analyze over only `skipped_no_case` → 0; `--timeout 0` reaches
  `set_timeout_override(0.0)`.
- Plan 04: copy the "Authoritative Surface" block verbatim into the CLI docs; the
  repo-wide `--rescore` token scrub across the remaining src/ docstrings is Plan
  04's gate (cli.py is already clean).

## Self-Check: PASSED
- src/geodispbench3d/cli.py present on disk.
- All three task commits present in git history (53a0aa9, c571faa, 7fab804).
