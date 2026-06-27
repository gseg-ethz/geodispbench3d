---
phase: 2
slug: targeted-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § Validation Architecture (coverage numbers measured
> this session in `iof3d_cosicorr3d-dev312`).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4 (+ coverage 7.x), `dev` extra |
| **Config file** | none — no `[tool.pytest.ini_options]`/`[tool.coverage]` in `pyproject.toml`; discovery defaults under `tests/`; `tests/conftest.py` is a docstring only; per-extra `conftest.py` use `importorskip` |
| **Quick run command** | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_<module>.py -x` |
| **Full suite command** | `conda run -n iof3d_cosicorr3d-dev312 pytest` (32 + new, **0 skipped**) |
| **Estimated runtime** | full suite ~30–60s; targeted module <10s |

**Established pattern to mirror** (`tests/core/test_rescore.py`): build a minimal suite via
inline-YAML strings in `tmp_path`, stub a parser package on `sys.path`, fabricate synthetic run
dirs with `write_trial_record(trial_record_path(run_dir), {...})`. F-20 characterization adds a
**fake `AxClient`** (stub exposing `create_experiment`, `get_next_trial`→`(index, params)`,
`complete_trial`, `log_trial_failure`, `get_best_trial`) and a **stub `ToolAdapter`** (returns a
canned `TrialResult`).

---

## Sampling Rate

- **After every task commit:** Run `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_<module>.py -x` (<10s)
- **After every plan wave:** Full gate — `ruff check .` + `ruff format --check .` + `pyright` (no-regression vs Wave-0 baseline, D-11/D-12) + `pytest` (all green, 0 skipped)
- **Before `/gsd-verify-work`:** Full suite green + ruff green + pyright ≤ baseline
- **Max feedback latency:** ~60 seconds (full suite)

---

## Per-Task Verification Map

> Indicative map; the planner binds exact task IDs. Threat refs n/a (no `<threat_model>` — internal refactor phase, ASVS L1 has no new external surface).

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| FIX-01 | Each F-NN resolved, suite stays green | regression | `pytest` (full) | existing 32 | ⬜ pending |
| FIX-02 | Dead code gone, no behavior change | regression + vulture | `pytest` + `vulture src/ --min-confidence 60` | existing | ⬜ pending |
| FIX-03 | `from_mapping` + `_parser_fn_repr` single-source, byte-identical key | unit | `pytest tests/core/test_runner.py tests/core/test_rescore.py -k repr_or_from_mapping` | ❌ W0 | ⬜ pending |
| FIX-04 | Full suite + ruff + pyright green-gate | gate | wave gate command set | n/a | ⬜ pending |
| F-20 | Runner trial loop + cross-case aggregation + partial-failure path | characterization→regression | `pytest tests/core/test_runner.py -x` | ❌ W0 | ⬜ pending |
| F-21 | Store create / append / empty-rows | unit | `pytest tests/core/test_store.py -x` | ❌ W0 | ⬜ pending |
| F-22 | evaluation parser-fail→None, metric-raise→skip, non-scalar coercion | unit | `pytest tests/core/test_evaluation.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 lands the characterization/regression net **before** the runner refactors (D-04), and
establishes the CI-faithful pyright baseline (D-12).

- [ ] **Baseline:** install `pyright==1.1.392` with `.[dev]`-only in the dev env (or a throwaway venv), run `pyright`, record the exact error count as the D-08/D-11 floor.
- [ ] `tests/core/test_runner.py` — **F-20 characterization** (the safety net), with a fake `AxClient` + stub adapter:
  - trial loop happy path: `get_next_trial`→executor→`complete_trial` for N trials; `get_best_trial` returned.
  - `_evaluate_across_cases` single-case → that case's scalar dict (`:334-335`).
  - `_evaluate_across_cases` multi-case all-finite → mean aggregation (`:341-346`).
  - `_evaluate_across_cases` multi-case **partial failure** (one case → NaN) → **pin CURRENT** NaN-ignoring-mean behavior. This is the F-05 regression anchor; extend after F-05 to assert the new finite-case-count signal.
  - `_normalize_trial_data` shapes: `(int, dict)` tuple; object with `.trial_index`/`.parameters`; `TypeError` raise on unparseable input.
  - provenance stamping writes `summary.json` blocks (exercises F-08 site `:295`) on a healthy run.
  - **F-08 counter** *(lands in Wave 2 with F-08 — plan 02-05 Task 2 — NOT Wave 0; 02-01 creates the test_runner.py harness, 02-05 extends it with this case since it pins NEW F-08 behavior)*: inject an unwritable `predictions_root` → cache write fails → assert the non-fatal counter increments and the surfaced summary line reflects it.
- [ ] `tests/core/test_store.py` — **F-21**: create-new-parquet, append round-trip rows, empty-rows short-circuit (`store.py:24-25` returns without writing), columns/schema preserved.
- [ ] `tests/core/test_evaluation.py` — **F-22 direct failure paths**: parser raises → `prediction=None`, trial scalars still returned (`:89-93`); metric raises → that metric skipped, others survive (`:177-179`); metric returns non-float → warning + skip (`:118-122`); `needs`-based kwarg assembly; gt-kind filtering (`_gt_kind_matches`).
- [ ] (Optional, D-06) smoke coverage for thin indirectly-covered modules (`analysis/runner.py`, `tool/callable_adapter.py`, `metrics/registry.py`) — accept indirect; add only where a real failure path exists.
- [ ] (Optional) add `[tool.coverage.run] source = ["geodispbench3d"]` to `pyproject.toml` so `--cov` targeting is repeatable.

*No framework install needed — pytest present.*

---

## Coverage Targets (D-05 floor + lift — measured this session)

Current: `runner.py` **13%**, `store.py` **44%**, `evaluation.py` **80%**, `trial_record.py` 57%, `predictions_cache.py` 85%, **TOTAL 55%**.

- `runner.py` 13% → **≥60%** (trial loop + `_evaluate_across_cases` + `_normalize_trial_data` + provenance; the Ax-shim span `77-136` is F-14/deferred and may stay uncovered, capping realistic ceiling ~70%). Behavior-anchored: trial loop + partial-failure path + normalize must all be exercised.
- `store.py` 44% → **≥90%** (27 stmts; create/append/empty trivially coverable).
- `evaluation.py` 80% → **≥95%** (only the 3 failure paths remain).
- **Floor (regression guard):** TOTAL must not drop below 55%; no touched module below its current %.

> D-05 bar: "done" is judged primarily by whether the **named behaviors** are exercised, with the coverage floor as a secondary regression guard. Do not game a percentage with shallow tests.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| pyright no-regression vs baseline | FIX-04 / D-11 | Baseline is a recorded count, not an assertion in the test suite | `conda run -n iof3d_cosicorr3d-dev312 pyright` → compare error count to Wave-0 baseline; confirm 0 errors on Phase-2-touched lines |

---

## Validation Sign-Off

- [ ] All tasks have an automated verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (runner/store/evaluation tests + pyright baseline)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
