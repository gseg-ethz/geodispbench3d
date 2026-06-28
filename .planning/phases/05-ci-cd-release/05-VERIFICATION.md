---
phase: 05-ci-cd-release
plan: 06
kind: integration-verification
human_verify_mode: end-of-phase
date: 2026-06-28
status: complete
requirements: [CICD-01, CICD-02, CICD-03, CICD-04]
---

# Phase 05 — Integration Verification (Plan 06)

Records the observed end-to-end results of the assembled CI/CD + release pipeline,
the in-phase fixes required to reach a green CI run, and the irreversible steps
explicitly deferred to milestone-ship under human control.

**Repo unchanged:** `gseg-ethz/geodispbench3d` is still **private**. No real publish,
no `v0.2.0` tag, no ruleset enablement, no approval-gate change were performed.

---

## Task 1 — CI green via a PR against `develop`

The CI trigger is `pull_request`/`push` to `main`+`develop` **only** (`.github/workflows/ci.yml:7-11`);
a bare phase-branch push runs nothing. CI was exercised by opening a PR against `develop`.

| Item | Value |
| --- | --- |
| Pull request | https://github.com/gseg-ethz/geodispbench3d/pull/6 |
| PR base ← head | `develop` ← `gsd/phase-05-ci-cd-release` |
| PR state | **OPEN, not merged** (`mergedAt: null`) — exists only to exercise CI |
| Final green Actions run | https://github.com/gseg-ethz/geodispbench3d/actions/runs/28317897531 |
| Head SHA | `aefb50a` |

### Final per-job status (all five green)

| Job | Conclusion |
| --- | --- |
| Lint (ruff + pyright) | ✅ success |
| Test (core, 3.12) | ✅ success |
| Test (f2s3, 3.12) | ✅ success |
| Build wheel + install smoke | ✅ success |
| Docs build | ✅ success |

### Local reproduction (conda env `iof3d_cosicorr3d-dev312`, before pushing)

- Fast gate: `ruff check .` clean · `ruff format --check .` 66 files formatted · `pyright` **0 errors, 9 warnings**.
- Build gate: `python -m build` → wheel+sdist · `twine check dist/*` **PASSED** (both).
- Tests: `python -m pytest tests/core` 128 passed · `tests/f2s3` 2 passed.
  (Note: use `python -m pytest`, not bare `pytest` — bare resolves to a user-site Python 3.13.)

### Findings surfaced and fixed in-phase (the verification did its job)

The first PR push could not even start CI, and the first real run was **red** — the lean CI
`core` env (`.[dev]` only) exposed latent defects the fat local dev env masked. This is exactly
what the publication-readiness milestone exists to catch ("demonstrably lean, correct, well-tested").

| # | Run | Finding | Fix (atomic `fix(05-06)` commit) |
| - | --- | ------- | --- |
| 0 | (PR `CONFLICTING`) | GitHub could not build the PR merge ref (`.planning/STATE.md` diverged from the Phase-4 ship on `develop`), so **CI never enqueued**. | Forward-only merge of `origin/develop` into the phase branch, STATE.md conflict resolved (`db447d3`). No prior phase commit rewritten. |
| 1 | `28317105591` RED | `test_store.py` (×2) — `ImportError: Unable to find a usable engine; tried 'pyarrow','fastparquet'`. `ResultsStore` writes parquet via pandas but no engine was a declared core dep (present locally only transitively). | **A** — declare `pyarrow >= 16` (first NumPy-2 series; resolves to 24.0.0 in CI / 19.0.1 locally under `numpy ~= 2.0`) as a core dependency (`0482c20`). |
| 2 | `28317105591` RED | `test_parser_path_resolves_without_iof3d` — `ModuleNotFoundError: No module named 'pchandler'`. A `tests/core` test asserts a contract *about* pchandler, which lives only in the `[f2s3]` extra. | **C** — `pytest.importorskip("pchandler")`; skips cleanly in the lean core suite, still runs for real in the f2s3 suite and the dev env (`65a3630`). |
| 3 | `28317105591` RED | `test_sweep_*` (×2) — `ax.exceptions.core.UserInputError: Metric(s) {'runtime_seconds'} not found in metric_name_to_signature`. `ax-platform ~= 1.1` resolved to **1.3.1** in CI; 1.3.x tightened `complete_trial` to reject metrics not registered on the experiment. | **B** — pass only the registered objective metric to `complete_trial` (`_objective_raw_data`); loss-free (extras persist to parquet via `on_record_rows`, `get_best_trial` output only logged). Pin widened to `ax-platform >= 1.3, < 2.0` (`bb8c1b9`). Validated in an isolated CI-mirror venv (ax 1.3.1): the 5 failing core tests pass; back-compatible on the dev env's ax 1.1.2 (128 passed). |
| 4 | `28317673439` RED | `Build wheel + install smoke` — `OSError: [Errno 28] No space left on device`. First time this step ran (it was skipped while Test was red). `ax-platform → botorch → torch` + the NVIDIA CUDA wheel stack (several GB), installed into the fresh smoke venv on top of the job's deps, exhausted the ~14 GB runner disk. | **CI-infra** — reclaim large unused preinstalled toolchains (android/dotnet/ghc/CodeQL; Python toolcache untouched) before the heavy install, and `--no-cache-dir` on the smoke install so the multi-GB wheels are not retained (`aefb50a`). |

`check_ci_ruleset_contexts.py` and `check_publish_gate.py` still pass after the ci.yml change
(job names unchanged, no publish mechanism added).

**CICD-01 / CICD-02: proven by the green run** (lint+type+matrix on 3.12; wheel+sdist built,
`twine check`, install-smoke).

---

## Task 2 — External prerequisites + TestPyPI OIDC dry-run

### External prerequisites — CONFIRMED

| Prereq | State |
| --- | --- |
| GitHub Environments `pypi`, `testpypi` | EXIST (`gh api .../environments` → both present, `protection_rules: []`) |
| Repo secrets for the release-please App | `APP_ID`, `APP_PRIVATE_KEY` present (repo-level) |
| `gseg-release-please` GitHub App | Installed on the repo |
| PyPI + TestPyPI pending trusted publishers | Registered for project `geodispbench3d` (user-confirmed) |

### Built-version assertion (review MEDIUM 05-06)

A branch build with no new tag receives a deterministic setuptools_scm **post-release dev**
version, not `0.2.0`:

```
$ python -m build && twine check dist/*
geodispbench3d-0.1.0.post119-py3-none-any.whl   PASSED
geodispbench3d-0.1.0.post119.tar.gz             PASSED
ASSERT built version = 0.1.0.post119   (HEAD aefb50a)
```

The real `0.2.0` is produced only by the release-please tag at ship (see Task 3), never by a
branch build — this is why the live dry-run uploads a `.postN` artifact and why a TestPyPI
proof must disable `skip-existing` (each `.postN` is unique anyway).

### Prohibited PyPI-token secrets — NONE present (T-05-02)

Prohibited names/patterns (case-insensitive): `PYPI_API_TOKEN`, `TEST_PYPI_API_TOKEN`,
`TWINE_PASSWORD`, `TWINE_USERNAME`, `*PYPI*TOKEN*`, `*PYPI*PASSWORD*`.

Names-only GitHub secrets API readback (values are never exposed):

```
$ gh api repos/gseg-ethz/geodispbench3d/actions/secrets --jq '[.secrets[].name]'
["APP_ID", "APP_PRIVATE_KEY"]
```

No secret matches any prohibited pattern → publishing is OIDC-only; no stored PyPI token can
cross the runner→PyPI boundary.

### Live TestPyPI `workflow_dispatch` dry-run — SHIP-TIME-DEFERRED (honest deferral)

The live OIDC dry-run is **not** run now, for a precise branch-topology reason (independent of
repo visibility): `workflow_dispatch` can only dispatch a workflow that exists on the repo's
**default branch** (`main`). `publish-testpypi.yml` currently lives only on the phase branch
`gsd/phase-05-ci-cd-release`; a dispatch now would 404 / no-op. A skipped run must not be
misreported as a successful OIDC proof, so it is deferred rather than faked.

**Fires as the first post-merge step at ship**, once the publish workflows reach `main`:
trigger `publish-testpypi.yml` via `workflow_dispatch` with `skip-existing` disabled (or a
unique version), confirm the exact built version is newly created on test.pypi.org via OIDC,
and record the version + URLs. This is the end-to-end proof of **CICD-03**.

---

## Task 3 — CICD-04 release-please verification gate

CICD-04 is **not** marked complete on TestPyPI success alone (review HIGH 05-06). The
release-please path is proven as far as is safe in-phase, without cutting a real release.

### (1) Wiring proof — PASS

`.github/workflows/release-please.yml` (comment lines stripped before scanning active wiring):

- triggers on `workflow_run: workflows: [CI], types: [completed], branches: [main]`;
- gated `if: github.event.workflow_run.conclusion == 'success'`;
- mints a short-lived **gseg-ethz App token** via `actions/create-github-app-token@bcd2ba49…` (v3.2.0, SHA-pinned), using `secrets.APP_ID` + `secrets.APP_PRIVATE_KEY`;
- drives `googleapis/release-please-action@45996ed1…` (v5.0.0, SHA-pinned);
- **no `GITHUB_TOKEN` and no `RELEASE_PLEASE_TOKEN`/PAT** in the active wiring (GITHUB_TOKEN appears only in an explanatory comment).

### (2) Deterministic-0.2.0 seed proof — PASS

- `.release-please-manifest.json` is `{".": "0.1.0"}` (aligned with `setuptools_scm` `fallback_version`).
- A reachable `Release-As: 0.2.0` footer forces the first cut to exactly `0.2.0` (otherwise
  `bump-patch-for-minor-pre-major` would cut `0.1.1`):
  `git log --grep='Release-As: 0.2.0'` → `ce1dcfc chore(05-03): seed durable 0.1.0 manifest baseline and bootstrap v0.2.0`.
- No sticky `release-as` in `release-please-config.json`.

### (3) Ship-time release → tag → publish procedure (completes CICD-04)

Ordered sequence, executed at `/gsd-ship` after the phase merges to `main`:

1. CI runs green on `main` (the same five jobs proven here).
2. `release-please.yml` fires on `workflow_run [CI] completed @ main` (conclusion success) and
   opens the release PR — version `0.2.0` from the manifest + `Release-As` footer.
3. Merge the release PR → release-please creates the immutable `v0.2.0` tag and a GitHub Release.
4. `publish-pypi.yml` triggers on `release: published`.
5. `check_release_preflight.py` passes (tag `^v\d+\.\d+\.\d+$`, built version == tag, not
   draft/prerelease, tag reachable from `main`).
6. OIDC publish to real PyPI via `pypa/gh-action-pypi-publish` bound to env `pypi` — no stored token.

**CICD-04 status: wiring + deterministic-0.2.0 seed proven in-phase; the end-to-end first cut is
explicitly pending the first ship-time release.** (Mirrors the in-phase-vs-ship ledger discipline
of plans 01/03 — addressed and gated, never silently omitted.)

---

## Deferred ship-time actions (NOT performed now)

| Action | Why deferred | How / when |
| --- | --- | --- |
| Live TestPyPI `workflow_dispatch` dry-run (CICD-03 end-to-end) | `publish-testpypi.yml` not yet on `main` → dispatch 404s | First post-merge step at ship |
| Real PyPI publish + first `v0.2.0` tag (CICD-04 end-to-end) | Irreversible; gated on human ship | `/gsd-ship` → merge release PR |
| Ruleset enablement (`apply-rulesets.sh`) | Enabling before the green run lands on `main` = self-lockout (T-05-09) | Ship-time, after CI green on `main` |
| `pypi` required-reviewer approval gate | Environment protection rules unavailable for a **private** repo (HTTP 422) | After go-public: `gh api --method PUT repos/gseg-ethz/geodispbench3d/environments/pypi --input - <<<'{"reviewers":[{"type":"User","id":49650019}]}'` |

---

## Requirements ledger

| Req | Status this run |
| --- | --- |
| CICD-01 | **Complete** — lint+type+full 3.12 matrix green on the PR-against-develop run. |
| CICD-02 | **Complete** — wheel+sdist build, `twine check`, install-smoke green on the same run. |
| CICD-03 | Wiring proven (OIDC publish-testpypi/publish-pypi workflows, no stored token, names-only readback clean). **End-to-end pending** the ship-time live TestPyPI dispatch. |
| CICD-04 | Wiring + deterministic-0.2.0 seed proven. **End-to-end pending** the first ship-time release→tag→publish cut. |

---

## Threat-model dispositions observed

| Threat | Disposition observed |
| --- | --- |
| T-05-02 (stored PyPI token sneaking in) | Mitigated — prohibited-pattern list defined; names-only readback shows only `APP_ID`/`APP_PRIVATE_KEY`. |
| T-05-12 (first release fails / wrong version, missing prereqs) | Mitigated — prereqs confirmed; built-version assertion recorded; CICD-04 wiring+seed gate; real publish gated to ship. |
| T-05-16 (stale TestPyPI artifact masking an unaccepted upload) | Carried to ship — the dry-run will disable `skip-existing` and confirm the exact version newly created on test.pypi.org. |
| T-05-09 (rulesets-before-green self-lockout) | Mitigated — ruleset enablement explicitly deferred to ship. |
