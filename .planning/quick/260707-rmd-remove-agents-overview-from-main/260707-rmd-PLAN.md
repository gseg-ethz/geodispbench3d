---
quick_id: 260707-rmd
slug: remove-agents-overview-from-main
description: Remove AGENTS.md + OVERVIEW.md from public main; keep AGENTS.md on develop with a ship-exclude
created: 2026-07-07
status: ready
---

# Quick Task 260707-rmd: strip internal docs from public main

## Goal

Get two non-package docs off the public `main` branch: `AGENTS.md` (internal
dev-environment guidance) and `OVERVIEW.md` (externally-maintained ETH
one-pager). Do it durably given `main` is a filtered projection of `develop`.

## Decisions (from invocation + discussion)

- **OVERVIEW.md:** remove from **both** branches. It is relocated/maintained
  outside the repo; a stale in-repo copy would only keep re-shipping.
- **AGENTS.md:** remove from **main only**, keep on `develop`. The dev workflow
  depends on it (mandated conda env); the env name is also duplicated in
  `.claude/CLAUDE.md`, but the mandate + rationale live in AGENTS.md.
- **Durability:** no automated ship-filter exists, so record a ship-exclude for
  `AGENTS.md` in `.planning/SHIP-EXCLUDES.md` so future `main` projections drop
  it. `OVERVIEW.md` needs no exclude (removed from develop too).

## Tasks

1. **PR -> main:** `git rm AGENTS.md OVERVIEW.md`.
   - verify: CI green (5 checks); files absent from `main` tree.
2. **PR -> develop:** `git rm OVERVIEW.md`; add `.planning/SHIP-EXCLUDES.md`;
   record this quick task + STATE.md row.
   - verify: CI green; `AGENTS.md` still present on develop; ship-exclude listed.

## Notes

- `main` is a filtered/squash projection of `develop` with no shared lineage
  (auto-memory `main-develop-no-shared-lineage`), so removals are done per
  branch, not by merging one into the other.
- Removal commits are `chore:`; they fold into the standing release-please PR
  (#13) as changelog lines but cut no tag / no PyPI unless that PR is merged.
