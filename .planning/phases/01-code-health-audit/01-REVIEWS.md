---
phase: 1
reviewers: [codex]
reviewed_at: 2026-06-26T13:56:15Z
plans_reviewed: [01-01-PLAN.md, 01-02-PLAN.md]
notes: "claude skipped (self — running inside Claude Code CLI); gemini/coderabbit/opencode/qwen/cursor/antigravity not installed; no local model servers running. Codex was the sole independent reviewer."
---

# Cross-AI Plan Review — Phase 1

## Codex Review

## Summary

Both plans are directionally strong and mostly match the repo. The referenced risks are real: `suite: object/Any` and `type: ignore` usage exists in [cli.py](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:123) and [runner.py](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:173), `_parser_fn_repr` is duplicated in [runner.py](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/runner.py:363) and [rescore.py](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:395), the stdout JSON heuristic is present in [cli_adapter.py](/scratch/35_geodispbench3d/src/geodispbench3d/tool/cli_adapter.py:190), and the F2S3/pchandler packaging gap is real in [pyproject.toml](/scratch/35_geodispbench3d/pyproject.toml:56). Overall, the plans should produce a useful audit report, but I would tighten evidence coverage and add stronger traceability checks before execution.

## Strengths

- The phase boundary is clear: Plan 01 gathers detector evidence, Plan 02 writes the authoritative report, and neither mutates `src/`. That matches the read-only audit goal.

- The detector set is appropriate for the mechanical buckets. `coverage` is already a dev dependency in [pyproject.toml](/scratch/35_geodispbench3d/pyproject.toml:60), while `vulture`, `deptry`, and `radon` are correctly treated as new dev-only tools.

- The human package-legitimacy gate in Plan 01 is a good control for installing new PyPI packages into the mandated conda env.

- Plan 02 targets real high-value surfaces. For example, `run --rescore` really does return nonzero when `summary.succeeded != summary.total` in [cli.py](/scratch/35_geodispbench3d/src/geodispbench3d/cli.py:214), while failed original trials are counted in `total` but skipped in [rescore.py](/scratch/35_geodispbench3d/src/geodispbench3d/sweep/rescore.py:105).

- The F2S3 route-forward concern is well-founded: the parser imports `pchandler` directly in [output_parser.py](/scratch/35_geodispbench3d/src/geodispbench3d_f2s3/output_parser.py:28), but the `f2s3` extra is empty in [pyproject.toml](/scratch/35_geodispbench3d/pyproject.toml:59).

## Concerns

- **MEDIUM:** Plan 01’s coverage evidence is narrower than the phase’s “across `src/`” framing. It runs `coverage run -m pytest tests/core` and scopes the report to `src/geodispbench3d` only, per [01-01-PLAN.md](/scratch/35_geodispbench3d/.planning/phases/01-code-health-audit/01-01-PLAN.md:108). That misses coverage evidence for `src/geodispbench3d_iof3d` and `src/geodispbench3d_f2s3`, even though those packages are included in the release package list at [pyproject.toml](/scratch/35_geodispbench3d/pyproject.toml:81). This matters because `tests/f2s3` skips if `pchandler` is absent in [tests/f2s3/conftest.py](/scratch/35_geodispbench3d/tests/f2s3/conftest.py:15), and CI currently installs an empty `f2s3` extra in [.github/workflows/ci.yml](/scratch/35_geodispbench3d/.github/workflows/ci.yml:63).

- **MEDIUM:** Plan 02 requires every `.planning/codebase/CONCERNS.md` entry to be accounted for, but its automated checks only grep for a few keywords and table/section counts in [01-02-PLAN.md](/scratch/35_geodispbench3d/.planning/phases/01-code-health-audit/01-02-PLAN.md:115). Given the breadth of existing concerns, from broad exception swallowing to missing checkpoint/resume, this can pass while silently dropping prior findings.

- **LOW:** Detector installs are unpinned. Plan 01 says to install `vulture`, `deptry`, and `radon` by name in [01-01-PLAN.md](/scratch/35_geodispbench3d/.planning/phases/01-code-health-audit/01-01-PLAN.md:104), then record resolved versions. That is reproducible as documentation, but not as a rerunnable command if the tools change behavior later.

- **LOW:** Both plans say to create summary files, but those files are not listed in `files_modified`. Plan 01 omits `01-01-SUMMARY.md` from the front matter while requiring it at [01-01-PLAN.md](/scratch/35_geodispbench3d/.planning/phases/01-code-health-audit/01-01-PLAN.md:192). Plan 02 does the same for `01-02-SUMMARY.md` at [01-02-PLAN.md](/scratch/35_geodispbench3d/.planning/phases/01-code-health-audit/01-02-PLAN.md:167).

## Suggestions

- Expand Plan 01 coverage capture to either:
  - run all tests and report skips explicitly, with `--include='src/geodispbench3d*'`, or
  - keep `tests/core` as the primary coverage run but add a separate “plugin coverage/skips” evidence section for `tests/f2s3` and `tests/iof3d`.

- Add a required `CONCERNS.md traceability appendix` to `REPORT.md`, with rows like `CONCERNS slug/location -> F-NN | superseded | false positive`. This would make D-10 verifiable.

- Record detector install commands with exact versions after approval, for example install latest approved versions once, capture `--version`, then write the reproduction command as pinned `vulture==x deptry==y radon==z`.

- Add `01-01-SUMMARY.md` and `01-02-SUMMARY.md` to `files_modified` and artifacts, or remove the output requirement if summaries are managed outside plan metadata.

## Risk Assessment

Overall risk: **MEDIUM**.

The plans are well-scoped and likely to satisfy AUDIT-01..04 at a human-review level. The main risk is not implementation breakage; it is audit incompleteness disguised as success because the coverage evidence and verification checks are weaker than the stated whole-repo/report traceability goals. Tightening plugin coverage evidence and adding a prior-concerns mapping would reduce this to LOW.

---

## Consensus Summary

Only one independent external reviewer (**codex**) was available this run — `claude`
is skipped for independence (we are running inside Claude Code), and no other CLIs or
local model servers are installed. There is therefore no cross-reviewer consensus to
triangulate; the section below records codex's verdict, which is source-grounded
(every claim carries a verified `file:line` citation against the live tree).

### Verdict

**Overall risk: MEDIUM** — plans are well-scoped, read-only, and will satisfy
AUDIT-01..04 at a human-review level. The risk is *audit incompleteness disguised as
success*: the automated verification gates are weaker than the stated whole-repo /
traceability goals.

### Strengths (codex-confirmed against source)

- Clean phase split: Plan 01 gathers detector evidence, Plan 02 authors the
  authoritative report, neither mutates `src/` — matches the read-only audit goal.
- Detector set fits the mechanical buckets; `coverage` already a dev dep
  (`pyproject.toml:60`), `vulture`/`deptry`/`radon` correctly treated as new dev-only tools.
- Human package-legitimacy gate (Plan 01 Task 1) is a sound control for new PyPI installs.
- Plan 02 targets *real* surfaces — the rescore exit-code conflation is real
  (`cli.py:214` vs `rescore.py:105`), as is the F2S3/`pchandler` packaging gap
  (`output_parser.py:28` imports `pchandler`, `f2s3` extra empty at `pyproject.toml:59`).

### Concerns (highest-priority first)

1. **MEDIUM — coverage evidence narrower than "across `src/`".** Plan 01 runs
   `coverage run -m pytest tests/core` scoped to `src/geodispbench3d` only, missing
   `geodispbench3d_iof3d` / `geodispbench3d_f2s3` (both shipped per `pyproject.toml:81`).
   `tests/f2s3` self-skips without `pchandler` (`tests/f2s3/conftest.py:15`) and CI
   installs an empty `f2s3` extra (`.github/workflows/ci.yml:63`).
2. **MEDIUM — D-10 (CONCERNS.md superset) is not machine-verifiable.** Plan 02's
   automated checks only grep a few keywords + table/section counts (`01-02-PLAN.md:115`),
   so the report can pass while silently dropping prior findings.
3. **LOW — detector installs unpinned.** Plan 01 installs by name then records resolved
   versions (`01-01-PLAN.md:104`) — reproducible as documentation, not as a re-runnable
   pinned command.
4. **LOW — SUMMARY files not in `files_modified`.** Both plans require a `*-SUMMARY.md`
   (`01-01-PLAN.md:192`, `01-02-PLAN.md:167`) but omit it from front-matter `files_modified`.

### Suggested plan tightenings (before execution)

- Broaden Plan 01 coverage capture: either run all tests with `--include='src/geodispbench3d*'`
  and report skips explicitly, or add a separate "plugin coverage/skips" evidence section
  for `tests/f2s3` and `tests/iof3d`.
- Add a required **CONCERNS.md traceability appendix** to `REPORT.md`
  (`CONCERNS slug/location → F-NN | superseded | false-positive`) to make D-10 verifiable —
  and consider strengthening the Plan 02 verify gate to assert its presence.
- Capture pinned detector versions (`vulture==x deptry==y radon==z`) in the reproduce-it README.
- Add the `*-SUMMARY.md` files to `files_modified`/artifacts, or drop the output requirement.

### Divergent Views

None — single reviewer this run.
