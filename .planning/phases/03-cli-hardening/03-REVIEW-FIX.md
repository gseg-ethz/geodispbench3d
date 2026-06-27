---
phase: 03-cli-hardening
fixed_at: 2026-06-27T00:00:00Z
review_path: .planning/phases/03-cli-hardening/03-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-06-27T00:00:00Z
**Source review:** .planning/phases/03-cli-hardening/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (Critical + Warning; 0 Critical, 3 Warning)
- Fixed: 3
- Skipped: 0

Verification: full suite green (117 passed) after all three fixes; `ruff check`
clean on every modified file. Each fix was validated against its targeted tests
(`tests/core/test_rescore.py`, `tests/core/test_cli_adapter.py`,
`tests/core/test_cli.py`) before committing.

## Fixed Issues

### WR-01: `rescore` directory walk mutates the filesystem, creating spurious empty `ax_trial/` dirs

**Files modified:** `src/geodispbench3d/sweep/trial_record.py`, `src/geodispbench3d/sweep/rescore.py`
**Commit:** ecadb1b
**Applied fix:** Added a pure `trial_summary_file(run_dir)` path constructor (no
`mkdir`) to `trial_record.py`, exported it in `__all__`, and refactored
`trial_record_path` to delegate to it while keeping the `mkdir` for write paths.
`_walk_run_dirs` in `rescore.py` now uses the pure helper for its `.is_file()`
membership check, so the read-only walk over `run_dir_root` no longer creates
empty `ax_trial/` directories under unrelated sibling directories. Behavior of
`trial_record_path` (still mkdirs) is unchanged, so all existing write/test
callers are unaffected. Verified with `tests/core/test_rescore.py` (9 passed).

### WR-02: CLI adapter subprocess `env` replaces the whole environment and is read from the wrong YAML block

**Files modified:** `src/geodispbench3d/tool/loader.py`, `src/geodispbench3d/tool/cli_adapter.py`, `src/geodispbench3d/conf/schema/tool.schema.json`
**Commit:** 531d6f1
**Applied fix:** Changed `_build_cli_adapter` to source `env` from the
documented `execution` block (`execution_raw.get("env")`, already parsed at
loader.py:155) instead of the `outputs` block. Added an `execution.env` property
(object of string values) to `tool.schema.json` with a description of the
merge-not-replace semantics. Changed `CliToolAdapter.__init__` to merge overrides
over the inherited environment (`{**os.environ, **env}`) rather than passing a
bare partial dict to `Popen(env=...)`, which would have stripped
PATH/HOME/CONDA_*/LD_LIBRARY_PATH and broken `conda run` resolution. Verified with
`tests/core/test_cli_adapter.py` + `tests/core/test_cli.py` (37 passed).

### WR-03: Post-timeout reap can still hang indefinitely if a descendant escapes the process group

**Files modified:** `src/geodispbench3d/tool/cli_adapter.py`
**Commit:** b1a716c
**Applied fix:** Added a `_REAP_GRACE_SECONDS = 10.0` class constant and bounded
the second (post-`SIGKILL`) `proc.communicate()` with that timeout. If an escaped
descendant (daemonized / re-parented out of the process group) still holds the
inherited stdout/stderr fds, the drain is abandoned after the grace period with a
`logger.warning` and empty `stdout/stderr`, so the sweep is never blocked
indefinitely. The leader is still reaped by the earlier SIGKILL; only the wait on
a re-parented grandchild is bounded. Verified with `tests/core/test_cli_adapter.py`
+ `tests/core/test_cli.py` (37 passed).

## Skipped Issues

None — all in-scope findings were fixed.

> Out-of-scope (Info-tier, not addressed under `critical_warning` scope): IN-01
> (further `tool.schema.json` drift — note WR-02 already added `execution.env`),
> IN-02 (unreachable `main()` fallthrough), IN-03 (rescore parser-miss
> double-counted as `succeeded` + `parser_misses`).

---

_Fixed: 2026-06-27T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
