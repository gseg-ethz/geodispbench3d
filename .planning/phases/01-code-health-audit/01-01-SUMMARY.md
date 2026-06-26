---
phase: 01-code-health-audit
plan: 01
subsystem: testing
tags: [audit, detectors, vulture, deptry, radon, ruff-c901, coverage, evidence]

# Dependency graph
requires: []
provides:
  - "audit-evidence/ directory: seven reproducible raw detector captures + pinned-version README"
  - "EVIDENCE.md: file:line-anchored mechanical-evidence summary across four buckets (dead code, coverage gaps, dependency hygiene, complexity)"
  - "Confirmed reproducibility surface for AUDIT-01 mechanical findings"
affects: [01-02-PLAN, code-health-audit, REPORT.md synthesis, AUDIT-04]

# Tech tracking
tech-stack:
  added: [vulture==2.16 (dev-only/conda), deptry==0.25.1 (dev-only/conda), radon==6.0.1 (dev-only/conda)]
  patterns:
    - "Detectors installed dev-only into the conda env, never into pyproject.toml (read-only audit invariant)"
    - "Every detector invocation prefixed conda run -n iof3d_cosicorr3d-dev312 (AGENTS.md)"

key-files:
  created:
    - .planning/phases/01-code-health-audit/audit-evidence/vulture.txt
    - .planning/phases/01-code-health-audit/audit-evidence/coverage.txt
    - .planning/phases/01-code-health-audit/audit-evidence/coverage-skips.txt
    - .planning/phases/01-code-health-audit/audit-evidence/deptry.txt
    - .planning/phases/01-code-health-audit/audit-evidence/radon-cc.txt
    - .planning/phases/01-code-health-audit/audit-evidence/radon-mi.txt
    - .planning/phases/01-code-health-audit/audit-evidence/ruff-c901.txt
    - .planning/phases/01-code-health-audit/audit-evidence/README.md
    - .planning/phases/01-code-health-audit/EVIDENCE.md
  modified: []

key-decisions:
  - "Detectors installed dev-only into conda env (human-approved), not pyproject.toml — read-only audit preserved"
  - "ruff C901 is the primary/authoritative complexity signal; radon kept as supplementary corroboration"
  - "deptry run with --known-first-party geodispbench3d to suppress 48 editable-install self-import false positives"

patterns-established:
  - "Detector captures carry a header block (command + pinned version + env + reproduce note) before raw output"
  - "EVIDENCE.md carries NO severity/disposition labels — adjudication is deferred to Plan 02 / AUDIT-04"

requirements-completed: [AUDIT-01]

# Metrics
duration: 10min
completed: 2026-06-26
status: complete
---

# Phase 1 Plan 01: Mechanical Audit Evidence Capture Summary

**Captured reproducible vulture/deptry/radon/ruff-C901/coverage output through the mandated conda env and distilled it into a file:line-anchored EVIDENCE.md, with no source or pyproject.toml change.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-26T15:26:09Z
- **Completed:** 2026-06-26T15:35:48Z
- **Tasks:** 3 (Task 1 was a human-approved blocking gate; Tasks 2-3 produced artifacts)
- **Files created:** 9 (8 under audit-evidence/, plus EVIDENCE.md)

## Accomplishments
- Installed the three human-approved detectors (vulture 2.16, deptry 0.25.1, radon 6.0.1) **dev-only into the conda env**, leaving `pyproject.toml` and `src/` untouched.
- Captured seven reproducible raw detector outputs plus a pinned-version `README.md` documenting the exact conda-prefixed command behind each file.
- Distilled `EVIDENCE.md` across four mechanical buckets — every entry file:line/function anchored and traced back to its raw capture, with **no severity or disposition labels** (those belong to Plan 02 / AUDIT-04).
- Surfaced quantified corroboration for CONCERNS.md: runner.py at 13% coverage, store.py at 44%, the iof3d adapter's 220-line `build_app_config_from_parameters` at ruff C901 = 22 (the worst on every measure), and the `datetime.utcnow()` deprecation warnings.

## Task Commits

1. **Task 1: Verify legitimacy of net-new detectors** — human-approved gate (no files; resolution recorded in Task 2 commit/README) — folded into `2f9d03f`
2. **Task 2: Install detectors + capture raw output** — `2f9d03f` (chore)
3. **Task 3: Distill EVIDENCE.md** — `e9488dd` (docs)

**Plan metadata:** _(this commit)_ (docs: complete plan)

## Files Created/Modified
- `audit-evidence/vulture.txt` — dead-code scan (min-confidence 60), 15 hits across the three packages
- `audit-evidence/coverage.txt` — per-file coverage for all three shipped packages (TOTAL 55%), with the plugin-self-skip honesty note
- `audit-evidence/coverage-skips.txt` — records that **nothing self-skipped here** (iof3D dev env) but would in CI/lean, with the mechanism
- `audit-evidence/deptry.txt` — dependency hygiene: no DEP001 missing; 7 DEP002 dev-tool scan-scope artifacts
- `audit-evidence/ruff-c901.txt` — primary complexity signal: 5 functions above McCabe 10
- `audit-evidence/radon-cc.txt` — supplementary cyclomatic complexity (ran cleanly on 3.12); 17 functions at grade C+
- `audit-evidence/radon-mi.txt` — supplementary maintainability index; adapter.py lowest at 26.21
- `audit-evidence/README.md` — pinned reproduce-it commands + flag rationale
- `EVIDENCE.md` — the four-bucket distilled summary feeding Plan 02

## Decisions Made
- **Detectors dev-only in the conda env (human-approved), never in `pyproject.toml`** — preserves the read-only-audit invariant; the tools are one-shot evidence aids.
- **ruff C901 = primary complexity signal, radon = supplementary** — radon happened to run cleanly on Python 3.12 so no graceful degradation was needed, but ruff (pinned first-party) remains authoritative.
- **deptry run with `--known-first-party geodispbench3d`** — the editable src-layout install otherwise produces 48 DEP003 self-import false positives; suppressing them exposes the real signal (no missing deps).

## Deviations from Plan

### Notable (documented, not auto-fixes)

**1. Plugin test suites did NOT self-skip in this env**
- **Found during:** Task 2 (coverage capture)
- **Plan assumption:** `tests/iof3d` and `tests/f2s3` self-skip in this env, so plugin coverage would be misleadingly 0%.
- **Reality:** the mandated env `iof3d_cosicorr3d-dev312` IS the iof3D dev env — `iof3D` and `pchandler` are importable, so both plugin suites **ran** (32 passed, 0 skipped). Plugin-package coverage here is therefore *real*, not a self-skip artifact.
- **Handling:** captured honestly in `coverage.txt` and `coverage-skips.txt` — they explain that the numbers reflect exercised code in THIS env, while in CI/lean envs the suites self-skip and the same packages would read 0%/low because unexercised (not untested). Flagged in STATE blockers for Plan 02. This is *more* honest than the plan's expectation, so no acceptance criterion was weakened.

**2. coverage `--include='src/geodispbench3d*'` replaced by `--source=<three packages>` scoping**
- **Found during:** Task 2 — the `--include` glob gets mangled passing through `conda run` shell quoting ("No data to report").
- **Fix:** scoped measurement at `coverage run` time via `--source=geodispbench3d,geodispbench3d_iof3d,geodispbench3d_f2s3`, which makes the per-file table already equivalent to the requested include (every measured file is `src/geodispbench3d*`). Documented in `coverage.txt` and `README.md`.

**3. deptry scoped to project root with first-party suppression + ANSI strip**
- **Found during:** Task 2 — an initial `deptry src` run was dominated by dev-tool false positives and ANSI escape codes; a `deptry .` run added 48 self-import DEP003 false positives.
- **Fix:** final command `deptry . --known-first-party geodispbench3d` piped through `sed` to strip ANSI. Rationale documented in `deptry.txt` and `README.md`.

_No `src/` file and no `pyproject.toml` change was made (read-only-audit invariant verified via `git diff --quiet -- src pyproject.toml`)._

## Known Stubs
None. (This plan produces only evidence/documentation artifacts; no source code or data-bearing UI was created.)

## Self-Check: PASSED
- All 9 created files exist and are non-empty (verified).
- Task commits exist: `2f9d03f` (evidence), `e9488dd` (EVIDENCE.md) — both confirmed in `git log`.
- Read-only-audit invariant holds: `git diff --quiet -- src pyproject.toml` → clean.
- EVIDENCE.md carries the four bucket sections, plugin-coverage honesty, and no severity/disposition labels (verified).
