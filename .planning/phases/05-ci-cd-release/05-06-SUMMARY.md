---
phase: 05-ci-cd-release
plan: 06
subsystem: ci-cd-release
tags: [integration-verification, github-actions, oidc, release-please, pyarrow, ax-platform, parquet, ci-green, end-of-phase-verify]

requires:
  - phase: 05-ci-cd-release
    plan: 03
    provides: "publish-pypi.yml / publish-testpypi.yml (OIDC), release-please workflow_run + App token, manifest 0.1.0 + Release-As 0.2.0 footer"
  - phase: 05-ci-cd-release
    plan: 05
    provides: "Restructured ci.yml (lint ‖ matrix, build gate, docs) with the four rendered job-name contexts the rulesets gate on"
provides:
  - "05-VERIFICATION.md — observed green CI run on a PR against develop (all five jobs), TestPyPI/CICD-04 gates, deferred ship-time actions"
  - "pyarrow declared as a core dependency (parquet store now installable in a lean env)"
  - "Sweep runner adapted to the Ax 1.3.x complete_trial contract (objective-only raw_data); ax-platform pin widened to >= 1.3, < 2.0"
  - "tests/core pchandler-coupled guard test skips cleanly in the lean core suite"
  - "ci.yml build job reclaims runner disk for the torch/CUDA install-smoke"
affects: [milestone-ship (CICD-03/04 end-to-end live publish + first v0.2.0 cut)]

tech-stack:
  added:
    - "pyarrow >= 16 (core dependency — pandas parquet engine; NumPy-2 compatible)"
  patterns:
    - "Lean-CI-env verification surfaces latent deps the fat dev env masks (parquet engine, Ax version drift, test-suite/dep coupling)"
    - "Forward-only develop→phase-branch merge to make a CI-trigger PR mergeable without rewriting prior phase commits"
    - "Ax raw_data filtered to the registered objective to satisfy 1.3.x metric_name_to_signature (loss-free; extras persist to parquet)"
    - "GitHub-Actions disk reclaim + --no-cache-dir for heavy torch/CUDA install-smoke"
    - "Honest ship-time deferral: live TestPyPI dispatch blocked by default-branch topology, recorded not faked"

key-files:
  created:
    - .planning/phases/05-ci-cd-release/05-VERIFICATION.md
  modified:
    - pyproject.toml
    - src/geodispbench3d/sweep/runner.py
    - tests/core/test_iof3d_import_guard.py
    - .github/workflows/ci.yml

key-decisions:
  - "PATH 1 (user-approved via checkpoint): apply the lean-env fixes on the phase branch and iterate CI to green, rather than route to a separate plan"
  - "Fix A — add pyarrow as a CORE dependency (not an extra): the parquet results store is core, non-optional functionality (review 05-06)"
  - "Fix B — ADAPT to Ax 1.3.x (durable), not downpin: pass only the registered objective to complete_trial; widen pin to >= 1.3, < 2.0"
  - "Fix C — pytest.importorskip('pchandler') keeps the parser-resolves contract test where pchandler exists, skips in lean core"
  - "Build disk fix is in-scope CI-config (reclaim toolchains + --no-cache-dir); the composite install path from Plan 05 was left unchanged"
  - "CICD-03/04 NOT marked fully complete: wiring + 0.2.0 seed proven in-phase; live publish / first cut pending ship (ledger discipline of plans 01/03)"

requirements-completed: [CICD-01, CICD-02]

coverage:
  - id: CICD-01
    description: "CI runs lint (ruff), type-check (pyright), and the full test matrix on Python 3.12"
    requirement: "CICD-01"
    verification:
      - kind: integration
        ref: "Green Actions run 28317897531 on PR #6 (→ develop): Lint (ruff + pyright), Test (core, 3.12), Test (f2s3, 3.12) all success"
        status: pass
    human_judgment: false
  - id: CICD-02
    description: "CI builds wheel + sdist and validates the distribution (twine check) + install smoke"
    requirement: "CICD-02"
    verification:
      - kind: integration
        ref: "Same run: Build wheel + install smoke success (build → twine check → fresh-venv install → import + --help)"
        status: pass
    human_judgment: false
  - id: CICD-03
    description: "OIDC trusted-publishing to PyPI/TestPyPI with no stored token"
    requirement: "CICD-03"
    verification:
      - kind: integration
        ref: "Wiring proven: env pypi/testpypi exist; names-only secret readback = [APP_ID, APP_PRIVATE_KEY] (no *PYPI*TOKEN*); built version asserted 0.1.0.post119"
        status: pass
      - kind: integration
        ref: "Live TestPyPI workflow_dispatch dry-run over OIDC"
        status: deferred  # ship-time: publish-testpypi.yml not yet on default branch main
    human_judgment: false
  - id: CICD-04
    description: "release-please cuts v0.2.0 off a protected main and publish-pypi.yml publishes on release"
    requirement: "CICD-04"
    verification:
      - kind: other
        ref: "Wiring proven (workflow_run[CI]@main, conclusion==success, App token v3.2.0 SHA-pinned, rp-action v5.0.0 SHA-pinned, no GITHUB_TOKEN/PAT) + deterministic seed (manifest 0.1.0 + Release-As 0.2.0 footer ce1dcfc)"
        status: pass
      - kind: integration
        ref: "End-to-end first cut: release PR → v0.2.0 tag → publish-pypi preflight → OIDC publish"
        status: deferred  # ship-time first release
    human_judgment: false

metrics:
  duration: ~54min  # includes a mid-plan checkpoint for the A/B/C/disk fix decisions
  completed: 2026-06-28

status: complete
---

# Phase 5 Plan 06: Integration Verification — CI green on a PR, OIDC + release-please gates Summary

**Exercised the full pipeline by opening PR #6 against `develop`, drove the CI run to green across all five jobs, and in doing so the lean CI `core` env surfaced four latent defects the fat dev env had masked — a missing parquet engine, an Ax 1.3.x `complete_trial` API tightening, a pchandler-coupled core test, and a runner-disk exhaustion in the first-ever build install-smoke — each fixed on the phase branch (user-approved PATH 1) and re-observed to green; then proved CICD-03's OIDC/no-token wiring (built version `0.1.0.post119` asserted, names-only secret readback clean) and CICD-04's release-please wiring + deterministic-0.2.0 seed, with the live TestPyPI dispatch, real publish, first `v0.2.0` tag, and ruleset enablement honestly deferred to ship.**

## Performance

- **Duration:** ~54 min wall (includes a mid-plan checkpoint where the A/B/C + disk-fix decisions were taken)
- **Started:** 2026-06-28T08:46Z
- **Completed:** 2026-06-28
- **Tasks:** 3
- **Files created:** 1; **modified:** 4 (+ STATE/ROADMAP/REQUIREMENTS at finalize)

## Accomplishments

- **CICD-01 / CICD-02 proven by a real green run.** PR #6 (`develop` ← `gsd/phase-05-ci-cd-release`, **open, not merged**) drove Actions run `28317897531` green across Lint (ruff + pyright), Test (core, 3.12), Test (f2s3, 3.12), Build wheel + install smoke, Docs build. The trigger is `pull_request`/`push` to `main`+`develop` only, so a PR against `develop` is the canonical CI-trigger path (a bare branch push runs nothing).
- **The verification did its job — four latent defects caught and fixed.** The lean CI `core` env (`.[dev]`) exposed what local development (full iof3D stack) masked. All four are recorded in `05-VERIFICATION.md` with the run that surfaced each.
- **CICD-03 wiring proven.** Environments `pypi`/`testpypi` exist; prohibited PyPI-token patterns defined; names-only GitHub secrets readback = `[APP_ID, APP_PRIVATE_KEY]` (no `*PYPI*TOKEN*`) → OIDC-only. Built version asserted `0.1.0.post119` (twine PASSED) — a branch build yields a deterministic `.postN` dev version, never `0.2.0`.
- **CICD-04 gate (not omitted).** release-please wiring proven (workflow_run[CI]@main, `conclusion==success`, App token v3.2.0 + rp-action v5.0.0 both SHA-pinned, no GITHUB_TOKEN/PAT) and the deterministic-0.2.0 seed proven (manifest `0.1.0` + reachable `Release-As: 0.2.0` footer `ce1dcfc`); the ordered ship-time release→tag→publish procedure is recorded.

## Task Commits

Per-task verification writes plus the in-phase fixes (all atomic):

1. **CI-trigger blocker (forward-only merge)** — `db447d3` (merge `origin/develop`, STATE.md conflict resolved)
2. **Fix A — pyarrow core dependency** — `0482c20` (fix)
3. **Fix C — pchandler importorskip guard** — `65a3630` (fix)
4. **Fix B — Ax 1.3.x complete_trial adaptation + pin widen** — `bb8c1b9` (fix)
5. **Build disk reclaim + --no-cache-dir** — `aefb50a` (fix)

(05-VERIFICATION.md + this SUMMARY + STATE/ROADMAP/REQUIREMENTS land in the final docs commit.)

## Deviations from Plan

The plan's frontmatter declared only `05-VERIFICATION.md` as modified, but reaching a green CI run required fixing real defects the lean env surfaced. These were **not** applied unilaterally: on first diagnosis the executor **stopped at a checkpoint** and surfaced the red-CI finding with options; the user returned **PATH 1** (apply A/B/C on the phase branch, iterate to green). Tracked deviations:

- **[Rule 3 - Blocking] CI never enqueued (merge conflict).** The PR was `CONFLICTING` on `.planning/STATE.md` (Phase-4 ship diverged `develop`), so GitHub could not build the merge ref. Fixed forward-only by merging `origin/develop` in and resolving STATE.md — no prior phase commit rewritten. Commit `db447d3`.
- **[Rule 2 - Missing critical functionality] Parquet engine.** `ResultsStore` (core persistence) writes parquet via pandas with no declared engine. Added `pyarrow >= 16`. Commit `0482c20`.
- **[Rule 1 - Bug] Ax 1.3.x API drift.** `ax-platform ~= 1.1` resolved to 1.3.1, which rejects unregistered metrics in `complete_trial`. Adapted the runner to pass the objective only; widened the pin to `>= 1.3, < 2.0`. Validated in an isolated CI-mirror venv (ax 1.3.1) + back-compat on dev-env ax 1.1.2. Commit `bb8c1b9`.
- **[Rule 1 - Bug] Test/dep coupling.** A `tests/core` test required pchandler (only in `[f2s3]`). Guarded with `pytest.importorskip`. Commit `65a3630`.
- **[Rule 3 - Blocking, CI-config] Build disk exhaustion.** First-ever install-smoke filled the ~14 GB runner (torch + CUDA wheel stack). Reclaimed unused toolchains + `--no-cache-dir`. Commit `aefb50a`.

No Rule 4 architectural change beyond the checkpointed dependency/version decisions, which the user approved.

## Verification Evidence

- **Final green run:** `28317897531` — all five jobs success (per-job table in `05-VERIFICATION.md`). PR #6 OPEN, `mergedAt: null`.
- **Local repro (conda env):** ruff clean, format clean, pyright 0 errors/9 warns; build+twine PASSED; `python -m pytest tests/core` 128 passed (ax 1.1.2 back-compat), `tests/f2s3` 2 passed.
- **Isolated CI-mirror venv (ax 1.3.1 + pyarrow 24.0.0, numpy 2.5.0):** the 5 previously-failing core tests pass; full `tests/core` 127 passed + 1 skipped (pchandler). Venv torn down.
- **ci.yml integrity after the build-job edit:** parses; job names unchanged; `check_publish_gate.py` and `check_ci_ruleset_contexts.py` both pass.
- **Task 2/3 asserts:** built version `0.1.0.post119`; secrets `[APP_ID, APP_PRIVATE_KEY]` only; release-please wiring + 0.2.0 seed asserts pass (commands in `05-VERIFICATION.md`).

## Threat Surface

No new security surface. Observed dispositions: T-05-02 (no stored PyPI token — names-only readback clean), T-05-12 (prereqs confirmed + built-version assertion + CICD-04 gate; real publish gated to ship), T-05-09 (ruleset enablement deferred to ship), T-05-16 (skip-existing-disabled proof carried to the ship-time dry-run). No `## Threat Flags`.

## Known Stubs

None. The verification artifact records real observed results; no placeholder data or TODO/FIXME introduced. CICD-03/04 are intentionally gated (wiring proven, end-to-end pending ship) — not stubs, and documented as such.

## Deferred (ship-time, under human control)

Live TestPyPI `workflow_dispatch` dry-run (blocked now: `publish-testpypi.yml` not on default branch `main`), real PyPI publish, first `v0.2.0` tag, ruleset enablement (`apply-rulesets.sh`), and the `pypi` required-reviewer approval gate (HTTP 422 while private; apply after go-public). Repo remains **private**.

## Self-Check: PASSED

- `05-VERIFICATION.md` present on disk.
- All five task commits found: `db447d3`, `0482c20`, `65a3630`, `bb8c1b9`, `aefb50a`.
- Final CI run `28317897531` green across all five jobs; PR #6 open (not merged).

---
*Phase: 05-ci-cd-release*
*Completed: 2026-06-28*
