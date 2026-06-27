# Phase 3: CLI Hardening - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make all three CLI surfaces fail **predictably and visibly** instead of silently,
and showcase F2S3 as the canonical `CliToolAdapter` example. Concretely, this
phase turns the four audit findings the report **routed to Phase 3** into landed,
tested behavior, plus the F2S3 documentation/showcase:

- **F-06** — `rescore`/`analyze` exit codes conflate a *pre-existing failed trial*
  (`skipped_failed`) with a *genuine rescore error* (`cli.py:214`, `:282`).
- **F-07** — `outputs_from="stdout_json"` reverse-scans stdout and treats the last
  `{`-line as the result payload — silent data corruption (`cli_adapter.py:190-201`).
- **F-16** — F2S3 `conda run` has no env/binary preflight; a missing env surfaces only
  as a generic `FileNotFoundError` (`f2s3.yaml:13`, `cli_adapter.py:115-123`).
- **F-32** — `subprocess.run` has no timeout, so a hung tool stalls the whole sweep
  (`cli_adapter.py:107-114`).

Satisfies requirements **CLI-01…CLI-05** and ROADMAP Phase 3 success criteria 1–5.

**In scope:** argument validation + documented exit-code taxonomy; the
`CliToolAdapter` subprocess contract (nonzero exit, missing outputs, timeout);
F2S3 env/binary preflight + "how to obtain" doc; tests for all of the above.

**Explicitly NOT in this phase:** new adapter capabilities; parallel execution
(EXEC-01, v2); the deferred/accepted audit findings (F-04, F-12, F-14, F-15, F-17,
F-19; F-18/F-24/F-25); licensing/packaging (F-26/F-27/F-29/F-31 → Phase 4); CI
(F-23/F-28 → Phase 5). The interactive timeout watchdog is a **deferred seed** (below).

</domain>

<decisions>
## Implementation Decisions

### F2S3 showcase & execution model (CLI-05, F-16)
- **D-01 (execution model):** **Document both, default `conda run`.** Ship
  `entry: conda run -n f2s3-dev312 f2s3` as the canonical/default entry (keeps F2S3 a
  faithful subprocess + env-isolation showcase); the docs additionally describe the
  in-env "`f2s3` on `PATH`" override as a supported alternative for users who already
  have the binary in their active env.
- **D-02 (preflight location):** **Generic adapter check + YAML remediation hint.**
  `CliToolAdapter` performs a generic preflight — is the entry's leading executable
  resolvable, and for a `conda run -n ENV …` entry does `conda`/the env resolve — and
  raises a clear, structured error. The tool config gains an **optional**
  `remediation` / `help_url` field so F2S3 (and any tool) can inject a targeted
  "how to obtain / how to set up the env" hint into that error. Reusable for every
  CLI tool; F2S3 supplies the specific message.
- **D-03 (how-to-obtain source):** The "how to obtain F2S3" note (CLI-05) references
  the **gseg-ethz F2S3 repo**:
  `https://github.com/gseg-ethz/F2S3_pc_deformation_monitoring`. It lives in
  `docs/tools/f2s3.md` and is echoed by the YAML `remediation` hint. The doc points
  at the repo's own README for build/env setup (env name `f2s3-dev312`); no build
  steps are duplicated into our docs.

### Subprocess timeout (F-32)
- **D-04 (timeout config):** **Opt-in `execution.timeout_seconds`** in the tool
  config, **plus a `--timeout` flag on `run`** that overrides per-invocation. Unset =
  no timeout (today's behavior, now explicit + documented). A heavy point-cloud
  benchmark must never surprise-kill a valid long trial, and the tool author knows
  their own runtime ceiling. The `--timeout` flag is one of the new argument surfaces
  the Area-4 validation + tests must cover.
- **D-05 (timeout behavior):** On expiry: **kill the subprocess, record a non-fatal
  `timeout` failure** (`success=False`, `error="timeout"`), report it to Ax as a
  failed trial so the sweep continues, log a warning, and bump the existing
  "N non-fatal failures" counter. **No interactive prompt and no watchdog thread** —
  reuse the `success=False` / `PassDiagnostics` plumbing already introduced by the
  Phase 2 F-08 work. (`subprocess.run(timeout=…)` raises `TimeoutExpired`, which the
  adapter catches at `cli_adapter.py:106-123` alongside the existing
  `FileNotFoundError` branch.)

### Output-collection contract (F-07)
- **D-06 (deprecate `stdout_json`):** **`glob` becomes the single blessed output
  path; `stdout_json` is deprecated.** Safe: no in-repo CLI tool uses `stdout_json`
  (F2S3 = `glob`; iof3D is an in-process callable, not a CLI tool). **Planner nuance:**
  prefer a deprecation stub that raises a clear *"use `outputs_from: glob`"* error if
  an old YAML still sets `stdout_json`, over a silent hard-remove (pre-public, low cost,
  friendlier migration).
- **D-07 (empty-glob behavior):** When `predictions_glob` is set but matches **zero
  files**, the trial is a **flagged failure** (`success=False`,
  `error="no predictions matched <glob>"`) — nothing to score is data corruption, not
  success. An empty `figures_glob` stays **non-fatal** (figures are auxiliary).

### Exit codes & argument validation (F-06, CLI-01)
- **D-08 (exit-code taxonomy):** **Minimal POSIX `0` / `1` / `2`**, documented as a
  table in the CLI reference. `0` = success; `1` = runtime failure (genuine
  rescore/parser errors, real trial-scoring failures, environment/preflight failures,
  config-load failures — **NOT** pre-existing `skipped_failed`); `2` = usage/argument
  error (argparse-native only). The **F-06 fix**: base the `rescore`/`analyze`
  non-zero code on genuine errors (`parser_misses`), not on the presence of
  `skipped_failed` dirs.
- **D-09 (rescore subcommand split):** **Promote `rescore` to its own subcommand** —
  `geodispbench3d rescore <suite>` — so the four rescore-only flags
  (`--reuse-parser-options`, `--use-prediction-cache`, `--pass-id`, and the rescore
  meaning of `--max-trials`) live on it and argparse **structurally rejects** them on
  `run`. Pre-public is the cheapest moment for this CLI break. **Ripple to handle:**
  `cli.py` argparse + dispatch (today `_cmd_run` branches on `args.rescore`),
  `docs/rescoring-and-analysis.md`, `README.md` (line ~47), `docs/quickstart.md`, and a
  short migration note.

### Preflight timing (F-16)
- **D-10 (fail-fast in `prepare()`):** Implement the preflight in
  `CliToolAdapter.prepare()` — already called once before the trial loop
  (`runner.py:192`, `:251`) — so a missing env/binary raises the structured error +
  remediation (D-02) **before Ax launches trial 0**; the sweep aborts cleanly with
  **exit 1** (environment error, not a usage error). Sweep-path only — `rescore`/
  `analyze` don't invoke the tool, so they need no preflight.

### Config-load & input-path errors (CLI-01)
- **D-11 (clean errors at `main()`):** `main()` wraps load/dispatch in a handler that
  catches `FileNotFoundError` / `ValueError` from the config loaders (`load_suite` et al.,
  `suite/loader.py:91,95,103`), prints the exception message as a clean one-line
  `error: <msg>` (**no traceback**), and exits **1**. Exit `2` stays strictly argparse
  usage. **Optional planner nicety:** a `--traceback` flag (or `--log-level DEBUG`)
  re-exposes the full stack for developers.

### CLI-04 test mechanics
- **D-12 (real stub executable + `main()`-level tests):** Test the hardened behaviors
  with **tiny stub executables** written to `tmp_path` (a sleep-N script to trip the
  timeout; an exit-code-N script for nonzero exit; a script that writes-or-omits output
  files for the glob paths), pointed at by a test `tool.yaml` `entry`. Drive both
  `CliToolAdapter.run_trial` **and** `main(["run", …])` / `main(["rescore", …])`,
  asserting exit codes and clean messages. This exercises the **real**
  `subprocess`/timeout/glob plumbing (timeout is itself a `subprocess.run` mechanic, so
  faithfulness matters). The preflight is tested via a deliberately-missing `entry`. **No
  real `conda` or F2S3 env is required.** There is no `main()`-level CLI test today — this
  is net-new (`tests/core/test_cli.py`), complementing the existing
  `tests/core/test_cli_adapter.py` (which only covers argv building).

### Claude's Discretion
- **Consistency cleanups** (not separately discussed; apply these sensible defaults,
  adjustable by the planner):
  - `_cmd_dashboard` currently returns `2` when streamlit is missing; under the 0/1/2
    taxonomy that's a missing-runtime-dependency error → it should be **exit 1**, not the
    usage code `2`.
  - `list-metrics` on a malformed `metrics.yaml` should route through the same D-11
    clean-error + exit-1 handler instead of returning `0`.
  - `stdout_json` removal form (D-06): stub-with-error vs hard-remove is executor
    judgment, with the deprecation stub preferred.
- **Exact `--timeout` semantics** (e.g. interaction with `execution.timeout_seconds`:
  CLI flag overrides the YAML value) and the precise structured-error message wording are
  planner/executor discretion, subject to the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & the routed-finding contract
- `.planning/phases/01-code-health-audit/REPORT.md` — **the authoritative input.**
  Read the detail sections for **F-06, F-07, F-16, F-32** (each carries location
  `file:line`, evidence/impact, and a fix sketch) plus the **AUDIT-03 CLI-Surface Risk
  Assessment** synthesis (per-surface risks for `cli.py`, `CliToolAdapter`, F2S3
  `conda run`). F-01/F-13 (Phase 2) are the typed-`SuiteConfig` foundation these fixes
  build on.
- `.planning/ROADMAP.md` §"Phase 3: CLI Hardening" — goal + 5 success criteria + the
  (now-resolved) F2S3 in-env-vs-conda-run open question.
- `.planning/REQUIREMENTS.md` §"CLI Hardening" (CLI-01…CLI-05) — the five locked
  requirements; §"Out of Scope" confirms no feature growth.
- `.planning/phases/02-targeted-fixes/02-CONTEXT.md` — Phase 2 decisions this phase
  builds on (D-03 non-fatal-failure counter + CLI summary line; typed `SuiteConfig`).

### F2S3 showcase
- `https://github.com/gseg-ethz/F2S3_pc_deformation_monitoring` — **the gseg-ethz F2S3
  source** the "how to obtain" note (CLI-05 / D-03) must link; see its README for
  build/env (`f2s3-dev312`).
- `src/geodispbench3d_f2s3/conf/tool/f2s3.yaml` — the canonical F2S3 tool config
  (entry, `outputs.from: glob`, hashed run dir) to harden + add the `remediation` hint.
- `docs/tools/f2s3.md` — home for the F2S3 canonical-example doc + how-to-obtain note.
- `docs/integrating/cli-tool.md` — the generic `CliToolAdapter` integration guide;
  the subprocess-contract documentation (timeout, exit codes, glob outputs) lands here.

### Surfaces to harden
- `src/geodispbench3d/cli.py` — argparse + the five handlers (`_cmd_sweep` :127,
  `_cmd_rescore` :188, `_cmd_analyze` :239, `_cmd_dashboard` :285, `_cmd_list_metrics`
  :310; `main` :24). Exit codes, arg validation, rescore-subcommand split, clean-error
  wrapper.
- `src/geodispbench3d/tool/cli_adapter.py` — `run_trial` (:98), the `subprocess.run`
  call (:107), `_collect_outputs` (:188), and `prepare()` (to be implemented for the
  preflight).
- `src/geodispbench3d/tool/base.py` — the `ToolAdapter` ABC with the `prepare()`/
  `teardown()` lifecycle hooks (:87, :90) that anchor the fail-fast preflight (D-10).
- `src/geodispbench3d/sweep/runner.py` — calls `adapter.prepare()`/`teardown()`
  (:192/:204, :251/:273); convergence point for the timeout-as-failed-trial reporting.
- `src/geodispbench3d/suite/loader.py` — `load_suite` eager raises (:91/:95/:103) that
  D-11 wraps at `main()`.

### Dev-environment constraint (governs every test/lint run)
- `AGENTS.md` — all `python`/`pip`/`pytest`/`ruff`/`pyright` go through the conda env
  `iof3d_cosicorr3d-dev312`; the F2S3 suite runs via `conda run -n f2s3-dev312`. The
  CLI-04 stub-executable tests (D-12) are designed to run in the dev env **without**
  needing the F2S3 env.

### Codebase baselines
- `.planning/codebase/CONVENTIONS.md` — fail-soft exception pattern (D-05 reuses it),
  exit-code convention, logging rules.
- `.planning/codebase/ARCHITECTURE.md` — confirms the single-threaded trial loop (why
  the interactive watchdog is out of scope) and adapter process-isolation model.
- `.planning/codebase/TESTING.md` — current suite layout (core/iof3d/f2s3); D-12's new
  `tests/core/test_cli.py` slots into `tests/core`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ToolAdapter.prepare()` / `teardown()`** (`tool/base.py:87,90`) are no-op hooks
  already invoked once by the runner (`runner.py:192/204`, `:251/273`) — the natural,
  zero-new-plumbing home for the fail-fast preflight (D-10).
- **`PassDiagnostics` + the "N non-fatal failures" CLI summary line** (Phase 2 F-08) —
  the timeout and empty-glob failures (D-05/D-07) plug straight into this existing
  counting/surfacing plumbing rather than inventing new reporting.
- **`CliToolAdapter`'s existing failure branches** (`cli_adapter.py:115-140`) already
  return `success=False` with a structured `error` for `FileNotFoundError` and nonzero
  exit — the timeout (`TimeoutExpired`) and empty-predictions failures follow the same
  shape.
- **Typed `SuiteConfig`** (Phase 2 F-01) means the CLI handlers are now concretely typed
  — the rescore-subcommand split (D-09) and exit-code rework happen against pyright-checked
  code, not `Any`.
- **`tests/core/test_cli_adapter.py`** already builds argv via the adapter; D-12's stub-
  executable tests extend the same fixtures with a real-subprocess layer.

### Established Patterns
- **Fail-soft, countable degradation** (CONVENTIONS + Phase 2 D-03): non-fatal problems
  are caught, narrowed, logged at `warning`, and counted — never made interactive or
  silently swallowed. D-05/D-07 follow this exactly.
- **`entry` is `shlex.split`** (`cli_adapter.py:172`, tested at
  `test_cli_adapter.py:69`) — `conda run -n ENV bin` already tokenizes correctly, so the
  preflight can inspect the leading token(s) to resolve the executable.
- **Subcommand dispatch in `main()`** (`cli.py:91-102`) — adding a `rescore` subcommand
  (D-09) is a known pattern (it mirrors `analyze`); `_cmd_rescore` already exists and is
  reused, only the argparse wiring + dispatch change.

### Integration Points
- **Timeout** wires at `cli_adapter.py:107` (`subprocess.run(timeout=…)`) → caught
  alongside `FileNotFoundError` → `success=False` → reported to Ax as a failed trial in
  `runner.py`.
- **Preflight** wires at `CliToolAdapter.prepare()` → raised before the trial loop in
  `runner.run_with_suite` → propagates to `main()` → exit 1.
- **Exit-code rework** centers on `cli.py:214`/`:282` (rescore/analyze) keyed off
  `summary.parser_misses` instead of `succeeded == total`, and a clean-error wrapper in
  `main()` (`:91-102`).

</code_context>

<specifics>
## Specific Ideas

- **F2S3 stays the showcase, conda-run stays default** — the user explicitly wants
  F2S3 to remain a faithful `CliToolAdapter` example (subprocess + env isolation), with
  the in-env override documented, not substituted.
- **No surprise-killing of long trials** — the heavy-workload nature of the harness is
  the stated reason the timeout is opt-in, not defaulted. A killed timeout must be a
  *visible, counted* failure, never silent and never interactive.
- **Pre-public is the moment for clean CLI breaks** — the user accepted the
  `rescore`-subcommand restructure (D-09) specifically because there are no external
  users yet; deferring it would only make the break costlier later.
- **Faithful tests over fast tests** — the user chose real stub executables over
  monkeypatching precisely because timeout/exit-code are real subprocess mechanics worth
  exercising end-to-end (D-12).

## Research / planning items to resolve (not user decisions)
- **Preflight resolution mechanics for `conda run -n ENV bin`:** confirm how to cheaply
  verify the env/binary without invoking the tool — e.g. `shutil.which("conda")` + (env
  existence?) + the trailing binary. Decide how deep the env check goes vs just "`conda`
  resolves and the entry is well-formed." Keep it fast (runs before every sweep).
- **`--timeout` vs `execution.timeout_seconds` precedence** — assume CLI flag overrides
  YAML; confirm and document.
- **Which suites run in which env for the new tests** — the D-12 stub-executable tests
  should run fully in `iof3d_cosicorr3d-dev312` with no F2S3 env dependency; verify the
  F2S3 *parser* tests (`tests/f2s3`) still gate on `conda run -n f2s3-dev312` as today.
- **OmegaConf parse behavior for the new `timeout_seconds` / `remediation` fields** —
  confirm adding optional fields to the tool config dataclass doesn't reject existing
  in-repo YAMLs, and that `f2s3.yaml` round-trips.

</specifics>

<deferred>
## Deferred Ideas

- **Interactive timeout watchdog ("kill or keep waiting?" poll).** When no timeout is
  configured, after a default elapsed time prompt the user whether to kill the trial.
  **Out of scope for Phase 3** and seeded for future consideration: it requires
  converting the blocking `subprocess.run` to a `Popen`/watchdog-thread model and a
  TTY-vs-headless branch, which fights the unattended-batch design (Ax sweeps run for
  hours, often headless on HPC, where an interactive prompt would itself hang forever).
  → **Filed as a seed** (see `gsd-capture` / `.planning/seeds/`).

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 3-CLI Hardening*
*Context gathered: 2026-06-27*
