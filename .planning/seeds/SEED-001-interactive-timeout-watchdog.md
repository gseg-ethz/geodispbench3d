---
id: SEED-001
status: dormant
planted: 2026-06-27
planted_during: v1.0 / Phase 3 — CLI Hardening
trigger_when: revisiting subprocess timeout / sweep-execution UX, or when interactive/attended sweep runs become a use case
scope: medium-large
---

# SEED-001: Interactive timeout watchdog ("kill or keep waiting?" poll)

## Why This Matters

When a CLI trial overruns and **no** `execution.timeout_seconds` / `--timeout` is
configured, instead of either a silent hang (today, pre-Phase-3) or a hard kill
(Phase 3 D-04/D-05), the harness could — after a default elapsed time — actively
poll the user: "trial N has run M minutes, kill or keep waiting?". This preserves
the user's instinct (surfaced during Phase 3 discussion) that neither silent-hang
nor surprise-kill is ideal for an attended run.

## When to Surface

**Trigger:** revisiting timeout/sweep-execution UX, or if attended/interactive sweep
runs (vs unattended HPC batch) become a first-class use case.

Deliberately deferred out of **Phase 3 (CLI Hardening)** because it would:
- require converting the blocking `subprocess.run` (`cli_adapter.py:107`) to a
  `Popen` + poll loop or a watchdog thread — against the current single-threaded
  trial-loop architecture (`.planning/codebase/ARCHITECTURE.md`);
- require a TTY-vs-headless branch, because the primary use case is **unattended**
  Ax sweeps running for hours, often headless on HPC, where an interactive prompt
  would itself block forever (strictly worse than the hang it replaces).

Phase 3 instead shipped: opt-in timeout → on expiry kill + record non-fatal
`timeout` failure → report to Ax → sweep continues + counted (D-04/D-05).

## Scope Estimate

**Medium-large** — touches the adapter's process-execution model (Popen/watchdog),
adds interactivity + TTY detection, and must stay opt-in/headless-safe. Not a small
change; weigh against the v2 parallel-execution work (EXEC-01), which also reworks
the trial loop.

## Breadcrumbs

- `src/geodispbench3d/tool/cli_adapter.py:98-153` — `run_trial` / the blocking
  `subprocess.run` call this would rework.
- `.planning/phases/03-cli-hardening/03-CONTEXT.md` — D-04/D-05 (the shipped
  timeout decision) + Deferred Ideas section.
- `.planning/codebase/ARCHITECTURE.md` — single-threaded trial loop constraint.
- Related v2: `REQUIREMENTS.md` EXEC-01 (parallel sweep execution).

## Notes

Planted during the Phase 3 discuss-phase at the user's explicit request ("put the
possibility of an active poll on a list via seed for future idea").
