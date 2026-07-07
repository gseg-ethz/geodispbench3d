---
quick_id: 260707-rmd
slug: remove-agents-overview-from-main
description: Remove AGENTS.md + OVERVIEW.md from public main; keep AGENTS.md on develop with a ship-exclude
date: 2026-07-07
status: complete
---

# Quick Task 260707-rmd: strip internal docs from public main — Summary

## Outcome

`AGENTS.md` and `OVERVIEW.md` are removed from public `main`. `AGENTS.md` is
retained on `develop` for development and protected from ship regression by a
recorded ship-exclude; `OVERVIEW.md` is removed from `develop` too.

## What was done

- **PR #15 -> `main`** (`chore:`): `git rm AGENTS.md OVERVIEW.md`. Both absent
  from the public tree.
- **PR (this) -> `develop`** (`chore:`): `git rm OVERVIEW.md`; added
  `.planning/SHIP-EXCLUDES.md` recording `AGENTS.md` (and `.planning/`) as
  paths to strip from future `main` projections; `AGENTS.md` kept on develop.

## Files changed

- `AGENTS.md` — removed from `main` only (kept on `develop`)
- `OVERVIEW.md` — removed from both branches
- `.planning/SHIP-EXCLUDES.md` — new (develop): ship-exclude source of truth

## Notes / follow-ups

- Durability: with no automated ship-filter, `SHIP-EXCLUDES.md` is the source
  of truth to consult at `gsd-ship`; auto-memory `milestone-ship-to-main-process`
  updated to point at it.
- No release cut: `chore` removals fold into the parked release-please PR #13;
  tags remain `v0.2.0`, nothing published.
