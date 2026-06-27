---
phase: 3
reviewers: [codex]
reviewed_at: 2026-06-27T13:03:27Z
plans_reviewed: [03-01-PLAN.md, 03-02-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md]
---

# Cross-AI Plan Review — Phase 3

## Codex Review

# Cross-AI Plan Review

## 03-01-PLAN.md

### Summary

The plan identifies the central defect correctly: `TrialResult(success=False)` currently reaches `evaluate_trial()` and may be completed in Ax because `_evaluate_across_cases()` never checks `success` ([runner.py:311](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:311), [runner.py:324](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:324)). The proposed typed failure signal and Ax failure routing are sound. However, the plan leaves two important holes: the legacy runner path still ignores `success=False`, and an all-failed sweep still unconditionally asks Ax for a best trial.

### Strengths

- Correctly fixes the core propagation defect. Currently only raised exceptions reach `log_trial_failure()` ([runner.py:256](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:256), [runner.py:268](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:268)); an explicit runner check is necessary.

- `error_kind` avoids brittle parsing of human-readable errors. The current result contract only has `success` and `error` ([base.py:43](/scratch/35_geodispbench3d/src/geodispbench3d/tool/base.py:43)).

- Checking empty prediction globs after collection fits the current architecture: `_collect_outputs()` returns empty predictions as success today ([cli_adapter.py:202](/scratch/35_geodispbench3d/src/geodispbench3d/tool/cli_adapter.py:202)).

- The loader plan correctly distinguishes explicit `stdout_json` from an omitted value. Current code collapses both through the same default ([loader.py:132](/scratch/35_geodispbench3d/src/geodispbench3d/tool/loader.py:132)).

- Process-group termination materially improves the current unrestricted `subprocess.run()` call ([cli_adapter.py:107](/scratch/35_geodispbench3d/src/geodispbench3d/tool/cli_adapter.py:107)).

### Concerns

- **HIGH — all-failed sweeps can still fail after the trial loop.** `run_with_suite()` unconditionally calls `self._ax.get_best_trial()` ([runner.py:275](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:275)). If every trial times out or crashes, Ax may have no completed trial. That undermines the planned “timeout-only sweep exits 0” behavior and may produce an unexpected traceback instead.

- **HIGH — the legacy `run()` path retains the same success-propagation defect.** `_default_executor()` ignores `result.success` and returns its metrics ([runner.py:208](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:208)); `run()` then completes that trial ([runner.py:198](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:198)). The plan calls this a central adapter contract but only fixes `run_with_suite()`.

- **HIGH — missing binary inside a conda environment is not preflighted.** The plan deliberately checks only `conda` and the environment, leaving the trailing executable to trial 0. This does not fully meet Phase success criterion 3: “missing env or missing binary” must be detected with an actionable error. The current F2S3 command is an argv sequence beginning with `conda`, so `shutil.which(tokens[0])` cannot validate `f2s3`.

- **MEDIUM — Popen replacement requirements are incomplete.** The current call guarantees captured text output and custom environment handling ([cli_adapter.py:108](/scratch/35_geodispbench3d/src/geodispbench3d/tool/cli_adapter.py:108)). The plan should explicitly require `stdout=PIPE`, `stderr=PIPE`, `text=True`, and `env=self._env`; otherwise behavior can regress during the mechanical rewrite.

- **MEDIUM — rescore failure attribution needs a richer internal result.** `_RescoreOutcome` currently collapses evaluation, cache-write, and log-append failures into one `non_fatal_failures` count ([rescore.py:289](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:289), [rescore.py:335](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:335), [rescore.py:351](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:351)). Plan 01 says to split them but does not explicitly add typed fields to `_RescoreOutcome`.

### Suggestions

- Add a defined no-successful-trials outcome: `best_trial=None`, or catch Ax’s no-best-trial exception and return a valid summary.

- Apply the `success=False` guard in `_default_executor()` too, ideally through one shared helper.

- For `conda run`, perform a bounded binary check such as `conda run -n ENV command -v BIN`, or explicitly narrow CLI-03 and success criterion 3 if that cost is unacceptable.

- Add typed `_RescoreOutcome` fields such as `eval_failures` and `degradation_failures`.

- Specify complete Popen I/O and cleanup behavior, including cleanup if `killpg()` itself fails.

### Risk Assessment

**HIGH.** The primary fix is well targeted, but all-failed sweeps and the second runner entry point can still violate the claimed contract.

---

## 03-02-PLAN.md

### Summary

The CLI restructuring is sensible and grounded in the current parser layout. The rescore split removes structural ambiguity, and typed summary counters are a better basis for exit codes than `succeeded == total`. The exception-wrapper design and timeout exit semantics need reconciliation before execution.

### Strengths

- Promoting `rescore` matches the existing subparser pattern ([cli.py:24](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:24), [cli.py:79](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:79)).

- It correctly targets the current F-06 logic: rescore and analyze presently use `succeeded == total` ([cli.py:236](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:236), [cli.py:282](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:282)).

- Correctly changes dashboard’s missing dependency from usage code 2 to runtime code 1 ([cli.py:293](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:293)).

- `set_timeout_override()` is preferable to direct mutation of `_timeout`.

### Concerns

- **HIGH — timeout exit semantics contradict the documented contract.** Plan 02 requires timeout-only sweeps to exit 0, while Plan 04 says a timeout creates a failed trial “and the run exits non-zero.” D-08 also classifies runtime failures as exit 1. This must be decided once and applied consistently.

- **MEDIUM — the proposed exception wrapper is not actually narrow.** Wrapping the whole dispatch means `ValueError` from Ax, metrics, results persistence, or other runtime code would be converted to a one-line config error. `_cmd_sweep()` contains much more than loading and preflight ([cli.py:127](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:127)). The plan’s stated narrowness is not achieved by catching around the dispatch block.

- **MEDIUM — `--traceback` is unnecessarily unavailable to dashboard.** If it is a general developer diagnostic switch, a top-level parser option is simpler and consistent. The parent-parser approach also requires careful duplication avoidance.

- **LOW — rescore `--max-trials` remains accepted only to warn that it is ignored.** Moving the flag specifically because it has “rescore meaning” while retaining no operational meaning is confusing.

### Suggestions

- Resolve timeout exit status before implementation. The least surprising taxonomy is: any failed Ax trial, including timeout, yields exit 1, while the sweep still continues internally.

- Move clean-error handling into small helpers around `load_suite()`, `load_analysis()`, `load_metrics_config()`, and `adapter.prepare()`. Do not catch `ValueError` around full command execution.

- Either remove rescore `--max-trials` or implement an actual run-directory limit.

- Define parser construction in a testable `_build_parser()` helper.

### Risk Assessment

**MEDIUM-HIGH.** The command split is straightforward, but unresolved exit semantics and overly broad error masking affect the CLI’s central guarantees.

---

## 03-03-PLAN.md

### Summary

The test plan is materially stronger than the existing coverage and directly targets the current untested failure path. Real subprocess stubs are appropriate. Some proposed tests depend on underspecified or fragile fixtures, and the all-failed Ax case is missing despite being essential to timeout-only behavior.

### Strengths

- The fake-Ax test directly verifies the important distinction between `complete_trial()` and `log_trial_failure()`, corresponding to the current loop at [runner.py:256](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:256).

- Real stubs exercise the exact subprocess behavior absent from existing argv-only tests.

- The child-process cleanup test is necessary for the stronger process-tree termination claim.

- Direct loader tests correctly cover the current default-collapse defect at [loader.py:134](/scratch/35_geodispbench3d/src/geodispbench3d/tool/loader.py:134).

### Concerns

- **HIGH — no explicit all-trials-failed test.** The fake Ax test intentionally follows a failed trial with a successful one, so it cannot expose the unconditional `get_best_trial()` problem at [runner.py:275](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:275). The timeout-only CLI test should naturally hit this, but its fixture design allows replacing the real runner and may accidentally bypass it.

- **MEDIUM — main-level sweep tests are underspecified and risk excessive mocking.** “Stub executable or fake Ax loop” leaves too much discretion. A fake loop can miss real loader → adapter → runner → summary → exit-code integration.

- **MEDIUM — PID-dead assertions can be flaky.** Process termination and reaping are asynchronous. A bounded polling helper is safer than an immediate `os.kill(pid, 0)` assertion.

- **MEDIUM — tests are split awkwardly across `test_cli.py` and `test_cli_adapter.py`.** Adapter contract tests should live together; main-level tests should not become a large mixed-responsibility file.

- **LOW — one-second timeouts will make the suite unnecessarily slow.** Stubs can use shorter bounded timeouts if startup race handling is robust.

### Suggestions

- Add a runner test where every trial fails and assert a valid summary without calling an invalid best-trial path.

- Require at least one true end-to-end main-level suite using the real runner and real adapter stub.

- Add a bounded `wait_until_process_dead(pid, deadline)` helper.

- Keep loader/adapter tests in `test_cli_adapter.py`, CLI parser/exit tests in `test_cli.py`, and runner tests in `test_runner_failure.py`.

- Test cleanup when timeout termination itself raises `ProcessLookupError`.

### Risk Assessment

**MEDIUM.** Coverage intent is strong, but the most consequential all-failed case is absent and fixture discretion could bypass key integration paths.

---

## 03-04-PLAN.md

### Summary

The documentation plan covers the right pages and correctly expands the stale-reference search beyond the initial list. Its main issue is a direct contradiction with Plan 02 over timeout exit status. Some grep gates also do not fully enforce the stated documentation contract.

### Strengths

- Correctly treats F2S3 as a generic CLI-adapter example rather than introducing tool-specific execution machinery.

- Documents the exact POSIX/non-POSIX termination boundary instead of making an unconditional portability claim.

- Updates both human documentation and the documentation-only schema.

- The repository-wide source scan is stronger than editing only the visible CLI guide.

### Concerns

- **HIGH — timeout documentation contradicts Plan 02.** Task 1 says timeout produces a failed trial “and the run exits non-zero”; Plan 02 explicitly requires a timeout-only run to exit 0. Publishing both would violate CLI-01’s documented taxonomy.

- **MEDIUM — the stale-token gate and migration-note requirement conflict.** Acceptance says the migration note may name `--rescore`, while verification requires no `--rescore` anywhere under `src/` but only forbids the full old command form under `docs/`. The plan’s “NO token remains repo-wide” wording is therefore inaccurate.

- **MEDIUM — grep validation is too weak for semantic correctness.** Checking for words like “timeout,” “exit,” and “deprecated” does not verify that the table or failure behavior matches implementation.

- **LOW — code/docstring cleanup is mixed into the documentation plan.** This is manageable, but it means Plan 04 is not truly docs-only and can conflict with Plan 01 edits to runner/rescore files.

### Suggestions

- Resolve timeout exit semantics first and have Plan 04 consume the exact expression recorded in `03-02-SUMMARY.md`.

- Add focused documentation assertions for each exit-code row and the timeout status.

- Clarify the stale-reference rule: removed invocations are forbidden, but a prose migration note may name the old flag.

- Consider moving source docstring cleanup into Plan 02, leaving Plan 04 documentation-only and reducing Wave 3 overlap.

### Risk Assessment

**MEDIUM.** Documentation scope is good, but shipping contradictory timeout semantics would materially confuse users and CI consumers.

---

## Overall Assessment

**Overall risk: HIGH until three issues are resolved:**

1. Define behavior when every Ax trial fails; avoid unconditional best-trial retrieval.
2. Apply the failed-result contract to both runner paths or explicitly deprecate the legacy one.
3. Establish one timeout exit-code policy across Plans 01–04.

After those corrections, the phase structure and testing strategy are generally strong and should achieve CLI-01 through CLI-05.

---

## Consensus Summary

Single reviewer (Codex, `codex-cli 0.142.2`), re-reviewing the current plan
revisions against the live working tree with `file:line` grounding. This run
supersedes the earlier 12:15Z review of the pre-revision plans (retained in git
history at commit `48ddb22`).

### Agreed Strengths

- The core defect is correctly identified and targeted: `TrialResult(success=False)`
  reaching `evaluate_trial()` / being completed in Ax because `_evaluate_across_cases()`
  never checks `success` (`runner.py:311`, `:324`). The typed `error_kind` failure
  signal and Ax failure routing are sound and avoid brittle error-string parsing.
- The CLI restructuring (promoting `rescore` to its own subcommand, typed summary
  counters as the basis for exit codes) is well-grounded in the existing parser
  layout and correctly targets the F-06 `succeeded == total` logic.
- The test plan materially strengthens coverage of the untested failure path; real
  subprocess stubs are the right call over argv-only assertions.
- The docs plan correctly frames F2S3 as a generic `CliToolAdapter` example and does
  a repo-wide stale-reference scan rather than editing only the visible CLI guide.

### Agreed Concerns (highest priority — must resolve before execution)

1. **HIGH — All-failed sweeps still break after the trial loop.** `run_with_suite()`
   unconditionally calls `self._ax.get_best_trial()` (`runner.py:275`). If every trial
   times out or crashes, Ax may have no completed trial, producing a traceback and
   undermining the planned "timeout-only sweep exits 0" behavior. Needs a defined
   no-successful-trials outcome (`best_trial=None` or catch the no-best-trial exception).

2. **HIGH — The legacy `run()` path retains the same success-propagation defect.**
   `_default_executor()` ignores `result.success` (`runner.py:208`) and `run()` completes
   the trial (`runner.py:198`). Plan 01 calls this a central adapter contract but only
   fixes `run_with_suite()`. Apply the `success=False` guard to both paths via one shared
   helper, or explicitly deprecate the legacy path.

3. **HIGH — Timeout exit-code policy is self-contradictory across plans.** Plan 02
   requires a timeout-only sweep to exit `0`; Plan 04 documents a timeout as a failed
   trial where "the run exits non-zero"; D-08 classifies runtime failures as exit `1`.
   This must be decided once and applied consistently across Plans 01–04 (and the docs
   table / schema). Codex's recommendation: any failed Ax trial, including timeout,
   yields exit `1` while the sweep continues internally.

### Secondary Concerns

- **MEDIUM — Missing binary inside a conda env is not preflighted.** Preflight checks only
  `conda` + the env, leaving the trailing executable (`f2s3`) to trial 0; `shutil.which(tokens[0])`
  validates `conda`, not `f2s3`. This does not fully meet success criterion 3. Either add a
  bounded `conda run -n ENV command -v BIN` check, or explicitly narrow CLI-03 / SC-3.
- **MEDIUM — The "narrow" CLI exception wrapper isn't narrow.** Wrapping the whole dispatch
  converts `ValueError` from Ax/metrics/persistence into a one-line config error
  (`cli.py:127`). Move clean-error handling into small helpers around `load_suite()`,
  `load_analysis()`, `load_metrics_config()`, `adapter.prepare()` instead.
- **MEDIUM — `_RescoreOutcome` collapses distinct failures** (eval / cache-write / log-append)
  into one `non_fatal_failures` count (`rescore.py:289`, `:335`, `:351`); Plan 01 says to split
  them but does not add typed fields. Add e.g. `eval_failures` / `degradation_failures`.
- **MEDIUM — Test gaps & fragility:** no explicit all-trials-failed runner test (the fake-Ax
  test follows a failure with a success, so it can't expose the `get_best_trial()` problem);
  PID-dead assertions can be flaky (use a bounded `wait_until_process_dead` poll); Popen
  replacement should explicitly require `stdout=PIPE`, `stderr=PIPE`, `text=True`, `env=self._env`.
- **MEDIUM — Doc grep gates are too weak** to enforce semantic correctness, and the
  stale-`--rescore`-token gate conflicts with allowing a migration note to name the old flag.

### Divergent Views

None — single reviewer this run.

### Overall

**Risk: HIGH** until the three agreed concerns are resolved: (1) define all-trials-failed
behavior and avoid unconditional best-trial retrieval, (2) apply the failed-result contract
to both runner paths, (3) settle one timeout exit-code policy across Plans 01–04. After those
corrections the phase structure and testing strategy are strong and should achieve CLI-01–CLI-05.
