---
phase: 03-cli-hardening
verified: 2026-06-27T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: CLI Hardening Verification Report

**Phase Goal:** All three CLI surfaces handle failures predictably and F2S3 is documented as the canonical CliToolAdapter example (subprocess + conda-run pattern)
**Verified:** 2026-06-27T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Package CLI (`run`/`rescore`/`analyze`/`dashboard`/`list-metrics`) validates arguments and exits with documented non-zero codes on error | ✓ VERIFIED | `cli.py`: 0/1/2 taxonomy wired — sweep `return 1 if (trial_failures or eval_failures or successful_trials == 0) else 0` (:331), rescore `1 if (parser_misses or eval_failures)` (:384), analyze `1 if (skipped_unreadable or eval_failures)` (:433); narrow `_CleanExit`/`_load_or_clean_exit` wrapper (:39-63) flattens loader errors to `error: <msg>` + exit 1; `ToolPreflightError` caught at dispatch boundary (:203). Tests: `test_unknown_flag_is_usage_error_exit_2`, `test_missing_suite_is_clean_error_exit_1`, `test_sweep_crash_exits_1_clean_exits_0`, `test_traceback_flag_reraises_loader_error` all pass. |
| 2 | `CliToolAdapter` subprocess contract covers nonzero exit, missing output, and timeout — all surface as clear failures, not silent corruption | ✓ VERIFIED | `cli_adapter.py`: nonzero-exit → `success=False, error_kind="nonzero_exit"` (:270-284); empty `predictions_glob` → `error_kind="missing_output"` (:291-299); timeout via `Popen(start_new_session=True)` + `communicate(timeout)` + process-group `SIGKILL` tree-kill (:228-265, `_terminate_process_tree` :312-330). Runner propagation: `_raise_if_failed` before `evaluate_trial` (:426-433) → `log_trial_failure` not `complete_trial` (:350-376). Behavioral tests pass: `test_run_trial_nonzero_exit_is_failure`, `test_run_trial_timeout_is_failure`, `test_run_trial_timeout_reaps_descendant_process`, `test_run_trial_timeout_robust_to_process_lookup_error`, `test_run_trial_empty_glob_fails_populated_glob_succeeds`, `test_failed_first_trial_is_logged_not_completed_and_sweep_continues`. |
| 3 | F2S3 `conda-run` integration detects missing env or missing binary and emits an actionable error message | ✓ VERIFIED | `cli_adapter.py` `prepare()` (:111-164): `shutil.which` for the leader, `_preflight_conda_env`/`_parse_conda_target` resolve `-n`/`-p`, `_conda_env_names()` enumerates via `conda env list --json` mapping nonzero/malformed-JSON/TimeoutExpired all to `ToolPreflightError` (:166-199). `f2s3.yaml` carries `remediation` + `help_url` (gseg-ethz). Behavioral tests pass: `test_prepare_missing_binary_raises_preflight_error`, `test_prepare_missing_conda_env_raises_preflight_error`, `test_conda_enumerator_failure_modes_map_to_preflight_error`, `test_run_missing_conda_env_exits_1_with_remediation`. (Accepted D-02 limitation: trailing in-env binary not preflighted; surfaced by trial 0's nonzero-exit handling.) |
| 4 | Tests cover hardened CLI behaviours: invalid arguments, exit codes, adapter failure modes | ✓ VERIFIED | Net-new `tests/core/test_runner_failure.py` + `test_cli.py`, extended `test_cli_adapter.py` — 42 passed in the three phase files (full suite 117 passed). Covers usage exit 2, clean-error exit 1, sweep crash/timeout/all-failed taxonomy, rescore/analyze F-06 split, hermetic preflight, descendant cleanup, termination race, loader output-mode validation, `--timeout`/`--traceback`, narrow-wrapper boundary. |
| 5 | F2S3 documented as canonical `CliToolAdapter` example incl. "how to obtain F2S3" note sourced from gseg-ethz repo | ✓ VERIFIED | `docs/tools/f2s3.md`: "How to obtain F2S3" section (:10) links `gseg-ethz/F2S3_pc_deformation_monitoring`, process-tree termination guarantee (:89). `docs/integrating/cli-tool.md`: subprocess-contract failure-mode table, failed-trial→Ax `log_trial_failure`, D-05/RESOLVED-A non-fatal timeout semantics, 0/1/2 exit-code table (:171-209). `docs/integrating/index.md` no longer presents blessed `stdout_json`. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/geodispbench3d/tool/base.py` | `ToolPreflightError`, `TrialResult.error_kind` | ✓ VERIFIED | error_kind :61; ToolPreflightError :64 with remediation/help_url in `str()` :86-89; in `__all__` :128. |
| `src/geodispbench3d/tool/cli_adapter.py` | preflight + process-group timeout + empty-glob + error_kind | ✓ VERIFIED | All branches present and wired (see truth 2/3). |
| `src/geodispbench3d/sweep/runner.py` | `TrialExecutionError`, `_raise_if_failed`, `_resolve_best_trial`, typed counters | ✓ VERIFIED | TrialExecutionError :51 (+`__all__` :676), `_raise_if_failed` :66 called from both paths (:266, :433), `_resolve_best_trial` :270 no-throw, SweepRunSummary.timeouts/trial_failures/eval_failures/successful_trials :122-125. |
| `src/geodispbench3d/cli.py` | rescore subcommand, narrow wrapper, `--timeout`, exit taxonomy | ✓ VERIFIED | rescore subparser :107, run lacks rescore-only flags, `--timeout` :97, exit expressions wired (truth 1). |
| `src/geodispbench3d_f2s3/conf/tool/f2s3.yaml` | remediation + help_url, conda-run entry, timeout unset | ✓ VERIFIED | entry :13, remediation :17, help_url (gseg-ethz) :21, timeout_seconds commented :30. |
| docs (f2s3.md, cli-tool.md, index.md, rescoring-and-analysis.md, yaml-schemas.md) | hardened-CLI documentation | ✓ VERIFIED | All present and consistent with implemented strings. |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| `CliToolAdapter.run_trial` timeout | `TrialResult(success=False, error_kind="timeout")` | Popen+killpg+communicate | ✓ WIRED |
| `_evaluate_across_cases` success=False | `log_trial_failure` (not complete_trial) | `_raise_if_failed`→TrialExecutionError→per-trial handler | ✓ WIRED |
| `_default_executor` (legacy run) success=False | `log_trial_failure` | shared `_raise_if_failed` guard | ✓ WIRED |
| all-failed sweep | valid summary, best_trial None | `_resolve_best_trial` swallows Ax throw | ✓ WIRED |
| `_cmd_sweep` `--timeout` | adapter | `set_timeout_override` (public seam) | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase test files green | `python -m pytest tests/core/test_runner_failure.py test_cli.py test_cli_adapter.py -q` | 42 passed in 10.14s | ✓ PASS |
| src/ `--rescore` flag-token scrub | `grep -rnF -- "--rescore" src/` | no matches | ✓ PASS |
| docs/ old command-form scrub | `grep -rEn "geodispbench3d +run +\S+ +--rescore" docs/` | no matches | ✓ PASS |
| index.md blessed stdout_json removed | `grep -qE "^\s*from:\s*stdout_json\s*$" docs/integrating/index.md` | no match | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| CLI-01 | 03-02 | Validated argument handling + tested error/exit-code paths | ✓ SATISFIED | cli.py taxonomy + test_cli.py |
| CLI-02 | 03-01, 03-04 | CliToolAdapter documented contract + robust failure handling | ✓ SATISFIED | cli_adapter.py + docs/integrating/cli-tool.md |
| CLI-03 | 03-01 | F2S3 conda-run verifies env/binary presence, surfaces failures | ✓ SATISFIED | `prepare()` preflight + 4 preflight tests. NOTE: REQUIREMENTS.md still marks CLI-03 `[ ]`/"Pending" (line 28, 92) — stale tracking checkbox; the implementation and tests exist and pass. Recommend updating REQUIREMENTS.md to Complete. |
| CLI-04 | 03-03 | Hardened CLI behaviors covered by tests | ✓ SATISFIED | test_runner_failure.py + test_cli.py (42 tests) |
| CLI-05 | 03-04 | F2S3 documented as canonical example + how-to-obtain note | ✓ SATISFIED | docs/tools/f2s3.md gseg-ethz link |

All five declared requirement IDs are claimed by a plan; no orphaned requirements.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| --- | --- | --- | --- |
| `sweep/rescore.py` | `_walk_run_dirs` mutates FS via `trial_record_path` mkdir-on-read (WR-01) | ⚠️ Warning (advisory) | Spurious empty `ax_trial/` dirs under non-run-dir siblings; does not affect goal. |
| `tool/loader.py` / `cli_adapter.py` | subprocess `env` read from `outputs` block + full-environment replacement (WR-02) | ⚠️ Warning (advisory) | `env` feature unusable as written; not shipped in any config, not goal-relevant. |
| `cli_adapter.py` | unbounded second `communicate()` reap on timeout (WR-03) | ⚠️ Warning (advisory) | Re-parented descendant could re-introduce a hang; conda-run topology (tested) reaps fine. |

These three are the advisory WARNINGs from `03-REVIEW.md` (0 blockers). None block goal achievement; surfaced for future cleanup.

### Human Verification Required

None. All success criteria have both presence and passing behavioral-test evidence.

### Gaps Summary

No gaps. All five ROADMAP success criteria are observably true in the codebase, backed by 42 passing phase tests (117 full-suite). The only bookkeeping note: REQUIREMENTS.md still shows CLI-03 as Pending despite the preflight being fully implemented and tested — a stale checkbox, not a missing deliverable.

---

_Verified: 2026-06-27T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
