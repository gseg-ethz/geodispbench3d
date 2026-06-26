# Phase 1: Code-Health Audit - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

A **read-only** code-health audit that produces a single written findings report
(`REPORT.md`). No code changes land in this phase — the report is the only
deliverable, and it gates Phase 2 (fixes are scoped *from* it, not pre-committed).

The audit covers, at minimum (AUDIT-01–04): bloat, dead code, and duplication;
the three architecture-flagged anti-patterns (untyped `SuiteConfig`, duplicated
`SweepParameter` coercion, duplicated `_parser_fn_repr`); a focused risk review of
the three CLI surfaces (`cli.py`, `CliToolAdapter`, F2S3 `conda-run`); and every
finding severity-classified with a fix/defer/accept disposition.

**This is a confidence gate, not a fix phase.** Clarifies/locks *how* the audit is
run and *how* the report is shaped — never *whether* to fix things (that's Phase 2).

</domain>

<decisions>
## Implementation Decisions

### Report shape & format
- **D-01:** The report is a **single `REPORT.md`** with a summary findings table at
  the top (columns: stable ID, location, severity, disposition) followed by one
  detail section per finding. Human-readable and greppable by finding ID; the table
  is the index Phase 2 iterates over.
- **D-02:** Each finding record carries, beyond the required severity + disposition:
  **location (file:line)**, **evidence/impact** (the concrete failure mode), a
  **fix sketch** (recommended approach), and a **requirement mapping** (which
  AUDIT/FIX requirement or owning phase the finding ties to).
- **D-03:** Finding IDs are **stable** (e.g. `F-01`) so Phase 2 plans and commits
  can reference them directly.

### Severity & disposition rubric
- **D-04:** Severity scale is **publish-anchored: Blocker / Major / Minor.**
  Blocker = unsafe to publish as-is; Major = should fix this milestone, not unsafe;
  Minor = cosmetic / low-value. Severity is tied to release readiness.
- **D-05:** **The audit recommends a disposition per finding (with rationale); the
  user ratifies** the final fix/defer/accept set at the Phase 2 discussion. The
  audit does not unilaterally lock fix scope — human-in-the-loop gate preserved
  (audit-first philosophy).
- **D-06:** Disposition decision rule:
  - **fix** = Blocker/Major severity **and** low-to-moderate fix effort, in-scope
    for this milestone.
  - **defer** = real but belongs to known v2 / out-of-milestone work (e.g. parallel
    sweeps, Ax 2.x migration, partitioned parquet) — recorded, not fixed now.
  - **accept** = by-design or too low-value to touch (e.g. YAML-executes-code plugin
    behavior) — documented as accepted risk, no action.
  - **route-forward** = findings about CLI / licensing / packaging / CI are **tagged
    to their owning phase (3/4/5)** rather than dispositioned fix/defer/accept here,
    to avoid double-handling.

### Audit lens / categories
- **D-07:** Beyond the four required buckets (bloat / dead code / duplication / CLI
  risk) and the security observations already in the codebase map, the audit adds a
  **first-class "design sensibility" category: code that is *functional but not
  really sensible*** — awkward constructions, non-idiomatic patterns, questionable
  designs a reader would reasonably challenge. This is an explicit user ask, not a
  security-only audit. Seed examples to formalize: the 220-line
  `build_app_config_from_parameters` field-by-field reconstruction
  (`geodispbench3d_iof3d/adapter.py`), the `getattr(...) or getattr(...lambda...)`
  provenance chain (`sweep/runner.py:238-241`), the `_ = asdict` lint-suppression
  hack (`sweep/rescore.py:27,410`), and the heuristic "scan stdout bottom-up for the
  first `{`-line" output collection (`tool/cli_adapter.py:190-201`).

### Audit method
- **D-08:** **Reasoned manual file:line review is the spine** of the audit — it is
  the only way to catch the design-sensibility findings (D-07). Automated detectors
  run as **supporting evidence** for the mechanical buckets, not as the primary
  inventory.
- **D-09:** Detectors to run and capture output from (beyond the repo's existing
  ruff / pyright):
  - **Dead code:** `vulture` (or `deadcode`) — reproducible unused-code list.
  - **Coverage:** run the existing `pytest` + `coverage` to quantify the test-gap
    findings (e.g. `runner.py`, `evaluation.py`, `store.py` untested).
  - **Dependency hygiene:** `deptry` — unused/missing/transitive deps (directly
    relevant to the `pchandler` / `iof3d` extras tangle this milestone untangles).
  - **Complexity:** `radon` (or ruff `C901`) — flag high-complexity / long functions
    as quantified evidence for design-sensibility findings.
  - All tool invocations go through the mandated conda env per `AGENTS.md` (no bare
    `python`/`pip`/`pytest`).

### Relation to existing map & breadth
- **D-10:** **Validate + extend** the existing `.planning/codebase/CONCERNS.md`:
  independently re-examine each of its ~20 findings (confirm real, still present,
  correctly located) and go deeper to surface what it missed — especially the
  design-sensibility findings. The new `REPORT.md` **supersedes** CONCERNS.md as the
  authoritative, dispositioned record.
- **D-11:** **Whole-repo read scope** — `src/`, `tests/`, packaging (`pyproject.toml`),
  CI (`.github/`), and docs are all in audit *read* scope. Per D-06, findings that
  belong to Phases 3/4/5 (CLI/licensing/packaging/CI) are **surfaced and tagged to
  the owning phase**, not resolved or fully detailed here — whole-repo breadth feeds
  those phases without pre-empting their work.

### Claude's Discretion
- Exact `REPORT.md` table column ordering/markdown formatting, finding-ID numbering
  scheme, and section grouping within the report.
- Which specific detector versions/flags to use and how to embed their raw output
  (inline vs appendix), as long as the runs are reproducible and conda-env-correct.
- Whether to group findings by category or by severity in the detail sections.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 1: Code-Health Audit" — goal, success criteria, requirement list.
- `.planning/REQUIREMENTS.md` §Audit (AUDIT-01–04) — the four locked audit requirements this phase satisfies.
- `.planning/PROJECT.md` §Requirements/Active, §Context, §Key Decisions — milestone framing, the audit-first gate, and the three pre-flagged anti-patterns.

### Pre-audit input (to validate + extend, then supersede)
- `.planning/codebase/CONCERNS.md` — the ~20-finding pre-audit (tech debt, known bugs, security, fragile areas, test-coverage gaps) that the report independently re-verifies and extends.
- `.planning/codebase/ARCHITECTURE.md` — flags the three anti-patterns (untyped `SuiteConfig`, duplicated `SweepParameter` coercion, duplicated `_parser_fn_repr`) and the append-only parquet O(n) note.
- `.planning/codebase/TESTING.md` — current test suite layout (core/iof3d/f2s3) and gaps, input to the coverage evidence.
- `.planning/codebase/CONVENTIONS.md` — the project's idioms; the baseline against which "not really sensible / non-idiomatic" design-sensibility findings are judged.
- `.planning/codebase/STRUCTURE.md`, `.planning/codebase/STACK.md`, `.planning/codebase/INTEGRATIONS.md` — repo layout, dependency stack, and the iof3D/F2S3/pchandler integration surfaces.

### Dev-environment constraint
- `AGENTS.md` — mandates all python/pip/pytest invocations run through the conda env `iof3d_cosicorr3d-dev312`; F2S3 runs via `conda run -n f2s3-dev312`. Applies to every detector run in the audit.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.planning/codebase/CONCERNS.md`: a strong starting inventory with file:line
  anchors — the audit validates and extends it rather than starting cold (D-10).
- Existing quality tooling (ruff, pyright, pytest, coverage, pre-commit) is already
  configured in `pyproject.toml` — the audit reuses it and adds vulture/deptry/radon
  as evidence detectors (D-09).

### Established Patterns
- Findings should cite **`file:line`** anchors throughout, matching CONCERNS.md's
  existing convention (D-02).
- Tool-agnostic core: the audit's design-sensibility lens (D-07) is judged against
  the conventions documented in `.planning/codebase/CONVENTIONS.md`.

### Integration Points
- The report's `route-forward` tags (D-06) are the explicit hand-off into Phases 3
  (CLI), 4 (licensing/packaging), and 5 (CI/CD) — whole-repo breadth (D-11) feeds
  those phases.
- `REPORT.md` is the input contract for Phase 2 planning: its findings table is the
  unit Phase 2 turns into atomic fix-commits.

</code_context>

<specifics>
## Specific Ideas

- User explicitly broadened the audit beyond a "security/bloat" framing: they want
  findings for code that is **"functional but not really sensible as such"** —
  captured as the design-sensibility category (D-07).
- The report is meant to be **ratified, not auto-applied**: the audit recommends,
  the user confirms dispositions at Phase 2 (D-05).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Findings that surface for Phases
3/4/5 are not "deferred ideas" here; they are routed forward via the `route-forward`
disposition (D-06) and recorded in the report itself.)

</deferred>

---

*Phase: 1-Code-Health Audit*
*Context gathered: 2026-06-26*
