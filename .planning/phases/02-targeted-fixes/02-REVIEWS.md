---
phase: 2
reviewers: [codex]
reviewed_at: 2026-06-26T23:53:24Z
plans_reviewed:
  - 02-01-PLAN.md
  - 02-02-PLAN.md
  - 02-03-PLAN.md
  - 02-04-PLAN.md
  - 02-05-PLAN.md
  - 02-06-PLAN.md
  - 02-07-PLAN.md
note: >
  Single-reviewer pass. Claude was skipped for independence (this command runs
  inside the Claude Code CLI); Gemini/OpenCode/Qwen/Cursor/Antigravity are not
  installed. review.default_reviewers is ["codex"]. The "Consensus Summary"
  below therefore reflects codex's own cross-plan synthesis, not agreement
  across multiple independent models.
---

# Cross-AI Plan Review — Phase 2

## Codex Review

# Cross-AI Plan Review — Phase 2

## Summary

The plan set has strong traceability, sequencing, and source awareness. Wave 0 correctly precedes behavior changes, and most source anchors are accurate. However, several execution contracts are internally inconsistent: pyright commands require exit code 0 despite the accepted nonzero baseline; the F-08 counter lacks a concrete propagation design through shared helpers; and F-05's "per-trial summary record" does not fit the current per-case run-directory model. These are execution-blocking plan defects, not implementation details.

Overall risk: **MEDIUM-HIGH** until the pyright gate and observability data model are corrected.

---

# 02-01 — Runner Characterization Net

## Summary

Good tests-first placement and appropriate use of a fake Ax client. The plan correctly targets the highest-risk orchestration paths. The harness instructions need one important clarification: `AxSweepRunner` constructs `AxClient` internally, so dependency injection must occur by monkeypatching the module symbol or changing production code—which this characterization plan should avoid.

## Strengths

- Correctly covers the untested trial loop at [`runner.py:145`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:145), including completion and failure behavior.
- Pins all supported `_normalize_trial_data` forms at [`runner.py:375`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:375).
- Correctly characterizes the current NaN-survivor aggregation at [`runner.py:334`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:334) before F-05 changes observability.
- Avoiding real Ax is appropriate because experiment construction introspects the Ax API at [`runner.py:76`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:76).

## Concerns

- **MEDIUM:** The fake-client installation mechanism is unspecified. The constructor unconditionally executes `AxClient(...)` at [`runner.py:69`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:69). "Construct an AxSweepRunner with the fake client" will not work unless the test monkeypatches `geodispbench3d.sweep.runner.AxClient` before construction.
- **MEDIUM:** `create_experiment` must have a signature compatible with the runner's `inspect.signature` dispatch at [`runner.py:76-116`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:76). A generic `*args, **kwargs` fake will fail the parameter-name detection.
- **LOW:** A fixed `>=50%` task threshold may encourage incidental coverage and could fail because of coverage-tool configuration rather than behavior. The named paths are the stronger acceptance criterion.

## Suggestions

- Explicitly require `monkeypatch.setattr(runner_module, "AxClient", FakeAxClient)`.
- Give `FakeAxClient.create_experiment` an explicit accepted signature, such as `parameters`, `name`, `objective_name`, and `minimize`.
- Add teardown assertions. `run_with_suite` guarantees adapter teardown via `finally` at [`runner.py:217-218`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:217); this is valuable characterization.
- Treat coverage as recorded evidence rather than a hard per-plan pass/fail threshold.

## Risk Assessment

**LOW-MEDIUM.** The target behavior is correct; the main risk is a test harness that cannot instantiate the runner.

---

# 02-02 — Store/Evaluation Tests and Pyright Baseline

## Summary

The store and evaluation tests are well scoped. The pyright-baseline task, however, violates the repository environment rules as written and does not produce a reproducible CI-faithful dependency environment.

## Strengths

- Store tests directly exercise all branches in [`store.py:23-40`](/scratch/35_geodispbench3d/src/geodispbench3d/results/store.py:23).
- Evaluation tests cover the two genuine plugin boundaries at [`evaluation.py:78-92`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:78) and [`evaluation.py:157-179`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:157).
- Testing parser failure while preserving adapter scalars matches `scalar = dict(trial_result.scalar_metrics)` at [`evaluation.py:106`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:106).
- Recording a baseline with per-file detail is a reasonable no-regression mechanism.

## Concerns

- **HIGH:** Task 3 says to run bare `python -m venv`. This directly violates `AGENTS.md`, which requires every Python command to use `conda run -n iof3d_cosicorr3d-dev312 ...`.
- **HIGH:** A venv created from the mandated environment and installed with `.[dev]` is not necessarily "CI-faithful"; dependency resolution may use current indexes and differ from CI. Network access may also be unavailable.
- **MEDIUM:** The verification command masks pyright failure intentionally and prints success-like text regardless:
  `pyright > /dev/null 2>&1; echo ...`.
  It verifies only that pyright ran, not that the baseline document matches its output.
- **LOW:** Adding coverage configuration is unrelated to F-21/F-22 and marked optional in research. It expands the plan's write scope without being required.

## Suggestions

- Replace bare Python with:
  `conda run -n iof3d_cosicorr3d-dev312 python -m venv ...`
  if a venv is retained.
- Prefer a deterministic baseline script that captures pyright JSON output, tool version, command, and counts, then validates the document against that output.
- Do not claim "dev-only resolution" unless the environment is actually isolated and dependency versions are recorded.
- Remove the optional `pyproject.toml` change unless coverage configuration is explicitly required.

## Risk Assessment

**MEDIUM-HIGH.** Tests are solid, but the baseline task is noncompliant and weakly verified.

---

# 02-03 — Typed SuiteConfig, Provenance Fold, Finite-Case Signal

## Summary

F-01 and F-13 are straightforward and source-supported. F-05 is underdesigned: the current method produces one run directory per case, aggregates only after all cases finish, and does not retain those run directories for a later aggregate update. "Write the per-trial summary record" therefore has no unambiguous destination.

## Strengths

- `load_suite` already returns `SuiteConfig` at [`suite/loader.py:60`](/scratch/35_geodispbench3d/src/geodispbench3d/suite/loader.py:60), supporting the planned retyping.
- `ToolConfig.source_path` is populated at [`tool/loader.py:84`](/scratch/35_geodispbench3d/src/geodispbench3d/tool/loader.py:84), so removing the fallback at [`runner.py:238-241`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:238) is justified.
- Keeping finite-case metadata out of Ax `raw_data` is prudent because that mapping is sent directly to `complete_trial` at [`runner.py:214`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:214).
- Preserving the existing mean avoids an unnecessary optimization-policy change.

## Concerns

- **HIGH:** The summary-record mechanism is unresolved. Provenance is written inside the case loop to each case-specific `result.outputs.run_dir` at [`runner.py:247-296`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:247), while finite counts are known only after aggregation at [`runner.py:334-347`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:334). The plan does not specify whether every case record, one record, or a new trial-level record receives the aggregate.
- **HIGH:** Finite counts are metric-specific. Each objective key may be absent or NaN in different cases at [`runner.py:339-346`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:339). A single `cases_finite` count can be misleading unless it is explicitly tied to the configured objective.
- **HIGH:** The automated pyright command requires a zero exit code. `runner.py` has accepted deferred pyright errors around `_normalize_trial_data`; therefore `pyright runner.py cli.py && pytest` contradicts D-11.
- **MEDIUM:** The plan says re-run pyright after each ignore removal, which is impractical and not enforceable within an atomic executor task.

## Suggestions

- Define the signal precisely as `objective_cases_finite` and `objective_cases_total`, calculated for `self._objective_name`.
- Choose an explicit persistence model:
  - write the aggregate count to every participating case summary after aggregation, retaining the run directories; or
  - introduce a dedicated trial-level summary artifact.
- If logging alone satisfies D-02, remove the ambiguous summary-record requirement.
- Replace zero-exit pyright checks with a baseline comparison script that permits known deferred diagnostics and rejects new/touched-line diagnostics.

## Risk Assessment

**HIGH.** F-05 cannot be implemented consistently from the current plan without making an unreviewed data-model decision.

---

# 02-04 — SweepParameter Deduplication

## Summary

This is a clean, appropriately isolated refactor. It needs explicit unit tests for the new conversion boundary and corrected pyright verification.

## Strengths

- The three duplicated constructors genuinely match, including the block at [`parameters.py:57-72`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/parameters.py:57) and [`tool/loader.py:192-209`](/scratch/35_geodispbench3d/src/geodispbench3d/tool/loader.py:192).
- The classmethod belongs on `SweepParameter` and introduces no new cross-layer dependency.
- Explicit `values` narrowing can remove the existing ambiguous `list(entry.get(...))` typing.

## Concerns

- **MEDIUM:** The verification invokes pyright on `geodispbench3d_iof3d/factory.py`, which has an accepted deferred error unrelated to F-02. Requiring command success conflicts with the baseline policy.
- **MEDIUM:** No dedicated tests are added for `from_mapping`, despite the task being marked TDD. Existing loader tests may not exercise all 11 fields or malformed inputs.
- **LOW:** "Add from_mapping to parameters.py `__all__`" is conceptually incorrect. `from_mapping` is a class member, not a module-level export.

## Suggestions

- Add parameterized tests covering all fields, omitted defaults, `values=None`, tuple/list values, and missing `name`.
- Remove the `__all__` instruction.
- Compare pyright diagnostics against the baseline rather than requiring exit 0.

## Risk Assessment

**LOW-MEDIUM.** The implementation is simple; verification and test specificity need adjustment.

---

# 02-05 — Broad Exceptions and Non-Fatal Counters

## Summary

This is the weakest plan in the set. It correctly recognizes that arbitrary plugin boundaries must remain broad, but the exception sets and counter architecture are not compatible with the actual APIs. Shared helpers currently return only values, have no logger/counter context, and are called by multiple workflows.

## Strengths

- Correctly preserves broad catches around user/plugin code at [`evaluation.py:78-92`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:78), [`evaluation.py:157-179`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:157), and [`rescore.py:243-260`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:243).
- Correctly leaves trial-level Ax failure handling separate at [`runner.py:159`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:159) and [`runner.py:215`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:215).
- Preserving fail-soft behavior is aligned with current code.

## Concerns

- **HIGH:** There is no concrete mechanism for evaluation failures to increment a pass-level counter. `evaluate_trial` returns only `EvaluationOutput` with scalar metrics, rows, and prediction at [`evaluation.py:29-42`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/evaluation.py:29). The plan must either add diagnostics to this object or pass a counter/callback into it.
- **HIGH:** `read_prediction` and `load_trial_record` have no logger or counter parameters and simply return `None`/`{}` at [`predictions_cache.py:111-121`](/scratch/35_geodispbench3d/src/geodispbench3d/results/predictions_cache.py:111) and [`trial_record.py:83-90`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/trial_record.py:83). Counting failures requires API changes and affects every caller.
- **HIGH:** The proposed rescore append exception set is inaccurate. `append_rescore_entry` calls `.append` on `payload["rescore_log"]` at [`trial_record.py:107-115`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/trial_record.py:107); valid but malformed JSON can produce `AttributeError`, while `JSONDecodeError` is swallowed earlier by `load_trial_record`. Catching `(OSError, JSONDecodeError)` does not preserve existing fail-soft behavior.
- **HIGH:** Analyze has its own broad `evaluate_trial` boundary at [`analysis/runner.py:100-116`](/scratch/35_geodispbench3d/src/geodispbench3d/analysis/runner.py:100), but Task 1 does not classify it while Task 2/3 promises an analyze counter.
- **HIGH:** Returning "best trial alongside count" is not specified. Changing `run_with_suite` from `Any` to a tuple affects `_cmd_sweep` and any programmatic caller. A result dataclass would be safer.
- **MEDIUM:** An "unwritable path" test is platform-dependent, especially under privileged users. Permissions may not reliably force failure.
- **MEDIUM:** `logger.debug → warning` does not apply to `load_trial_record` or `read_prediction`, since neither currently logs.
- **MEDIUM:** Again, the pyright verification requires exit 0 despite the baseline exception policy.

## Suggestions

- Introduce a typed diagnostics model, for example:
  `PassDiagnostics(non_fatal_failures: int, by_kind: dict[str, int])`.
- Add `non_fatal_failures` to `EvaluationOutput`, `_RescoreOutcome`, `RescoreSummary`, and `AnalysisSummary`; aggregate explicitly.
- For low-level readers, either:
  - return a typed result carrying `value/error`, or
  - accept an optional diagnostics callback.
- Include `analysis/runner.py:114` explicitly in the catch inventory.
- Re-evaluate exception sets by tracing actual callees. Add malformed-valid-JSON tests for `rescore_log`.
- Test cache failure by monkeypatching `write_prediction` to raise `OSError`, not filesystem permissions.
- Return a named `SweepRunSummary` rather than an unstructured tuple.
- Add CLI tests asserting all three summary lines; Task 3 currently has no direct CLI output test.

## Risk Assessment

**HIGH.** The requirements are reasonable, but the plan lacks an implementable and testable counter contract.

---

# 02-06 — Timestamp and Mechanical Hygiene

## Summary

The mechanical changes are low risk and accurately anchored. The acceptance grep for `utcnow` is too broad because helper names `_utcnow` and `_utcnow_compact` may remain even after implementation.

## Strengths

- All five deprecated calls are correctly identified, including [`trial_record.py:271-272`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/trial_record.py:271) and [`predictions_cache.py:97`](/scratch/35_geodispbench3d/src/geodispbench3d/results/predictions_cache.py:97).
- The `+00:00` versus `Z` change is explicitly acknowledged.
- Hoisted imports in `runner.py` are internal or standard library; they do not introduce optional runtime dependencies.
- The dead `asdict` suppression is confirmed at [`rescore.py:409-410`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:409).

## Concerns

- **MEDIUM:** `! grep -rn 'utcnow' src/geodispbench3d` will fail if helper functions retain names such as `_utcnow` and `_utcnow_compact`, even though all deprecated calls are removed.
- **LOW:** Timestamp format compatibility is checked only by grep. Existing persisted data consumers may compare timestamp strings lexically or parse only `Z`.
- **LOW:** `grep '^from ax|^import ax'` is not a meaningful lazy-import assertion because Ax is already imported inside top-level guarded `try` blocks at [`runner.py:16-23`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:16).

## Suggestions

- Search specifically for `datetime.utcnow(` rather than the substring `utcnow`.
- Add timestamp parsing assertions using `datetime.fromisoformat`.
- Rely on `test_imports.py` for optional dependency gating rather than the Ax grep.

## Risk Assessment

**LOW.** Minor verification defects only.

---

# 02-07 — Parser Helper, Dead Fields, Guards, Final Gate

## Summary

The deduplication and dead-field inventory are accurate. The final plan has gaps in guard placement, guard behavior, suite-loading verification, and final pyright enforcement.

## Strengths

- Correctly identifies all three `yaml_hash` sites, including reconstruction at [`trial_record.py:234-242`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/trial_record.py:234).
- `parser_fn_repr` belongs near `ParserProvenance` at [`trial_record.py:59-69`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/trial_record.py:59).
- Dead-field locations are accurately traced:
  - `outputs_options`: [`tool/loader.py:44`](/scratch/35_geodispbench3d/src/geodispbench3d/tool/loader.py:44)
  - `scan_by_epoch`: [`dataset/schema.py:53-57`](/scratch/35_geodispbench3d/src/geodispbench3d/dataset/schema.py:53)
  - `gt_kinds_supported`: [`dataset/schema.py:67`](/scratch/35_geodispbench3d/src/geodispbench3d/dataset/schema.py:67)
- Unknown dataset keys are ignored because the loader explicitly extracts known fields at [`dataset/schema.py:84-110`](/scratch/35_geodispbench3d/src/geodispbench3d/dataset/schema.py:84).

## Concerns

- **HIGH:** Guarding only `_cmd_sweep` does not prevent programmatic callers from silently ignoring `ExecutionConfig`. `run_with_suite` at [`runner.py:173`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:173) remains callable directly.
- **HIGH:** "Raise (or warn)" is too weak. A warning still permits the unsupported configuration to execute as a no-op. D-09 requires an explicit not-implemented guard; it should deterministically raise.
- **HIGH:** The stated suite-load verification does not load a suite.
  `python -c "from ... import load_suite; print(...)"` only imports the function.
- **HIGH:** The final FIX-04 gate still describes pyright no-regression but provides no executable baseline-diff mechanism. Raw pyright exits nonzero.
- **MEDIUM:** Task 3 adds guard behavior but no tests for `parallel_trials != 1` and `override_tool_mode is not None`.
- **MEDIUM:** Removing `yaml_hash` drops useful provenance integrity even if currently unread. Since FIX-02 requires audit-mandated deletion this may be intentional, but a compatibility test should prove old records containing `yaml_hash` still deserialize.
- **LOW:** Optional YAML/schema cleanup should be mandatory or removed. Optional edits undermine deterministic plan scope.
- **LOW:** `parser_fn_repr` exact-string tests should include nested/local callables because `__qualname__` is used at [`runner.py:363-372`](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:363).

## Suggestions

- Put a shared validation function on `ExecutionConfig` or call a common guard from both `_cmd_sweep` and `run_with_suite`.
- Mandate `NotImplementedError` or `ValueError`; do not allow warning-only behavior.
- Add tests for both non-default execution fields and their default values.
- Actually load every shipped suite in the verification command.
- Add an old-summary compatibility test containing `yaml_hash`.
- Make YAML/schema cleanup deterministic.
- Implement a baseline comparison utility before claiming FIX-04 completion.

## Risk Assessment

**MEDIUM-HIGH.** Dead-code work is sound, but the final gate and execution guards do not yet prove the phase goals.

---

# Cross-Plan Concerns

- **HIGH — Pyright gate contradiction:** Plans 02-03, 02-04, and 02-05 invoke pyright under `&&`, requiring exit 0. This contradicts D-11's accepted nonzero baseline. A machine-checkable diagnostic-diff command must replace every raw pyright gate.
- **HIGH — F-08 ownership/data flow:** The counter crosses runner, evaluation, rescore, analysis, cache, and trial-record APIs without a defined type or propagation contract.
- **HIGH — F-05 persistence semantics:** "Per-trial summary" conflicts with the current per-case run directories and must be specified before implementation.
- **MEDIUM — Requirement mapping:** Wave-0 plans list only FIX-04 even though they directly implement F-20/F-21/F-22 under FIX-01's ratified finding set. Traceability should show that relationship.
- **MEDIUM — Atomic commits:** Several plans require multiple atomic commits within one plan, but summaries and wave gates do not state how partial failure or rollback is managed.

# Recommended Plan Changes Before Execution

1. Add a baseline-aware pyright comparison script and use it in every wave.
2. Redesign 02-05 around explicit diagnostics/result dataclasses.
3. Decide exactly where F-05 finite-case metadata is stored and whether it is objective-specific.
4. Correct 02-02's environment instructions to comply with `AGENTS.md`.
5. Add direct CLI-summary tests and execution-guard tests.
6. Replace import-only "suite load" checks with actual loading of every shipped suite.

# Overall Risk Assessment

**MEDIUM-HIGH.** The phase decomposition and audit traceability are strong, but two central behavior changes—F-05 and F-08—are not sufficiently designed against the existing data flow. The raw pyright commands also make several plans fail by construction. Once those three issues are resolved, the remaining work is mostly low-risk refactoring and characterization testing.

---

## Consensus Summary

> Single-reviewer pass (codex only). This section synthesizes codex's
> cross-plan findings; it is not multi-model consensus.

### Agreed Strengths

- Strong audit traceability and source-anchored plans — most `file:line`
  references check out against the actual code.
- Correct wave sequencing: Wave 0 characterization tests precede the
  behavior-changing refactors.
- Genuinely isolated, low-risk refactors in 02-04 (SweepParameter dedup),
  02-06 (timestamp hygiene), and the dedup/dead-field inventory in 02-07.

### Agreed Concerns (highest priority)

1. **HIGH — Pyright gate contradiction (02-03, 02-04, 02-05).** Plans gate on
   raw `pyright ... && pytest`, requiring exit 0, but D-11 accepts a nonzero
   pyright baseline. These plans fail by construction. Needs a baseline-aware
   diagnostic-diff command in every wave.
2. **HIGH — F-08 counter has no propagation contract (02-05).** The non-fatal
   counter must cross `evaluate_trial`, rescore, analyze, `read_prediction`,
   and `load_trial_record`, none of which currently carry counter/logger
   context or return diagnostics. Needs a typed diagnostics model + a
   structured `SweepRunSummary` rather than an ad-hoc tuple.
3. **HIGH — F-05 persistence semantics undefined (02-03).** "Per-trial summary
   record" doesn't fit the current per-case run-directory model; finite counts
   are only known post-aggregation and are objective-specific. Needs an
   explicit storage decision (per-case vs. new trial-level artifact) and an
   `objective_cases_finite/total` definition tied to `self._objective_name`.
4. **HIGH — 02-02 environment non-compliance.** Bare `python -m venv` violates
   `AGENTS.md` (conda env mandated), and the "CI-faithful" claim isn't
   guaranteed. Baseline verification also masks pyright failure.
5. **HIGH — 02-07 execution guards too weak.** Guarding only `_cmd_sweep`
   leaves `run_with_suite` callable with ignored `ExecutionConfig`;
   "raise (or warn)" should deterministically raise (D-09); the suite-load
   check only imports rather than loading suites.

### Divergent Views

None — single reviewer, so no cross-model disagreement to record. The closest
thing to internal tension is codex flagging coverage thresholds (02-01) and
optional `pyproject.toml`/YAML edits (02-02, 02-07) as LOW-severity scope
questions rather than blockers; the planner may reasonably keep or drop these.
