# Branch-protection rulesets

This directory holds the **branch-protection enforcement layer** for
`gseg-ethz/geodispbench3d` as version-controlled JSON, plus the script that
applies it. The rulesets are a *deliverable*: they are reviewed and committed
here now, and **enabled at milestone-ship**, not during phase execution.

| File | Purpose |
|------|---------|
| `protect-main.json` | Ruleset on `refs/heads/main` |
| `protect-develop.json` | Ruleset on `refs/heads/develop` |
| `../scripts/apply-rulesets.sh` | Idempotent create-or-update applier (`gh api`) |

## What the rulesets enforce

Both payloads share one rule body; the only delta is the protected ref.

- **`pull_request`** — changes reach the branch only through a PR.
  `required_approving_review_count: 0` (solo maintainer; no second reviewer is
  required), and `allowed_merge_methods` is **`[squash, rebase]` only**. `merge`
  is deliberately dropped: `required_linear_history` rejects merge commits, so
  offering a merge button that always fails would only confuse (review MEDIUM
  05-04).
- **`required_status_checks`** — these contexts must pass before merge, pinned
  **character-for-character** to the rendered CI job names:
  - `Lint (ruff + pyright)`
  - `Test (core, 3.12)`
  - `Test (f2s3, 3.12)`
  - `Build wheel + install smoke`

  This is an **interface contract** with `ci.yml`. A one-character drift in a job
  name silently leaves the gate unsatisfiable, so Plan 05 machine-checks equality
  between these contexts and the rendered `ci.yml` job names
  (`check_ci_ruleset_contexts.py`). If you rename a CI job, update these payloads
  in the same change.
- **`non_fast_forward` + `deletion` + `required_linear_history`** — no force-push,
  no branch deletion, no merge commits.
- **`bypass_actors: []`** — nobody bypasses the gate, including admins.
- **`enforcement: active`** — the ruleset is live once applied.

### The `strict: false` tradeoff (deliberate)

`strict_required_status_checks_policy` is **`false`** in both payloads. With
strict policy *on*, a PR must be rebased onto the latest base before its green
checks count — every upstream commit re-invalidates every open PR's checks. With
it *off*, a PR that was green against a slightly out-of-date base can still merge.

For a solo-maintainer repo this is the right call: the churn of forced re-runs on
every base advance outweighs the small risk of a semantic conflict that the green
checks didn't catch. This is a conscious choice (review LOW 05-04), not an
oversight. Flip it to `true` if the project gains concurrent contributors.

## When and how to apply (ship-time only)

**Do not run the apply script during normal development or phase execution.**
Activating required checks before the pipeline is green — or before the milestone
PR to `main` has passing checks and the gseg-ethz App token is wired — will lock
out the very PR that ships the milestone (self-lockout, RESEARCH Pitfall 4).

Run it once, at milestone-ship, after:

1. CI is green on `main` and `develop` (all four contexts have actually run).
2. The gseg-ethz GitHub App is installed and its `APP_ID` / `APP_PRIVATE_KEY`
   secrets are wired (release-please authenticates through it).

Then, from a clone with an authenticated `gh`:

```bash
# 1. Always dry-run first — runs the full preflight, writes nothing.
./.github/scripts/apply-rulesets.sh --dry-run

# 2. Apply for real once the dry-run is clean.
./.github/scripts/apply-rulesets.sh

# 3. Read back to confirm.
gh api repos/gseg-ethz/geodispbench3d/rulesets --jq '.[].name'
```

### Idempotent create-or-update

The script is safe to re-run. For each payload it GETs the repo's rulesets,
matches an existing ruleset by its `name`, and then **PUTs** (update) the matched
id or **POSTs** (create) a new one. A bare `POST` would create duplicate rulesets
on every re-run (review MEDIUM 05-04 / T-05-14); the name-match create-or-update
avoids that and prints the resulting ruleset id each time.

### Preflight (always runs before any write)

Before any POST/PUT — including in `--dry-run` — the script verifies:

- **Authentication** — `gh auth status`.
- **Repo identity** — the gh context resolves to `gseg-ethz/geodispbench3d`.
- **App installation** — the GitHub App is installed on the repo.
- **Recent contexts** — every required status-check context has *recently
  appeared* as a check run on each target branch's HEAD. A context that has never
  run cannot be satisfied, so requiring it would block all merges. The preflight
  refuses to proceed if any context is missing (T-05-09).

If any check fails the script exits non-zero with a `preflight: FAIL [check]`
message and writes nothing.
