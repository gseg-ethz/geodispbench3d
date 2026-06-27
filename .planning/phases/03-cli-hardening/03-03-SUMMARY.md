---
phase: 03-cli-hardening
plan: 03
subsystem: tests
tags: [cli-tests, subprocess, timeout, preflight, failure-propagation, exit-codes, hermetic]
requires:
  - TrialResult.error_kind (03-01)
  - CliToolAdapter.prepare / set_timeout_override / process-group timeout / empty-glob (03-01)
  - ToolPreflightError + _conda_env_names seam (03-01)
  - runner failure-propagation contract (_raise_if_failed / _resolve_best_trial) (03-01)
  - SweepRunSummary.timeouts/trial_failures/eval_failures/successful_trials (03-01)
  - loader stdout_json->glob rejection (03-01)
  - rescore subcommand + 0/1/2 exit taxonomy + narrow clean-error wrapper + --timeout/--traceback (03-02)
provides:
  - "tests/core/test_runner_failure.py — fake-Ax failure-propagation coverage (HIGH #3, RESOLVED-A/B)"
  - "tests/core/test_cli.py — adapter subprocess contract + hermetic preflight + loader validation + main() exit taxonomy"
  - "tests/core/test_cli_adapter.py — real-subprocess glob-collection smoke"
  - "CLI-04 satisfied (the phase's behavioral gate)"
affects:
  - Plan 04 (docs reference the proven contracts; phase verification consumes these tests)
tech-stack:
  added: []
  patterns:
    - "real tiny bash stub executables in tmp_path (shebang + chmod) for faithful subprocess/timeout/glob mechanics (D-12)"
    - "FakeAxClient recording double records complete_trial vs log_trial_failure per trial index"
    - "bounded wait_until_process_dead(pid, deadline) poll instead of an immediate os.kill (async reaping)"
    - "monkeypatched _conda_env_names / shutil.which / subprocess.run for hermetic preflight (no real conda)"
    - "TRUE end-to-end main()-level sweep: real AxSweepRunner + real CliToolAdapter + real stub entry"
    - "range hyperparameter in the e2e suite to keep Ax's Sobol search space non-degenerate"
key-files:
  created:
    - tests/core/test_runner_failure.py
    - tests/core/test_cli.py
  modified:
    - tests/core/test_cli_adapter.py
decisions:
  - "The e2e main()-level sweep tests drive REAL Ax (not FakeAxClient) to satisfy the review's TRUE-end-to-end requirement; kept fast via Sobol-only (sobol_trials==max_trials) and 2-trial sweeps."
  - "A single range float `alpha` hyperparameter is added to the e2e suite so Ax's search space is non-degenerate (an empty space exhausts Sobol after one draw -> SearchSpaceExhausted)."
  - "g2/g3 timeout sweeps use a marker-file / always-sleep stub with `--timeout 1` for deterministic timeout-vs-success outcomes under the real adapter."
  - "Conda env runs pytest/ruff as `python -m` (base shadows the env bin under `conda run`); pyright gated via the phase-02 baseline-diff gate, consistent with 03-01/03-02."
metrics:
  duration: 35min
  completed: 2026-06-27
  tasks: 3
  files: 3
status: complete
---

# Phase 3 Plan 03: CLI-04 Behavioral Tests Summary

One-liner: authored the phase's behavioral gate — a hermetic fake-Ax test
proving a `success=False` trial reaches Ax as a *failed* trial
(`log_trial_failure`, never scored) on both runner paths, plus real-stub
adapter/subprocess/timeout/preflight/loader coverage and TRUE end-to-end
`main()`-level sweep exit-code tests (crash→1, clean→0, some-success+timeout→0,
all-failed→1) — closing both HIGH gaps the Codex review flagged.

## What Was Built

### Task 1 — Runner/Ax failure-propagation tests (8a6f60c)
`tests/core/test_runner_failure.py` (net-new). A duck-typed `FakeAxClient`
(installed by monkeypatching `runner.AxClient` BEFORE construction) records which
completion method each trial index invoked; a configurable `StubFailAdapter`
returns canned `TrialResult` values with explicit `error_kind`.

- **HIGH #3 (the core defect):** parametrized over `timeout` and `nonzero_exit`,
  a `success=False` first trial → `log_trial_failure` (index in `failed`, NOT in
  `completed`); the sweep CONTINUES (the later success is completed); a spy on
  `runner.evaluate_trial` proves it was never invoked for the failed case; and
  the typed counter split holds (`timeout` → `timeouts==1`, `trial_failures==0`;
  `nonzero_exit` → `trial_failures==1`, `timeouts==0`).
- **RESOLVED-A:** a DISTINCT all-trials-failed sweep (and a
  timeouts-only-zero-success variant) with `FakeAxClient.get_best_trial` raising
  (mimicking real Ax) returns a valid `SweepRunSummary` — `best_trial is None`,
  `successful_trials == 0`, no unhandled `get_best_trial` escape, all trials in
  `log_trial_failure`.
- **RESOLVED-B:** the legacy `run()`/`_default_executor` path with a
  `success=False` stub records `log_trial_failure` (not `complete_trial`) and
  returns `None` cleanly when all trials failed.

### Task 2 — Adapter contract + hermetic preflight + loader (0900989, cf9ae12)
Real `chmod +x` bash stubs in `tmp_path` drive `CliToolAdapter.run_trial`:

- **nonzero_exit** → `success=False`, `error_kind="nonzero_exit"`, exit code in
  `error`; **timeout** (sleep stub vs short ceiling) → `error="timeout"`,
  `error_kind="timeout"`.
- **descendant cleanup:** a wrapper stub spawns a backgrounded `sleep 30`, writes
  its child PID, and `wait`s; after the timeout, the child PID is asserted dead
  via the bounded `wait_until_process_dead(pid, deadline)` poll (NOT an immediate
  `os.kill`).
- **termination race:** `os.killpg` monkeypatched to raise `ProcessLookupError`
  → `run_trial` still returns a clean timeout failure, no exception escapes.
- **empty/populated glob:** an empty `predictions_glob` → `missing_output`; a
  populated glob → `success` with `figures_glob` emptiness staying non-fatal.
- **hermetic preflight:** a missing binary → `ToolPreflightError` ("not found on
  PATH" + remediation); a `conda run -n no-such-env` entry with `_conda_env_names`
  monkeypatched → `ToolPreflightError`; and the three enumerator failure modes
  (nonzero exit / malformed JSON / `TimeoutExpired`, via a stubbed
  `subprocess.run`) each → `ToolPreflightError`. No real conda env required.
- **loader:** explicit `outputs.from: stdout_json` → `ValueError` (names glob);
  unset → adapter `_outputs_from == "glob"`; `fixed_path` → `ValueError` (names
  the value).
- `tests/core/test_cli_adapter.py` extended with a real-subprocess smoke test
  confirming the success path collects glob predictions.

### Task 3 — main()-level exit-code, usage, sweep crash/timeout/all-failed (cf9ae12)
`main([...])`-level coverage in `tests/core/test_cli.py`:

- usage error (unknown flag) → `SystemExit` code 2; missing suite → 1 with a
  clean one-line `error:` (no traceback); `--traceback` re-raises the loader
  exception; a rescore-only flag rejected on `run` (exit 2) and accepted on
  `rescore`.
- rescore over a pre-existing `skipped_failed` (healthy run scores) → 0; a genuine
  parser miss (suite parser returns None) → 1; `rescore --max-trials N` warns and
  still completes; analyze `skipped_no_case` → 0, `skipped_unreadable` (corrupt
  prediction) → 1.
- **SWEEP exit taxonomy — TRUE end-to-end** (real `AxSweepRunner` + real
  `CliToolAdapter` + real stub `entry`): crash (nonzero exit) → 1; clean (stub
  writes a valid prediction collected by glob) → 0; some-success-plus-timeout
  (marker-file stub + `--timeout 1`) → 0 (an individual timeout is non-fatal,
  D-05); all-failed and timeouts-only-zero-success → 1 (RESOLVED-A;
  `main()` does not crash on the no-best-trial path).
- preflight-to-exit-1 via `main()` (enumerator monkeypatched) → 1 with the
  remediation in stderr; `--timeout` override asserted via the public seam (`5`
  wins over the YAML sentinel, `--timeout 0` → no-timeout); and the
  NARROW_WRAPPER_BOUNDARY case — an unexpected runtime `ValueError` raised AFTER
  loaders/preflight succeed propagates with its traceback (not flattened to
  exit 1) without `--traceback`.

## Verification Evidence
- `python -m pytest tests/core -q` → 113 passed (was 79; +34 new across the
  three files).
- `python -m pytest` (full, incl. iof3d/f2s3 plugin suites) → 117 passed.
- `python -m ruff check tests/core` → All checks passed (after `ruff --fix` +
  `ruff format` on import ordering).
- pyright baseline-diff gate → PASS: no new errors above baseline.

## Deviations from Plan

### Rule 3 (blocking) — non-degenerate Ax search space for the e2e sweeps
The plan's e2e suites described a tool.yaml with `entry` + outputs but no
hyperparameters. The first TRUE end-to-end crash sweep raised
`ax.exceptions.core.SearchSpaceExhausted` — with an empty parameter space Ax's
Sobol exhausts after a single draw, so `get_next_trial` (which is OUTSIDE the
runner's per-trial try/except) threw before the second trial. Added a single
range float `alpha` hyperparameter to the e2e suite builder (`type: range`,
`value_type: float`, `lower: 0.0`, `upper: 1.0`); the stubs ignore the rendered
`--alpha` flag. This is a test-fixture correctness fix, not a source change.

### Verification-command adaptation (not a code deviation)
Per 03-01/03-02: under `conda run -n iof3d_cosicorr3d-dev312`, bare
`pytest`/`ruff` resolve to the base env, so verification ran as `python -m
pytest` / `python -m ruff`. `pyright` gated via the established
`.planning/phases/02-targeted-fixes/pyright_gate.py` baseline-diff (PASS).

No Rule 1/2/4 deviations. No source/production code changed — this plan is
tests-only. No architectural changes.

## Known Stubs
None. The "stubs" here are intentional tiny test executables (bash scripts in
`tmp_path`) and a `FakeAxClient` recording double — all test scaffolding, none
shipping. No placeholder data flows into product code.

## Threat Flags
None beyond the plan's threat register (T-03-09 tmp_path stub tampering = accept;
T-03-10 sleep/wrapper-stub DoS = mitigate via short ~0.3–1s ceilings + the
descendant-reaping assertion; T-03-SC no package installs). No new
network/auth/file-access surface introduced.

## Notes for Plan 04
- The proven contracts to document verbatim: failed-trial → `log_trial_failure`
  on both runner paths; the typed counter split (timeouts non-fatal per D-05;
  trial_failures/eval_failures exit-driving; zero-success → exit 1 even for
  timeouts-only per RESOLVED-A); the timeout tree-kill (process-group SIGKILL
  reaps conda-run descendants); the glob-only output contract; the D-02 accepted
  in-env-binary limitation; and the full 0/1/2 exit taxonomy.
- `tests/core/test_cli.py` is the executable reference for the exit-code table
  Plan 04 documents.

## Self-Check: PASSED
- `tests/core/test_runner_failure.py` present on disk.
- `tests/core/test_cli.py` present on disk.
- `tests/core/test_cli_adapter.py` present (modified).
- All three task commits present in git history (8a6f60c, 0900989, cf9ae12).
