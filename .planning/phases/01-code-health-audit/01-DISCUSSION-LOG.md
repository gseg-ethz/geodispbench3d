# Phase 1: Code-Health Audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 1-Code-Health Audit
**Areas discussed:** Report shape & format, Severity & disposition rubric, Audit method, Relation to CONCERNS.md + breadth

---

## Report shape & format

### Q: How should the findings report be structured?

| Option | Description | Selected |
|--------|-------------|----------|
| Table + detail sections | One REPORT.md: summary findings table (ID, location, severity, disposition) + per-finding detail sections | ✓ |
| Machine-readable index + report | findings.yaml Phase 2 iterates programmatically + companion REPORT.md | |
| Prose report | Narrative grouped by theme, findings inline | |

**User's choice:** Table + detail sections.

### Q: What should each finding record carry? (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| Location (file:line) | Precise anchor(s) | ✓ |
| Evidence/impact | Failure mode caused | ✓ |
| Fix sketch | Recommended approach per finding | ✓ |
| Requirement / req-mapping | Tag finding to AUDIT/FIX requirement | ✓ |

**User's choice:** All four.

---

## Severity & disposition rubric

### Q: What severity scale?

| Option | Description | Selected |
|--------|-------------|----------|
| Publish-blocking framing | Blocker / Major / Minor, anchored to the release gate | ✓ |
| Standard 4-tier | Critical / High / Medium / Low | |
| Impact × effort | Two-axis scoring | |

**User's choice:** Publish-blocking framing (Blocker / Major / Minor).

### Q: Who assigns disposition, and when?

| Option | Description | Selected |
|--------|-------------|----------|
| Audit recommends, you ratify | Report proposes disposition; user confirms at Phase 2 | ✓ |
| Audit assigns outright | Audit commits fix/defer/accept via written rule | |

**User's choice:** Audit recommends, user ratifies.

### Q: What decision rule drives the disposition? (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| Fix = blocker/major + cheap | Default fix for high-severity, low-effort, in-scope | ✓ |
| Defer = out-of-milestone scope | Real but v2/known-future work | ✓ |
| Accept = intentional/low-value | By-design or too low-value | ✓ |
| Out-of-scope phases route forward | CLI/licensing/packaging findings tagged to owning phase 3/4/5 | ✓ |

**User's choice:** All four.

**Notes:** User added (via free text) that the audit should not be a security-only
exercise — they want findings for code that is "functional but not really sensible as
such." This was folded in as a first-class **design-sensibility** category (CONTEXT.md
D-07), with seed examples (220-line iof3D adapter fn, the `getattr ... or getattr ...
lambda` provenance chain, the `_ = asdict` lint hack, the stdout-bottom-up JSON scrape).

---

## Audit method

### Q: How should the audit gather evidence?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual spine + tool evidence | Reasoned manual file:line review backbone; detectors as supporting evidence | ✓ |
| Tool-first, manual gap-fill | Detector output as primary inventory, manual fills gaps | |
| Purely manual | Reasoned review only, no new tooling | |

**User's choice:** Manual spine + tool evidence.

### Q: Which automated detectors? (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| Dead-code (vulture/deadcode) | Static unused-code list | ✓ |
| Coverage report | Quantify test-gap findings | ✓ |
| Dependency hygiene (deptry) | Unused/missing/transitive deps | ✓ |
| Complexity (radon/ruff C901) | Flag high-complexity/long functions | ✓ |

**User's choice:** All four.

---

## Relation to CONCERNS.md + breadth

### Q: How should Phase 1 treat the existing CONCERNS.md?

| Option | Description | Selected |
|--------|-------------|----------|
| Validate + extend | Independently re-verify each finding, go deeper; report supersedes the map | ✓ |
| Spine, go deeper | Trust the map as inventory, focus on net-new + disposition | |
| Fresh independent pass | Audit from scratch, reconcile at end | |

**User's choice:** Validate + extend.

### Q: What's the read scope of the audit?

| Option | Description | Selected |
|--------|-------------|----------|
| src/ + tests/, note adjacent | Audit src/ + tests/ deep, surface-note packaging/config | |
| Strictly src/ | src/ only, per AUDIT-01 literal wording | |
| Whole repo | src/, tests/, packaging, CI, docs all in scope | ✓ |

**User's choice:** Whole repo.

**Notes:** Reconciled with the route-forward disposition rule — whole-repo breadth
surfaces and tags CLI/licensing/packaging/CI findings to phases 3/4/5 rather than
resolving them, so breadth feeds those phases without pre-empting their work.

---

## Claude's Discretion

- Exact REPORT.md table column ordering / markdown formatting and finding-ID scheme.
- Specific detector versions/flags and how raw output is embedded (inline vs appendix).
- Whether report detail sections are grouped by category or by severity.

## Deferred Ideas

None — discussion stayed within phase scope. Findings for phases 3/4/5 are routed
forward via disposition tagging, not deferred as ideas.
