# Audit Evidence — raw detector output (Phase 01, Plan 01)

This directory holds the **reproducible raw output** of the automated detectors that
provide *supporting* evidence for the Phase 1 code-health audit (D-08: reasoned manual
review is the spine; detectors are corroboration, not the primary inventory). The
distilled, file:line-anchored summary lives one level up in
[`../EVIDENCE.md`](../EVIDENCE.md).

Every detector was run through the mandated conda env `iof3d_cosicorr3d-dev312`
(per `AGENTS.md` — bare `python`/`pip`/`pytest` are forbidden). Nothing under `src/`
and nothing in `pyproject.toml` was modified by this evidence run (read-only-audit
invariant).

## Environment

- Env: `iof3d_cosicorr3d-dev312` (the iof3D dev env — `iof3D` + `pchandler` are importable here)
- Python: `3.12.12`
- Captured: 2026-06-26

## Pinned detector versions (reproduce-it install)

The three net-new detectors are **dev-only**, installed into the conda env for the
duration of the audit and **NOT** added to `pyproject.toml`. They were
human-verified on PyPI (blocking-human legitimacy gate, Task 1) and approved before
install. `ruff`, `coverage`, and `pytest` are already declared project dev tooling.

```bash
# net-new detectors (dev-only, conda env only — NOT a pyproject.toml change):
conda run -n iof3d_cosicorr3d-dev312 pip install vulture==2.16 deptry==0.25.1 radon==6.0.1
```

| Tool     | Version | Role                                            |
|----------|---------|-------------------------------------------------|
| vulture  | 2.16    | dead-code finder                                |
| deptry   | 0.25.1  | unused / missing / transitive dependency check  |
| radon    | 6.0.1   | complexity (cc) + maintainability index (mi) — SUPPLEMENTARY |
| ruff     | 0.15.12 | C901 cyclomatic complexity — **PRIMARY** signal (already pinned dev tool) |
| coverage | 7.11.0  | test-coverage measurement (already a dev dep)   |
| pytest   | 8.4.2   | test runner (already a dev dep)                 |

> radon note: radon is unmaintained (last release v6.0.1, March 2023; PyPI
> classifiers stop at Python 3.9) but its README claims 3.12 support. In **this**
> env it ran cleanly on Python 3.12.12 (`radon cc` and `radon mi` both exited 0), so
> the complexity evidence did **not** need to degrade to ruff-only. ruff C901 remains
> the authoritative/primary complexity signal regardless; radon is kept dev-only and
> one-shot.

## How each capture file was produced

All commands are run from the repo root `/scratch/35_geodispbench3d`. A detector that
exits non-zero **because it found findings** is success, not failure — output is
captured regardless (the trailing `conda.cli.main_run ... failed` line some files
carry is just conda echoing that non-zero exit).

| File | Command |
|------|---------|
| `vulture.txt` | `conda run -n iof3d_cosicorr3d-dev312 vulture src/ --min-confidence 60` |
| `coverage.txt` | `conda run -n iof3d_cosicorr3d-dev312 coverage run --source=geodispbench3d,geodispbench3d_iof3d,geodispbench3d_f2s3 -m pytest tests/ -ra` then `coverage report -m` |
| `coverage-skips.txt` | pytest collection + short-test-summary from the same `coverage run ... pytest tests/ -ra` invocation |
| `deptry.txt` | `NO_COLOR=1 conda run -n iof3d_cosicorr3d-dev312 deptry . --known-first-party geodispbench3d` (piped through `sed -r "s/\x1b\[[0-9;]*m//g"` to strip ANSI) |
| `ruff-c901.txt` | `conda run -n iof3d_cosicorr3d-dev312 ruff check src/ --select C901 --config 'lint.mccabe.max-complexity=10' --output-format concise` |
| `radon-cc.txt` | `conda run -n iof3d_cosicorr3d-dev312 radon cc src/ -s -a --total-average --order SCORE` |
| `radon-mi.txt` | `conda run -n iof3d_cosicorr3d-dev312 radon mi src/ -s --sort` |

### Notes on flag / scope choices (Claude's Discretion, D-09)

- **vulture `--min-confidence 60`**: a moderate threshold — surfaces actionable
  unused names while suppressing the noisiest low-confidence guesses. vulture's own
  per-finding confidence is preserved in the output for the manual review to weigh.
- **coverage `--source=<three packages>`**: scopes measurement to exactly the three
  shipped packages, so the per-file table is already equivalent to
  `coverage report --include=src/geodispbench3d*` (every measured file is
  `src/geodispbench3d*`). The explicit `--include` glob was dropped only because it
  gets mangled passing through `conda run` shell quoting; the `--source` scoping
  achieves the same result.
- **coverage honesty**: in this env the plugin suites `tests/iof3d` and `tests/f2s3`
  **ran** (iof3D + pchandler importable) — 32 passed, 0 skipped. In CI / a lean env
  they self-skip and the plugin packages would read 0%/low because the suite is
  unexercised, not untested. `coverage-skips.txt` records this in full.
- **deptry `--known-first-party geodispbench3d`**: the package is editable-installed
  (src layout), so deptry's dist-info scan otherwise treats every intra-package
  `import geodispbench3d.*` as a DEP003 transitive dependency (48 false positives in
  the unfiltered run). Marking the core package first-party removes that self-import
  noise. There are **no DEP001 (missing)** findings.
- **ruff C901 `max-complexity=10`**: ruff's conventional default; functions above
  McCabe complexity 10 are flagged. This is the PRIMARY complexity signal.
- **radon `cc -s -a --order SCORE` / `mi -s --sort`**: absolute, letter-graded
  scores sorted worst-first; the maintainability index is radon's unique value over
  ruff. SUPPLEMENTARY corroboration only.

## Read-only-audit invariant

This evidence run made **no** change under `src/` and **no** change to
`pyproject.toml`. The only artifacts produced are the capture files in this directory
and `../EVIDENCE.md`. Verify with:

```bash
git diff --quiet -- src pyproject.toml && echo "read-only invariant OK"
```
