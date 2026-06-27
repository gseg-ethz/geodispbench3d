---
phase: 5
reviewers: [codex]
reviewed_at: 2026-06-27T22:19:27Z
plans_reviewed: [05-01-PLAN.md, 05-02-PLAN.md, 05-03-PLAN.md, 05-04-PLAN.md, 05-05-PLAN.md, 05-06-PLAN.md]
---

# Cross-AI Plan Review — Phase 5

> Reviewer: **Codex** (`codex-cli 0.142.2`, source-grounded against the live working tree).
> Single-reviewer pass requested via `/gsd-review --phase 5 --codex`. The
> "Key Findings" section below distills Codex's highest-priority concerns in lieu
> of a multi-reviewer consensus.

## Codex Review

## Overall assessment

The architecture is coherent and substantially improves the current pipeline: today `test` depends on the failing lint job and `build` depends on `test`, so one pyright failure suppresses all downstream validation (`.github/workflows/ci.yml:47-49`, `86-88`). The plans correctly separate lint and tests, preserve setuptools-scm tag discovery, use OIDC, pin actions, and machine-check ruleset context names.

However, several execution gaps prevent accepting the plans unchanged. The most important are: the v0.2.0 bootstrap is only documentation rather than durable repository state; Plan 01 omits test files that currently contain pyright errors; Plan 05 never specifies how `actionlint` becomes available; moving docs leaves the package Documentation URL broken; and Plan 06's "push the phase branch" will not trigger the workflow unless a PR is opened.

Overall risk: **HIGH until the release seeding and CI execution gaps are corrected; MEDIUM afterward.**

---

## 05-01 — Python 3.12 and pyright foundation

### Summary

The plan correctly addresses the actual standing-red type gate rather than preserving a baseline-diff workaround. The scope is mostly appropriate, but its declared edit set cannot produce the promised zero-error pyright result because pyright includes tests and current errors exist under `tests/core/`.

### Strengths

- The Python migration edits the actual source-of-truth fields: `requires-python` is currently 3.11-compatible (`pyproject.toml:8`), the 3.11 classifier remains (`pyproject.toml:17`), Ruff targets `py311` (`pyproject.toml:113-116`), and pyright targets 3.11 (`pyrightconfig.json:12`).
- Excluding only the dormant iof3D package is defensible. It ships publicly (`pyproject.toml:100`) even though its dependencies are deliberately unavailable (`pyproject.toml:51-64`).
- Installing `.[f2s3,dev]` before pyright is necessary because the F2S3 parser imports `pchandler` (`src/geodispbench3d_f2s3/output_parser.py:28-30`).
- The plan explicitly fixes genuine source errors instead of globally suppressing them. Current examples include unsafe NumPy narrowing (`src/geodispbench3d/results/predictions_cache.py:199-206`) and attribute probing that pyright cannot narrow (`src/geodispbench3d/sweep/runner.py:646-663`).

### Concerns

- **HIGH — The file scope omits existing test errors.** `pyrightconfig.json:2` includes both `src` and `tests`. A current mandated-environment run reports errors at `tests/core/test_loaders.py:97` and `tests/core/test_rescore.py:153-155`, but Plan 01 only declares `src/geodispbench3d/**` for residual fixes. It cannot meet "pyright exits 0" without editing tests, changing include scope, or proving dependency installation changes the inferred types.
- **MEDIUM — Missing regression coverage for the Python support declaration.** Existing packaging tests verify licensing and URLs (`tests/core/test_packaging_metadata.py:49-113`) but do not assert `requires-python`, classifiers, Ruff target, or pyright version.
- **LOW — Installing docs dependencies mutates the shared development environment.** This follows the mandated Conda environment, but the plan should record resolved versions and avoid claiming exact pins merely because one mutable environment resolves them.

### Suggestions

- Add `tests/core/test_loaders.py` and `tests/core/test_rescore.py` to `files_modified`, or explicitly narrow pyright to production source and justify excluding tests.
- Capture pyright JSON before editing and require zero errors after installation, not merely shell text containing `exit=`.
- Add packaging tests asserting Python 3.12-only metadata and removal of the 3.11 classifier.
- Run the complete core suite after type fixes, because narrowing changes can alter behavior.

### Risk assessment

**MEDIUM-HIGH.** The direction is correct, but the current edit scope does not match pyright's configured analysis scope.

---

## 05-02 — Sphinx and ReadTheDocs

### Summary

The Sphinx/MyST approach is appropriate for the existing Markdown, but moving the documentation tree has a concrete metadata consequence that the plan misses.

### Strengths

- Existing documentation is already Markdown and organized into tool, integration, and reference sections (`docs/index.md:15-39`), making MyST preferable to an RST rewrite.
- Deriving the version through installed metadata is consistent with setuptools-scm (`pyproject.toml:138-146`).
- Warnings-as-errors is a useful gate for the numerous relative links found throughout the docs, such as `docs/concepts.md:29-57` and `docs/integrating/metrics.md:56-120`.

### Concerns

- **HIGH — Moving `docs/index.md` breaks the published Documentation URL.** Package metadata currently points to `.../blob/main/docs/index.md` (`pyproject.toml:37`). Plan 02 moves that file to `docs/source/index.md` but does not modify `pyproject.toml`.
- **MEDIUM — Repository-relative links need systematic rewriting.** For example, `docs/concepts.md:29` currently uses `../src/...`; after moving into `docs/source/`, it needs an additional parent traversal or an absolute GitHub link. Similar links occur throughout nested pages.
- **MEDIUM — Sphinx warnings alone may not fully validate links to files outside the source tree.** MyST can classify repository-file links differently from documentation cross-references.
- **LOW — Destructive movement creates unnecessary URL churn.** Keeping authored Markdown in place with a small Sphinx source wrapper or symlinks/copies could preserve existing GitHub links.

### Suggestions

- Either update `project.urls.Documentation` to `docs/source/index.md` in this plan or point it to the final RTD URL when available.
- Add a link checker or an explicit script that validates every local Markdown target after the move.
- Consider retaining a compatibility `docs/index.md` that redirects readers to `source/index.md`.
- Add `pyproject.toml` to Plan 02's modified files if the move remains.

### Risk assessment

**MEDIUM.** The docs build is straightforward, but the current plan would publish a dead Documentation URL.

---

## 05-03 — Publish and release automation

### Summary

OIDC publishing and GitHub App authentication are sound choices, but the plan does not actually guarantee the first release is v0.2.0. It also allows any published GitHub Release to invoke real PyPI publication.

### Strengths

- The plan replaces the current mutable actions and PAT/GITHUB_TOKEN fallback (`.github/workflows/release-please.yml:27-36`).
- Fetching full tag history is essential because package versions come from setuptools-scm (`pyproject.toml:138-146`).
- Separating build and publish jobs allows least-privilege permissions.
- Real PyPI and TestPyPI use different environments and attestation behavior, reducing credential and provenance risk.

### Concerns

- **HIGH — v0.2.0 is not seeded in repository state.** The manifest remains `0.0.0` (`.release-please-manifest.json:1-3`), while configuration uses pre-1.0 minor bump behavior (`release-please-config.json:6-8`). Plan 03 explicitly leaves these unchanged and merely documents a future commit footer (`05-03-PLAN.md:156-165`). Therefore its must-have "first cut is exactly v0.2.0" is not established.
- **HIGH — The bootstrap footer is operationally fragile.** It depends on an executor using exactly the intended commit message and that commit remaining in the first release window. Plan 06 then explicitly defers the first tag (`05-06-PLAN.md:103-104`), so no plan verifies the footer is effective.
- **MEDIUM — Real PyPI publish is triggered by any published GitHub Release.** A manually published release or release from an unintended tag can enter the production publish path. The plan does not validate tag format, target branch, expected package version, or correspondence between release tag and built metadata.
- **MEDIUM — Floating major/minor tags add write operations that are unrelated to package publication and may conflict with tag protection.** They need explicit force/update semantics and a documented reason.
- **MEDIUM — PyYAML verification is brittle.** GitHub's `on:` key is parsed as boolean by YAML 1.1 implementations unless quoted. The current workflow uses unquoted `on` (`.github/workflows/ci.yml:3`), while plan verification indexes `d["on"]`.
- **LOW — `files_modified` lists release configuration files that Task 3 intentionally does not modify.**

### Suggestions

- Make v0.2.0 durable: either set the manifest/bootstrap configuration deliberately and remove it after release, or require and verify a committed `Release-As: 0.2.0` footer with `git log`.
- Add a publish preflight script that checks:
  - event tag matches `vX.Y.Z`;
  - built wheel/sdist version equals the release tag;
  - release is not draft/prerelease;
  - tag commit is reachable from `main`.
- Test release-please bootstrap behavior in a disposable repository or with release-please's manifest/config tooling.
- Use a YAML 1.2 parser or quote `"on"` consistently.
- Treat moving floating tags as a separate optional task.

### Risk assessment

**HIGH.** The secure transport is good, but version correctness and production trigger authorization are not sufficiently guaranteed.

---

## 05-04 — Branch protection rulesets

### Summary

The ruleset artifacts and exact-context contract are well conceived. The primary weakness is operational idempotency and a small mismatch between the configured merge methods and linear-history enforcement.

### Strengths

- Exact required check names correspond to the current naming model (`.github/workflows/ci.yml:14`, `47-48`, `86-88`).
- Deferring activation avoids locking the repository while checks are still being renamed.
- Empty bypass actors and required status checks meaningfully enforce the quality gate.
- Machine reconciliation in Plan 05 is stronger than relying on documentation alone.

### Concerns

- **MEDIUM — The apply script is not idempotent.** Repeated POST requests will create duplicate rulesets. A comment showing PUT syntax does not safely select the correct existing ruleset.
- **MEDIUM — Allowing merge commits conflicts with required linear history.** Listing `merge` as an allowed method is misleading when linear history rejects merge commits.
- **MEDIUM — Applying active protection to both branches without a preflight can still lock out maintainers.** The script should verify that all required context names have recently appeared before POST/PUT.
- **LOW — `strict: false` permits merging against an out-of-date base.** This may be intentional for a solo-maintainer workflow, but the tradeoff should be explicit.

### Suggestions

- Query rulesets by name and create-or-update them deterministically.
- Remove `merge` from allowed methods if linear history is required.
- Add `--dry-run` and preflight checks for repository identity, authentication, existing contexts, and App installation.
- Record and verify returned ruleset IDs.

### Risk assessment

**MEDIUM.** The policy is sensible; the application mechanism needs safer lifecycle handling.

---

## 05-05 — CI restructuring

### Summary

The topology directly fixes the present masking problem and the ruleset reconciliation script is valuable. The plan nevertheless omits a viable installation mechanism for `actionlint` and leaves ambiguity around composite-action reuse.

### Strengths

- Removing `needs: [lint]` from tests fixes the current skipped-test failure mode (`.github/workflows/ci.yml:47-50`).
- Keeping build behind tests preserves artifact quality (`.github/workflows/ci.yml:86-88`).
- The matrix accurately reflects the actual F2S3 tests, which only exercise the parser and do not invoke the binary (`tests/f2s3/test_parser.py:1-5`).
- Install-smoke testing is already useful and should be preserved (`.github/workflows/ci.yml:110-118`).
- The context reconciliation script is a strong defense against silent required-check name drift.

### Concerns

- **HIGH — `actionlint` is unavailable and no installation is specified.** It is not present in the current environment, and the dev extra contains only Ruff, pyright, pre-commit, pytest, and coverage (`pyproject.toml:79-85`). "Run an actionlint step" is not executable without adding a pinned binary/action/container acquisition method.
- **MEDIUM — The composite action is optional in the CI rewrite despite being a required artifact.** This creates two possible dependency-install implementations and weakens consistency between test, docs, build, and publish jobs.
- **MEDIUM — The publish workflows are created in Plan 03 before the composite action exists.** If Plan 03 adopts the referenced local composite, it cannot be independently verified in its own wave; if it does not, the claimed shared setup abstraction is inaccurate.
- **MEDIUM — The publish-gate scanner could miss equivalent publishing mechanisms.** Searching only for `gh-action-pypi-publish` and literal `twine upload` will miss shell indirection, `python -m twine upload`, reusable workflows, or custom scripts.
- **LOW — F2S3 CI does not validate the documented conda-run subprocess integration.** The test suite explicitly says no F2S3 binary check exists (`tests/f2s3/conftest.py:7-8`). This is acceptable only because CLI hardening was completed earlier; it should not be described as end-to-end F2S3 execution.

### Suggestions

- Provision `actionlint` explicitly using a verified SHA/checksum or a SHA-pinned action. Include its version in the supply-chain inventory.
- Make composite-action use mandatory for the applicable jobs, or remove it as unnecessary abstraction.
- Run `check_ci_ruleset_contexts.py` in CI, not only locally, so later name drift remains guarded.
- Parse workflow step structures for publish-gate enforcement and recognize `python -m twine upload`.
- Add unit tests for both guard scripts using temporary workflow fixtures.

### Risk assessment

**MEDIUM-HIGH.** The CI graph is correct, but the workflow as described is likely to fail immediately at the unspecified actionlint step.

---

## 05-06 — Integration verification

### Summary

A real CI run and TestPyPI OIDC exercise are appropriate final gates. As written, however, the phase-branch push does not trigger CI, and release-please/CICD-04 is never exercised.

### Strengths

- It correctly distinguishes reversible TestPyPI validation from irreversible production publishing.
- It records external prerequisites rather than treating workflow files as sufficient proof.
- It requires observed job results rather than only local lint/build commands.

### Concerns

- **HIGH — Pushing a phase branch alone will not start CI.** The current and retained trigger only runs pushes to `main` or `develop`, plus PRs targeting those branches (`.github/workflows/ci.yml:3-7`). Plan 06 says only "Push the phase branch and observe the CI run" (`05-06-PLAN.md:70-77`). It must open/update a PR against `develop` or intentionally dispatch a workflow.
- **HIGH — CICD-04 is not verified.** Plan 06 requirements omit CICD-04 and explicitly defers the first tag (`05-06-PLAN.md:103-112`). Consequently, workflow-run → release-please PR → tag/release → production workflow triggering remains untested.
- **MEDIUM — `skip-existing: true` can conceal a stale TestPyPI artifact.** A successful workflow may skip upload rather than prove the newly built artifact was accepted.
- **MEDIUM — No version assertion is recorded for TestPyPI.** With setuptools-scm and no new tag, branch builds may receive post-release versions. The plan should record the exact built and uploaded version.
- **MEDIUM — Checking that "no PyPI token secret exists" may be limited by GitHub secret APIs, which expose names but never values.** Verification should define exactly which secret names are prohibited.

### Suggestions

- Require opening or updating a PR against `develop`, then record the PR and Actions run URLs.
- Add a dry-run/sandbox proof for release-please or explicitly leave CICD-04 pending until the first release succeeds.
- Before TestPyPI upload, inspect wheel metadata and assert the expected version; after upload, query TestPyPI and confirm that exact file/version was newly created.
- Temporarily disable `skip-existing` for the proof run or require a unique version.
- Define prohibited secret names/patterns and record the GitHub API readback used.

### Risk assessment

**HIGH.** The final verification procedure cannot execute as written, and one of the four core CI/CD requirements remains observationally unproven.

---

## Recommended dependency/order changes

1. Fix Plan 01's pyright scope and include test-file corrections.
2. Keep Plan 02 after Plan 01, but update package metadata for the moved docs URL.
3. Split release seeding from Plan 03 and make it durable and verifiable.
4. Keep Plan 04 before Plan 05 for context reconciliation.
5. Specify pinned actionlint provisioning before implementing Plan 05.
6. Make Plan 06 open a PR against `develop`.
7. Add a final release-please verification gate for CICD-04; do not mark the phase complete solely from TestPyPI success.

With those amendments, the four-wave structure is reasonable and the residual risk falls to **MEDIUM**, dominated by external GitHub App/PyPI configuration and first-release behavior.

---

## Key Findings Summary

Single-reviewer pass, so this is a prioritization of Codex's source-grounded
findings rather than a cross-reviewer consensus. The five **HIGH**-severity,
release-blocking gaps — each cited against the live tree — are:

1. **v0.2.0 is not durable repository state (05-03).** Manifest is still `0.0.0`
   (`.release-please-manifest.json:1-3`); the plan relies on a future commit
   footer that no plan verifies. The "first cut is exactly v0.2.0" must-have is
   not established.
2. **Plan 01 cannot reach zero-error pyright as scoped (05-01).** `pyrightconfig.json`
   includes `tests`, and live errors exist at `tests/core/test_loaders.py:97` and
   `tests/core/test_rescore.py:153-155`, but Plan 01 only edits `src/**`.
3. **`actionlint` has no installation mechanism (05-05).** Not in the env, not in
   the `dev` extra (`pyproject.toml:79-85`); the lint job will fail immediately at
   the actionlint step.
4. **Moving docs breaks the published Documentation URL (05-02).** `pyproject.toml:37`
   points at `docs/index.md`; Plan 02 moves it without updating the metadata.
5. **Plan 06's verification cannot execute as written (05-06).** A phase-branch push
   does not trigger CI (trigger is `main`/`develop` + PRs only,
   `.github/workflows/ci.yml:3-7`), and CICD-04 (release-please end-to-end) is
   never exercised.

Cross-cutting **MEDIUM** themes worth folding into a replan: production PyPI
publish is triggerable by any GitHub Release without tag/version preflight
(05-03); the branch-protection apply script is non-idempotent and lists `merge`
while requiring linear history (05-04); and the composite-action abstraction is
"optional" yet referenced as shared infrastructure across waves (05-05/05-03).

**To incorporate this feedback into planning:**
```
/gsd-plan-phase 5 --reviews
```
