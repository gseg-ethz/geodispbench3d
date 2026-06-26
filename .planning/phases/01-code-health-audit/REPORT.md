# Phase 1 — Code-Health Audit: REPORT.md

**Authored:** 2026-06-26 · Plan 01-02 (reasoned manual file:line review, D-08) ·
env `iof3d_cosicorr3d-dev312` (Python 3.12) per AGENTS.md.

> **This report supersedes `.planning/codebase/CONCERNS.md`** as the authoritative,
> dispositioned code-health record (D-10). Every CONCERNS.md finding has been
> independently re-verified against the current source and is accounted for in the
> CONCERNS Traceability appendix (carried forward as an `F-NN`, or marked superseded /
> resolved / false-positive with a reason).
>
> **Dispositions are recommendations, not locked scope.** Per D-05 the audit
> *recommends* a disposition per finding; the user *ratifies* the final
> fix/defer/accept/route-forward set at the Phase 2 discussion. Nothing here
> pre-commits a fix.

## How to read this report

- **Stable IDs (`F-01` …):** the unit Phase 2 plans/commits reference directly (D-03).
- **Severity (publish-anchored, D-04):**
  - **Blocker** — unsafe to publish to public PyPI as-is.
  - **Major** — should fix this milestone; not a publish-blocker on its own.
  - **Minor** — cosmetic / low-value / forward-compat hygiene.
- **Disposition (D-06):**
  - **fix** — Blocker/Major + low-to-moderate effort, in-milestone (lands in Phase 2).
  - **defer** — real but belongs to known v2 / out-of-milestone work (recorded, not fixed now).
  - **accept** — by-design or too low-value to touch (documented accepted risk).
  - **route-forward** — owned by a later phase; tagged to it rather than dispositioned
    here. Owning phases: **Phase 3** = CLI hardening, **Phase 4** = licensing/metadata/
    packaging, **Phase 5** = CI/CD & release.
- **Evidence basis:** every finding below was confirmed by reading the cited
  `file:line` (D-08). Plan 01's detectors (`EVIDENCE.md` + `audit-evidence/`) are cited
  as *corroboration* only, never as the primary inventory.

## Summary Findings Table

Every finding indexed by stable ID, location, severity, and recommended disposition
(D-01). Rows correspond one-to-one with the detail sections below. Dispositions are
**recommendations pending Phase 2 ratification** (D-05).

| ID | Finding | Location (file:line) | Severity | Disposition | Owner |
|------|---------|----------------------|----------|-------------|-------|
| F-01 | Untyped `SuiteConfig` / `suite: Any` + `type: ignore` cluster | cli.py:123-205; runner.py:173,223 | Major | fix | Phase 2 |
| F-02 | Duplicated `SweepParameter` coercion (x3) | parameters.py:57; tool/loader.py:192; iof3d/factory.py:137 | Major | fix | Phase 2 |
| F-03 | Duplicated `_parser_fn_repr` (x2) | runner.py:363; rescore.py:395 | Minor | fix | Phase 2 |
| F-04 | Parquet store O(n^2) + read-modify-write race | results/store.py:30-40 | Major | defer | v2 |
| F-05 | Cross-case mean aggregation hides partial failures | runner.py:334-346 | Major | fix | Phase 2 |
| F-06 | `--rescore` exit-code conflation | cli.py:214; rescore.py:106-128 | Major | route-forward | Phase 3 |
| F-07 | `stdout_json` bottom-up "first `{`" heuristic | cli_adapter.py:190-201 | Major | route-forward | Phase 3 |
| F-08 | Pervasive broad `except Exception` swallowing | runner/rescore/evaluation/predictions_cache/trial_record | Major | fix | Phase 2 |
| F-09 | Deprecated `datetime.utcnow()` (x5) | trial_record.py:272; rescore.py:304,406; analysis/runner.py:173; predictions_cache.py:97 | Major | fix | Phase 2 |
| F-10 | Lazy imports inside the per-case hot loop | runner.py:232-282,308,339 | Minor | fix | Phase 2 |
| F-11 | `_ = asdict` lint-suppression hack | rescore.py:27,409-410 | Minor | fix | Phase 2 |
| F-12 | 220-line field-by-field `build_app_config_from_parameters` | iof3d/adapter.py:128-347 | Major | defer | v2 |
| F-13 | `getattr...or getattr...lambda` provenance chain | runner.py:238-241 | Major | fix | Phase 2 |
| F-14 | Ax API compatibility shims (signature introspection) | runner.py:17-28,72-136,375-409 | Major | defer | v2 |
| F-15 | iof3D adapter coupling to upstream private dataclasses | iof3d/adapter.py:19-27,128-347; factory.py:18 | Major | defer | v2 |
| F-16 | F2S3 `subprocess` + `conda run` coupling; untested e2e | f2s3.yaml:13; cli_adapter.py:98-150 | Major | route-forward | Phase 3 |
| F-32 | `CliToolAdapter` subprocess has no timeout | cli_adapter.py:107-114 | Major | route-forward | Phase 3 |
| F-17 | In-memory full-cloud load + merge in parsers | f2s3/output_parser.py:126-145; iof3d/output_parser.py:108-122 | Minor | defer | v2 |
| F-18 | Only one GT kind implemented (doc/impl mismatch) | dataset/ground_truth.py:63-73,118 | Minor | accept | - |
| F-19 | No sweep checkpoint / resume | runner.py:69,200-221 | Major | defer | v2 |
| F-20 | `runner.py` untested (13%) | sweep/runner.py | Major | fix | Phase 2 |
| F-21 | `store.py` untested (44%) | results/store.py | Major | fix | Phase 2 |
| F-22 | `evaluation.py` failure-paths + 3 modules indirectly covered | evaluation.py:89-93,118-122,177-179 | Minor | fix | Phase 2 |
| F-23 | iof3D adapter untested (CI job disabled) | ci.yml:60; iof3d/adapter.py | Major | route-forward | Phase 5 |
| F-24 | Arbitrary code execution from YAML (by design) | tool/loader.py:152-221; registry.py:63-73; rescore.py:384-392 | Minor | accept | - |
| F-25 | Subprocess from YAML `entry` (shell=False, positive) | cli_adapter.py:108-114,167-185 | Minor | accept | - |
| F-26 | `Private :: Do Not Upload` classifier | pyproject.toml:21-23 | Blocker | route-forward | Phase 4 |
| F-27 | README "Proprietary" vs BSD `LICENSE` | README.md:80-82 | Blocker | route-forward | Phase 4 |
| F-28 | iof3d CI test job disabled | ci.yml:58-60 | Major | route-forward | Phase 5 |
| F-29 | Empty `f2s3` extra / packaging story undecided | pyproject.toml:56-59 | Minor | route-forward | Phase 4 |
| F-30 | Declared-but-unread config/schema fields | suite/loader.py:30-31; schema.py:53-67; trial_record.py:40; tool/loader.py:44 | Minor | fix | Phase 2 |
| F-31 | Legacy `iof3d-ax` CLI unexercised + dup grammar | iof3d/cli.py:9-134; pyproject.toml:40 | Minor | route-forward | Phase 4 |

**Severity tally:** 2 Blocker (F-26, F-27), 18 Major, 12 Minor.
**Disposition tally:** 13 fix, 7 defer, 4 accept, 8 route-forward (Phase 3: F-06/F-07/F-16/F-32; Phase 4: F-26/F-27/F-29/F-31; Phase 5: F-23/F-28).

## AUDIT-03 — CLI-Surface Risk Assessment

Focused, per-surface risk review of the three CLI surfaces in whole-repo read scope
(D-11). Each surface's risks are captured as `F-NN` findings in the detail sections;
this section is the synthesis the success criterion asks for.

### Package CLI — `cli.py`

- **Argument validation:** argparse-level only. `main` requires a subcommand
  (`cli.py:22`), but the four `--rescore`-only flags (`--reuse-parser-options`,
  `--use-prediction-cache`, `--pass-id`, and the rescore use of `--max-trials`) are
  accepted on a plain `run` and silently ignored — only `--max-trials` even warns
  (`cli.py:180-181`). There is no validation that a flag is meaningful for the chosen mode.
- **Exit-code semantics:** `run` always returns `0` once a sweep completes
  (`cli.py:167`); `--rescore` (`cli.py:214`) and `analyze` (`cli.py:256`) both return
  `0 if succeeded == total else 1`, which conflates a real error with the presence of a
  pre-existing failed trial — see **F-06**.
- **Type exposure:** the `suite: object`/`Any` + `type: ignore` cluster (**F-01**) means
  a renamed suite field fails at runtime *inside a CLI handler*, not at pyright time.
- **Owning findings:** F-01, F-06 → **Phase 3** (documented exit codes + argument validation).

### `CliToolAdapter` subprocess contract

- **Output collection:** the `stdout_json` reverse-scan heuristic (**F-07**) can misread
  a trailing JSON-looking line as the result payload — silent data corruption.
- **Failure modes — covered:** a missing binary returns `success=False`,
  `error="Tool entry not found"` (`cli_adapter.py:115-123`); a nonzero exit logs
  stdout/stderr and returns `success=False`, `error="exit=N"` (`cli_adapter.py:127-140`).
- **Failure modes — gaps:** there is **no timeout** on the `subprocess.run` call
  (`cli_adapter.py:107-114`), so a hung tool stalls the whole sweep — see **F-32**; and
  under `outputs_from: glob`, missing output files silently yield empty
  `predictions`/`figures` (`cli_adapter.py:202-221`) rather than a flagged failure (the
  missing-output half of the contract is folded into F-07/F-32's Phase 3 routing).
- **Owning findings:** F-07, F-32 → **Phase 3** (the CLI-hardening contract explicitly
  names nonzero exit, missing outputs, and timeout).

### F2S3 `conda run` integration

- **Env/binary assumptions:** the shipped entry is `conda run -n f2s3-dev312 f2s3`
  (`f2s3.yaml:13`) with absolute scratch paths baked into `static_params` (`:29-30`) and
  the hashed run-dir root (`:51`). A missing env, missing `conda`, or missing binary
  surfaces only as a generic `FileNotFoundError` / nonzero exit (**F-16**) with no
  pre-flight check or remediation hint, and the parser is never run against real F2S3
  output in CI.
- **Owning findings:** F-16 → **Phase 3** (F2S3 as the canonical `CliToolAdapter`
  showcase + "how to obtain F2S3" note), with the packaging half in **Phase 4** (**F-29**).

## Detailed Findings

### AUDIT-02 — Architecture Anti-Patterns

The three anti-patterns flagged in `ARCHITECTURE.md` were each re-read and confirmed
present and correctly located.

#### F-01 — Untyped `SuiteConfig` threaded as `suite: Any` / `object` with a `type: ignore` cluster

- **Location:** `src/geodispbench3d/cli.py:123-167` (`_cmd_sweep`, 9 `# type: ignore[attr-defined]`),
  `:170-205` (`_cmd_rescore`, 3 more), `src/geodispbench3d/sweep/runner.py:173` / `:223`
  (`run_with_suite`, `_evaluate_across_cases` typed `suite: Any`).
- **Evidence / impact:** `load_suite` already returns a concrete frozen
  `SuiteConfig` (`suite/loader.py:46-57`), yet every consumer down-types it to
  `object`/`Any` and reaches in via attribute access guarded by `# type: ignore`.
  Pyright (basic mode, whole-project, per CONVENTIONS) therefore cannot catch a
  renamed/typo'd suite field — `suite.search.objective`, `suite.tool.adapter`,
  `suite.results.parquet_path` would all fail at runtime, not type-check time. This
  is the root cause that also enables F-13.
- **Fix sketch:** Annotate `_cmd_sweep`/`_cmd_rescore`/`run_with_suite`/
  `_evaluate_across_cases` as `SuiteConfig` (import from `suite/loader.py`) and delete
  the `type: ignore` markers. The dataclass is already structural; no schema change needed.
- **Severity:** Major · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-02, AUDIT-04.

#### F-02 — Duplicated `SweepParameter` coercion logic across three sites

- **Location:** `src/geodispbench3d/sweep/parameters.py:57-72` (`load_sweep_config`),
  `src/geodispbench3d/tool/loader.py:192-210` (`_load_hyperparameters`),
  `src/geodispbench3d_iof3d/factory.py:137-150` (`_coerce_hparam`).
- **Evidence / impact:** All three build a `SweepParameter` from a raw mapping with
  byte-identical field extraction (`name`, `kind`, `value_type`, `values`, `lower`,
  `upper`, `log_scale`, `step`, `activates_on`, `is_ordered`, `sort_values`). Adding
  one field to `SweepParameter` requires editing three call sites; they can silently
  drift (e.g. one forgetting `sort_values`).
- **Fix sketch:** Add a `SweepParameter.from_mapping(entry)` classmethod in
  `sweep/parameters.py` and call it from all three sites. The iof3d factory already
  imports `SweepParameter`, so no new dependency edge is introduced.
- **Severity:** Major · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-02, AUDIT-04.

#### F-03 — Duplicated `_parser_fn_repr` helper

- **Location:** `src/geodispbench3d/sweep/runner.py:363-372` and
  `src/geodispbench3d/sweep/rescore.py:395-402`.
- **Evidence / impact:** Two byte-identical copies of "render a callable as
  `module:qualname`". The string is used as a provenance/cache key (it lands in
  `ParserProvenance.fn` and the predictions-cache path), so the two copies *must* stay
  identical or a rescore would compute a different cache key than the original sweep.
- **Fix sketch:** Promote a single `parser_fn_repr` into `sweep/trial_record.py`
  (alongside the `ParserProvenance` dataclass that consumes it) and import it in both
  modules. STRUCTURE.md explicitly nominates `trial_record.py` as the home for shared
  provenance/record helpers.
- **Severity:** Minor · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-02, AUDIT-04.

### AUDIT-01 — Bugs, Bloat, Dead Code & Duplication

#### F-04 — Parquet results store is O(n²) read-modify-write and not concurrency-safe

- **Location:** `src/geodispbench3d/results/store.py:30-40` (`append_record_rows`).
- **Evidence / impact:** Every append does `read_parquet(whole file) → concat →
  to_parquet(whole file)`. For a sweep emitting record rows per trial × case ×
  record-metric this is quadratic total work, and two processes appending to the same
  parquet (parallel sweeps sharing a results path) lose rows last-writer-wins. Confirmed
  by reading: there is no append-mode write, no locking, no partitioning. Corroborated
  by coverage (`store.py` 44%, the create/append path uncovered — EVIDENCE.md §2).
- **Fix sketch:** Write a partitioned dataset (one parquet fragment per trial/pass under
  a directory) or buffer rows and flush once at end-of-sweep; readers already glob /
  duckdb-query so a directory dataset is transparent.
- **Severity:** Major · **Disposition:** defer (D-06 names "partitioned parquet" as
  out-of-milestone v2 work; single-threaded today so the race is latent) ·
  **Maps to:** AUDIT-01, AUDIT-04.

#### F-05 — Cross-case mean aggregation silently hides partial trial failures

- **Location:** `src/geodispbench3d/sweep/runner.py:334-346` (`_evaluate_across_cases`).
- **Evidence / impact:** When a dataset has multiple cases, the objective reported to
  Ax is the NaN-ignoring mean of each scalar across cases (`finite = [v for v in values
  if … not isnan]`). A trial whose parser fails (NaN) on some cases but succeeds on
  others is scored from the surviving subset — Ax sees an optimistically biased
  objective and steers the search toward parameter regions that actually fail on the
  dropped cases. No coverage count is surfaced.
- **Fix sketch:** Track per-trial case coverage; either penalize missing cases, refuse
  to complete the trial below a coverage threshold, or at minimum emit the
  finite-case-count alongside the aggregated objective so the degradation is visible.
- **Severity:** Major · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-06 — `run --rescore` exit code conflates "pre-existing failed trial" with "rescore error"

- **Location:** `src/geodispbench3d/cli.py:214` (`return 0 if summary.succeeded ==
  summary.total else 1`), `src/geodispbench3d/sweep/rescore.py:106-128` (`total`
  increments for every run dir; `skipped_failed` covers dirs whose original
  `status != "success"`).
- **Evidence / impact:** `total` counts run dirs skipped because the *original* trial
  failed, but `succeeded` only counts freshly-scored dirs, so any sweep containing at
  least one failed trial makes a subsequent (perfectly successful) `--rescore` exit
  non-zero. A CI/automation caller cannot distinguish "re-scoring broke" from "an old
  trial had failed". Confirmed by reading the counter arithmetic.
- **Fix sketch:** Base the exit code on `parser_misses` / genuine rescore errors
  (`summary.parser_misses`), not on the presence of pre-existing `skipped_failed`
  trials. (Same class as the `analyze` exit-code logic at `cli.py:256`.)
- **Severity:** Major · **Disposition:** route-forward → **Phase 3** (CLI hardening
  success-criterion 1: documented non-zero exit codes) · **Maps to:** AUDIT-01,
  AUDIT-03, AUDIT-04.

#### F-07 — `stdout_json` output collection is a bottom-up "first `{`-line" heuristic *(D-07 seed #4)*

- **Location:** `src/geodispbench3d/tool/cli_adapter.py:190-201` (`_collect_outputs`).
- **Evidence / impact:** With `outputs_from="stdout_json"` (the adapter default,
  `cli_adapter.py:81`) the adapter scans stdout *in reverse* and parses the first line
  that `startswith("{")` as the entire result payload. Any tool that prints a
  JSON-object-looking line *after* its real payload (a debug dump, a progress line, a
  warning rendered as JSON) silently overrides the true result. Order-sensitive +
  silent = a correctness landmine, and it is the design-sensibility seed #4 (a heuristic
  standing in for a contract). The region is uncovered (coverage 60%, lines 190-223 —
  EVIDENCE.md §2).
- **Fix sketch:** Require a sentinel prefix (e.g. `GEODISPBENCH3D_RESULT: {…}`) or a
  dedicated results file rather than scraping stdout; until then document `outputs_from:
  glob` as the recommended mode.
- **Severity:** Major · **Disposition:** route-forward → **Phase 3** (`CliToolAdapter`
  subprocess contract: "missing output files … surface as clear failures, not silent
  data corruption") · **Maps to:** AUDIT-01, AUDIT-03, D-07, AUDIT-04.

#### F-08 — Pervasive broad `except Exception` that only `logger.debug(...)` and continues

- **Location:** `src/geodispbench3d/sweep/runner.py:61, 295, 324, 354`;
  `src/geodispbench3d/sweep/rescore.py:257, 295, 310`;
  `src/geodispbench3d/sweep/evaluation.py:89, 177`;
  `src/geodispbench3d/results/predictions_cache.py:120` (`read_prediction` → `None`);
  `src/geodispbench3d/sweep/trial_record.py:89` (`load_trial_record` → `{}`).
- **Evidence / impact:** Non-fatal side effects (provenance stamping, prediction-cache
  writes, audit-log appends, trial-log dir creation, summary read-back) swallow *all*
  exceptions at debug level. The fail-soft intent is sound and matches CONVENTIONS, but
  the catches are un-narrowed and untested (several tagged `# pragma: no cover -
  defensive`), so a real `OSError`/`json.JSONDecodeError`/schema drift becomes
  invisible: a sweep can complete "successfully" while silently dropping provenance,
  cache entries, or whole metric values, corrupting downstream `--rescore`/`analyze`/
  dashboard output with no surfaced error.
- **Fix sketch:** Narrow to expected types (`OSError`, `json.JSONDecodeError`,
  `ImportError`), promote to `WARNING` with a per-pass failure counter, and surface an
  aggregate "N non-fatal failures" line in each CLI summary so silent degradation is at
  least countable. Keep the fail-soft control flow.
- **Severity:** Major · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-09 — Deprecated `datetime.utcnow()` (5 sites) producing misleading naive-`+"Z"` timestamps

- **Location:** `src/geodispbench3d/sweep/trial_record.py:272` (`_utcnow`);
  `src/geodispbench3d/sweep/rescore.py:304` (`rescored_at`), `:406` (`_utcnow_compact`);
  `src/geodispbench3d/analysis/runner.py:173` (`_utcnow_compact`);
  `src/geodispbench3d/results/predictions_cache.py:97` (`cached_at`).
- **Evidence / impact:** `datetime.utcnow()` is deprecated on 3.12 (CI's Python) and
  the project targets `requires-python ~=3.11`. Each call produces a *naive* datetime
  with a manually appended `"Z"`, which misrepresents a naive timestamp as UTC-aware.
  Corroborated: the test suite emits `utcnow()` DeprecationWarnings from
  `predictions_cache.py:97`, `rescore.py:304/406` (EVIDENCE.md §2 side-evidence).
- **Fix sketch:** Replace with `datetime.now(UTC)` and format via `.isoformat()` so the
  offset is real; drop the hand-appended `"Z"`.
- **Severity:** Major · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-10 — Lazy imports inside the per-case hot loop

- **Location:** `src/geodispbench3d/sweep/runner.py:232-236` (`trial_record`
  provenance imports), `:280-282` (`dataclasses.asdict` + `update_trial_record`),
  `:308` (`predictions_cache.write_prediction`), `:339` (`import math`).
- **Evidence / impact:** `_evaluate_across_cases` imports modules inside the loop body
  rather than at module top. Runtime cost is negligible (imports are cached) but it
  obscures the dependency graph and hints at a circular-import workaround that
  ARCHITECTURE.md says does not actually exist (the graph is acyclic).
- **Fix sketch:** Hoist these to module-level imports; if any genuinely dodges a cycle,
  document the cycle in a comment instead of hiding it.
- **Severity:** Minor · **Disposition:** fix (Phase 2, trivial) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-11 — `_ = asdict` lint-suppression hack on a dead import *(D-07 seed #3)*

- **Location:** `src/geodispbench3d/sweep/rescore.py:27` (`from dataclasses import
  asdict, dataclass`) and `:409-410` (`# Suppress an unused-import warning for asdict;
  kept for future expansion.` / `_ = asdict`).
- **Evidence / impact:** `asdict` is imported but never called in `rescore.py`; the
  module keeps it alive solely to silence the linter via `_ = asdict`. This is the
  design-sensibility seed #3: it trains contributors that the lint gate is negotiable
  and leaves a dead import in place. (Vulture did *not* flag it precisely because the
  `_ = asdict` line makes it look "used" — EVIDENCE.md §1 note.)
- **Fix sketch:** Delete the `asdict` import and the `_ = asdict` line; re-add when a
  real use appears.
- **Severity:** Minor · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-01, D-07, AUDIT-04.

#### F-30 — Declared-but-unread config / schema fields (dead-code leads)

- **Location:** `src/geodispbench3d/suite/loader.py:30-31`
  (`ExecutionConfig.parallel_trials`, `.override_tool_mode` — parsed at `:92-96`, never
  consumed: the runner loop is sequential and no code reads `override_tool_mode`);
  `src/geodispbench3d/dataset/schema.py:53-57` (`CaseSpec.scan_by_epoch` — public-looking
  method with no caller), `:67` (`DatasetSpec.gt_kinds_supported` — parsed, never read);
  `src/geodispbench3d/sweep/trial_record.py:40` (`ToolProvenance.yaml_hash` — written but
  never read back by any consumer); `src/geodispbench3d/tool/loader.py:44`
  (`ToolConfig.outputs_options` — populated, never consumed).
- **Evidence / impact:** Vulture flagged these at 60% confidence (EVIDENCE.md §1);
  manual reading confirms none are read. They are not bugs, but they are bloat /
  misleading surface: `parallel_trials` and `override_tool_mode` advertise capabilities
  the runner does not implement (ARCHITECTURE.md: "parallelism is a future extension").
- **Fix sketch:** Triage per field — delete the genuinely dead (`outputs_options`,
  `yaml_hash` if no provenance consumer is planned, `scan_by_epoch`), or wire the
  forward-compat ones (`parallel_trials`, `override_tool_mode`) behind an explicit
  "not implemented" guard so the config does not silently no-op.
- **Severity:** Minor · **Disposition:** fix (Phase 2; per-field triage, some may be
  accept-as-forward-compat) · **Maps to:** AUDIT-01, AUDIT-04.

### Design Sensibility (D-07)

A first-class category for code that is *functional but not really sensible* — awkward,
non-idiomatic, or questionable constructions judged against CONVENTIONS.md. The four
D-07 seeds are formalized here as **F-12** and **F-13** (below) plus **F-11** (`_ =
asdict` hack) and **F-07** (stdout heuristic) cross-listed above.

#### F-12 — 220-line field-by-field `build_app_config_from_parameters` *(D-07 seed #1)*

- **Location:** `src/geodispbench3d_iof3d/adapter.py:128-347`.
- **Evidence / impact:** A single function reconstructs `AppConfig`/`FlowSettings`/
  `ImgRes`/`Angle` field-by-field (~70 `_resolve(...)`/`_resolve_alias(...)` calls),
  mirroring a legacy `iof3D_analysis.ax.sweep.apply_parameters`. It is the worst
  hotspot on every mechanical measure (ruff C901 = 22, the single highest; radon MI =
  26.21, the lowest file; 17%/236-line coverage — EVIDENCE.md §4/§2). Beyond size, the
  *shape* is the problem: any rename in iof3D's config dataclasses breaks it silently,
  and it **silently coerces invalid sweep parameters back to base** (e.g. an
  `opencv_detector` outside `{sift,kaze}` at `:189-190`, a `ratio_test` outside `(0,1)`
  at `:208-209`), so a malformed sweep value is masked rather than reported — Ax then
  optimizes over a parameter that had no effect.
- **Fix sketch:** Drive the mapping from a declarative parameter→field table instead of
  hand-written branches; and assert/raise on unknown/out-of-range parameter values
  rather than coercing to base. Refactor one field group at a time against the iof3d
  test suite (never blind).
- **Severity:** Major · **Disposition:** defer (deeply iof3D-coupled and CI-untestable
  today — see F-23; a *guarded partial* — raising on invalid params — is a reasonable
  Phase 2 stretch) · **Maps to:** AUDIT-01, D-07, AUDIT-04.

#### F-13 — `getattr(...) or getattr(...lambda...)` provenance lookup chain *(D-07 seed #2)*

- **Location:** `src/geodispbench3d/sweep/runner.py:238-241`.
- **Evidence / impact:** `tool_yaml = getattr(suite.tool, "source_path", None) or
  getattr(suite.tool.raw, "get", lambda *_: None)("__source_path__")` — a two-tier
  `getattr` chain with a throwaway-lambda fallback that silently yields `None`, which
  then flows into `ToolProvenance.from_yaml_path` and produces provenance with a null
  `yaml_path`/`yaml_hash`. This is a direct symptom of F-01 (untyped suite): `ToolConfig`
  *already* has a typed `source_path: Path | None` field (`tool/loader.py:48`), so the
  entire `or getattr(... raw ... lambda ...)` tail is dead defensiveness against a type
  the code actually controls.
- **Fix sketch:** With F-01's typed `SuiteConfig`, replace the whole expression with
  `suite.tool.source_path`. No lambda, no `raw` dict probing.
- **Severity:** Major · **Disposition:** fix (Phase 2; folds into F-01) ·
  **Maps to:** AUDIT-02, D-07, AUDIT-04.

### Fragility, Performance & Dependencies-at-Risk

#### F-14 — Ax API compatibility shims via runtime signature introspection

- **Location:** `src/geodispbench3d/sweep/runner.py:17-28` (import fallback),
  `:72-136` (`_create_experiment` probes `inspect.signature` for `parameters` /
  `parameter_definitions` / `search_space`, then `objective_name` / `objectives` /
  `optimization_config`), `:375-409` (`_normalize_trial_data` isinstance/`hasattr`
  probing of `get_next_trial()`'s return).
- **Evidence / impact:** The runner guesses the shape of a pinned-but-pre-2.0 Ax
  (`ax-platform ~= 1.1`) at runtime. A minor Ax bump can change those shapes and the
  shims may *mis-map* kwargs rather than fail loudly. `runner.py` has 13% coverage
  (EVIDENCE.md §2) so nothing catches a mis-map. `_create_experiment` is also a
  complexity hotspot (ruff C901 = 14).
- **Fix sketch:** Pin Ax to the exact tested version and record a fixture asserting the
  real `create_experiment`/`get_next_trial` shapes so a version bump fails a test instead
  of silently mis-mapping; budget the full Ax 2.x migration separately.
- **Severity:** Major · **Disposition:** defer (D-06 names "Ax 2.x migration" as
  out-of-milestone; the cheap in-milestone hardening — exact pin + shape fixture — is
  worth surfacing to Phase 2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-15 — iof3D adapter coupling to upstream internal dataclasses

- **Location:** `src/geodispbench3d_iof3d/adapter.py:19-27` (the only `iof3D.*` /
  `pchandler` / `pc2img` import site), `:128-347` (the field-by-field translation, see F-12);
  `src/geodispbench3d_iof3d/factory.py:18` (`from iof3D.v2.cli_hydra import _build_app_config`
  — a *private* upstream function).
- **Evidence / impact:** The adapter is the single seam to iof3D's *internal*
  `AppConfig`/`FlowSettings`/`ImgRes`/`Angle` and to a private `_build_app_config`. Any
  upstream rename breaks the adapter, and because the iof3d CI job is disabled (F-23) the
  break surfaces only on a manual local run.
- **Fix sketch:** Prefer iof3D's public API surface where one exists; stop importing the
  underscore-private `_build_app_config` (request/await a public builder upstream). Pin
  the iof3D version the adapter is validated against.
- **Severity:** Major · **Disposition:** defer (gated on iof3D publishability — Phase 4
  open question) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-16 — F2S3 driven via `subprocess` against a separate `conda run` env; unverified end-to-end

- **Location:** `src/geodispbench3d_f2s3/conf/tool/f2s3.yaml:13`
  (`entry: conda run -n f2s3-dev312 f2s3`), `:29-30` (absolute scratch source/target
  cloud paths), `:51` (absolute hashed run-dir root);
  `src/geodispbench3d/tool/cli_adapter.py:98-150` (subprocess invocation + failure
  handling); `src/geodispbench3d_f2s3/output_parser.py` (parses per-tile ASCII; only
  output-shape is tested).
- **Evidence / impact:** The shipped F2S3 tool config hard-codes a `conda run -n
  f2s3-dev312` entry *and* absolute scratch paths. A missing env, missing binary, or
  absent `conda` surfaces only as a generic non-zero exit / `FileNotFoundError` at
  `cli_adapter.py:115-123` — there is no pre-flight check or actionable message. The
  parser tests exercise output-shape only, never a real F2S3 run, so an F2S3
  output-format change is caught at runtime, not in CI.
- **Fix sketch:** (Phase 3) document the subprocess contract and add a binary/env
  pre-flight with a clear remediation message; parameterize the absolute paths out of
  the shipped YAML. (Phase 4) decide the F2S3 packaging story (see F-29).
- **Severity:** Major · **Disposition:** route-forward → **Phase 3** (F2S3 as the
  canonical `CliToolAdapter` showcase + "how to obtain F2S3" note) · **Maps to:**
  AUDIT-03, AUDIT-01, AUDIT-04.

#### F-32 — `CliToolAdapter` subprocess has no timeout; a hung tool stalls the sweep indefinitely

- **Location:** `src/geodispbench3d/tool/cli_adapter.py:107-114` (`subprocess.run(argv,
  capture_output=True, text=True, env=self._env, check=False)` — no `timeout=` argument).
- **Evidence / impact:** A tool that hangs (deadlock, blocking on stdin, GPU stall)
  blocks `run_trial` forever; the sweep cannot advance and Ax never gets its next trial.
  There is no watchdog and no per-trial wall-clock cap. Surfaced by the manual review of
  the AUDIT-03 `CliToolAdapter` surface (not in CONCERNS.md).
- **Fix sketch:** Add a configurable `timeout` to `CliInvocationSpec`/the adapter and
  translate `subprocess.TimeoutExpired` into a `success=False` trial with
  `error="timeout"`, mirroring the existing `FileNotFoundError` path.
- **Severity:** Major · **Disposition:** route-forward → **Phase 3** (`CliToolAdapter`
  contract criterion explicitly lists *timeout*) · **Maps to:** AUDIT-03, AUDIT-04.

#### F-17 — In-memory full-cloud load + merge in both output parsers

- **Location:** `src/geodispbench3d_f2s3/output_parser.py:126-145` (`_load_and_merge_tiles`
  → `PointCloudData.merge(*pcds)`), `src/geodispbench3d_iof3d/output_parser.py:108-122`.
- **Evidence / impact:** Both parsers materialize every tile/leaf cloud and merge into
  one in-memory `PointCloudData` before sampling within a fixed radius of each GT label.
  Sampling only needs points near each GT point, so the full merge is wasted memory for
  large outputs. Not a correctness issue; relevant only at scale.
- **Fix sketch:** Spatially pre-filter per tile (sphere filter before merge) or build a
  KD-tree index; only worth it for very large outputs.
- **Severity:** Minor · **Disposition:** defer (scale-only; v2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-18 — Only one ground-truth kind is actually implemented

- **Location:** `src/geodispbench3d/dataset/ground_truth.py:63-73` (`load_ground_truth`
  raises `NotImplementedError` for any unregistered kind), `:118` (only
  `point_displacements` is registered); the module docstring (`:1-7`) and
  `GroundTruthSpec` (`dataset/schema.py:28-42`) advertise `dense_flow`,
  `transformation_matrix`, `segmentation_mask` as if available.
- **Evidence / impact:** The registry design is sound and extensible (downstream
  `register_gt_loader`), so the *behavior* is acceptable by design. The defect is the
  **mismatch between advertised and implemented kinds** — a user reading the docstring
  expects four kinds and gets a runtime `NotImplementedError`.
- **Fix sketch:** Reconcile the docstring/schema comments to state that only
  `point_displacements` ships and the rest are extension points; no behavior change required.
- **Severity:** Minor · **Disposition:** accept (registry is by-design extensible;
  recommend the doc clarification above) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-19 — No sweep checkpoint / resume

- **Location:** `src/geodispbench3d/sweep/runner.py:69` (the `AxClient` lives only in
  the `AxSweepRunner` instance), `:200-221` (`run_with_suite` runs to completion in one
  process).
- **Evidence / impact:** A crash mid-sweep loses all Ax optimization state (surrogate
  model + trial history). Only per-trial run dirs / parquet rows survive, which
  `--rescore` can re-evaluate but cannot resume the Bayesian search from.
- **Fix sketch:** Persist an `AxClient` JSON snapshot between trials and reload on restart.
- **Severity:** Major · **Disposition:** defer (a v2 capability, not a publish-blocker)
  · **Maps to:** AUDIT-01, AUDIT-04.

### Test-Coverage Gaps (re-verified against this env's run)

> **Coverage honesty (carried from Plan 01):** this audit's coverage numbers were
> captured in the iof3D dev env where the plugin suites *ran* (32 passed, 0 skipped).
> In CI / a lean framework-only env, `tests/iof3d` + `tests/f2s3` self-skip
> (`importorskip`) and the iof3d CI job is disabled, so the plugin packages would read
> 0%/low there because the **suite is unexercised, not because the code is untested**.

#### F-20 — Sweep orchestration (`runner.py`) has no direct test

- **Location:** `src/geodispbench3d/sweep/runner.py` (the whole module; coverage **13%**,
  151/174 stmts missed — EVIDENCE.md §2).
- **Evidence / impact:** The most behavior-dense, most Ax-API-exposed module — Ax shims,
  `run_with_suite`, cross-case aggregation (F-05), provenance stamping, prediction
  caching — has no direct test. A broken kwarg mapping (F-14) or aggregation regression
  (F-05) passes CI today.
- **Fix sketch:** Add direct tests with a fake `AxClient` covering the trial loop,
  `_normalize_trial_data`, and `_evaluate_across_cases` aggregation (incl. the partial-
  failure path of F-05).
- **Severity:** Major · **Disposition:** fix (Phase 2 — its success criterion is a clean
  full pytest suite) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-21 — Parquet store (`store.py`) untested

- **Location:** `src/geodispbench3d/results/store.py` (coverage **44%**; the
  create/append read-modify-write path uncovered — EVIDENCE.md §2).
- **Evidence / impact:** The persistence layer feeding the dashboard and `analyze` is
  unverified, including the empty-rows short-circuit (`:24-25`) and the
  create-vs-append branch (`:35-39`) that F-04 will rewrite.
- **Fix sketch:** Add unit tests for create, append, and empty-rows behavior; they also
  pin the contract before any F-04 partitioning change.
- **Severity:** Major · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-22 — Evaluation glue (`evaluation.py`) + a few modules only *indirectly* covered

- **Location:** `src/geodispbench3d/sweep/evaluation.py` (coverage **80%**, not zero —
  exercised via rescore/analyze tests; still-missing: the parser-failure→`None` path
  `:89-93`, objective-coercion `:118-122`, `_invoke_metric` failure `:177-179`); plus
  `analysis/runner.py`, `tool/callable_adapter.py`, `metrics/registry.py` with no
  *direct* test reference.
- **Evidence / impact:** **Re-verification correction to CONCERNS.md:** CONCERNS lists
  `evaluation.py` as "untested"; the measured 80% (EVIDENCE.md §2) shows it is
  indirectly exercised. The real gap is the *failure paths* (parser raises → `None`,
  metric raises → skipped), which are exactly the silent-degradation surfaces of F-08.
- **Fix sketch:** Add direct unit tests for `evaluate_trial`'s `needs`-based kwarg
  assembly, gt-kind filtering, and the two failure→skip paths; add smoke tests for the
  three indirectly-covered modules.
- **Severity:** Minor · **Disposition:** fix (Phase 2) · **Maps to:** AUDIT-01, AUDIT-04.

#### F-23 — iof3D adapter is effectively untested because its CI job is disabled

- **Location:** `.github/workflows/ci.yml:60` (`{ name: iof3d, … enabled: "false" }`);
  `src/geodispbench3d_iof3d/adapter.py` (580 lines; `tests/iof3d` self-skips via
  `importorskip("iof3D")`).
- **Evidence / impact:** The largest, most upstream-coupled module (F-12, F-15) is
  exercised by nothing CI can run, because iof3D is not on a reachable package index.
  The disabled job is correct *given* that constraint, but it means publish confidence
  for the iof3d extra rests on manual local runs only.
- **Fix sketch:** Gated on Phase 4 (publish iof3D / resolve the extra); then flip the CI
  matrix flag to `"true"` in Phase 5.
- **Severity:** Major · **Disposition:** route-forward → **Phase 5** (CI), gated on
  **Phase 4** (iof3D publishability) · **Maps to:** AUDIT-03, AUDIT-01, AUDIT-04.

### Security (by-design surfaces)

#### F-24 — Arbitrary code execution from suite/tool/metrics/analysis YAML (by design)

- **Location:** `src/geodispbench3d/tool/loader.py:152-189` (`_build_custom_adapter`
  instantiates an arbitrary class with YAML `init_kwargs`; `_build_factory_adapter`
  calls an arbitrary function), `:213-221` (`_resolve_callable`);
  `src/geodispbench3d/metrics/registry.py:63-73` (`resolve_metric_fn`);
  `src/geodispbench3d/sweep/rescore.py:384-392` (`_resolve_dotted`).
- **Evidence / impact:** Tool/metric/parser callables and adapter classes are resolved
  from `"package.module:attr"` strings in YAML and imported + called. This is intentional
  plugin behavior for *trusted local* configs (the project has no network/untrusted-
  config path — INTEGRATIONS.md confirms no remote services).
- **Fix sketch:** No code change. Document in the YAML-schema reference that suite YAML
  is executable and must be treated as trusted code; if external configs ever become a
  use case, add an allowlist of importable module prefixes.
- **Severity:** Minor · **Disposition:** accept (by-design; document the trust
  assumption) · **Maps to:** AUDIT-04. *(Threat register: T-01-02 accept.)*

#### F-25 — Subprocess invocation from YAML `entry` (already reasonable — positive control)

- **Location:** `src/geodispbench3d/tool/cli_adapter.py:108-114` (`subprocess.run`,
  `check=False`, **no `shell=True`**), `:167-185` (`_build_argv` via `shlex.split`),
  `:246-269` (`_render_parameters` passes values as separate argv elements).
- **Evidence / impact:** `argv[0]`/`extra_args` come from tool YAML and parameter values
  are interpolated, but `shell=False` + `shlex.split` + per-element argv means there is
  no shell-metacharacter expansion. This is the *correct* posture; recorded as a positive
  control, not a defect.
- **Fix sketch:** Keep `shell=False`. If config provenance ever loosens, validate that
  param names cannot inject leading `--` from untrusted sources.
- **Severity:** Minor · **Disposition:** accept (already safe) · **Maps to:** AUDIT-03, AUDIT-04.

### Packaging, Licensing & CI (route-forward)

#### F-26 — `Private :: Do Not Upload` classifier blocks (and contradicts) public release

- **Location:** `pyproject.toml:21-23`.
- **Evidence / impact:** PyPI rejects any package whose classifiers begin with
  `Private ::`. The classifier is also a semantic contradiction with the milestone goal
  (public PyPI release). Until removed, `twine`/upload fails outright — a hard
  publish-blocker.
- **Fix sketch:** Remove the classifier (Phase 4); the inline comment already flags it.
- **Severity:** Blocker · **Disposition:** route-forward → **Phase 4** · **Maps to:** AUDIT-04.

#### F-27 — README declares "Proprietary" while `LICENSE` is BSD-3-Clause

- **Location:** `README.md:80-82` ("## License" / "Proprietary — see `LICENSE`.") vs
  `LICENSE` (BSD 3-Clause, ETH Zurich) and `pyproject.toml:10`
  (`license = { text = "BSD-3-Clause" }`).
- **Evidence / impact:** The README misrepresents the license of an about-to-be-public
  package as proprietary, directly contradicting the actual BSD-3-Clause `LICENSE` and
  the `pyproject` metadata. Shipping this is a licensing-integrity blocker.
- **Fix sketch:** Rewrite the README License section to state BSD-3-Clause and point to
  `LICENSE` (Phase 4).
- **Severity:** Blocker · **Disposition:** route-forward → **Phase 4** · **Maps to:** AUDIT-04.

#### F-28 — iof3d CI test job hard-disabled

- **Location:** `.github/workflows/ci.yml:58-60` (matrix `iof3d … enabled: "false"`),
  `:67-84` (the `if: matrix.job.enabled == 'true'` guards short-circuit to an echo).
- **Evidence / impact:** See F-23 for the testing consequence. As a CI/release concern,
  the disabled job means the published iof3d extra has zero automated verification. The
  flag flip is owned by the CI phase but gated on iof3D being installable.
- **Fix sketch:** Phase 5 flips the flag once Phase 4 makes iof3D reachable.
- **Severity:** Major · **Disposition:** route-forward → **Phase 5** (gated on Phase 4)
  · **Maps to:** AUDIT-04.

#### F-29 — `f2s3` extra is empty and the F2S3 packaging story is undecided

- **Location:** `pyproject.toml:56-59` (`f2s3 = []` with a comment noting F2S3 is *also*
  installable as a library), interacting with F-16's `conda run` subprocess default.
- **Evidence / impact:** The shipped F2S3 path assumes an externally-managed conda env +
  binary; the empty extra means `pip install geodispbench3d[f2s3]` installs nothing
  actionable. Whether to ship an in-process F2S3 adapter (removing the subprocess/env
  coupling) is an open Phase 4 question (STATE.md open questions).
- **Fix sketch:** Phase 4 decides: keep subprocess-only (document clearly) vs. add the
  F2S3 Python lib to the extra and an in-process adapter.
- **Severity:** Minor · **Disposition:** route-forward → **Phase 4** · **Maps to:** AUDIT-04.

#### F-31 — Legacy `iof3d-ax` Hydra CLI is unexercised and duplicates parameter-grammar logic

- **Location:** `src/geodispbench3d_iof3d/cli.py:9-134` (entire module, coverage **0%**
  even in this env — EVIDENCE.md §2), `:29` (`_collect_run_kwargs`, ruff C901 = 11),
  declared as a second console script in `pyproject.toml:40`.
- **Evidence / impact:** A whole second entry point (`iof3d-ax`) ships publicly, is
  never imported by any test, and carries its own complexity hotspot. STATE.md lists
  "ship `geodispbench3d_iof3d` + `iof3d-ax` publicly, or exclude" as an open Phase 4
  question — so this is a packaging-scope decision, not an in-milestone fix.
- **Fix sketch:** Phase 4 decides include-vs-exclude; if kept, add at least a smoke test.
- **Severity:** Minor · **Disposition:** route-forward → **Phase 4** · **Maps to:**
  AUDIT-01, AUDIT-04.

---

## Appendix A — CONCERNS Traceability

One row per existing `.planning/codebase/CONCERNS.md` finding, mapping it to its
carried-forward `F-NN` or to a `superseded` / `resolved` / `false-positive` mark with a
reason. This is the machine-verifiable evidence that REPORT.md is a superset of
CONCERNS.md (D-10) — no prior finding was silently dropped.

| CONCERNS.md finding (section → title) | Maps to | Status | Reason / note |
|---------------------------------------|---------|--------|---------------|
| Tech Debt → Pervasive broad `except Exception` swallowing | F-08 | carried-forward | Re-verified at all cited sites; extended with a per-pass failure-counter fix sketch. |
| Tech Debt → `suite`/`config` passed as untyped `Any`/`object` | F-01 | carried-forward | Confirmed 12 `type: ignore` in cli.py + `suite: Any` in runner.py. |
| Tech Debt → Deprecated `datetime.utcnow()` | F-09 | carried-forward | All 5 sites confirmed; DeprecationWarnings corroborated by EVIDENCE.md §2. |
| Tech Debt → Dead-code suppression hack (`_ = asdict`) | F-11 | carried-forward | Confirmed rescore.py:27 + :409-410; also formalized as D-07 seed #3. |
| Tech Debt → Lazy imports inside hot loops | F-10 | carried-forward | Confirmed runner.py:232-282,308,339. |
| Known Bugs → Parquet store O(n^2) and not concurrency-safe | F-04 | carried-forward | Confirmed store.py:30-40 read-modify-write; no locking/partitioning. |
| Known Bugs → Cross-case mean aggregation hides partial failures | F-05 | carried-forward | Confirmed runner.py:334-346 NaN-ignoring mean. |
| Known Bugs → `run --rescore` exit code conflates failed trial / rescore error | F-06 | carried-forward | Confirmed cli.py:214 + rescore.py counter arithmetic; routed to Phase 3. |
| Known Bugs → stdout-JSON output collection heuristic / order-sensitive | F-07 | carried-forward | Confirmed cli_adapter.py:190-201 reverse-scan; also D-07 seed #4. |
| Security → Arbitrary code execution from YAML (by design) | F-24 | carried-forward | Confirmed loader/registry/rescore resolve sites; accept + document. |
| Security → Subprocess invocation from YAML `entry` | F-25 | carried-forward | Confirmed `shell=False` + `shlex.split`; recorded as positive control. |
| Security → Path-traversal guard on predictions cache (positive note) | F-08 | resolved | `_safe_segment` (predictions_cache.py:155-163) confirmed effective; residual silent corrupt-cache->miss folded into F-08. No standalone defect. |
| Performance → Full parquet rewrite per append | F-04 | carried-forward | Same root cause as the O(n^2) bug; consolidated into F-04. |
| Performance → In-memory tile load + merge in parsers | F-17 | carried-forward | Confirmed both parsers' merge-before-sample. |
| Fragile → Ax API compatibility shims | F-14 | carried-forward | Confirmed runner.py:17-28,72-136,375-409 introspection. |
| Fragile → iof3D adapter coupling to upstream dataclasses | F-15 | carried-forward | Confirmed sole iof3D import site + private `_build_app_config` use. |
| Fragile → Provenance lookup chain in the runner | F-13 | carried-forward | Confirmed runner.py:238-241 getattr-or-lambda chain; also D-07 seed #2. |
| Scaling → Single-file parquet results store | F-04 | carried-forward | Same store.py:30-40 limit; consolidated into F-04. |
| Scaling → No sweep checkpoint / resume | F-19 | carried-forward | Confirmed AxClient is in-memory only. |
| Dependencies at Risk → iof3D not on a reachable index | F-23 / F-28 | carried-forward | Confirmed CI job disabled (ci.yml:60); split into testing (F-23) + CI (F-28). |
| Dependencies at Risk → ax-platform ~1.1 pre-2.0 unstable API | F-14 | carried-forward | Same shim cluster; consolidated into F-14. |
| Dependencies at Risk → F2S3 external binary via subprocess | F-16 | carried-forward | Confirmed `conda run -n f2s3-dev312` entry + untested e2e. |
| Missing Features → Only one ground-truth kind implemented | F-18 | carried-forward | Confirmed only `point_displacements` registered; reframed as doc-vs-impl mismatch. |
| Missing Features → No sweep checkpoint/resume | F-19 | carried-forward | Duplicate of the Scaling entry; single F-19. |
| Test Coverage → Sweep orchestration (`runner.py`) untested | F-20 | carried-forward | Confirmed 13% coverage. |
| Test Coverage → Metric dispatch glue (`evaluation.py`) untested | F-22 | superseded | Re-verification correction: measured 80% (indirectly exercised), not "untested"; F-22 re-scopes the gap to the failure paths. |
| Test Coverage → Parquet store (`store.py`) untested | F-21 | carried-forward | Confirmed 44% coverage. |
| Test Coverage → iof3D adapter present but skipped in CI | F-23 | carried-forward | Confirmed job disabled + `importorskip`. |
| Test Coverage → Other modules with no direct test reference | F-22 | carried-forward | analysis/runner.py, callable_adapter.py, metrics/registry.py folded into F-22's smoke-test sketch. |

*New findings beyond CONCERNS.md (surfaced by this review): F-02 (SweepParameter
coercion x3), F-03 (`_parser_fn_repr` x2), F-12 (220-line `build_app_config`), F-30
(declared-but-unread fields), F-32 (no subprocess timeout), F-26 (`Private` classifier),
F-27 (README/LICENSE mismatch), F-29 (empty `f2s3` extra), F-31 (`iof3d-ax` legacy CLI).*
