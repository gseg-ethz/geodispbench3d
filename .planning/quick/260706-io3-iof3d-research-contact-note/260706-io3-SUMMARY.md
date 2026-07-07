---
quick_id: 260706-io3
slug: iof3d-research-contact-note
description: Add iof3D research-access contact note to README; land on main + sync develop
date: 2026-07-06
status: complete
---

# Quick Task 260706-io3: iof3D research-access contact note — Summary

## Outcome

The README now tells users the dormant iof3D adapter is under active
development and that researchers can request it at `meyernic@ethz.ch`. The note
is live on `main` and mirrored onto `develop`, and develop's release-please
state was brought up to date at the same time.

## What was done

- **PR #10 -> `main`** (squash `7017f5b`, `docs:`): augmented the existing
  README `[iof3d]` dormancy note with the active-development + research-contact
  line. All 5 required CI checks green.
- **PR #12 -> `develop`** (rebase `ec0b99d`, `chore:`): file-level sync of the
  three files that had diverged from `main` —
  `.release-please-manifest.json` `0.1.0` -> `0.2.0`, empty -> full
  `CHANGELOG.md`, and the README note. `.planning/` deliberately untouched.
- **PR #11 closed** (unmerged): the initial `main -> develop` rebase
  back-merge — abandoned as CONFLICTING/dangerous once it was clear `main` is a
  filtered projection of `develop` with no shared lineage.

## Files changed

- `README.md` (note; on both branches)
- `CHANGELOG.md`, `.release-please-manifest.json` (develop sync to the v0.2.0
  baseline)

## Notes / follow-ups

- **No release cut.** release-please opened PR #13 (`chore(main): release
  0.2.1`) off the `docs:` commit — its config treats `docs` as releasable.
  Left unmerged by design; tags remain `v0.2.0`, nothing published to PyPI. It
  will re-edit itself on future releasable pushes to `main`.
- Ran outside the normal quick-executor path: branching was steered by hand
  for the main-first flow, so this record + the STATE.md row were added
  afterward as catch-up bookkeeping.
- Lessons captured in auto-memory: `main`/`develop` share no lineage (sync
  file-level); a `docs:` commit triggers a release-please PR here.
