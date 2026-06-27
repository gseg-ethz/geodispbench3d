---
phase: 03-cli-hardening
plan: 04
subsystem: docs + src-docstring-scrub
tags: [docs, cli-contract, exit-codes, timeout, rescore-subcommand, stale-flag-scrub, f2s3]
requires:
  - CliToolAdapter timeout/preflight/glob contract (03-01)
  - runner failure-propagation + typed counters (03-01)
  - rescore subcommand + exit-code taxonomy (03-02)
provides:
  - F2S3 documented as the canonical CliToolAdapter example (how-to-obtain + gseg-ethz link)
  - subprocess-contract + 0/1/2 exit-code documentation (CLI-02)
  - rescore-subcommand migration note (D-09)
  - yaml-schemas reference updated (glob-blessed/stdout_json-deprecated, timeout_seconds, remediation/help_url)
  - repo-wide src/ + docs/ --rescore flag-token scrub
affects:
  - public docs surface (CLI-05 deliverable)
tech-stack:
  added: []
  patterns:
    - "docs pinned to the exact error strings / field names recorded in the Plan-01/02 SUMMARYs"
    - "repo-wide negative grep gate as a stale-pattern enforcement seam"
key-files:
  created: []
  modified:
    - docs/tools/f2s3.md
    - docs/integrating/cli-tool.md
    - docs/integrating/index.md
    - docs/rescoring-and-analysis.md
    - docs/reference/yaml-schemas.md
    - src/geodispbench3d/analysis/__init__.py
    - src/geodispbench3d/sweep/rescore.py
    - src/geodispbench3d/sweep/evaluation.py
    - src/geodispbench3d/sweep/trial_record.py
    - src/geodispbench3d/sweep/runner.py
decisions:
  - "Timeout exit semantics documented per locked D-05 + RESOLVED-A: an individual timeout is NON-FATAL to the exit code; only a genuine crash/eval failure OR a zero-success sweep drives exit 1 (the stale 'timeout -> run exits non-zero' wording is corrected)."
  - "Conda env runs pytest/ruff as `python -m` (base shadows the env bin under `conda run`), consistent with 03-01/03-02."
  - "docs/ migration note NAMES the removed `--rescore` flag in prose (allowed) but reproduces no full old command-form invocation (forbidden); src/ forbids ANY `--rescore` token."
metrics:
  duration: 12min
  completed: 2026-06-27
  tasks: 2
  files: 10
status: complete
---

# Phase 3 Plan 04: CLI-hardening documentation + repo-wide stale-flag scrub Summary

One-liner: documented the hardened CLI surfaces from Plans 01–02 — F2S3 as the
canonical `CliToolAdapter` example with a how-to-obtain note, the subprocess
contract (four failure modes + failed-trial→Ax + the exact process-tree timeout
guarantee), the 0/1/2 exit-code taxonomy with the D-05/RESOLVED-A non-fatal
timeout semantics, the rescore-subcommand migration, and the updated YAML schema
reference — and scrubbed the now-removed `--rescore` flag token repo-wide from
src/ docstrings/comments and docs/ command-form examples.

## What Was Built

### Task 1 — F2S3 canonical example + subprocess contract + exit taxonomy (c76f47a)
- `docs/tools/f2s3.md`: new **How to obtain F2S3** section linking
  `https://github.com/gseg-ethz/F2S3_pc_deformation_monitoring` (D-03) and the
  `f2s3-dev312` env; documents the `remediation`/`help_url` preflight hint and the
  deliberate D-02 limitation (preflight validates conda + env, NOT the trailing
  in-env binary — surfaced by trial 0's nonzero-exit handling). New **Per-trial
  timeout** section: the opt-in `execution.timeout_seconds` knob (shipped unset),
  the `--timeout` override, and the EXACT termination guarantee — process-group
  `SIGKILL` (`os.killpg`) reaping the `conda run` tree on POSIX, direct-child
  fallback on non-POSIX, `ProcessLookupError` swallowed, trial still recorded as a
  timeout. Marked F2S3 as the canonical `CliToolAdapter` example; added the
  in-env `entry: f2s3` override note (D-01).
- `docs/integrating/cli-tool.md`: rewrote **Locating outputs** to glob-blessed
  (default when unset), `stdout_json` deprecated (explicit use raises at load),
  `fixed_path` removed; empty-glob → failed trial. New **Subprocess contract**
  section: a failure-mode table (nonzero exit / empty output / timeout / missing
  env-binary) with `error_kind`s, the failed-trial → Ax `log_trial_failure`
  propagation (sweep continues), and the **Timeout exit semantics** subsection
  matching locked D-05 + RESOLVED-A (individual timeout NON-FATAL; exit 0 when
  ≥1 success; zero-success sweep exits 1 incl. timeouts-only). New **Package CLI
  exit codes** 0/1/2 table consuming the exact sweep expression
  `1 if (trial_failures or eval_failures or successful_trials == 0) else 0`.
- `docs/integrating/index.md`: replaced the blessed `from: stdout_json` MVP
  example with `from: glob` + `predictions_glob`; scrubbed the "stdout/JSON output
  parsing" wording to "glob-based output collection".

### Task 2 — rescore-subcommand migration + schema reference + repo-wide scrub (d02b40a)
- `docs/rescoring-and-analysis.md`: every rescore example rewritten from the old
  `run … --rescore` form to `geodispbench3d rescore <suite>`; section header,
  flag prose, "when to use" comparison, and cache-update line all updated. Added a
  **Migration note** that names the removed `--rescore` flag and the rescore-only
  flag rejection on `run` in prose, WITHOUT reproducing the full old command line.
- `docs/reference/yaml-schemas.md`: tool schema gains `remediation`/`help_url` and
  `execution.timeout_seconds` (opt-in; unset/`<=0` = no timeout; noted distinct
  from the suite-level execution block); `outputs.from` reduced to glob-blessed
  with stdout_json-deprecated and fixed_path dropped. CLI section expanded to the
  full authoritative surface (run/rescore/analyze/dashboard/list-metrics flags +
  `--timeout` + `--traceback`) and a 0/1/2 exit-code line.
- `src/` stale-flag scrub (docstring/comment-only, no logic change):
  `analysis/__init__.py:3`, `sweep/rescore.py:1`, `evaluation.py:42`,
  `trial_record.py` (:15, the literal `--rescore --reuse-parser-options`
  invocation at :60, :61, and the `:279` provenance-read-back comment), and
  `runner.py` (the `:462`/`:484` `# --rescore / analyze` comments) all rephrased to
  the `rescore` subcommand / "rescore mode" wording.

## File-Ownership Boundary (review LOW)
Plan 04 (Wave 3) ran strictly AFTER Plan 01 (Wave 1) landed all logic in
`runner.py` / `rescore.py`. This plan touched those two files ONLY for the
`--rescore` token scrub in docstrings/comments — no logic changed. Sequential
waves, no concurrent-edit conflict. `tests/core` stayed green (113 passed),
confirming the scrub was behavior-neutral.

## Deviations from Plan
None — plan executed exactly as written. No Rule 1–4 auto-fixes required (docs +
docstring/comment-only edits; no bugs, missing functionality, or blocking issues
discovered).

### Verification-command adaptation (not a code deviation)
Per 03-01/03-02: under `conda run -n iof3d_cosicorr3d-dev312`, bare
`pytest`/`ruff` resolve to the base env, so verification ran as
`python -m pytest` / `python -m ruff`.

## Verification Evidence
- Task 1 gate: all required strings present (gseg-ethz link + process-tree
  termination in f2s3.md; timeout/exit/log_trial_failure/deprecated/non-fatal in
  cli-tool.md; no blessed `from: stdout_json` line in index.md) → PASS.
- Task 2 gate: `python -m pytest tests/core -q` → **113 passed**;
  `geodispbench3d rescore` present in rescoring-and-analysis.md;
  timeout_seconds/remediation/deprecated present in yaml-schemas.md; **no
  `--rescore` token anywhere under src/**; **no `geodispbench3d run <suite>
  --rescore` command-form under docs/** → PASS.
- `python -m ruff check src/geodispbench3d/sweep src/geodispbench3d/analysis` →
  All checks passed.

## Known Stubs
None. This is a documentation + docstring-scrub plan; no data paths, placeholders,
or unwired components introduced.

## Threat Flags
None. No new network/auth/file-access surface. Per the plan's threat register the
content is pinned to the exact error strings/fields in the Plan-01/02 SUMMARYs and
a repo-wide negative gate forbids the old rescore command form surviving (T-03-12
mitigation); the timeout claim is bounded to the implemented process-group
guarantee.

## Self-Check: PASSED
- All 10 modified files present on disk.
- Both task commits present in git history (c76f47a, d02b40a).
