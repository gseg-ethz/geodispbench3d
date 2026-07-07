# Ship Excludes — paths to strip from public `main`

`main` is a filtered/squash projection of `develop` (see the auto-memory
`main-develop-no-shared-lineage`). At each milestone ship, rebuild `main` from
`develop` **without** the paths below. There is no automated filter script yet,
so this list is the source of truth — check it during `gsd-ship`.

| Path | Reason | Since |
|------|--------|-------|
| `.planning/` | GSD planning tree; internal, never public | v0.2 ship (2026-06-28) |
| `AGENTS.md` | Internal dev-env guidance (mandated conda env + hardcoded local absolute path); kept on `develop` for development only | 2026-07-07 (quick 260707-rmd) |
| `.claude/` | GSD-generated project instructions (`.claude/CLAUDE.md`) for the dev workflow; kept on `develop` for development only | 2026-07-07 (quick 260707-clc) |

Notes:
- `OVERVIEW.md` is **not** listed here: it was removed from `develop` as well
  (quick 260707-rmd), so it cannot regress onto `main` and needs no exclude.
- When adding an exclude, also remove the file from the current `main` via a
  direct PR (the exclude only governs *future* ships).
