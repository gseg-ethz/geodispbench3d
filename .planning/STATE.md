---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 4
current_phase_name: Licensing, Metadata & Packaging
status: "Phase 03 shipped — PR #3 (base develop)"
stopped_at: Phase 4 context gathered
last_updated: "2026-06-27T17:39:41.059Z"
last_activity: 2026-06-27
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 13
  completed_plans: 13
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-26)

**Core value:** Nothing is published to PyPI until the codebase is demonstrably lean, correct, well-tested, and its CLI-integration story is sound.
**Current focus:** Phase 03 — cli-hardening

## Current Position

Phase: 4 — Licensing, Metadata & Packaging
Plan: Not started
Status: Phase 03 shipped — PR #3 (base develop)
Last activity: 2026-06-27

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 13
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | - | - |
| 02 | 7 | - | - |
| 03 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 10min | 3 tasks | 9 files |
| Phase 01 P02 | 20min | 2 tasks | 1 files |
| Phase 02 P01 | 7min | 2 tasks | 1 files |
| Phase 02 P02 | 55min | 3 tasks | 5 files |
| Phase 02 P03 | 12min | 3 tasks | 4 files |
| Phase 02 P04 | 12min | 1 tasks | 4 files |
| Phase 02 P05 | 15min | 3 tasks | 11 files |
| Phase 02 P06 | 15min | 3 tasks | 8 files |
| Phase 02 P07 | 18min | 3 tasks | 12 files |
| Phase 03 P01 | 15min | 3 tasks | 8 files |
| Phase 03 P02 | 8min | 3 tasks | 4 files |
| Phase 03 P03 | 35min | 3 tasks | 3 files |
| Phase 03 P04 | 12min | 2 tasks | 10 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Audit-first: code-health audit gates all fixes (no fixes before the report)
- Internal plan reviews run through the codex CLI
- Branching: develop + phase branches; PRs to main at milestone only, .planning/ stripped
- [Phase 01]: Audit detectors (vulture 2.16, deptry 0.25.1, radon 6.0.1) installed dev-only into the conda env per human approval; NOT added to pyproject.toml (read-only audit)
- [Phase ?]: REPORT.md (32 findings F-01..F-32) supersedes CONCERNS.md as the dispositioned Phase 1 deliverable
- [Phase ?]: 2 Blockers gate public publish (F-26 Private classifier, F-27 README/LICENSE mismatch), routed to Phase 4
- [Phase ?]: [Phase 02-01]: runner.py coverage measured via 'coverage run -m pytest -p no:cov' (72%, up from 13%); plan's 'pytest --cov' crashes on a torch/pytest-cov early-import conflict in this env
- [Phase ?]: [Phase 02-01]: F-20 characterization harness (FakeAxClient + StubAdapter) landed; partial-failure NaN survivor-mean pinned as the F-05/F-08 regression anchor
- [Phase ?]: 02-02: pyright gate baseline is the dev-env capture (1.1.403 + full extras, 21 errors); CI-faithful 1.1.392/.[dev] (16 errors) is a doc-only strict-subset reference
- [Phase ?]: 02-02: pyright_gate.py uses line-number-independent (file, rule, normalized-message) multiset signatures, replacing raw 'pyright &&' for 02-03/04/05/07
- [Phase 02-03]: SuiteConfig retype + provenance collapse (F-01/F-13); objective-specific finite-case signal (F-05) via SweepRunSummary + dedicated trial-level artifact, kept off the Ax objective payload — Typed consumers remove 15 attr-defined ignores with no new pyright errors; finite/total is objective-specific (self._objective_name) and surfaced via log + artifact + return, never injected into complete_trial raw_data
- [Phase 02]: 02-04: SweepParameter coercion single-sourced via from_mapping classmethod (F-02/FIX-03); three sites routed through it, _coerce_hparam removed; net -2 pyright errors (values-list patterns cleared at tool/loader.py + factory.py); from_mapping is a class member, not in __all__
- [Phase ?]: [Phase 02-05]: F-08 resolved — typed PassDiagnostics threaded through sweep/rescore/analyze; 8 IO excepts narrowed (rescore append corrected to (OSError, AttributeError, TypeError)), 4 plugin-callable boundaries documented-broad; read_prediction/load_trial_record gain on_non_fatal; each CLI summary prints an aggregate 'N non-fatal failures' line; fail-soft flow preserved
- [Phase ?]: F-09 (02-06): stamp UTC via datetime.now(UTC).isoformat() with no hand-appended Z; helper names _utcnow/_utcnow_compact kept, only the call swapped
- [Phase ?]: F-10 (02-06): hoisted only internal/stdlib imports in runner.py; Ax stays lazy/guarded; test_imports.py is the authoritative lazy-gating guard. F-08 cache-write test repatched to the hoisted geodispbench3d.sweep.runner.write_prediction binding
- [Phase ?]: 02-07: F-03 parser_fn_repr single-sourced in sweep/trial_record.py (public, __all__); runner+rescore import it; byte-identity locked across module/method/nested(<locals>) callables so the sweep/rescore cache key cannot drift
- [Phase ?]: 02-07: F-30 four dead fields deleted (outputs_options, scan_by_epoch, gt_kinds_supported, yaml_hash incl. _tool_from_record deserializer); old yaml_hash records still load; hash_file retained as public util
- [Phase ?]: 02-07: ExecutionConfig.ensure_supported() raises deterministically (D-09) on non-default parallel_trials/override_tool_mode, called from BOTH _cmd_sweep and run_with_suite (bypass-proof); fields retained; FIX-04 green-gate closed
- [Phase ?]: [Phase 03-01]: success=False reported to Ax via log_trial_failure on BOTH runner paths (RESOLVED-B shared _raise_if_failed), never scored; all-failed sweep yields best_trial=None + successful_trials=0 (RESOLVED-A _resolve_best_trial). Typed counters split timeouts (non-exit, D-05) from trial_failures/eval_failures (exit-driving). Preflight validates leading exe + conda env only, NOT the in-env binary (D-02 accepted limitation; gap covered by trial 0). CLI-02/CLI-03 left Pending — shared with Plans 03/04.
- [Phase ?]: [Phase 03-02]: rescore is its own subcommand (run rejects rescore-only flags => exit 2); exit taxonomy 0/1/2 across all 5 handlers incl. sweep (1 if trial_failures|eval_failures|successful_trials==0; timeouts non-fatal per D-05 but zero-success=>1 per RESOLVED-A); rescore 1 if parser_misses|eval_failures; analyze 1 if skipped_unreadable|eval_failures. Narrow _load_or_clean_exit wraps ONLY loader calls (runtime ValueError keeps traceback); ToolPreflightError caught at dispatch boundary; --timeout via set_timeout_override; --traceback single <subcommand> form; cli.py --rescore scrub done (repo-wide is Plan 04).
- [Phase ?]: Plan 04 docs: timeout exit semantics per D-05 + RESOLVED-A — an individual timeout is NON-FATAL to the exit code; only a genuine crash/eval failure or a zero-success sweep drives exit 1.
- [Phase ?]: Plan 04 scrub rule: docs/ migration note may NAME the removed --rescore flag in prose but reproduces no full old command-form; src/ forbids ANY --rescore token (repo-wide negative grep gate).

### Open Questions (surface at phase discussions)

- Phase 3: F2S3 binary in-env vs subprocess/`conda-run`
- Phase 4: resolve `pchandler` for F2S3 via `f2s3` extra vs a `pchandler`-free parser
- Phase 4: ship `geodispbench3d_iof3d` + `iof3d-ax` script publicly, or exclude

### Pending Todos

None yet.

### Blockers/Concerns

yet.

- Plugin suites (tests/iof3d, tests/f2s3) do NOT self-skip in the iof3D dev env, so plugin-package coverage here is real; in CI/lean envs they self-skip and read 0%/low. Plan 02 synthesis must preserve this distinction.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260626-jix | Create OVERVIEW.md one-pager for ETH open-source docs | 2026-06-26 | 99d254c | [260626-jix-create-overview-md-one-pager-for-eth-ope](./quick/260626-jix-create-overview-md-one-pager-for-eth-ope/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| CI-health | Green the CI Lint gate (raw `pyright` red on a standing 14-error baseline → Test/Build skipped on every PR). Options + decision tracked in ROADMAP Phase 5 open question. | Deferred → Phase 5 | 2026-06-27 (Phase 3 ship, PR #3) |

## Session Continuity

Last session: 2026-06-27T17:39:41.051Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-licensing-metadata-packaging/04-CONTEXT.md
