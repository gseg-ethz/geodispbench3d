# Phase 3: CLI Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-27
**Phase:** 3-CLI Hardening
**Areas discussed:** F2S3 showcase & execution model, Subprocess timeout policy (F-32), Output-collection contract (F-07), Exit codes & argument validation (F-06), Preflight timing, Config-load & input-path errors, CLI-04 test mechanics

---

## F2S3 showcase & execution model (CLI-05, F-16)

### Execution model

| Option | Description | Selected |
|--------|-------------|----------|
| conda-run subprocess (keep) | Keep `entry: conda run -n f2s3-dev312 f2s3`; faithful CliToolAdapter showcase | |
| in-env binary on PATH | `entry: f2s3`; simpler but loses env-isolation showcase, contradicts current design | |
| Document both, default conda-run | Ship conda-run as canonical default; docs note in-env override | ✓ |

**User's choice:** Document both, default conda-run.

### Preflight location

| Option | Description | Selected |
|--------|-------------|----------|
| Generic adapter check + YAML remediation hint | CliToolAdapter generic preflight raises structured error; tool.yaml optional `remediation`/`help_url` field | ✓ |
| F2S3-specific preflight only | Bespoke check in the F2S3 path; most targeted, no generic surface | |
| Generic adapter check only | Clear error, but no per-tool remediation field (actionable hint lives only in docs) | |

**User's choice:** Generic adapter check + YAML remediation hint.

### How-to-obtain source

| Option | Description | Selected |
|--------|-------------|----------|
| I'll give you the repo URL | User provides exact gseg-ethz F2S3 repo URL | ✓ |
| Use a placeholder, planner resolves | TODO placeholder; planner fills URL | |
| Generic pointer, no specific repo | No hardcoded URL | |

**User's choice:** Provided URL — `https://github.com/gseg-ethz/F2S3_pc_deformation_monitoring`.
**Notes:** No extra build notes; doc points at the repo's README for build/env (`f2s3-dev312`).

---

## Subprocess timeout policy (F-32)

| Option | Description | Selected |
|--------|-------------|----------|
| Opt-in via tool.yaml field (no default) | `execution.timeout_seconds`; unset = no timeout | |
| Default timeout + YAML override | Generous default applied to every tool | |
| Opt-in + CLI flag override | tool.yaml field + `--timeout` flag on `run` | ✓ |

**User's choice:** Opt-in + CLI flag override.
**Notes:** User first asked whether an interactive "kill or keep waiting?" poll would explode scope. Confirmed it would (blocking `subprocess.run`; requires Popen/watchdog + TTY-vs-headless branch; primary use case is unattended HPC sweeps where a prompt hangs forever). On-expiry behavior clarified and accepted: kill + record non-fatal `timeout` failure + report to Ax + sweep continues + counted in the F-08 summary line; no interactive prompt, no watchdog thread. User asked to **seed** the interactive-poll idea for the future → SEED-001.

---

## Output-collection contract (F-07)

### stdout-based collection

| Option | Description | Selected |
|--------|-------------|----------|
| Sentinel-delimited + glob becomes default | Require `GEODISPBENCH3D_RESULT:` sentinel; flip default to glob | |
| Sentinel only, keep stdout_json default | Add sentinel but keep stdout_json default | |
| Deprecate stdout_json entirely | Drop stdout_json; glob is the only path | ✓ |

**User's choice:** Deprecate stdout_json entirely.
**Notes:** Safe — no in-repo CLI tool uses stdout_json (F2S3=glob, iof3D=callable). Planner nuance: deprecation stub raising "use outputs_from: glob" preferred over silent hard-remove (pre-public).

### Empty glob behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Empty predictions = failure; figures optional | Empty `predictions_glob` → flagged failure; empty `figures_glob` non-fatal | ✓ |
| Any configured glob empty = failure | Strictest; punishes tools that legitimately emit no figures | |
| Warn + count, never fail | Visible but non-fatal; weaker than SC2 | |

**User's choice:** Empty predictions = failure; figures optional.

---

## Exit codes & argument validation (F-06)

### Exit-code taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal POSIX: 0 / 1 / 2 | 0 success; 1 runtime failure (not skipped_failed); 2 usage/argument | ✓ |
| Richer taxonomy (0/1/2/3…) | Distinct codes per error class | |
| 0 / 1 only, no usage distinction | Collapse non-success to 1 | |

**User's choice:** Minimal POSIX 0/1/2.

### Mode-mismatched argument handling

| Option | Description | Selected |
|--------|-------------|----------|
| Reject as usage error (exit 2), keep run --rescore | Validate + reject rescore-only flags without --rescore; no restructure | |
| Split rescore into its own subcommand | `geodispbench3d rescore <suite>`; argparse rejects flags on run structurally | ✓ |
| Warn + proceed | Warn per mismatched flag, don't fail | |

**User's choice:** Split rescore into its own subcommand.
**Notes:** Accepted the pre-public CLI break as the cheapest moment. Ripple acknowledged: cli.py argparse/dispatch, docs/rescoring-and-analysis.md, README, quickstart, migration note; widens CLI-04 test scope (no main() test exists today).

---

## Preflight timing

| Option | Description | Selected |
|--------|-------------|----------|
| Fail-fast in prepare() (abort before trial 0) | Preflight in CliToolAdapter.prepare(); missing env raises before Ax launches; exit 1 | ✓ |
| Both: prepare() fail-fast + per-trial guard | Defensive superset for mid-sweep env disappearance | |
| Per-trial only | First+every trial fails; wastes a full sweep | |

**User's choice:** Fail-fast in prepare().
**Notes:** prepare()/teardown() already wired in runner.py:192/204, 251/273. Preflight failure = environment error → exit 1 (not usage code 2). Sweep-path only.

---

## Config-load & input-path errors

| Option | Description | Selected |
|--------|-------------|----------|
| Catch at main(): clean message, exit 1 (uniform) | main() catches FileNotFoundError/ValueError; clean `error: <msg>`; exit 1; exit 2 stays argparse-only | ✓ |
| Catch at main(): path-not-found = 2, malformed = 1 | More precise but more branching | |
| Let tracebacks surface (status quo) | No catch; raw tracebacks | |

**User's choice:** Catch at main(): clean message, exit 1 (uniform).
**Notes:** Optional planner nicety: `--traceback`/DEBUG re-exposes the full stack for developers.

---

## CLI-04 test mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Real stub executable + main()-level argv tests | Stub scripts to tmp_path exercise real subprocess/timeout/glob; drive run_trial + main() | ✓ |
| Layered: stub executable + targeted monkeypatch | Stubs + monkeypatch where a real process is awkward/slow | |
| Monkeypatch subprocess.run only | Hermetic/fast but never exercises real timeout/exit plumbing | |

**User's choice:** Real stub executable + main()-level argv tests.
**Notes:** Faithful over fast — timeout is a real subprocess mechanic. Preflight tested via a deliberately-missing entry; no real conda/F2S3 env needed. Net-new `tests/core/test_cli.py`.

---

## Claude's Discretion

- **Consistency cleanups** (not separately discussed; sensible defaults applied, planner-adjustable):
  - `_cmd_dashboard` missing-streamlit → exit 1 (not the usage code 2).
  - `list-metrics` on a bad metrics.yaml → route through the D-11 clean-error + exit-1 handler instead of returning 0.
  - `stdout_json` removal form → deprecation stub with error preferred over hard-remove.
- **Exact `--timeout` precedence** (CLI flag overrides `execution.timeout_seconds`) and the precise structured-error wording.

## Deferred Ideas

- **Interactive timeout watchdog ("kill or keep waiting?" poll)** — out of scope for Phase 3 (requires Popen/watchdog rework + TTY-vs-headless branch, fights the unattended-batch design). Filed as **SEED-001** (`.planning/seeds/SEED-001-interactive-timeout-watchdog.md`) at the user's explicit request.
