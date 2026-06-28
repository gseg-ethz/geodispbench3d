---
phase: 05-ci-cd-release
plan: 05
subsystem: ci-cd-release
tags: [github-actions, ci, matrix, composite-action, sha-pinning, actionlint, supply-chain, interface-contract, pyright, twine]

requires:
  - phase: 05-ci-cd-release
    plan: 01
    provides: "Python 3.12-only baseline + genuine 0-error scoped pyright gate (the lint job runs it on .[f2s3,dev])"
  - phase: 05-ci-cd-release
    plan: 04
    provides: "protect-{main,develop}.json required_status_checks contexts — the char-for-char interface ci.yml job names must render"
  - phase: 05-ci-cd-release
    plan: 03
    provides: "publish-pypi.yml / publish-testpypi.yml (the only files allowed to carry a publish mechanism); name:CI consumed by release-please workflow_run"
provides:
  - "Restructured ci.yml: lint ‖ test matrix (3.12-only core+f2s3), build needs:[test], independent Docs build; all uses: SHA-pinned, \"on\" quoted"
  - "Rendered job names Test (core, 3.12) / Test (f2s3, 3.12) + Lint (ruff + pyright) + Build wheel + install smoke — satisfy the Plan 04 ruleset gate"
  - "setup-python-deps composite (python-version + extras inputs) — the single dependency-install impl for the test/build/docs jobs"
  - "check_publish_gate.py — supply-chain guard (publish mechanisms only in the two publish workflows)"
  - "check_ci_ruleset_contexts.py — in-phase reconciliation guard (rendered ci.yml names == both ruleset context sets)"
  - "Checksum-verified pinned actionlint (1.7.7) provisioned + run in the lint job"
affects: [05-06 integration verification (live CI-green observation + TestPyPI dry-run)]

tech-stack:
  added: []
  patterns:
    - "Parametrized composite action as the one CI dependency-install implementation (scoped to CI jobs; publish workflows stay inline)"
    - "asymmetric test matrix via strategy.matrix.include (core+f2s3 on 3.12 only; pchandler 2.1.0 is >=3.12,<3.13)"
    - "rendered matrix job name as a char-for-char interface contract with branch-protection required_status_checks, machine-checked in-phase"
    - "supply-chain tool provisioning by pinned-version binary + hardcoded SHA256 verify (fail closed) instead of a floating action"
    - "two CI lint-job guard scripts (publish-gate + ruleset-context) run in CI, not only locally"

key-files:
  created:
    - .github/actions/setup-python-deps/action.yml
    - .github/scripts/check_publish_gate.py
    - .github/scripts/check_ci_ruleset_contexts.py
  modified:
    - .github/workflows/ci.yml

key-decisions:
  - "actionlint pinned to 1.7.7 linux_amd64, sha256 023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757, verified before exec (fail closed) — recorded in a supply-chain inventory comment (T-05-15)"
  - "lint job does NOT use the composite (it installs .[f2s3,dev] + provisions actionlint); the composite is mandatory for test/build/docs only, per the review-MEDIUM scoping"
  - "build job uses the composite for setup then adds `pip install build twine` (no `build` extra exists); the editable install is harmless under build isolation"
  - "Docs build job is excluded from the reconciliation guard's required-context set — blocking-on-PR but not a required_status_check (RTD activates post-public)"

requirements-completed: [CICD-01, CICD-02]

coverage:
  - id: CICD-01
    description: "CI runs lint (ruff), type-check (pyright), and the full test matrix on Python 3.12"
    requirement: "CICD-01"
    verification:
      - kind: integration
        ref: "ci.yml parses; lint job runs ruff check + ruff format --check + scoped pyright; test matrix renders Test (core, 3.12) + Test (f2s3, 3.12); lint ‖ test (no needs chain). Locally: ruff check . + ruff format --check . clean; pyright = 0 errors, 9 warnings"
        status: pass
      - kind: integration
        ref: "live CI-green observation on a PR against develop"
        status: deferred  # Plan 06 phase gate
    human_judgment: false
  - id: CICD-02
    description: "CI builds wheel + sdist and validates the distribution (twine check)"
    requirement: "CICD-02"
    verification:
      - kind: integration
        ref: "build job (needs:[test]) runs python -m build → twine check → install-smoke → upload-artifact. Locally in an isolated venv: built geodispbench3d-*.whl + .tar.gz, twine check → PASSED (both)"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-06-28
status: complete
---

# Phase 5 Plan 05: CI Restructure — lint ‖ matrix, build gate, docs, supply-chain guards Summary

**Restructured `ci.yml` to the D-02/D-03(3.12-only)/D-07 topology — lint and a 3.12 core+f2s3 test matrix run in parallel, a twine-checked build gates behind the tests, an independent Sphinx Docs build runs warnings-as-errors, and every action is SHA-pinned — then reconciled the rendered matrix job names to render `Test (core, 3.12)` / `Test (f2s3, 3.12)` char-for-char with the Plan 04 rulesets, added a parametrized `setup-python-deps` composite as the one CI dependency-install path, provisioned a checksum-verified pinned actionlint, and shipped two CI lint-job guard scripts (publish-gate + ruleset-context reconciliation).**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-06-28T07:57Z
- **Completed:** 2026-06-28T08:11Z
- **Tasks:** 4
- **Files created:** 3; **modified:** 1

## Accomplishments

- **Critical interface reconciliation (load-bearing).** The pre-existing `ci.yml` rendered `Test (core)` / `Test (f2s3)` (matrix `name: Test (${{ matrix.job.name }})`), which would have left the Plan 04 ruleset gate permanently unsatisfiable. The restructured test job uses `name: Test (${{ matrix.suite }}, ${{ matrix.python }})` over an `include:` matrix, rendering exactly `Test (core, 3.12)` and `Test (f2s3, 3.12)` — matching `protect-main.json` / `protect-develop.json` char-for-char. `check_ci_ruleset_contexts.py` now machine-asserts this equality in CI.
- **setup-python-deps composite (Task 1).** Parametrized (`python-version` default `3.12`, `extras` default `dev`): SHA-pinned `setup-python` + `actions/cache` + `pip install -e .[extras]`. Mandatory for the test/build/docs jobs (one dependency-install implementation); the Plan 03 publish workflows intentionally stay inline. Caller-must-checkout-first documented.
- **check_publish_gate.py (Task 2).** Scans `.github/workflows/*.yml`, parses step structures, and asserts any publish mechanism (`pypa/gh-action-pypi-publish` at any ref; `twine upload` / `python -m twine upload` / `python3 -m twine upload` / `sh -c` shell-indirection) lives only in `publish-pypi.yml` / `publish-testpypi.yml`. Exits non-zero naming the offending file/step; documents the variable-hidden + reusable-workflow limitations in the failure message (T-05-03).
- **ci.yml restructure (Task 3).** `name: CI` preserved (release-please `workflow_run` dep), `"on"` quoted (PyYAML boolean-key trap). Lint job: install `.[f2s3,dev]`, ruff check + ruff format --check + scoped pyright (genuine 0-error per Plan 01), provision checksum-verified actionlint, then run `actionlint` + both guard scripts. Test job: dropped `needs:[lint]` (lint ‖ test), `include:` matrix (core + f2s3, 3.12-only; iof3d omitted; f2s3 parser-only). Build job: `needs:[test]`, composite setup, kept twine check + install-smoke + upload-artifact, SHA-pinned checkout/upload, retained `fetch-depth:0 + fetch-tags:true`. Docs job: independent, composite `extras=docs`, `sphinx-build -W --keep-going`.
- **check_ci_ruleset_contexts.py (Task 4).** Renders the required ci.yml job names (lint + build literal names, test name template expanded over `strategy.matrix.include`), excludes the Docs job, loads both rulesets' `required_status_checks` contexts, and asserts all three sets equal the canonical four-context set; prints the symmetric difference on any one-character drift (T-05-10). Verified: a temporary `Test (core, 3.12)`→`Test (core, 3.11)` drift in a ruleset makes it exit non-zero.

## Task Commits

1. **Task 1: parametrized setup-python-deps composite** — `120fdf3` (feat)
2. **Task 2: check_publish_gate.py supply-chain guard** — `c8b7b12` (feat)
3. **Task 3: restructure ci.yml (lint ‖ matrix, build gate, docs, SHA pins)** — `ea25ea0` (feat)
4. **Task 4: check_ci_ruleset_contexts.py reconciliation guard** — `d763729` (feat)

## Files Created/Modified

- `.github/actions/setup-python-deps/action.yml` (new) — composite: setup-python `a309ff8b…` (v6.2.0) + cache `27d5ce7f…` (v5.0.5) + `pip install -e .[extras]`; inputs python-version/extras; caller-checkout + scope notes.
- `.github/scripts/check_publish_gate.py` (new) — stdlib + yaml; step-structure scan; hardened publish-mechanism detection; allowed = {publish-pypi.yml, publish-testpypi.yml}.
- `.github/scripts/check_ci_ruleset_contexts.py` (new) — stdlib json + yaml; renders matrix names; three-way equality against the canonical contexts; symmetric-diff diagnostics.
- `.github/workflows/ci.yml` (restructured) — lint ‖ test matrix, build needs:[test], Docs build; actionlint provisioning; both guards; all SHA-pinned; `"on"` quoted; `name: CI` kept.

## Decisions Made

- **actionlint provisioned, not assumed.** It is absent from the conda env and the `dev` extra, so the lint job downloads `actionlint_1.7.7_linux_amd64.tar.gz` and verifies its SHA256 (`023070a2…`, fetched live from the official `actionlint_1.7.7_checksums.txt`) before executing — fail closed on mismatch. The version + digest are recorded in a supply-chain inventory comment (T-05-15 / review HIGH 05-05).
- **Composite scope is CI-only.** The lint job deliberately does not use the composite (it installs `.[f2s3,dev]` for pyright import resolution and provisions actionlint); the composite is mandatory for test/build/docs. The publish workflows keep inline setup (they verified independently in Wave 2). This is the review-MEDIUM scoping, honored here and in Plan 03.
- **Build job composite + build tooling.** No `build`/`twine` extra exists, so the build job runs the composite for python+cache+editable install, then `pip install build twine`. The editable install is redundant-but-harmless under PEP 517 build isolation.
- **Docs excluded from the required-context set.** The reconciliation guard intentionally omits the `Docs build` job — it is blocking-on-PR but not a `required_status_check` until RTD activates post-public (planning amendment Q4).

## Deviations from Plan

None — all four tasks landed exactly per their `<action>` blocks. No Rule 1/2/3 auto-fixes and no Rule 4 architectural pauses. (One within-scope formatting touch: `ruff format` reshaped two lines in `check_publish_gate.py` immediately after authoring, folded into the Task 2 commit — not a behavior change.)

## Verification Evidence

- **ci.yml structure:** `yaml.safe_load` clean; `name=='CI'`; `"on"` has pull_request+push (not coerced to boolean True); `test` has no `needs`; `build.needs==['test']`; `actionlint` + `sha256` + both guard-script names present in source.
- **Interface strings (load-bearing):** lint name `Lint (ruff + pyright)`; build name `Build wheel + install smoke`; test template renders `{Test (core, 3.12), Test (f2s3, 3.12)}`; top-level `name: CI`. `check_ci_ruleset_contexts.py` exits 0 (rendered == protect-main == protect-develop == canonical four), and exits 1 on an injected one-character drift.
- **check_publish_gate.py:** exits 0 against the current four workflows; a temp `zz-evil.yml` with `python -m twine upload` makes it exit 1 with a file/step-named message.
- **Local lint/type gate (AGENTS conda env):** `ruff check .` All checks passed; `ruff format --check .` 66 files already formatted; `pyright` → **0 errors**, 9 warnings (warnings don't fail the gate).
- **CICD-02 build:** in an isolated venv `python -m build` produced `geodispbench3d-0.1.0.post108-py3-none-any.whl` + `.tar.gz`; `twine check dist/*` → **PASSED** (both).
- **Deferred to CI/Plan 06 (not runnable locally):** the actual `actionlint` run (binary not installed locally — the checksum is real and the workflow YAML parses cleanly), and the live CI-green observation on a PR against develop (Plan 06 phase gate). Matches Plan 03's same deferral pattern.

## Threat Surface

No new security surface beyond the plan's `<threat_model>`. Mitigations implemented: SHA-pinned actions (T-05-01); `check_publish_gate.py` confines publish mechanisms to the two publish workflows (T-05-03); top-level `permissions: contents: read`, no write scopes in ci.yml jobs (T-05-04); lint ‖ test with no needs-chain so a lint failure can't skip the matrix (T-05-11); checksum-verified actionlint binary, fail-closed (T-05-15). No `## Threat Flags` to report.

## Known Stubs

None. All three new files and the restructured workflow are complete; no placeholder values, empty data sources, or TODO/FIXME markers were introduced. The dormant `iof3d` matrix slot is intentionally omitted (Phase 4 deferral), not stubbed.

## Next Phase Readiness

- **Plan 06 (integration verification)** owns the live proof: a PR against develop exercising the full CI run green (CICD-01 phase gate), a TestPyPI `workflow_dispatch` dry-run (CICD-03), and — at ship — `apply-rulesets.sh` (the rendered job names now satisfy the gate). The reconciliation guard guarantees the contexts already match.
- **External prerequisites (unchanged, from Plan 03):** PyPI/TestPyPI pending publishers, the gseg-ethz App secrets, and the `pypi`/`testpypi` GitHub Environments must be provisioned before the first real publish.
- No code blockers.

## Self-Check: PASSED

- All 3 created files + the modified ci.yml present on disk.
- All four task commits found in git history (`120fdf3`, `c8b7b12`, `ea25ea0`, `d763729`).

---
*Phase: 05-ci-cd-release*
*Completed: 2026-06-28*
