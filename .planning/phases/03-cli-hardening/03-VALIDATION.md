---
phase: 3
slug: cli-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-27
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4 (`dev` extra) |
| **Config file** | none (`pytest.ini`/`tox.ini`/`setup.cfg` absent; no `[tool.pytest]`) |
| **Quick run command** | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_cli.py tests/core/test_cli_adapter.py -q` |
| **Full suite command** | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q` |
| **Estimated runtime** | ~30 seconds (core suite; the real-sleep timeout stub adds ~3s) |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `{full suite command}` + `ruff check` + `pyright`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | CLI-02, CLI-03 | T-03-03 | A hung tool is killed at `timeout` and recorded as a counted non-fatal `timeout` failure; the sweep continues (F-32/D-04/D-05). | unit (impl; behavior gated by 3-03-01 `-k timeout`) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q && conda run -n iof3d_cosicorr3d-dev312 ruff check src/geodispbench3d && conda run -n iof3d_cosicorr3d-dev312 pyright` | ✅ | ⬜ pending |
| 3-01-02 | 01 | 1 | CLI-02 | T-03-04 | Explicit `outputs.from: stdout_json` raises a glob-pointing error; an empty `predictions_glob` yields `success=False` (figures stay auxiliary) (F-07/D-06/D-07). | unit (impl; behavior gated by 3-03-01 `-k "empty_glob or stdout_json_deprecated"`) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q && conda run -n iof3d_cosicorr3d-dev312 ruff check src/geodispbench3d && conda run -n iof3d_cosicorr3d-dev312 pyright` | ✅ | ⬜ pending |
| 3-01-03 | 01 | 1 | CLI-03 | T-03-02 | A missing conda env or unresolvable binary raises `ToolPreflightError` with remediation/help_url before trial 0; the preflight never spawns the env (F-16/D-02/D-10). | unit (impl; behavior gated by 3-03-01 `-k preflight`) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q && conda run -n iof3d_cosicorr3d-dev312 ruff check src/geodispbench3d && conda run -n iof3d_cosicorr3d-dev312 pyright` | ✅ | ⬜ pending |
| 3-02-01 | 02 | 2 | CLI-01 | T-03-07 | `rescore` is its own subcommand; the four rescore-only flags are structurally rejected on `run` (exit 2); `run` exposes `--timeout` (D-09/D-04). | unit (impl; behavior gated by 3-03-02 `-k "subcommand or timeout_override"`) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q && conda run -n iof3d_cosicorr3d-dev312 ruff check src/geodispbench3d && conda run -n iof3d_cosicorr3d-dev312 pyright` | ✅ | ⬜ pending |
| 3-02-02 | 02 | 2 | CLI-01 | T-03-06 | A bad config path/value (and `ToolPreflightError`) prints a single `error: <msg>` line with no traceback and exits 1; argparse usage stays exit 2 (D-11/D-10). | unit (impl; behavior gated by 3-03-02 `-k "usage or config_error"`) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q && conda run -n iof3d_cosicorr3d-dev312 ruff check src/geodispbench3d && conda run -n iof3d_cosicorr3d-dev312 pyright` | ✅ | ⬜ pending |
| 3-02-03 | 02 | 2 | CLI-01 | T-03-08 | rescore/analyze exit code keyed off genuine errors (`parser_misses`), not pre-existing `skipped_failed` (F-06); `--timeout` overrides the YAML ceiling via `is not None` (so `--timeout 0` is honored) (D-08/D-04). | unit (impl; behavior gated by 3-03-02 `-k "rescore_exit or timeout_override"`) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -q && conda run -n iof3d_cosicorr3d-dev312 ruff check src/geodispbench3d && conda run -n iof3d_cosicorr3d-dev312 pyright` | ✅ | ⬜ pending |
| 3-03-01 | 03 | 3 | CLI-04, CLI-02, CLI-03 | T-03-09, T-03-10 | Adapter subprocess contract is covered by real stub-executable tests: nonzero_exit, timeout, empty_glob (fail + success), figures-empty-ok, preflight (missing binary + missing conda env) — no real conda/F2S3 required (D-12). | unit (real subprocess) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_cli.py tests/core/test_cli_adapter.py -q` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 3 | CLI-04, CLI-01 | T-03-07, T-03-08 | `main()`-level coverage: usage→2, config_error→1, subcommand rejection, rescore_exit (F-06), preflight→1, and `--timeout` override (`run --timeout N` wins; `--timeout 0` = no timeout) (D-12/D-04). | unit (main-level) | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_cli.py -q` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 3 | CLI-05 | T-03-12 | F2S3 is documented as the canonical CliToolAdapter example with a how-to-obtain note + the subprocess contract (nonzero exit / empty glob / timeout / missing env) and 0/1/2 exit-code taxonomy (CLI-05/CLI-02/D-08). | doc review (grep gate) | `grep -q "gseg-ethz/F2S3_pc_deformation_monitoring" docs/tools/f2s3.md && grep -qi "timeout" docs/integrating/cli-tool.md && grep -qi "exit" docs/integrating/cli-tool.md` | ✅ | ⬜ pending |
| 3-04-02 | 04 | 3 | CLI-05 | T-03-12 | The `run --rescore` → `rescore` subcommand break has a migration note; the YAML schema reference reflects glob-blessed/stdout_json-deprecated, `execution.timeout_seconds`, and `remediation`/`help_url` (D-09/D-04/D-06/D-02). | doc review (grep gate) | `grep -q "geodispbench3d rescore" docs/rescoring-and-analysis.md && grep -qi "timeout_seconds" docs/reference/yaml-schemas.md && grep -qi "remediation" docs/reference/yaml-schemas.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*File Exists: ✅ = verify target already exists (regression-style gate over the live tests/core suite or existing docs) · ❌ W0 = net-new file the Wave 0 scaffold must create first (`tests/core/test_cli.py`).*

*Plans 01–02 are implementation tasks: their per-task verify runs the live `tests/core` suite + ruff + pyright as a no-regression gate; their NEW behaviors are asserted by the net-new tests authored in Plan 03 (the `-k` selectors above map each implementation task to its behavioral gate, cross-referenced with RESEARCH §"Validation Architecture → Phase Requirements → Test Map").*

---

## Wave 0 Requirements

- [ ] `tests/core/test_cli.py` — net-new `main()`-level + adapter-level CLI tests (no such file today); blocks 3-03-01 and 3-03-02.
- [ ] stub executables in `tmp_path` — sleep-N (timeout), exit-code-N (nonzero exit), writes/omits-output (glob paths), with shebang + chmod 0o755.
- [ ] pytest already installed in `iof3d_cosicorr3d-dev312` (no framework install needed).

*Existing `tests/core/test_cli_adapter.py` covers argv building; the new suite extends it with a real-subprocess layer. Plans 01/02 implementation tasks gate against the live suite (✅), so no Wave 0 scaffold is needed for them.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| F2S3 end-to-end conda-run with real env | CLI-05 | Requires the `f2s3-dev312` conda env + F2S3 binary not present in CI/dev env | Install per gseg-ethz F2S3 README, run a real F2S3 suite via `conda run -n f2s3-dev312` |
| F2S3 / CliToolAdapter doc accuracy review | CLI-05 | CLI-05 is a documentation deliverable; the grep gates confirm presence, not prose correctness | Read docs/tools/f2s3.md + docs/integrating/cli-tool.md: links resolve, examples match the shipped flag layout and the Plan-01/02 error strings |

*Stub-executable tests (D-12) cover the preflight/timeout/exit-code/glob plumbing WITHOUT needing a real conda or F2S3 env.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`tests/core/test_cli.py`)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planner, revision pass — per-task map populated from PLAN.md tasks cross-referenced with RESEARCH §"Validation Architecture")
