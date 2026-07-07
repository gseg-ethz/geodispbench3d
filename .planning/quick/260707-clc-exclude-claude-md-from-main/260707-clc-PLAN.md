---
quick_id: 260707-clc
slug: exclude-claude-md-from-main
description: Remove .claude/ (CLAUDE.md) from public main; keep on develop with a ship-exclude
created: 2026-07-07
status: ready
---

# Quick Task 260707-clc: exclude .claude/ from public main

## Goal

Strip Claude/GSD-specific config (`.claude/CLAUDE.md`, the GSD-generated
project instructions) from public `main`, keeping it on `develop` for the
development workflow. Follow-on to 260707-rmd (AGENTS.md).

## Decisions

- **`.claude/`:** remove from **main only**, keep on `develop`. It is the
  GSD-generated project-instruction file that drives development; the shipped
  package does not need it and public consumers should not see it.
- **Durability:** add `.claude/` to `.planning/SHIP-EXCLUDES.md` so future
  `main` projections drop it (no automated ship-filter exists).

## Tasks

1. **PR -> main:** `git rm -r .claude`.
   - verify: CI green; `.claude/` absent from `main` tree; present on develop.
2. **PR -> develop:** add `.claude/` row to `.planning/SHIP-EXCLUDES.md`;
   record this quick task + STATE.md row.

## Notes

- Only `.claude/CLAUDE.md` was tracked; skills/settings/agents live in `$HOME`,
  not the repo, so nothing else to strip.
- `chore:` removal folds into the standing release-please PR (#13); no tag/PyPI.
