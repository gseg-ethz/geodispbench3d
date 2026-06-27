---
phase: 3
reviewers: [codex]
reviewed_at: 2026-06-27T12:15:21Z
plans_reviewed: [03-01-PLAN.md, 03-02-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md]
---

# Cross-AI Plan Review — Phase 3

## Codex Review

# Cross-AI Plan Review — Phase 3 CLI Hardening

## Overall assessment

The plans are well-grounded and correctly identify the main implementation seams. However, two phase-critical control-flow gaps remain:

1. `TrialResult(success=False)` is still evaluated and reported to Ax as a completed trial.
2. The sweep CLI still returns `0` even when real trial failures occurred.

Until those are corrected, CLI-01/CLI-02 and the stated timeout/failed-trial contract are not actually satisfied.

Overall risk: **HIGH** until the failure-propagation design is revised.

---

## Plan 03-01 — Adapter contract and preflight

### Summary

The adapter changes target the correct files and reuse existing lifecycle and result structures. The output and timeout handling are appropriately localized, but the proposed runner change only counts failures; it does not cause Ax to mark them failed.

### Strengths

- Timeout belongs at the existing `subprocess.run` call in [`cli_adapter.py:108`](/scratch/35_geodispbench3d/src/geodispbench3d/tool/cli_adapter.py:108). Catching `TimeoutExpired` beside the existing `FileNotFoundError` branch at line 115 is coherent.
- `prepare()` is the correct preflight hook: it is invoked before trial allocation in [`runner.py:251`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:251).
- The loader currently collapses unset and explicit `stdout_json` at [`loader.py:134`](/scratch/35_geodispbench3d/src/geodispbench3d/tool/loader.py:134); reading the raw value first is necessary.
- Empty predictions currently pass silently through [`cli_adapter.py:202`](/scratch/35_geodispbench3d/src/geodispbench3d/tool/cli_adapter.py:202), so the planned check addresses a real corruption risk.
- Updating the documentation-only schema is appropriate; its current output enum is visible at [`tool.schema.json:48`](/scratch/35_geodispbench3d/src/geodispbench3d/conf/schema/tool.schema.json:48).

### Concerns

- **HIGH — Failed adapter results will still be completed in Ax.**  
  The plan adds `diag.add(...)` after [`runner.py:311`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:311), but execution then proceeds into `evaluate_trial` at line 324 and ultimately `complete_trial` at line 268. `evaluate_trial` does not stop on `trial_result.success=False`; it still invokes parsers and metrics at [`evaluation.py:83-160`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:83). Thus timeout/nonzero/empty-output results can be treated as completed Ax trials.

- **HIGH — Timeout may leave the actual F2S3 process running.**  
  The canonical entry is `conda run ... f2s3` at [`f2s3.yaml:13`](/scratch/35_geodispbench3d/src/geodispbench3d_f2s3/conf/tool/f2s3.yaml:13). A timeout kills the direct `conda` child, but the plan does not establish process-group termination for descendants. The claim that the tool is killed is therefore stronger than the mechanism guarantees.

- **MEDIUM — “No real conda required” is inconsistent with preflight mechanics.**  
  Testing `conda run -n no-such-env` reaches env enumeration only if a real `conda` executable exists. Otherwise it tests only the missing-leading-executable branch. The env-list subprocess should be stubbed or injected.

- **MEDIUM — Conda preflight error handling is underspecified.**  
  `conda env list --json` can return nonzero, malformed JSON, or raise `TimeoutExpired`. These need conversion into `ToolPreflightError`; otherwise raw subprocess/JSON exceptions escape the intended structured contract.

- **MEDIUM — Conda environment parsing has edge cases.**  
  Parsing basenames of environment paths does not represent the special `base` name correctly. Prefix paths also need `expanduser()` and normalization before existence checks.

- **MEDIUM — Output mode validation remains ambiguous.**  
  The current schema includes `fixed_path` at [`tool.schema.json:48`](/scratch/35_geodispbench3d/src/geodispbench3d/conf/schema/tool.schema.json:48), but the adapter has no distinct fixed-path branch: all non-`stdout_json` modes fall into glob collection. If glob is the single blessed mode, unsupported modes should be rejected explicitly.

- **LOW — A default F2S3 timeout conflicts with the stated opt-in philosophy.**  
  Adding an arbitrary multi-hour ceiling to the shipped YAML can surprise-kill legitimate workloads. Leaving it unset while documenting the field better matches D-04.

### Suggestions

- Introduce a dedicated trial-failure signal or explicit branch in `_evaluate_across_cases`:

  - Count the failure.
  - Stop processing remaining cases.
  - Prevent parser/metric evaluation.
  - Propagate to the existing per-trial exception handler so Ax calls `log_trial_failure`.

- Use process-group/session management if timeout must terminate the entire tool tree, especially through `conda run`.
- Give conda discovery a bounded timeout and map every failure to `ToolPreflightError`.
- Unit-test env resolution by monkeypatching the conda-list subprocess result, not by depending on installed conda state.
- Reject every unsupported `outputs.from` value at load time.

### Risk assessment

**HIGH.** The adapter may correctly produce `success=False`, but the runner currently converts that into a completed Ax trial. That breaks the central subprocess-failure contract.

---

## Plan 03-02 — Package CLI

### Summary

The subcommand split and clean-error boundary are sensible. The plan does not fully implement its own exit-code taxonomy, particularly for sweep failures and fail-soft evaluation errors.

### Strengths

- The current `run` parser mixes sweep and rescore arguments at [`cli.py:28-67`](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:28); a dedicated subparser is the correct structural validation mechanism.
- The F-06 defect is real: rescore returns based on `succeeded == total` at [`cli.py:236`](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:236), while pre-existing failures increment `skipped_failed` at [`rescore.py:130-137`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:130).
- Catching loader `FileNotFoundError`/`ValueError` around dispatch will improve the current traceback-heavy behavior.
- Changing dashboard’s missing dependency from exit `2` at [`cli.py:293-301`](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:293) to exit `1` correctly follows the taxonomy.

### Concerns

- **HIGH — Sweep still always exits `0`.**  
  `_cmd_sweep` unconditionally returns `0` at [`cli.py:185`](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:185). Plan 02 does not change that, despite claiming runtime and trial-scoring failures return `1`. The summary already exposes `non_fatal_failures` at lines 182–184, but no reliable breakdown distinguishes real tool failures from harmless observability degradation.

- **HIGH — Rescore exit status still misses genuine evaluation failures.**  
  The proposed condition uses only `parser_misses`. Rescore’s diagnostics also include evaluation, cache, record-read, and persistence failures, summarized only as `non_fatal_failures` at [`rescore.py:111-115`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:111). A metric/evaluation failure can therefore still exit `0`.

- **MEDIUM — Analyze lacks the counter required by the plan.**  
  Evaluation exceptions increment only generic diagnostics at [`analysis/runner.py:125-134`](/scratch/35_geodispbench3d/src/geodispbench3d/analysis/runner.py:125). `AnalysisSummary` has no evaluation-failure field at lines 44–49. Checking only `skipped_unreadable` cannot implement “and any genuine evaluation failures.”

- **MEDIUM — Direct mutation of `_timeout` is brittle.**  
  The proposed CLI writes an adapter private field. A public override method/property or an immutable configuration replacement would make the precedence contract testable without coupling CLI code to adapter internals.

- **MEDIUM — Broad `ValueError` handling can hide programming defects.**  
  Catching all `ValueError` from the entire dispatch path converts runtime bugs in Ax, metrics, or result handling into a one-line “config” error. Narrowing the protected region to loading/validation would preserve debuggability.

- **LOW — Top-level `--traceback` placement needs definition.**  
  With argparse subparsers, a top-level option commonly works only before the subcommand unless duplicated. The accepted invocation forms and tests should be explicit.

### Suggestions

- Add typed failure counters to `SweepRunSummary`, `RescoreSummary`, and `AnalysisSummary`, separating:

  - tool/runtime failures,
  - parser/evaluation failures,
  - benign skips,
  - observability/persistence degradation.

- Base exit `1` on the first two categories, not the aggregate non-fatal counter.
- Add a supported `CliToolAdapter.set_timeout_override()` or constructor/config replacement seam.
- Catch loader errors narrowly; catch `ToolPreflightError` around sweep execution; let unexpected runtime exceptions retain tracebacks unless explicitly suppressed.
- Add tests for both accepted placements of `--traceback`, or document one canonical placement.

### Risk assessment

**HIGH.** The advertised 0/1/2 contract is not achieved for sweep failures and is incomplete for rescore/analyze evaluation failures.

---

## Plan 03-03 — Tests

### Summary

Real stub executables are the right approach for subprocess behavior. Several planned tests cannot prove the claimed behavior without additional seams, and critical sweep/Ax propagation coverage is missing.

### Strengths

- Existing adapter tests only validate argv construction and hashing, as stated in [`test_cli_adapter.py:1-5`](/scratch/35_geodispbench3d/tests/core/test_cli_adapter.py:1). Real subprocess coverage is a meaningful addition.
- Timeout, nonzero exit, output collection, and executable preflight are good candidates for executable stubs.
- Main-level tests are necessary because no current test covers dispatch or exit codes.
- The explicit `--timeout 0` regression test is useful because truthiness-based precedence is an easy future error.

### Concerns

- **HIGH — No test asserts Ax receives a failed trial.**  
  Adapter-level `success=False` assertions are insufficient. The actual defect lies in the runner path from [`runner.py:311`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:311) to `complete_trial` at line 268. A fake Ax client must assert `log_trial_failure` is called and `complete_trial` is not.

- **HIGH — No sweep-level exit-1 test is planned.**  
  The plan tests preflight exit `1`, but not a trial that times out or exits nonzero after preflight succeeds. This allows `_cmd_sweep`’s unconditional return `0` to remain undetected.

- **MEDIUM — Missing-conda-env test is not hermetic as written.**  
  It depends on whether `conda` exists and on its environment listing. Mock the resolver/enumerator while keeping actual tool execution tests real.

- **MEDIUM — `run_dirs` cannot be passed through `main()`.**  
  `rescore_suite` supports `run_dirs` at [`rescore.py:88-99`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:88), but `_cmd_rescore` does not expose it and calls `rescore_suite` without it at [`cli.py:218-223`](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:218). Main-level tests must construct the expected result-root layout or monkeypatch `rescore_suite`.

- **MEDIUM — Explicit `stdout_json` coverage is not firmly assigned.**  
  The artifact list mentions it, but Task 1 acceptance criteria omit it. This loader behavior should have a direct test, including unset→glob and explicit→error cases.

- **MEDIUM — Descendant cleanup is untested.**  
  A simple sleep stub only proves the direct process is terminated. It does not cover a wrapper spawning a child, which approximates the canonical conda-run topology.

- **LOW — Extending two files may duplicate fixture machinery.**  
  Put subprocess helpers in one test module or a small fixture file rather than splitting similar tests across `test_cli.py` and `test_cli_adapter.py`.

### Suggestions

Add tests that verify:

- timeout/nonzero/empty-output causes `log_trial_failure`, not `complete_trial`;
- sweep continues to the next Ax trial;
- final CLI exit is `1` when one or more real trial failures occurred;
- parser/metric failures affect rescore/analyze exit codes;
- explicit `stdout_json`, unsupported `fixed_path`, and unset output mode;
- malformed/nonzero/timed-out `conda env list`;
- timeout cleanup for a wrapper-spawned child process.

### Risk assessment

**MEDIUM-HIGH.** The proposed tests cover adapter mechanics but miss the most important end-to-end contracts: Ax trial state and final sweep exit status.

---

## Plan 03-04 — Documentation

### Summary

The selected pages are relevant, but the documentation scope is incomplete for a deliberate CLI break. The grep-only checks are too weak to ensure examples match the shipped parser.

### Strengths

- [`docs/integrating/cli-tool.md`](/scratch/35_geodispbench3d/docs/integrating/cli-tool.md) is the correct location for the generic subprocess contract.
- F2S3’s shipped config clearly demonstrates the intended conda pattern at [`f2s3.yaml:7-17`](/scratch/35_geodispbench3d/src/geodispbench3d_f2s3/conf/tool/f2s3.yaml:7).
- The schema reference should distinguish tool-level and suite-level `execution`.
- Waiting for Plans 01–02 summaries before finalizing exact wording is good dependency ordering.

### Concerns

- **HIGH — The CLI migration leaves known stale public documentation.**  
  Current references exist outside the four planned files:

  - [`README.md`](/scratch/35_geodispbench3d/README.md) contains rescore usage.
  - [`src/geodispbench3d/analysis/__init__.py:3`](/scratch/35_geodispbench3d/src/geodispbench3d/analysis/__init__.py:3) says `run --rescore`.
  - [`docs/integrating/index.md:45`](/scratch/35_geodispbench3d/docs/integrating/index.md:45) still presents `stdout_json`.
  - Numerous internal docstrings reference `--rescore`, including [`rescore.py:1`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:1) and [`evaluation.py:42`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:42).

  The user decision explicitly named README and quickstart ripple, but Plan 04 omits them.

- **MEDIUM — Grep gates do not validate command correctness.**  
  Checking merely for “timeout” or “exit” can pass with stale examples or incorrect option placement.

- **MEDIUM — Documentation may promise stronger timeout cleanup than implemented.**  
  “Killed subprocess” should not imply the full conda/F2S3 descendant tree is guaranteed terminated unless Plan 01 adds process-group handling.

- **LOW — CLI-02 documentation is assigned to a CLI-05-only plan.**  
  Traceability would be clearer if Plan 04 listed both CLI-02 and CLI-05 in its requirements.

### Suggestions

- Expand `files_modified` to include README, quickstart, integrating index, and relevant public module docstrings.
- Add repository-wide stale-pattern gates, for example ensuring no user-facing `run ... --rescore` or blessed `stdout_json` examples remain.
- Prefer CLI help snapshot/parser tests over grep-only validation.
- Document the exact timeout termination guarantee delivered by the implementation.
- Mark Plan 04 as satisfying both CLI-02 and CLI-05.

### Risk assessment

**MEDIUM.** Documentation can ship internally inconsistent even if all current grep gates pass.

---

## Required revisions before execution

1. Define the runner behavior for `TrialResult.success=False` so Ax logs a failed trial and does not evaluate missing/corrupt output.
2. Add structured failure counters sufficient to derive final CLI exit status for sweep, rescore, and analyze.
3. Specify descendant-process termination for timeout through `conda run`.
4. Make conda env tests hermetic.
5. Add runner/Ax and sweep-exit integration tests.
6. Expand the CLI migration documentation sweep beyond the four selected files.

---

## Consensus Summary

Only one reviewer (Codex) was invoked for this pass, so "consensus" here reflects
Codex's grounded, source-cited findings rather than agreement across multiple models.
The review traced plan claims against the actual code and surfaced two phase-critical,
cross-cutting failure-propagation gaps that recur across three of the four plans.

### Agreed Strengths
- Plans target the correct implementation seams and reuse existing lifecycle/result
  structures (timeout at `cli_adapter.py:108`, preflight via `prepare()` at `runner.py:251`,
  rescore exit defect at `cli.py:236` / `rescore.py:130`).
- Real stub-executable testing approach for subprocess behavior is sound.
- Documentation page selection is appropriate; dependency ordering (docs after Plans 01–02)
  is correct.

### Agreed Concerns (highest priority)
- **HIGH — Failed trials still complete in Ax.** `TrialResult(success=False)` flows into
  `evaluate_trial` (`evaluation.py:83-160`) and `complete_trial` (`runner.py:268`); nothing
  branches on `success=False`. CLI-01/CLI-02 contract is not met as planned. (Plans 01 + 03)
- **HIGH — Sweep always exits `0`.** `_cmd_sweep` unconditionally returns `0` (`cli.py:185`);
  rescore/analyze exit logic keys off partial counters (`parser_misses`, `skipped_unreadable`)
  and misses genuine evaluation/metric failures buried in `non_fatal_failures`. The advertised
  0/1/2 taxonomy is not achieved. (Plans 02 + 03)
- **MEDIUM — Timeout may orphan the real F2S3 process.** `conda run` (`f2s3.yaml:13`) spawns
  descendants; killing the direct child does not guarantee process-tree termination. Needs
  process-group/session handling. (Plans 01, 03, 04)
- **MEDIUM — Conda-env tests are not hermetic.** They depend on a real `conda` install and its
  env listing; the resolver/enumerator should be mocked. (Plans 01 + 03)
- **HIGH — Documentation sweep is too narrow.** Stale `--rescore` / `stdout_json` references
  persist outside the four planned files (`README.md`, `analysis/__init__.py:3`,
  `docs/integrating/index.md:45`, multiple docstrings), and grep-only gates can pass on stale
  examples. (Plan 04)

### Required Revisions Before Execution
1. Define runner behavior for `TrialResult.success=False` → Ax `log_trial_failure`, no metric eval.
2. Add structured failure counters to `SweepRunSummary` / `RescoreSummary` / `AnalysisSummary`
   to derive exit status (separate tool/runtime, parser/eval, benign skip, observability).
3. Specify descendant-process termination for timeout through `conda run`.
4. Make conda-env tests hermetic (mock the subprocess).
5. Add runner/Ax and sweep-exit integration tests (assert `log_trial_failure`, not `complete_trial`;
   assert final exit `1` on real trial failure).
6. Expand the CLI-migration documentation sweep beyond the four selected files.

### Divergent Views
None — single reviewer.
