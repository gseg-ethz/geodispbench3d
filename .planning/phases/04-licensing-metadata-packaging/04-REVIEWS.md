---
phase: 4
reviewers: [codex]
reviewed_at: 2026-06-27T18:34:49Z
plans_reviewed: [04-01-PLAN.md, 04-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 4

> Reviewer: **Codex** (codex-cli 0.142.2, GPT-5 class). Claude was skipped for
> independence (this review was launched from inside Claude Code). Single external
> reviewer, so the Consensus section below distills Codex's own findings by
> severity rather than cross-model agreement.

## Codex Review

# Cross-AI Plan Review

## 04-01 — Licensing and metadata

### Summary

The plan correctly identifies the current licensing mismatch and publish-blocking classifier. Its metadata edits are appropriately narrow and backed by tests. The main gap is documentation consistency: removing the `iof3d` extra makes several existing installation statements inaccurate, but the plan updates only one nearby README note.

### Strengths

- The targeted license changes match the repository:

  - `pyproject.toml` already declares BSD-3-Clause at [pyproject.toml:10](/scratch/35_geodispbench3d/pyproject.toml:10).
  - `CITATION.cff` agrees at [CITATION.cff:10](/scratch/35_geodispbench3d/CITATION.cff:10).
  - `LICENSE` is BSD 3-Clause at [LICENSE:1](/scratch/35_geodispbench3d/LICENSE:1).
  - README is the sole contradictory license surface at [README.md:80](/scratch/35_geodispbench3d/README.md:80).

- Removing `Private :: Do Not Upload` is necessary and precisely scoped; the classifier and its removal comment are at [pyproject.toml:21](/scratch/35_geodispbench3d/pyproject.toml:21).

- The proposed classifiers complement rather than replace the existing correct Python, OSI-license, and OS classifiers at [pyproject.toml:15](/scratch/35_geodispbench3d/pyproject.toml:15).

- Testing metadata with `tomllib` is inexpensive, deterministic, and appropriate for preventing regression.

- The plan correctly recognizes that README becomes the PyPI long description through [pyproject.toml:91](/scratch/35_geodispbench3d/pyproject.toml:91).

### Concerns

- **MEDIUM — README remains internally contradictory.** Adding an unavailability note beside the `[iof3d]` command does not fix the combined installation command at [README.md:41](/scratch/35_geodispbench3d/README.md:41), which still advertises `[iof3d,f2s3,dashboard]`. The package-layout description also says the adapter is “gated by `[iof3d]`” at [README.md:66](/scratch/35_geodispbench3d/README.md:66), although the extra will no longer exist.

- **LOW — related documentation and test guidance remain stale.** The root test documentation says iof3D tests require the removed extra at [tests/conftest.py:7](/scratch/35_geodispbench3d/tests/conftest.py:7), as does [tests/iof3d/conftest.py:7](/scratch/35_geodispbench3d/tests/iof3d/conftest.py:7). These are not public package metadata, but they undermine the claimed consistency of the development workflow.

- **LOW — URL tests are too permissive.** Checking only that URLs are non-empty HTTPS values would accept private hosts or unrelated targets. The threat model claims public GitHub URLs, but the proposed test does not enforce the host or path.

- **LOW — testing `CITATION.cff` by line-oriented text parsing is brittle.** The plan says to assert the `license:` line equals a value, but YAML spacing or quoting changes could create false failures without changing meaning.

### Suggestions

- Update or remove the combined `[iof3d,f2s3,dashboard]` command and revise the “gated by `[iof3d]` extra” repository-layout wording.

- Add `tests/conftest.py` and `tests/iof3d/conftest.py` to the documentation-consistency edit, or explicitly defer them with a tracked task.

- Assert that Documentation and Changelog URLs use `github.com/gseg-ethz/geodispbench3d` and the intended paths.

- Either parse `CITATION.cff` structurally using an existing YAML dependency or keep the text assertion deliberately tolerant of quoting and whitespace.

### Risk Assessment

**LOW–MEDIUM.** The legal and metadata objectives will be met, but users could still encounter contradictory public installation instructions unless the remaining README references are corrected.

---

## 04-02 — Packaging and dormant iof3D guard

### Summary

The core design is sound: current package import eagerly reaches private dependencies, and a PEP 562 lazy export will make plain package import succeed while deferring adapter imports. The F2S3 dependency diagnosis is also correct. However, the proposed error handling is too broad, the simulated-absence tests risk contaminating process state, and the plan defers the only validation that proves the public F2S3 install actually resolves.

### Strengths

- The plan correctly traces the current failure:

  - Package import eagerly imports adapter, factory, and parser at [src/geodispbench3d_iof3d/__init__.py:20](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/__init__.py:20).
  - Adapter import immediately requires `iof3D`, `pc2img`, and `pchandler` at [adapter.py:19](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/adapter.py:19).
  - Factory independently imports `iof3D` at [factory.py:18](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/factory.py:18).

- The PEP 562 mechanism will achieve the requested basic behavior: after eager imports are removed, `import geodispbench3d_iof3d` executes only the lightweight package initializer; accessing a mapped adapter symbol invokes the heavy submodule.

- `parse_iof3d_output` is correctly identified as not requiring iof3D. Its module imports `pchandler`, NumPy, and core types, but no `iof3D` or `pc2img`, at [output_parser.py:23](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/output_parser.py:23).

- Splitting the CLI is necessary. The current entry-point module imports `iof3D` at module load at [cli.py:15](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/cli.py:15), before its Hydra-decorated `main` can run at [cli.py:76](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/cli.py:76).

- Moving the Hydra implementation to `_sweep_cli.py` should preserve relative config lookup because the new module remains in the same package directory.

- The F2S3 extra change is justified by actual code: package import eagerly reaches the parser at [geodispbench3d_f2s3/__init__.py:11](/scratch/35_geodispbench3d/src/geodispbench3d_f2s3/__init__.py:11), and that parser imports three `pchandler` APIs at [output_parser.py:28](/scratch/35_geodispbench3d/src/geodispbench3d_f2s3/output_parser.py:28).

- Retaining `geodispbench3d_iof3d` in the wheel is correctly accounted for by the explicit package list at [pyproject.toml:69](/scratch/35_geodispbench3d/pyproject.toml:69).

### Concerns

- **HIGH — `__getattr__` catches every `ImportError` and mislabels unrelated defects.** A transitive import bug, missing `pchandler`, or code regression inside a target module would all become “iof3D not publicly available.” Chaining preserves diagnostics but does not make the primary message accurate. This especially affects `parse_iof3d_output`, whose actual optional dependency is `pchandler`, not iof3D.

- **HIGH — PKG-02 is not demonstrated in this phase.** Declaring `f2s3 = ["pchandler ~= 2.1"]` should make resolution possible, but only a clean install verifies the published metadata and the dependency’s own constraints. The existing CI F2S3 job would exercise it at [ci.yml:61](/scratch/35_geodispbench3d/.github/workflows/ci.yml:61), but all test jobs are currently blocked behind the known-red lint job at [ci.yml:47](/scratch/35_geodispbench3d/.github/workflows/ci.yml:47). Deferring this therefore leaves a phase success criterion unproven.

- **MEDIUM — the claim that an unknown extra “errors” is inaccurate.** Pip commonly warns that the distribution does not provide the requested extra while continuing installation. Commenting out the extra prevents private dependencies from resolving, but does not reliably give users a hard failure.

- **MEDIUM — simulated-absence tests mutate `sys.modules` without restoration.** Directly popping modules is not undone by `monkeypatch`; later tests can observe missing or partially re-imported modules. This is particularly risky in the mandated dev environment where real iof3D tests may run later.

- **MEDIUM — no explicit test covers the nongated parser path.** The plan correctly explains that `parse_iof3d_output` remains usable when `pchandler` is available, but only tests an adapter symbol. A regression mapping the parser to the wrong module would go unnoticed.

- **MEDIUM — CLI testing by calling `cli.main()` does not fully prove console behavior.** It verifies `SystemExit`, but not installed entry-point wiring, stderr presentation, exit status, or traceback suppression at process level. The declared entry point is [pyproject.toml:40](/scratch/35_geodispbench3d/pyproject.toml:40).

- **LOW — documentation still claims the legacy CLI “still works.”** [docs/tools/iof3d.md:101](/scratch/35_geodispbench3d/docs/tools/iof3d.md:101) needs qualification once the public wheel intentionally ships it dormant.

- **LOW — `_sweep_cli.py` should preserve module/package data expectations.** Hydra’s `config_path="conf"` currently points relative to the module at [cli.py:76](/scratch/35_geodispbench3d/src/geodispbench3d_iof3d/cli.py:76). The same-directory move makes this likely safe, but it deserves a real installed-environment smoke test.

### Suggestions

- Catch only expected missing-private-dependency failures:

  ```python
  except ModuleNotFoundError as exc:
      if exc.name and exc.name.split(".", 1)[0] in {"iof3D", "pc2img"}:
          raise ImportError(_IOF3D_MISSING_HINT) from exc
      raise
  ```

  Let unrelated import failures propagate unchanged. Handle missing `pchandler` separately for `parse_iof3d_output`.

- Add a test proving `parse_iof3d_output` resolves while `iof3D` and `pc2img` are blocked and `pchandler` remains available.

- Isolate absence tests in subprocesses, or remove modules with `monkeypatch.delitem(sys.modules, name)` so pytest restores process state.

- Add a subprocess test for the actual launcher module, asserting exit code 1, actionable stderr, and absence of `Traceback`.

- Run one Phase 4 clean-environment checkpoint for `pip install '.[f2s3]'` and parser import. It can use a temporary venv created through the mandated Conda interpreter; it need not modify the dedicated development environment.

- Reword the absent-extra expectation as “pip does not install private iof3D dependencies and warns that the extra is unavailable,” unless an explicit failure shim is introduced.

- Update the public iof3D CLI documentation and stale test installation messages.

### Risk Assessment

**MEDIUM.** The architecture is appropriate and should make base-package import work, but broad exception translation could mask real defects, and the clean public F2S3 install remains unverified. Those issues should be corrected before execution or before declaring Phase 4 complete.

---

## Consensus Summary

A single independent reviewer (Codex) verified both plans against the live working
tree, citing concrete `file:line` evidence throughout. It confirmed the core
designs are sound — the licensing diagnosis (README is the sole contradictory
surface), the PEP 562 dormant-import mechanism, the `parse_iof3d_output`
not-gated reasoning, and the F2S3/pchandler dependency diagnosis all check out
against the actual code. The findings worth acting on before execution:

### Confirmed Strengths (source-verified)
- License state is exactly as the plan assumes: `pyproject.toml:10`,
  `CITATION.cff:10`, `LICENSE:1` already BSD-3-Clause; only `README.md:80`
  contradicts (04-01).
- `Private :: Do Not Upload` removal is precisely scoped at `pyproject.toml:21`;
  new classifiers complement the existing correct ones (04-01).
- Eager-import failure correctly traced: `__init__.py:20` →
  `adapter.py:19` / `factory.py:18`; `parse_iof3d_output` imports only
  pchandler at `output_parser.py:23` and is correctly left non-gated (04-02).
- `geodispbench3d_iof3d` correctly retained in the wheel via `pyproject.toml:69`.

### Highest-Priority Concerns
1. **(HIGH, 04-02) `__getattr__` over-broad `ImportError` catch.** Catching every
   `ImportError` mislabels unrelated defects (transitive bugs, a missing
   `pchandler`) as "iof3D not publicly available." Fix: catch `ModuleNotFoundError`
   and only translate when `exc.name` is in `{iof3D, pc2img}`; re-raise otherwise.
   This also matters for the pchandler-backed parser path.
2. **(HIGH, 04-02) PKG-02 left unproven in-phase.** Only a clean install proves
   `f2s3 = ["pchandler ~= 2.1"]` actually resolves on public metadata, and the CI
   f2s3 job is blocked behind the known-red lint gate (`ci.yml:47`/`:61`). The plan
   defers the runtime gate to Phase 5 (session decision 2) — Codex flags this leaves
   a phase success criterion unproven. Suggested: one throwaway-venv
   `pip install '.[f2s3]'` checkpoint built via the mandated Conda interpreter
   (without touching the dev env).
3. **(MEDIUM, 04-01) README stays internally contradictory.** The no-timeline note
   doesn't fix the combined `[iof3d,f2s3,dashboard]` command (`README.md:41`) or the
   "gated by `[iof3d]`" layout text (`README.md:66`) — the extra will no longer exist.
4. **(MEDIUM, 04-02) Simulated-absence tests mutate `sys.modules` without
   restoration**, risking contamination of later real-iof3D tests in the dev env.
   Use `monkeypatch.delitem` (auto-restored) or subprocess isolation.
5. **(MEDIUM, 04-02) "unknown extra errors" claim is inaccurate.** Pip typically
   *warns* that an extra is unavailable and continues; it is not a hard failure.
   Reword the acceptance criterion accordingly.

### Lower-Priority / Hygiene
- Stale install docs beyond the touched README note: `tests/conftest.py:7`,
  `tests/iof3d/conftest.py:7`, `docs/tools/iof3d.md:101` still reference the removed
  extra / claim the legacy CLI "still works." Fold in or track explicitly.
- URL test too permissive (assert the `github.com/gseg-ethz/geodispbench3d` host/path,
  not just non-empty HTTPS); CITATION.cff line-text assertion is brittle to YAML
  quoting/spacing.
- Add a positive test for the non-gated `parse_iof3d_output` mapping, and a
  subprocess-level launcher test (exit code 1, actionable stderr, no `Traceback`).

### Divergent Views
None — single reviewer.

### Overall Risk
04-01: **LOW–MEDIUM** (objectives met, but contradictory public install docs remain).
04-02: **MEDIUM** (sound architecture, but broad exception translation could mask
real defects and the clean public F2S3 install is unverified).
