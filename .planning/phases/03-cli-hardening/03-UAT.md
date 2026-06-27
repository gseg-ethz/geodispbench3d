---
status: complete
phase: 03-cli-hardening
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md]
started: 2026-06-27T15:11:01Z
updated: 2026-06-27T15:12:30Z
---

## Current Test

[testing complete]

## Tests

### 1. Build Sanity — behavioral test suite green
expected: `conda run -n iof3d_cosicorr3d-dev312 python -m pytest tests/core -q` → 113 passed, no failures.
result: pass

### 2. rescore is its own subcommand (disjoint flags)
expected: |
  `geodispbench3d rescore -h` shows: positional `suite`, `--reuse-parser-options`,
  `--use-prediction-cache`, `--pass-id`, `--max-trials`, `--log-level`, `--traceback`.
  `geodispbench3d run -h` shows `--timeout` and `--max-trials` but NONE of the four
  rescore-only flags. The two flag sets are disjoint.
result: pass
note: "User confirmed; also observed run -h shows --traceback and --log-level — expected, these are shared flags (--traceback via the parent parser, --log-level on run), not rescore-only, so the disjointness holds."

### 3. Old `run --rescore` form is rejected
expected: |
  `geodispbench3d run anything.yaml --rescore` exits 2 with
  `error: unrecognized arguments: --rescore` (argparse usage error). The old
  combined `run --rescore` invocation no longer exists.
result: pass

### 4. Clean error on a bad/missing config (no traceback)
expected: |
  `geodispbench3d run /nope.yaml` prints a single line
  `error: Suite YAML not found: /nope.yaml` to stderr and exits 1 — NO Python
  traceback. (A bad metrics.yaml under `list-metrics` behaves the same: clean
  `error:` + exit 1 instead of a stray 0 or a raw stack.)
result: pass

### 5. `--traceback` restores the full stack
expected: |
  `geodispbench3d run /nope.yaml --traceback` re-raises the original loader
  exception and prints the full `FileNotFoundError` traceback, still exit 1. The
  flag is accepted only in the canonical subcommand position
  (`geodispbench3d <subcommand> ... --traceback`).
result: pass

### 6. Preflight catches a missing conda env before trial 0
expected: |
  A sweep whose tool entry points at a non-existent conda env (e.g.
  `entry: conda run -n no-such-env f2s3`) fails fast in `adapter.prepare()` BEFORE
  any trial runs: a clean `error:` naming the missing env plus the configured
  remediation/help_url, exit 1 — not a raw subprocess/JSON traceback. (If no
  runnable suite is handy to point at a bogus env, mark this skipped.)
result: pass
note: "Confirmed live via /tmp/f2s3-bogus-suite.yaml → bogus tool (env no-such-env). Got clean `error: conda env 'no-such-env' not found (available: [...])` + Remediation + See: gseg-ethz help_url, exit=1, before trial 0. Confirmed remediation/help_url are tool-config-sourced (f2s3.yaml top-level, threaded by loader, appended only when present), not framework-generic. The mixed env-name in the remediation text was a user `sed` artifact (no /g flag), not a framework defect."

### 7. Docs reflect the hardened contract; stale `--rescore` token scrubbed
expected: |
  - `docs/tools/f2s3.md` documents F2S3 as the canonical CliToolAdapter example
    with the gseg-ethz link, the per-trial timeout (process-group SIGKILL) section,
    and the D-02 limitation (preflight does NOT validate the in-env binary).
  - `docs/rescoring-and-analysis.md` uses `geodispbench3d rescore <suite>` and
    carries a migration note about the removed `--rescore` flag.
  - No `--rescore` token survives anywhere under `src/`
    (`grep -rn -- --rescore src/` returns nothing).
result: pass
note: "Verification gate run live: (a) no --rescore token under src/; (b) rescoring-and-analysis.md uses `geodispbench3d rescore <suite>` + migration note (L16-21); (c) f2s3.md has gseg-ethz link (L14), D-02 limitation (L23), per-trial timeout w/ process-group SIGKILL/os.killpg (L70-90)."

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
