# Mechanical Audit Evidence (Phase 01, Plan 01)

**Captured:** 2026-06-26 · env `iof3d_cosicorr3d-dev312` (Python 3.12.12) · all detectors run via `conda run` per AGENTS.md

This file distills the automated-detector output in [`audit-evidence/`](./audit-evidence/)
into file:line-anchored mechanical findings, organized by bucket. It is **evidence,
not a verdict** — there are deliberately **no severity or disposition labels** here
(those belong to Plan 02 / AUDIT-04, where the reasoned manual review adjudicates each
item). Every entry points back to the raw capture file it came from so the chain stays
auditable. Detectors are *supporting* evidence (D-08); the manual file:line review in
Plan 02 is the spine.

Cross-references to `.planning/codebase/CONCERNS.md` flag where a detector
**corroborates** (or, in one case, **softens**) a pre-audit finding. Re-verifying
CONCERNS is Plan 02's job; here those notes are pointers only.

---

## 1. Dead Code

Source: [`audit-evidence/vulture.txt`](./audit-evidence/vulture.txt) — `vulture src/ --min-confidence 60` (vulture 2.16). All hits are at vulture's 60% confidence (its lowest reported tier here); treat as leads for the manual review, not confirmed-dead.

| Anchor | Vulture finding | Note |
|--------|-----------------|------|
| `src/geodispbench3d/tool/base.py:81` | unused variable `in_process_safe` | **Likely false positive** — this is the documented `ToolAdapter` contract opt-in flag; it is read across the adapter boundary, which vulture cannot see. Same flag re-flagged at the three sites below. |
| `src/geodispbench3d/tool/callable_adapter.py:42` | unused variable `in_process_safe` | Same contract attribute (false-positive suspicion). |
| `src/geodispbench3d/tool/cli_adapter.py:75` | unused variable `in_process_safe` | Same contract attribute (false-positive suspicion). |
| `src/geodispbench3d_iof3d/adapter.py:42` | unused variable `in_process_safe` | Same contract attribute (false-positive suspicion). |
| `src/geodispbench3d/sweep/rescore.py:72` | unused variable `skipped_no_summary` | Counter fields on the rescore summary. |
| `src/geodispbench3d/sweep/rescore.py:73` | unused variable `skipped_failed` | Counter fields on the rescore summary. |
| `src/geodispbench3d/sweep/rescore.py:110` | unused attribute `skipped_no_summary` | Paired with the counters above. |
| `src/geodispbench3d/sweep/rescore.py:118` | unused attribute `skipped_failed` | Paired with the counters above. |
| `src/geodispbench3d/sweep/rescore.py:127` | unused attribute `skipped_failed` | Paired with the counters above. |
| `src/geodispbench3d/dataset/schema.py:53` | unused method `scan_by_epoch` | Public-looking helper on the dataset schema. |
| `src/geodispbench3d/dataset/schema.py:67` | unused variable `gt_kinds_supported` | Declared-but-unread schema field. |
| `src/geodispbench3d/suite/loader.py:30` | unused variable `parallel_trials` | Config field; relates to the "parallelism is future, not current" architectural note. |
| `src/geodispbench3d/suite/loader.py:31` | unused variable `override_tool_mode` | Declared-but-unread config field. |
| `src/geodispbench3d/sweep/trial_record.py:40` | unused variable `yaml_hash` | Declared-but-unread provenance field. |
| `src/geodispbench3d/tool/loader.py:44` | unused variable `outputs_options` | Declared-but-unread loader field. |

> Note: vulture did **not** flag the known `_ = asdict` suppression hack at
> `src/geodispbench3d/sweep/rescore.py:27,410` (CONCERNS "Dead-code suppression hack")
> — that import is deliberately kept alive precisely so the linter stays quiet, so
> vulture sees it as "used". The manual review should still examine it.

---

## 2. Test-Coverage Gaps

Source: [`audit-evidence/coverage.txt`](./audit-evidence/coverage.txt) (coverage 7.11.0, scoped to the three shipped packages) and [`audit-evidence/coverage-skips.txt`](./audit-evidence/coverage-skips.txt). **Whole-run total: 55%** (2359 stmts, 1050 missed).

**Honesty note — plugin packages:** this run executed in the iof3D dev env, where
`iof3D` + `pchandler` are importable, so `tests/iof3d` and `tests/f2s3` **ran** (32
passed, **0 skipped**). The plugin-package numbers below therefore reflect *actually
exercised* code **in this env**. In CI / a lean framework-only env those suites
**self-skip** (`tests/iof3d` conftest `importorskip('iof3D')`; `tests/f2s3` conftest
`importorskip('pchandler')`; the iof3d CI job is `enabled: false`; CI installs an empty
f2s3 extra) — there the two plugin packages would read 0%/low because the **suite is
unexercised, not because the code is untested**. See `coverage-skips.txt`.

### Core package (`geodispbench3d`) — foregrounding the CONCERNS-flagged modules

| Anchor | Cover | Stmts/Miss | Note |
|--------|-------|-----------|------|
| `src/geodispbench3d/sweep/runner.py` | **13%** | 174 / 151 | **Corroborates CONCERNS "Sweep orchestration (runner.py) — untested".** Missing spans cover the Ax shims (51-136), the live trial loop and cross-case aggregation (193-346), and trial-data normalization (378-409). |
| `src/geodispbench3d/results/store.py` | **44%** | 27 / 15 | **Corroborates CONCERNS "Parquet store (store.py) — untested".** Missing 24-27, 33-40, 46-49 = the create/append read-modify-write path. |
| `src/geodispbench3d/sweep/evaluation.py` | **80%** | 76 / 15 | **Softens CONCERNS "Metric dispatch glue (evaluation.py) — untested".** It is *indirectly* exercised (rescore/analyze tests), not zero-coverage. Still-missing: 89-93, 118, 121-122, and the parser-failure→`None` path at 177-179. |
| `src/geodispbench3d/cli.py` | 11% | 108 / 96 | CLI dispatch largely unexercised by the suite (driven only via console entry in practice). |
| `src/geodispbench3d/sweep/parameters.py` | 32% | 102 / 69 | `_build_parameter_spec` grammar (117-175) largely uncovered — note this is also a complexity hotspot (§4). |
| `src/geodispbench3d/tool/callable_adapter.py` | 35% | 60 / 39 | The in-process callable adapter (50-125) is mostly uncovered. CONCERNS lists it under "Other modules with no direct test reference". |
| `src/geodispbench3d/dashboard/app.py` | 0% | 84 / 84 | Streamlit UI, never imported by the suite. |
| `src/geodispbench3d/sweep/trial_record.py` | 57% | 117 / 50 | Provenance read/write partially covered. |
| `src/geodispbench3d/tool/cli_adapter.py` | 60% | 138 / 55 | The stdout-JSON `_collect_outputs` heuristic region (190-223) is uncovered (cf. CONCERNS known-bug). |
| `src/geodispbench3d/tool/loader.py` | 71% | 118 / 34 | The `custom`/`factory` adapter-build paths (146-163) are uncovered. |

### Plugin packages (ran in THIS env; would self-skip in CI/lean — see note above)

| Anchor | Cover | Stmts/Miss | Note |
|--------|-------|-----------|------|
| `src/geodispbench3d_iof3d/adapter.py` | 17% | 236 / 196 | The 220-line `build_app_config_from_parameters` (139-335) is the bulk of the uncovered span — also the top complexity hotspot (§4). Corroborates CONCERNS "iof3D adapter — present but skipped in CI". |
| `src/geodispbench3d_iof3d/cli.py` | 0% | 66 / 66 | The legacy Hydra `iof3d-ax` CLI (9-134) is unexercised even here. |
| `src/geodispbench3d_iof3d/factory.py` | 63% | 52 / 19 | Partially covered by the iof3d adapter test. |
| `src/geodispbench3d_iof3d/output_parser.py` | 76% | 75 / 18 | Parser largely covered. |
| `src/geodispbench3d_f2s3/output_parser.py` | 84% | 87 / 14 | F2S3 parser well covered by `tests/f2s3` (which ran here). |

> Side-evidence (same run): the suite emits `datetime.utcnow()` DeprecationWarnings from
> `results/predictions_cache.py:97`, `sweep/rescore.py:304` and `:406` — corroborates
> CONCERNS "Deprecated `datetime.utcnow()`". Recorded in `coverage-skips.txt`.

---

## 3. Dependency Hygiene

Source: [`audit-evidence/deptry.txt`](./audit-evidence/deptry.txt) — `deptry . --known-first-party geodispbench3d` (deptry 0.25.1). **No DEP001 (missing) and no DEP003 (transitive) findings** after suppressing the editable-install self-import false positives (48 of them — `geodispbench3d` importing its own submodules).

| Anchor | deptry code | Finding | Note |
|--------|-------------|---------|------|
| `pyproject.toml` | DEP002 | `duckdb` defined but not used in scanned code | Dashboard extra; used via guarded import / ad-hoc query, not in core `src/`. Scan-scope artifact. |
| `pyproject.toml` | DEP002 | `ruff` defined but not used | Dev tool — runs as a CLI, not imported. |
| `pyproject.toml` | DEP002 | `pyright` defined but not used | Dev tool — runs as a CLI, not imported. |
| `pyproject.toml` | DEP002 | `pre-commit` defined but not used | Dev tool — runs as a CLI, not imported. |
| `pyproject.toml` | DEP002 | `pytest` defined but not used | Dev tool — exercised in `tests/`, not imported in `src/`. |
| `pyproject.toml` | DEP002 | `coverage` defined but not used | Dev tool — runs as a CLI / over `tests/`. |
| `pyproject.toml` | DEP002 | `sphinx` defined but not used | Docs extra — runs as a CLI. |

> Reading: the DEP002 set is entirely **dev / dashboard / build tooling** that is
> exercised in `tests/`, CI, the docs build, or the dashboard module — not imported in
> `src/`. This is a scan-scope artifact, not a literal "remove this dependency". The
> genuinely informative signal is the **absence** of any DEP001 (missing) finding:
> every third-party import in `src/` maps to a declared dependency. deptry surfaced
> **nothing** directly touching the `iof3d` / `pchandler` / `f2s3` extras tangle —
> those imports resolve cleanly in this env (the iof3d stack is installed); the extras
> question is an architectural/packaging matter for the manual review and the
> downstream packaging phase, not a deptry-detectable defect.

---

## 4. Complexity Hotspots

**Primary signal — ruff C901** ([`audit-evidence/ruff-c901.txt`](./audit-evidence/ruff-c901.txt), ruff 0.15.12, `max-complexity=10`). ruff flagged **5** functions above McCabe 10:

| Anchor | Function | ruff C901 |
|--------|----------|-----------|
| `src/geodispbench3d_iof3d/adapter.py:128` | `build_app_config_from_parameters` | **22** > 10 |
| `src/geodispbench3d/sweep/runner.py:72` | `_create_experiment` | 14 > 10 |
| `src/geodispbench3d/sweep/evaluation.py:51` | `evaluate_trial` | 12 > 10 |
| `src/geodispbench3d/sweep/parameters.py:116` | `_build_parameter_spec` | 12 > 10 |
| `src/geodispbench3d_iof3d/cli.py:29` | `_collect_run_kwargs` | 11 > 10 |

The single worst — `build_app_config_from_parameters` (the **220-line** field-by-field
`AppConfig` reconstruction, the design-sensibility seed in CONTEXT D-07) — is the
standout on every measure.

**Supplementary corroboration — radon** ([`audit-evidence/radon-cc.txt`](./audit-evidence/radon-cc.txt), [`radon-mi.txt`](./audit-evidence/radon-mi.txt), radon 6.0.1; ran cleanly on Python 3.12, no graceful-degradation needed). radon's CC scorer is more aggressive than ruff's McCabe (it counts boolean sub-expressions / comprehensions), so it flags **17** functions at grade C or worse. Both detectors agree on the two worst (`build_app_config_from_parameters`, `evaluate_trial`); radon additionally surfaces:

| Anchor | Function | radon cc | Also in ruff? |
|--------|----------|----------|---------------|
| `src/geodispbench3d/sweep/rescore.py:203` | `_rescore_one` | **D (22)** | no (below ruff's McCabe-10) |
| `src/geodispbench3d/sweep/evaluation.py:51` | `evaluate_trial` | **D (21)** | yes |
| `src/geodispbench3d/sweep/runner.py:223` | `AxSweepRunner._evaluate_across_cases` | C (20) | no |
| `src/geodispbench3d_iof3d/adapter.py:128` | `build_app_config_from_parameters` | C (19) | yes (22) |
| `src/geodispbench3d/sweep/runner.py:375` | `_normalize_trial_data` | C (15) | no |
| `src/geodispbench3d/sweep/runner.py:72` | `AxSweepRunner._create_experiment` | C (15) | yes |
| `src/geodispbench3d/sweep/parameters.py:116` | `_build_parameter_spec` | C (14) | yes |
| `src/geodispbench3d_iof3d/cli.py:29` | `_collect_run_kwargs` | C (13) | yes |
| `src/geodispbench3d_iof3d/adapter.py:555` | `_coerce_image_resolution` | C (13) | no |
| `src/geodispbench3d/analysis/runner.py:45` | `analyze` | C (13) | no |
| `src/geodispbench3d/sweep/trial_record.py:166` | `_to_jsonable` | C (12) | no |
| `src/geodispbench3d_iof3d/adapter.py:512` | `_build_hydra_run_config` | C (11) | no |
| `src/geodispbench3d/sweep/evaluation.py:155` | `_invoke_metric` | C (11) | no |
| `src/geodispbench3d/sweep/rescore.py:79` | `rescore_suite` | C (11) | no |
| `src/geodispbench3d_iof3d/cli.py:114` | `main` | C (11) | no |
| `src/geodispbench3d/tool/loader.py:100` | `_build_cli_adapter` | C (11) | no |
| `src/geodispbench3d/metrics/builtins.py:179` | `per_point_displacement_record` | C (11) | no |

**Maintainability index** (radon mi, worst-first; all files land grade A but the index
ranks them): the lowest two are `src/geodispbench3d_iof3d/adapter.py` (**26.21** — by far
the lowest, consistent with its size + the 220-line function) and
`src/geodispbench3d/sweep/runner.py` (**37.72** — the Ax-shim-heavy orchestrator), then
`sweep/rescore.py` (38.97) and `sweep/parameters.py` (45.34). These four are the same
modules dominating the CC and coverage tables.

> The ruff↔radon disagreement on absolute counts is expected (different algorithms);
> ruff C901 is the authoritative gate. radon's value here is the maintainability-index
> ranking and the wider C+ net, both pointing the manual review at the same cluster:
> the iof3d adapter and the sweep runner/rescore/parameters core.

---

*Evidence captured for AUDIT-01 supporting evidence. Synthesis, severity, and
disposition are Plan 02 / AUDIT-04.*
