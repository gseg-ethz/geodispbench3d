---
phase: 3
slug: cli-hardening
status: draft
nyquist_compliant: false
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
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core/test_cli.py tests/core/test_cli_adapter.py` |
| **Full suite command** | `conda run -n iof3d_cosicorr3d-dev312 pytest tests/core` |
| **Estimated runtime** | ~30 seconds (core suite; stub-executable timeout tests add a few seconds) |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `{full suite command}`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | CLI-XX | T-3-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*(Filled in by the planner/executor as tasks are defined — one row per task.)*

---

## Wave 0 Requirements

- [ ] `tests/core/test_cli.py` — net-new `main()`-level CLI tests (no such file today)
- [ ] stub executables in `tmp_path` — sleep-N (timeout), exit-code-N (nonzero exit), writes/omits-output (glob paths)
- [ ] pytest already installed in `iof3d_cosicorr3d-dev312` (no framework install needed)

*Existing `tests/core/test_cli_adapter.py` covers argv building; the new suite extends it with a real-subprocess layer.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| F2S3 end-to-end conda-run with real env | CLI-05 | Requires the `f2s3-dev312` conda env + F2S3 binary not present in CI/dev env | Install per gseg-ethz F2S3 README, run a real F2S3 suite via `conda run -n f2s3-dev312` |

*Stub-executable tests (D-12) cover the preflight/timeout/exit-code/glob plumbing WITHOUT needing a real conda or F2S3 env.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
