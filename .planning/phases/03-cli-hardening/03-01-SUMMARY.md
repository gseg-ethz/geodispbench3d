---
phase: 03-cli-hardening
plan: 01
subsystem: tool-adapter + sweep-runner
tags: [cli-adapter, subprocess, timeout, preflight, failure-propagation, typed-counters]
requires:
  - PassDiagnostics (02-05)
  - SweepRunSummary.non_fatal_failures (02-05)
  - parser_fn_repr single-source (02-07)
provides:
  - TrialResult.error_kind
  - ToolPreflightError
  - TrialExecutionError
  - CliToolAdapter.prepare / set_timeout_override / process-group timeout / empty-glob failure
  - runner failure-propagation contract (_raise_if_failed, _resolve_best_trial)
  - SweepRunSummary.timeouts / trial_failures / eval_failures / successful_trials
  - RescoreSummary.eval_failures + _RescoreOutcome eval/degradation split
  - AnalysisSummary.eval_failures
affects:
  - Plan 02 (exit-code taxonomy consumes the typed counters)
  - Plan 03 (behavioral tests for timeout / preflight / Ax propagation)
  - Plan 04 (documents the contract + the D-02 accepted limitation)
tech-stack:
  added: []
  patterns:
    - "Popen + start_new_session + communicate(timeout) for process-group tree-kill"
    - "explicit error_kind discriminator instead of substring-matching human errors"
    - "shared success guard called from both runner entry points (one seam, both paths)"
    - "typed subset readout via PassDiagnostics.by_kind without changing the aggregate total"
key-files:
  created: []
  modified:
    - src/geodispbench3d/tool/base.py
    - src/geodispbench3d/tool/cli_adapter.py
    - src/geodispbench3d/tool/loader.py
    - src/geodispbench3d/conf/schema/tool.schema.json
    - src/geodispbench3d_f2s3/conf/tool/f2s3.yaml
    - src/geodispbench3d/sweep/runner.py
    - src/geodispbench3d/sweep/rescore.py
    - src/geodispbench3d/analysis/runner.py
decisions:
  - "Conda env runs pytest/ruff as `python -m`, not bare `pytest`/`ruff` (the env's bin is shadowed by base on PATH under `conda run`); pyright is gated by the phase-02 baseline-diff gate, not raw `pyright`."
metrics:
  duration: 15min
  completed: 2026-06-27
  tasks: 3
  files: 8
status: complete
---

# Phase 3 Plan 01: CliToolAdapter Hardening + Failure-Propagation Contract Summary

JWT-style one-liner: hardened the `CliToolAdapter` subprocess contract (opt-in
process-group timeout, glob-only output collection, fail-fast env/binary
preflight) AND landed the central runner-side fix so a `TrialResult(success=False)`
becomes a genuine Ax *failed* trial (`log_trial_failure`, never scored) on both
runner paths, with typed failure counters that split timeouts from crashes.

## What Was Built

### Task 1 — Subprocess timeout (tree-kill) + output-collection contract + error_kind (347fb3e)
- `TrialResult.error_kind: str | None` — explicit, testable failure-kind signal,
  set on every `success=False` branch (`entry_not_found` / `nonzero_exit` /
  `timeout` / `missing_output`).
- `CliToolAdapter` now launches via `subprocess.Popen(..., start_new_session=True)`
  + `proc.communicate(timeout=...)`, preserving the prior `subprocess.run`
  guarantees (`stdout=PIPE`, `stderr=PIPE`, `text=True`, `env=self._env`).
- On `TimeoutExpired`: POSIX `os.killpg(os.getpgid(pid), SIGKILL)` reaps the whole
  process tree (incl. `conda run` descendants); non-POSIX falls back to
  `proc.kill()`; `ProcessLookupError` from the kill is swallowed and the trial
  still records a timeout. Termination never raises out of `run_trial`.
- `set_timeout_override(timeout)` public seam; `None`/`<= 0` means no timeout.
- Default `outputs_from` flipped `"stdout_json"` → `"glob"`. Loader reads the RAW
  `outputs.from`: unset → glob; explicit `stdout_json` → `ValueError` (points at
  glob); any other value → `ValueError` naming it.
- Empty `predictions_glob` (set, zero matches) → `success=False`,
  `error_kind="missing_output"`; empty `figures_glob` stays non-fatal.
- Schema: `execution.timeout_seconds` added; `outputs.from` enum reconciled to
  `["glob", "stdout_json"]` (glob blessed/default, stdout_json deprecated,
  `fixed_path` dropped). `f2s3.yaml` documents the optional `timeout_seconds`
  with a commented-out example, no shipped ceiling (D-04 opt-in).

### Task 2 — Env/binary preflight + ToolPreflightError (82a04e1)
- `ToolPreflightError(Exception)` in `tool/base.py`, keyword-only
  `remediation`/`help_url`, appended to `str()`; in base `__all__`.
- `CliToolAdapter.prepare()`: `shlex.split` the entry, raise on empty; raise when
  `shutil.which(leader)` is None; for a `conda run` entry, parse `-n`/`--name` and
  `-p`/`--prefix` (`--name=`/`--prefix=` forms too), `expanduser`+`exists` a
  prefix, and check env-name membership.
- `_conda_env_names()` — monkeypatchable seam; runs `conda env list --json` with a
  bounded 30s timeout; nonzero exit / malformed-JSON / `TimeoutExpired` all map to
  `ToolPreflightError` (no raw subprocess/JSON exception escapes). `base` resolved
  via the `envs/`-parent heuristic (root prefix → `"base"`).
- Loader threads top-level `remediation`/`help_url`; schema gains both; `f2s3.yaml`
  carries the F2S3 env-setup remediation + the gseg-ethz help_url, keeps the
  `conda run -n f2s3-dev312 f2s3` entry (D-01/D-03).

### Task 3 — Failure-propagation contract + typed counters with timeout split (c0b35f9)
- `TrialExecutionError(error_kind=...)` in `sweep/runner.py` (`__all__`).
- `_raise_if_failed(result)` shared guard raises on `success=False`; called from
  BOTH `_evaluate_across_cases` (suite path, before any scoring/side effects) AND
  `_default_executor` (legacy `run()` path) — RESOLVED-B. A failed result is
  reported to Ax via `log_trial_failure`, never `complete_trial`, and the sweep
  continues.
- `run_with_suite` per-trial handler: `error_kind == "timeout"` → `timeouts`
  (non-exit-driving, D-05); any other kind (and any unexpected exception) →
  `trial_failures`. `successful_trials` increments only on `complete_trial`.
- `_resolve_best_trial()` shared no-throw guard (RESOLVED-A) called from `run()`
  and `run_with_suite()`; returns `None` when Ax has no completed trial.
- `SweepRunSummary` gains `timeouts`, `trial_failures`, `eval_failures`
  (`= pass_diag.by_kind["evaluation"]`), `successful_trials` — additive, after
  `non_fatal_failures`.
- `_RescoreOutcome.non_fatal_failures` split into `eval_failures` +
  `degradation_failures` at the source (4 increment sites updated);
  `RescoreSummary.eval_failures` + `AnalysisSummary.eval_failures` derive from the
  `"evaluation"` diag kind. `non_fatal_failures` stays the aggregate fail-soft
  total (verified against the existing rescore degradation tests).

## Exact New Error Strings / Signals (for Plans 02–04)
- Timeout: `error="timeout"`, `error_kind="timeout"`.
- Empty glob: `error=f"no predictions matched glob {self._predictions_glob!r}"`,
  `error_kind="missing_output"`.
- Nonzero exit: `error=f"exit={returncode}"`, `error_kind="nonzero_exit"`.
- Entry not found: `error=f"Tool entry not found: {exc}"`, `error_kind="entry_not_found"`.
- Loader rejection (explicit): `"outputs.from: stdout_json is no longer supported; use outputs.from: glob with a predictions_glob"`.
- Loader rejection (unsupported): `"unsupported outputs.from value {v!r}; the only supported value is 'glob'"`.
- Preflight: `"tool entry is empty; nothing to invoke"`, `"tool executable {leader!r} not found on PATH"`, `"conda prefix {p!r} does not exist"`, `"conda env {name!r} not found (available: [...])"`, plus the conda-enumeration failure messages — all wrapped in `ToolPreflightError` (remediation/help_url appended).

## Contracts Recorded (authoritative for downstream plans)
- **RESOLVED-A (all-failed sweep):** `_resolve_best_trial()` returns `None` (never
  throws); an all-failed/all-timeout sweep yields a valid `SweepRunSummary` with
  `best_trial is None` AND `successful_trials == 0`. Plan 02 drives exit 1 from
  `successful_trials == 0` (paired with `best_trial is None`) — even a
  timeouts-only sweep that optimized nothing — WITHOUT changing D-05 for the
  partial case (a timeouts-only-but-some-success sweep still exits 0; an
  individual timeout stays non-fatal).
- **RESOLVED-B (both paths):** the `success=False` guard is shared; the legacy
  `run()`/`_default_executor` path (iof3d-ax CLI) also reports a failed result to
  Ax via `log_trial_failure`.
- **Exit-code inputs for Plan 02:** exit 1 ⇐ `trial_failures` + `eval_failures`
  (sweep), `parser_misses` OR `eval_failures` (rescore), `skipped_unreadable` OR
  `eval_failures` (analyze). `timeouts` is excluded from exit. `non_fatal_failures`
  remains the human "N non-fatal failures" line (aggregate; overlaps eval as a
  superset).
- **Timeout-termination guarantee:** process-group `SIGKILL` on POSIX (reaps
  conda-run descendants); direct `proc.kill()` fallback elsewhere;
  `ProcessLookupError` swallowed; trial still recorded as a timeout.

## ACCEPTED LIMITATION (D-02 — settled, not a gap)
The preflight validates the leading executable + that conda/the named env (or
prefix) resolves. It DELIBERATELY does NOT validate the trailing in-env binary
(e.g. `f2s3` inside `conda run -n f2s3-dev312 f2s3`): it neither spawns the env
nor runs `conda run ... which`. A binary missing inside the env is surfaced by
trial 0's existing nonzero-exit / `FileNotFoundError` handling
(`error_kind="entry_not_found"` / `"nonzero_exit"`). The Codex MEDIUM suggesting a
`conda run -n ENV command -v BIN` probe was explicitly REJECTED per locked D-02 to
keep the preflight cheap (it runs before every sweep) and to avoid spawning the
env. Plan 04 should state this guarantee precisely.

## Deviations from Plan

### Verification-command adaptation (not a code deviation)
The plan's verify block uses bare `pytest` / `ruff` / `pyright`. Under
`conda run -n iof3d_cosicorr3d-dev312`, bare `pytest`/`ruff` resolve to the **base**
env on `PATH` (Python 3.13, missing `geodispbench3d`/`pandas`), so verification was
run as `conda run -n ... python -m pytest` / `python -m ruff`. `pyright` is a node
binary with a pre-existing 19-error baseline from Phase 02; it was gated via the
established `.planning/phases/02-targeted-fixes/pyright_gate.py` baseline-diff
(PASS: no new errors), consistent with the locked 02-02 gate decision. No source
behavior changed as a result.

Otherwise: plan executed as written. No Rule 1–4 auto-fixes were required (no bugs,
missing functionality, or blocking issues discovered).

## Verification Evidence
- `python -m pytest tests/core -q` → 79 passed (after each task).
- `python -m pytest` (full, incl. iof3d/f2s3 plugin suites) → 83 passed.
- `python -m ruff check src/geodispbench3d` → All checks passed.
- pyright baseline gate → PASS: no new pyright errors above baseline.
- Inline contract probe (FakeAxClient harness): crash sweep → `trial_failures=3,
  timeouts=0, successful_trials=0, best_trial=None`, all routed to
  `log_trial_failure`, zero `complete_trial`; timeout-only sweep → `timeouts=2,
  trial_failures=0, successful_trials=0, best_trial=None`.

## Known Stubs
None. All new fields/paths are wired to real producers; no placeholder data flows.

## Threat Flags
None. No new network endpoints, auth paths, file-access patterns, or
trust-boundary schema changes beyond the threat register already enumerated in
the plan (`T-03-03` DoS mitigation and `T-03-13` repudiation mitigation are the
ones this plan delivers).

## Notes for Plan 02 / 03 / 04
- Plan 02: key exit logic off the typed counters above; `set_timeout_override` is
  the supported seam for a `--timeout` flag (do not mutate `_timeout`).
- Plan 03: `_conda_env_names` is monkeypatchable for hermetic preflight tests; the
  FakeAxClient harness in `tests/core/test_runner.py` already exercises
  `log_trial_failure` routing — extend it with the failed-adapter + all-failed
  assertions.
- Plan 04: document the timeout-tree-kill guarantee, the glob-only output
  contract, and the D-02 accepted in-env-binary limitation verbatim.

## Self-Check: PASSED
- All 8 modified source files present on disk.
- SUMMARY.md present.
- All three task commits present in git history (347fb3e, 82a04e1, c0b35f9).
