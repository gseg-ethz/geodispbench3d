# Phase 2: Targeted Fixes - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the Phase 1 audit (`REPORT.md`) into landed code. Phase 2 applies the
**13 audit findings recommended for fix** as reviewed commits, consolidates the
two flagged duplications to a single source each, removes confirmed dead code,
and keeps the quality suite (`ruff`, `pyright`, full `pytest`) green at every
wave boundary.

**Ratified fix set (the D-05 gate — this discussion locks it):**
`F-01`, `F-02`, `F-03`, `F-05`, `F-08`, `F-09`, `F-10`, `F-11`, `F-13`, `F-20`,
`F-21`, `F-22`, `F-30`.

**Explicitly NOT in this phase** (carried by the audit's own dispositioning):
- **defer → v2:** F-04 (parquet O(n²)/race), F-12 (220-line app-config builder),
  F-14 (Ax shims), F-15 (iof3D dataclass coupling), F-17 (in-memory cloud merge),
  F-19 (sweep checkpoint/resume).
- **accept (documented risk):** F-18, F-24, F-25.
- **route-forward:** F-06/F-07/F-16/F-32 → Phase 3 (CLI); F-26/F-27/F-29/F-31 →
  Phase 4 (licensing/packaging); F-23/F-28 → Phase 5 (CI/CD).

This is a fix phase, not a feature or design-rewrite phase. New capabilities and
the deferred/route-forward findings stay out.

</domain>

<decisions>
## Implementation Decisions

### Scope ratification (D-05 gate)
- **D-01:** The full 13-finding fix set above is **ratified as recommended** — no
  findings pulled out. F-05 is included with its behavior change accepted (see D-02).
- **D-02 (F-05):** Fix **as the audit recommends** — surface partial-case
  failures rather than letting the NaN-ignoring cross-case mean hide them. Per the
  fix sketch: track per-trial case coverage and at minimum emit the finite-case
  count alongside the aggregated objective (penalize / threshold-refuse are
  acceptable stronger options at planner discretion). The change to objective
  reporting is in-scope hardening.

### F-08 — broad-except boundary
- **D-03:** Apply the **full audit approach** to the ~10 broad `except Exception`
  sites (`runner.py:61,295,324,354`; `rescore.py:257,295,310`;
  `evaluation.py:89,177`; `predictions_cache.py:120`; `trial_record.py:89`):
  1. **Narrow** each catch to the expected types (`OSError`,
     `json.JSONDecodeError`, `ImportError`, etc.).
  2. Promote `logger.debug` → `logger.warning`.
  3. Add a **per-pass non-fatal-failure counter**, surfaced as an aggregate
     "N non-fatal failures" line in each CLI summary.
  - **Fail-soft control flow is preserved** — this reconciles with the CONVENTIONS
    "never let observability/caching/provenance failures break the primary path"
    rule. The goal is to make silent degradation *countable and visible*, not to
    make side-effect failures fatal.

### Test scope & order (F-20 / F-21 / F-22)
- **D-04 (order — tests first):** Characterization tests for `runner.py` (F-20)
  land **before** the `runner.py` refactors (F-01, F-05, F-08, F-13), so those
  refactors — especially the behavioral F-05/F-08 — land against a green
  regression net. Given `runner.py` is at 13% coverage, this safety net is the
  reason for the ordering, not incidental.
- **D-05 (bar — behavior-anchored + floor):** "Done" is judged primarily by
  whether the **specific named behaviors** are exercised (runner trial loop +
  partial-failure path; store create/append; evaluation failure paths), with a
  **coverage floor** as a secondary regression guard. Exact floor numbers are at
  planner discretion, anchored to "no regression below current coverage + a
  meaningful lift on the three named modules (`runner.py`, `store.py`,
  `evaluation.py`)." Do not game a percentage with shallow tests.
- **D-06 (F-22 depth):** Add **direct** tests where a module has real failure-path
  logic worth pinning (the behavior-anchored bar); **accept indirect coverage**
  for thin pass-through modules among the 3 currently-indirectly-covered.

### Commit granularity & quality gate
- **D-07 (commit grain — planner's discretion):** Atomic, ID-referencing commits
  where a finding is self-contained; grouped commits where findings are trivially
  mechanical (e.g. the F-09/F-10/F-11 hygiene cluster). Commits SHOULD reference
  the stable finding ID (D-03 from Phase 1) so history maps back to the audit table.
- **D-08 (green gate — every wave):** `ruff` + `pyright` + the full `pytest` suite
  must pass at **every wave boundary** (not necessarily after each individual
  commit). Intermediate commits within a wave may be transiently red. See D-11/D-12
  for the operational definition of the pyright half of this gate.

### Quality-gate operationalization (resolves RESEARCH A1 — decided 2026-06-27)
- **D-11 (pyright gate = no-regression, not zero):** At HEAD pyright is RED
  (21 errors / 9 warnings), and a chunk of those errors live in code Phase 2 does
  **not** touch — F-14 (Ax shims, `runner.py:395/401`), F-12/F-15 (iof3D adapter),
  and the dashboard, all dispositioned defer/route-forward. "pyright passes
  (0 errors)" is therefore unsatisfiable in Phase 2 without pulling deferred work
  in. The pyright half of D-08 is operationalized as: **(a) no NEW pyright errors
  above the established HEAD baseline, AND (b) 0 errors on the lines Phase 2 actually
  owns** (the touched regions of `cli.py`, `sweep/runner.py` non-shim,
  `sweep/parameters.py`, `tool/loader.py`, `sweep/trial_record.py`,
  `sweep/rescore.py`, `sweep/evaluation.py`, `results/store.py`,
  `dataset/schema.py`). `ruff` and the full `pytest` suite remain strict
  (0 problems / all 32 + new tests green, 0 skipped).
- **D-12 (baseline is CI-faithful):** Wave 0 establishes the baseline by installing
  the CI-pinned `pyright==1.1.392` with `.[dev]`-only resolution (matching
  `.github/workflows/ci.yml`'s lint job) and recording the exact error count as the
  floor — not the local `1.1.403` + full-extras superset. This matches the gate CI
  will actually enforce at publish time.
- **D-13 (mypy is a Phase 5 discussion, NOT decided here):** A proposal to demote
  pyright to informative and add a strict `mypy` gate (with aligned CI workflows,
  pchandler-style) is explicitly **deferred to Phase 5 (CI/CD) as an open question
  to evaluate — pros/cons to be discussed there, not pre-locked.** No mypy work,
  config, or dependency enters Phase 2. (CI workflow edits are already routed to
  Phase 5 via F-23/F-28.)

### F-30 — declared-but-unread fields
- **D-09 (guard the forward-compat fields, delete the rest):**
  - **Guard, don't delete:** `ExecutionConfig.parallel_trials` and
    `override_tool_mode` — these map to the tracked v2 requirement EXEC-01
    (parallel sweeps). Add an explicit "not implemented" guard (raise/warn when set
    to a non-default) so the config cannot silently no-op. Preserves the v2 seam.
  - **Delete the genuinely dead:** `ToolConfig.outputs_options`,
    `CaseSpec.scan_by_epoch`, `DatasetSpec.gt_kinds_supported`, and
    `ToolProvenance.yaml_hash` (unless a provenance consumer is being added).
  - Decision rule for the triage: **guard if it maps to a tracked v2 requirement,
    delete otherwise.**

### F-13 — provenance lookup chain
- **D-10:** F-13 **folds into F-01**. Once `SuiteConfig`/`ToolConfig` are properly
  typed (F-01), replace the
  `getattr(...) or getattr(...raw...lambda...)` chain at `runner.py:238-241` with
  the direct typed access `suite.tool.source_path`. Must be behavior-preserving for
  the case the typed field already covers.

### Claude's Discretion
- The mechanical findings — **F-09** (`datetime.utcnow()` → timezone-aware
  `datetime.now(UTC)`, 5 sites), **F-10** (hoist the in-loop internal imports to
  module top), **F-11** (delete the `_ = asdict` dead-import hack) — are
  planner/executor discretion on exact form, subject to D-08.
  **Guardrail for F-10:** hoisting must NOT pull any optional/heavy dependency
  (Ax, iof3D, streamlit) to module level — that would break the lazy-import gating
  CONVENTIONS mandates. The F-10 imports are all geodispbench3d-internal
  (`trial_record`, `predictions_cache`, `math`, `dataclasses`), so hoisting is safe;
  preserve the gating invariant if any other import surfaces during the work.
- **F-01** scope: at minimum retype the suite-consumer cluster
  (`_cmd_sweep`/`_cmd_rescore`/`run_with_suite`/`_evaluate_across_cases`) to
  `SuiteConfig` and delete the associated `# type: ignore[attr-defined]` markers;
  whether to sweep additional `type: ignore` removals repo-wide is executor judgment.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & the fix contract
- `.planning/phases/01-code-health-audit/REPORT.md` — **the authoritative input.**
  The summary findings table is the unit Phase 2 turns into fix commits; each
  `F-NN` detail section carries the location (file:line), evidence/impact, and a
  fix sketch. Read every ratified finding's section before planning its fix.
- `.planning/phases/01-code-health-audit/EVIDENCE.md` (+ `audit-evidence/`) —
  reproducible detector output (vulture/coverage/deptry/radon) corroborating the
  findings; the coverage numbers anchor the F-20/F-21/F-22 test targets.
- `.planning/ROADMAP.md` §"Phase 2: Targeted Fixes" — goal + 4 success criteria.
- `.planning/REQUIREMENTS.md` §Fixes (FIX-01…FIX-04) — the four locked requirements
  this phase satisfies; §Out of Scope confirms no feature growth.

### Dev-environment constraint (governs every test/lint run)
- `AGENTS.md` — all `python`/`pip`/`pytest`/`ruff`/`pyright` invocations run through
  the conda env `iof3d_cosicorr3d-dev312`; the F2S3 suite runs via
  `conda run -n f2s3-dev312`. The green-gate (D-08) is defined relative to these envs.

### Codebase baselines
- `.planning/codebase/CONVENTIONS.md` — the best-effort/fail-soft exception pattern
  (the constraint F-08/D-03 reconciles with) and the lazy optional-import rule (the
  F-10/D-discretion guardrail).
- `.planning/codebase/ARCHITECTURE.md` — confirms the dependency graph is acyclic
  (so F-10 hoisting dodges no real cycle) and that parallelism is a future
  extension (context for F-30/D-09 guarding `parallel_trials`).
- `.planning/codebase/STRUCTURE.md` — nominates `sweep/trial_record.py` as the home
  for shared provenance helpers (the F-03 consolidation target).
- `.planning/codebase/TESTING.md` — current suite layout (core/iof3d/f2s3) and gaps,
  input to the test-scope decisions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SuiteConfig` / `ToolConfig` are already concrete frozen dataclasses
  (`suite/loader.py:46-57`, `tool/loader.py:44-48`) — F-01 is a retype-and-delete-
  ignores job, not a schema change. `ToolConfig.source_path: Path | None` already
  exists, which is what F-13 collapses onto.
- `SweepParameter` (`sweep/parameters.py`) is already imported by the iof3d factory,
  so the F-02 `from_mapping` classmethod introduces no new dependency edge across the
  three coercion sites (`parameters.py:57`, `tool/loader.py:192`, `iof3d/factory.py:137`).
- Existing quality tooling (ruff, pyright, pytest, coverage) is configured in
  `pyproject.toml`; the green-gate reuses it.

### Established Patterns
- Findings cite `file:line` anchors and stable IDs (`F-NN`) — commits reference
  those IDs (D-07).
- Fail-soft side effects intentionally swallow (CONVENTIONS) — F-08/D-03 keeps the
  control flow, only narrowing types + raising visibility.

### Integration Points
- `runner.py` is the convergence point: F-01, F-05, F-08, F-13 all touch it, which
  is why F-20's characterization tests land first (D-04).
- F-03 consolidates `_parser_fn_repr` into `trial_record.py`; the string is a
  provenance/cache key, so both call sites (`runner.py:363`, `rescore.py:395`) must
  end up byte-identical — the single-source move is what guarantees that.

</code_context>

<specifics>
## Specific Ideas

- **F-05 should make degradation *visible*, not necessarily change the math** — the
  user accepted the audit's recommendation but the emphasis is surfacing the
  finite-case count / partial-failure signal; stronger penalize/threshold behavior
  is an acceptable but optional escalation.
- **F-08's purpose is "countable silent degradation"** — the aggregate
  "N non-fatal failures" summary line is explicitly wanted as part of this phase
  (not deferred to Phase 3).
- **Tests-first is a deliberate safety net**, chosen specifically because the
  behavioral refactors (F-05, F-08) land in a module at 13% coverage.

## Research / planning items to resolve (not user decisions)
- **Which suites actually execute in which env.** FIX-04 names "core/iof3d/f2s3,"
  but the executor runs in `iof3d_cosicorr3d-dev312` and the F2S3 suite needs
  `conda run -n f2s3-dev312`. The plan must verify which of core/iof3d/f2s3 are
  runnable in which env so the "wave green" gate (D-08) is operationally well-defined
  (e.g. core+iof3d in the dev env, f2s3 via the f2s3 env). Confirm before relying on
  "full pytest passes."
- **Dataclass parse behavior on deleted F-30 fields.** Confirm whether removing a
  dataclass field causes OmegaConf→dataclass parsing to reject existing YAML suites
  that still declare the key. Pre-public, so no external back-compat obligation, but
  the in-repo benchmark YAMLs must still load after the deletions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Findings the audit dispositioned
`defer`/`accept`/`route-forward` are recorded in `REPORT.md` and excluded from this
phase by D-01's scope statement (not "deferred ideas" surfaced here).

</deferred>

---

*Phase: 2-Targeted Fixes*
*Context gathered: 2026-06-27*
