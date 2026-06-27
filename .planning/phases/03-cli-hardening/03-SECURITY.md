---
phase: 03
slug: cli-hardening
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-06-27
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Block threshold: `high` (ASVS L1). Register authored at plan time across all four
plans (`register_authored_at_plan_time: true`); verification was performed at L1
grep-depth — sufficient for ASVS L1 — and the auditor was short-circuited because
no open threats remained at or above the block threshold.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| tool.yaml → CliToolAdapter | operator-supplied `entry`/`args` become subprocess argv | trusted config (no shell) |
| CliToolAdapter → OS subprocess (process group) | the tool tree executes with the bench's privileges | argv, env, cwd |
| preflight resolver → conda CLI | `conda env list --json` enumerates envs before trial 0 | env names / prefixes |
| adapter → Ax (`log_trial_failure`) | a failed trial is reported to the optimizer, not scored | trial index, error kind |
| shell → argparse | CLI argv from the operator; argparse owns structural validation | subcommand + flags |
| summary counters → exit code | typed failure counts decide 0/1, consumed by CI gates | int counters |
| loader/preflight exceptions → stderr | exception messages surface to the operator | error text |
| docs → integrator | published guidance shapes tool wiring (no executable surface) | example commands/paths |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering/Elevation | entry → argv | medium | accept | `shlex.split` of entry, argv passed as a list, no `shell=True` — no shell-injection surface; config is trusted operator input | closed |
| T-03-02 | Elevation | preflight resolver | medium | mitigate | `CliToolAdapter.prepare()` (`cli_adapter.py:121`) only resolves the leading executable (`shutil.which`, :141) + named/prefix conda env (`_conda_env_names`, :176); never spawns the tool or the env | closed |
| T-03-03 | Denial of Service | hung subprocess + descendants | **high** | mitigate | `Popen(start_new_session=True)` (`cli_adapter.py:244`) + process-group kill `os.killpg(os.getpgid(...), SIGKILL)` (:350) on `TimeoutExpired`; `ProcessLookupError` swallowed (:353); `error_kind="timeout"` (:288) | closed |
| T-03-04 | Information disclosure | nonzero-exit stdout/stderr logged | low | accept | tool stdout/stderr logged at error on failure (existing behavior); operator-facing logs, no secret handling | closed |
| T-03-05 | Spoofing | conda env-name match | low | accept | env membership checked against authoritative `conda env list --json`; a mis-set env fails preflight, not silently | closed |
| T-03-06 | Information disclosure | tracebacks on bad config | medium | mitigate | `_CleanExit` (`cli.py:39`) → single `error: <msg>` on stderr (:62), no traceback; full stack only behind `--traceback`; unexpected bugs keep tracebacks | closed |
| T-03-07 | Tampering | exit-code misuse in CI gates | **high** | mitigate | sweep exit 1 derived from typed counters `trial_failures or eval_failures or successful_trials == 0` (`cli.py:331`); a real failure cannot read as success (0) | closed |
| T-03-08 | Repudiation | silent rescore/sweep "success" | medium | mitigate | rescore exit keyed off `parser_misses or eval_failures` (`cli.py:384`); analyze off `skipped_unreadable or eval_failures` (:433) — genuine errors surfaced, not masked | closed |
| T-03-09 | Tampering | stub scripts in tmp_path | low | accept | stubs are test-authored, written to pytest `tmp_path`, removed with the fixture; no network, no privileged ops | closed |
| T-03-10 | Denial of Service | sleep/wrapper-stub timeout tests | low | mitigate | timeout tests use short ceilings against bounded sleeps; `test_run_trial_timeout_reaps_descendant_process` (`tests/core/test_cli.py:121`) asserts the descendant is reaped via a bounded poll — no orphan survives the suite | closed |
| T-03-11 | Information disclosure | example commands/paths in docs | low | accept | examples use the public gseg-ethz repo + non-secret scratch paths already in the repo; no credentials documented | closed |
| T-03-12 | Tampering | stale docs misleading integrators | medium | mitigate | the old `run --rescore` form is rejected by argparse (`test_rescore_only_flag_rejected_on_run`, `tests/core/test_cli.py:512`); docs carry a migration note (`docs/rescoring-and-analysis.md:16`); content pinned to Plan-01/02 error strings | closed |
| T-03-13 | Repudiation | failed trial silently completed in Ax | **high** | mitigate | `_raise_if_failed` (`runner.py:66`) raises `TrialExecutionError` on `success=False` (both runner paths); handler calls `log_trial_failure` not `complete_trial` (:253, :370); `_resolve_best_trial` (:270) returns None on all-failed sweep | closed |
| T-03-SC | Tampering | npm/pip/cargo installs | n/a | accept | no package installs across any plan — stdlib + existing in-repo modules + pytest (already in `[dev]`) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `high` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-01 | Tool `entry`/`args` are trusted operator config; `shlex.split` + list-argv + no `shell=True` removes the injection surface | Nicholas Meyer | 2026-06-27 |
| AR-03-02 | T-03-04 | Failure stdout/stderr is operator-facing diagnostic output; the bench handles no secrets | Nicholas Meyer | 2026-06-27 |
| AR-03-03 | T-03-05 | Env-name spoof fails preflight against authoritative `conda env list`; no silent fallthrough | Nicholas Meyer | 2026-06-27 |
| AR-03-04 | T-03-09 | Test stubs live in pytest `tmp_path`, removed with the fixture; no network/privileged ops | Nicholas Meyer | 2026-06-27 |
| AR-03-05 | T-03-11 | Doc examples use the public gseg-ethz repo + non-secret scratch paths; no credentials | Nicholas Meyer | 2026-06-27 |
| AR-03-06 | T-03-SC | No package installs in any Phase-03 plan; stdlib + existing modules only | Nicholas Meyer | 2026-06-27 |

**Accepted scope limitation (settled by D-02, not an open threat):** the generic
preflight (T-03-02) deliberately does NOT validate the trailing in-env binary
(e.g. `f2s3` inside `conda run -n f2s3-dev312 f2s3`). A binary missing inside the
env is surfaced by trial 0's nonzero-exit / `FileNotFoundError` handling
(`error_kind="entry_not_found"`). This keeps the preflight cheap and avoids
spawning the env; it is a documented decision, not a silent gap.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-27 | 14 | 14 | 0 | gsd-secure-phase (L1 grep verification, auditor short-circuited) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-27
