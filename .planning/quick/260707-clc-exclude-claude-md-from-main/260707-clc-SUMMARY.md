---
quick_id: 260707-clc
slug: exclude-claude-md-from-main
description: Remove .claude/ (CLAUDE.md) from public main; keep on develop with a ship-exclude
date: 2026-07-07
status: complete
---

# Quick Task 260707-clc: exclude .claude/ from public main — Summary

## Outcome

`.claude/` (only `.claude/CLAUDE.md` was tracked) is removed from public
`main` and kept on `develop`, protected from ship regression by a
`SHIP-EXCLUDES.md` entry. Follow-on to 260707-rmd.

## What was done

- **PR #17 -> `main`** (`chore:`): `git rm -r .claude`. Absent from the public
  tree; retained on `develop`.
- **PR (this) -> `develop`** (`chore:`): added `.claude/` to
  `.planning/SHIP-EXCLUDES.md`; recorded the quick task + STATE.md row.

## Files changed

- `.claude/CLAUDE.md` — removed from `main` only (kept on `develop`)
- `.planning/SHIP-EXCLUDES.md` — added `.claude/` exclude row

## Notes / follow-ups

- Ship auto-memory `milestone-ship-to-main-process` already updated to point at
  `SHIP-EXCLUDES.md`; its filter command should include `.claude` alongside
  `.planning` and `AGENTS.md` at the next ship.
- No release cut: `chore` removal folds into parked release-please PR #13; tags
  remain `v0.2.0`.
