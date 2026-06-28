#!/usr/bin/env bash
# apply-rulesets.sh — apply the branch-protection rulesets to gseg-ethz/geodispbench3d.
#
# ============================================================================
#  RUN THIS ONLY AT MILESTONE-SHIP.
#
#  These rulesets pin `required_status_checks` to the exact CI job names and set
#  enforcement:active. Applying them BEFORE the pipeline is green — or before the
#  in-flight milestone PR to `main` has passing checks and the gseg-ethz App token
#  is wired — will lock out the very PR that ships the milestone (self-lockout,
#  RESEARCH Pitfall 4). The JSON payloads + this script are the deliverable; a
#  human runs the script once, at ship time, after CI is green.
#
#  Always dry-run first:   ./apply-rulesets.sh --dry-run
#  Then apply for real:    ./apply-rulesets.sh
#  Read back afterwards:   gh api repos/gseg-ethz/geodispbench3d/rulesets --jq '.[].name'
# ============================================================================
#
# Behavior:
#   * Idempotent create-or-update. For each payload the script GETs the repo's
#     rulesets, matches an existing ruleset by its `name`, and then either
#     PUTs (update) the matched id or POSTs (create) a new one. Re-running never
#     creates duplicates (review MEDIUM 05-04 / T-05-14).
#   * --dry-run prints the intended POST/PUT and the target id without writing.
#   * A preflight runs before ANY write: repo identity, gh authentication, the
#     gseg-ethz App installation, and that every required status-check context
#     has RECENTLY appeared as a check run on the target branch (so activation
#     cannot lock out maintainers — T-05-09).

set -euo pipefail

REPO="gseg-ethz/geodispbench3d"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULESET_DIR="${SCRIPT_DIR}/../rulesets"
PAYLOADS=(
  "${RULESET_DIR}/protect-main.json"
  "${RULESET_DIR}/protect-develop.json"
)

DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: apply-rulesets.sh [--dry-run] [-h|--help]

  --dry-run   Run the preflight and print the intended create/update calls
              (POST/PUT + target ruleset id) without writing anything.
  -h, --help  Show this help.

Run at milestone-ship only, after CI is green. Dry-run first.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

log()  { printf '%s\n' "$*"; }
fail() { printf 'preflight: FAIL %s\n' "$*" >&2; exit 1; }

require_tools() {
  command -v gh >/dev/null 2>&1 || { echo "error: gh CLI not found on PATH" >&2; exit 1; }
  command -v jq >/dev/null 2>&1 || { echo "error: jq not found on PATH" >&2; exit 1; }
}

# Map a payload's first included ref ("refs/heads/main") to a branch name ("main").
branch_for_payload() {
  jq -r '.conditions.ref_name.include[0] | sub("^refs/heads/"; "")' "$1"
}

# Emit the required status-check context names, one per line.
contexts_for_payload() {
  jq -r '
    .rules[]
    | select(.type == "required_status_checks")
    | .parameters.required_status_checks[].context
  ' "$1"
}

ruleset_name_for_payload() {
  jq -r '.name' "$1"
}

preflight() {
  log "==> Preflight"

  # 1. Authentication.
  gh auth status >/dev/null 2>&1 || fail "[auth] gh is not authenticated; run 'gh auth login'"
  log "    [auth] gh authenticated"

  # 2. Repo identity — the gh context must resolve to the expected repo.
  local seen
  seen="$(gh repo view "$REPO" --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
  [[ "$seen" == "$REPO" ]] || fail "[repo] expected ${REPO}, gh resolved '${seen:-<none>}'"
  log "    [repo] ${REPO} reachable"

  # 3. gseg-ethz App installation — release-please / status checks authenticate
  #    through it. If the App is not installed, activating required checks can
  #    leave no authorized path to update the ref.
  if ! gh api "repos/${REPO}/installation" --jq '.app_slug' >/dev/null 2>&1; then
    fail "[app] no GitHub App installation visible on ${REPO} (is the gseg-ethz App installed?)"
  fi
  log "    [app] GitHub App installation present"

  # 4. Required contexts must have RECENTLY appeared as check runs on each target
  #    branch's HEAD. A context that has never run cannot be satisfied, so making
  #    it required would block all merges.
  local payload branch sha ctx have
  for payload in "${PAYLOADS[@]}"; do
    [[ -f "$payload" ]] || fail "[payload] missing ${payload}"
    branch="$(branch_for_payload "$payload")"
    sha="$(gh api "repos/${REPO}/commits/${branch}" --jq '.sha' 2>/dev/null || true)"
    [[ -n "$sha" ]] || fail "[checks] cannot resolve HEAD of '${branch}' on ${REPO}"
    have="$(gh api "repos/${REPO}/commits/${sha}/check-runs" --paginate \
            --jq '.check_runs[].name' 2>/dev/null || true)"
    while IFS= read -r ctx; do
      [[ -z "$ctx" ]] && continue
      if ! grep -Fxq "$ctx" <<<"$have"; then
        fail "[checks] context '${ctx}' has not recently run on '${branch}' (${sha:0:7}); refusing to require it"
      fi
      log "    [checks] '${ctx}' observed on '${branch}'"
    done < <(contexts_for_payload "$payload")
  done

  log "==> Preflight passed"
}

# Idempotent create-or-update for one payload.
apply_one() {
  local payload="$1"
  local name id existing
  name="$(ruleset_name_for_payload "$payload")"

  existing="$(gh api "repos/${REPO}/rulesets" --paginate 2>/dev/null || echo '[]')"
  id="$(jq -r --arg n "$name" '.[] | select(.name == $n) | .id' <<<"$existing" | head -n1)"

  if [[ -n "$id" && "$id" != "null" ]]; then
    if $DRY_RUN; then
      log "DRY-RUN: PUT repos/${REPO}/rulesets/${id}  (update '${name}' from ${payload})"
      return 0
    fi
    log "==> Updating ruleset '${name}' (id ${id})"
    local new_id
    new_id="$(gh api --method PUT "repos/${REPO}/rulesets/${id}" \
                --input "$payload" --jq '.id')"
    log "    updated ruleset id: ${new_id}"
  else
    if $DRY_RUN; then
      log "DRY-RUN: POST repos/${REPO}/rulesets  (create '${name}' from ${payload})"
      return 0
    fi
    log "==> Creating ruleset '${name}'"
    local new_id
    new_id="$(gh api --method POST "repos/${REPO}/rulesets" \
                --input "$payload" --jq '.id')"
    log "    created ruleset id: ${new_id}"
  fi
}

main() {
  log "############################################################"
  log "# apply-rulesets.sh — MILESTONE-SHIP ONLY"
  log "# Applying branch protection to ${REPO}"
  $DRY_RUN && log "# MODE: --dry-run (no writes)"
  log "############################################################"

  require_tools
  preflight

  for payload in "${PAYLOADS[@]}"; do
    apply_one "$payload"
  done

  if $DRY_RUN; then
    log "==> Dry-run complete. Re-run without --dry-run to apply."
  else
    log "==> Done. Verify with: gh api repos/${REPO}/rulesets --jq '.[].name'"
  fi
}

main
