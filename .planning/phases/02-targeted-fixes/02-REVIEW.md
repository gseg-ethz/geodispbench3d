---
phase: 02-targeted-fixes
reviewed: 2026-06-27T00:00:00Z
depth: deep
files_reviewed: 23
files_reviewed_list:
  - src/geodispbench3d/diagnostics.py
  - src/geodispbench3d/sweep/runner.py
  - src/geodispbench3d/sweep/trial_record.py
  - src/geodispbench3d/sweep/evaluation.py
  - src/geodispbench3d/sweep/rescore.py
  - src/geodispbench3d/sweep/parameters.py
  - src/geodispbench3d/cli.py
  - src/geodispbench3d/analysis/runner.py
  - src/geodispbench3d/results/predictions_cache.py
  - src/geodispbench3d/suite/loader.py
  - src/geodispbench3d/dataset/schema.py
  - src/geodispbench3d/tool/loader.py
  - src/geodispbench3d/conf/schema/dataset.schema.json
  - src/geodispbench3d_iof3d/factory.py
  - benchmarks/datasets/mattertal.yaml
  - benchmarks/datasets/mattertal_f2s3.yaml
  - tests/core/test_runner.py
  - tests/core/test_store.py
  - tests/core/test_evaluation.py
  - tests/core/test_parameters.py
  - tests/core/test_rescore.py
  - tests/core/test_analyze.py
  - tests/core/test_predictions_cache.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: resolved
resolved: 2026-06-27T00:00:00Z
resolution: All 5 findings fixed before phase verification (commits 06d95c7 CR-01, ec7cbeb WR-01, 4eb1754 WR-02, 9a7f0fe IN-01/IN-02). Full suite 83 passed; ruff/format/pyright-gate green.
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-27T00:00:00Z
**Depth:** deep
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the Phase-2 targeted-fixes changeset (F-08 typed `PassDiagnostics`,
F-01/F-13 typing, F-05 trial-summary artifact, F-02/F-03 dedup, F-09 tz-aware
datetime, F-30 dead-field removal + `ExecutionConfig.ensure_supported()`),
tracing the diagnostics counter and the narrowed exception sets across the
sweep / rescore / analyze call chains.

Most of the changeset holds up under adversarial tracing: the diagnostics
counter threading is free of double-counts (mutually-exclusive
success/except paths in each pass; `add()` is a no-op on `n<=0`); the F-09
change is serialization-only with no naive/aware comparison anywhere in `src`;
the F-30 dead-field removal is clean (`scan_by_epoch` / `gt_kinds_supported` /
`yaml_hash` have zero remaining references, the JSON schema has no
`additionalProperties: false`, and legacy `yaml_hash`-bearing records still
deserialize via `.get()`-based extraction); and the `from_mapping` /
`parser_fn_repr` single-sourcing is genuinely de-duplicated.

**However, one narrowing is over-tight and breaks fail-soft.** Both JSON
read paths (`load_trial_record`, `read_prediction`) were narrowed from
`except Exception` to `except (OSError, json.JSONDecodeError)`, which drops
coverage of `UnicodeDecodeError` — the exception raised when a *present*
summary/cache file contains non-UTF-8 bytes (a routine corruption mode:
truncated/binary garbage, disk faults). This is exactly the failure class the
`on_non_fatal` hooks were added to count fail-soft, and it now crashes the
whole rescore/analyze pass instead. This is the headline BLOCKER.

Two WARNINGs (a genuinely-uncounted fail-soft site at the F-05 trial-summary
write, contradicting the F-08 "every fail-soft site records into it" contract;
and an incomplete path-segment sanitizer) and two dead-code INFOs round out the
review.

## Critical Issues

### CR-01: Narrowed JSON-read except sets drop `UnicodeDecodeError`, crashing rescore/analyze on a non-UTF-8 file (breaks fail-soft)

**File:** `src/geodispbench3d/sweep/trial_record.py:121` and `src/geodispbench3d/results/predictions_cache.py:132`

**Issue:**
Both readers were narrowed this phase:

```python
# trial_record.load_trial_record  (was: except Exception)
except (OSError, json.JSONDecodeError) as exc:
    if on_non_fatal is not None:
        on_non_fatal(exc)
    return {}
```
```python
# predictions_cache.read_prediction  (was: except Exception)
except (OSError, json.JSONDecodeError) as exc:
    if on_non_fatal is not None:
        on_non_fatal(exc)
    return None
```

The files are opened in text mode (`open("r", encoding="utf-8")`), so
`json.load(fh)` calls `fh.read()`, which **decodes** before any JSON parsing.
A present file containing invalid UTF-8 bytes raises `UnicodeDecodeError`
*during the read*. `UnicodeDecodeError` subclasses `ValueError`, and so does
`json.JSONDecodeError` — but they are **siblings**: `UnicodeDecodeError` is
NOT a `json.JSONDecodeError` and NOT an `OSError`. The narrowed tuple therefore
does not catch it. (`grep -rn UnicodeDecodeError src` → no handling anywhere.)
The chosen set covers the docstring's "bad permissions, malformed JSON" but
misses "malformed *bytes*", which is the more common on-disk corruption mode.

Because these reads sit **outside** the only broad `except` in each pass
(those wrap `evaluate_trial`, not the file read), the exception propagates and
aborts the entire pass — defeating the F-08 guarantee that a single corrupt
artifact degrades fail-soft and is merely counted:

- `rescore_suite` loop top — `load_trial_record(trial_record_path(run_dir),
  on_non_fatal=lambda _exc: diag.add("trial_record_read"))`
  (`rescore.py:122-125`): the `on_non_fatal` hook exists *specifically* to
  count corrupt summaries, but a non-UTF-8 `summary.json` skips it and crashes
  `rescore_suite` outright. The whole rescore pass dies on one bad file.
- `analyze` loop — `read_prediction(path, on_non_fatal=lambda _exc:
  diag.add("prediction_read"))` (`analysis/runner.py:76`): a non-UTF-8 cache
  file crashes the whole analyze pass.
- `rescore._try_cache_lookup` → `read_prediction` (`rescore.py:414`, reached
  with `--use-prediction-cache`): propagates out of `_rescore_one` (the cache
  lookup precedes the `evaluate_trial` try) and aborts the pass.

The existing tests only exercise the `json.JSONDecodeError` path
(`{ this is not valid json`, `{ "rescore_log": <dict> }`), so this gap is
untested — a "tests pass" signal does not cover it.

**Fix:** widen the read except to also cover the decode failure. Since both
`json.JSONDecodeError` and `UnicodeDecodeError` derive from `ValueError`,
`(OSError, ValueError)` is the minimal closed set that restores fail-soft,
or list it explicitly:

```python
except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
    if on_non_fatal is not None:
        on_non_fatal(exc)
    return {}   # / return None in read_prediction
```

Apply to both `load_trial_record` and `read_prediction`. Add a regression test
that writes non-UTF-8 bytes (e.g. `path.write_bytes(b"\xff\xfe\x00bad")`) and
asserts the pass completes with the failure counted, not raised.

## Warnings

### WR-01: F-05 trial-summary write failure is swallowed but never counted — a fail-soft site missing from the diagnostics counter

**File:** `src/geodispbench3d/sweep/runner.py:481-486`

**Issue:**
`_surface_finite_case_signal` writes the F-05 trial-level artifact under a
broad fail-soft guard:

```python
except Exception:  # pragma: no cover - never fail a trial on summary write
    self._logger.warning("Unable to write trial-level summary for trial %s", ...)
```

This site neither receives the pass-wide `PassDiagnostics` (the method has no
`diagnostics` parameter) nor calls `diag.add(...)`, so a real fail-soft failure
here (the `write_trial_summary` mkdir/open/replace can raise `OSError`) is
swallowed **and invisible**. That contradicts two stated contracts:
- `diagnostics.py:7-9` module docstring: "every fail-soft site records into it";
- this method's own docstring (`runner.py:446-447`): "The artifact write is
  fail-soft ... (02-05 adds the non-fatal counter to this site)."

The counter parenthetical was never implemented. `SweepRunSummary`'s
enumeration of counted kinds (`runner.py:64-67`) also omits this site, so the
sweep can under-report its non-fatal-failure total whenever the
`trial_summaries/` write fails (e.g. read-only results root) while every other
side-effect on that trial succeeds.

**Fix:** thread the existing `pass_diag` into `_surface_finite_case_signal`
(add a `diagnostics: PassDiagnostics` param, pass `diag` from
`_evaluate_across_cases`) and record in the except:

```python
except Exception:
    self._logger.warning("Unable to write trial-level summary for trial %s", ...)
    diagnostics.add("trial_summary")
```

Then add `"trial_summary"` to the `SweepRunSummary` docstring's counted-kinds
list and update the method docstring to state the counter is wired (not "adds").

### WR-02: `_safe_segment` does not neutralize a whole-segment `..`/`.`, leaving a path-climb hole the docstring claims to close

**File:** `src/geodispbench3d/results/predictions_cache.py:169-177`

**Issue:**
`_safe_segment` preserves `.` and `-` and `_`, replacing only other
non-alphanumerics. Embedded separators in `"../../etc"` are neutralized
(`/` → `_`, giving `.._.._etc`), but a segment whose *entire* value is `".."`
(or `"."`) is returned verbatim:

```python
return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in str(value))
```

So `cache_path(root, tool_id="..", dataset_id="x", case="y", run_hash="z")`
yields `root/../x/y/z.json`, climbing out of `predictions_root`. The function
docstring asserts it stops `"../../etc"` breakouts, and the only test
(`test_unsafe_segments_are_sanitised`) covers `"../escape"` but never the
bare `".."` case, so the hole is both undocumented-as-a-gap and untested.
These segments derive from tool/dataset/case/run_hash, which in the analyze
and rescore flows are read from a run dir's / cache file's recorded
provenance — i.e. potentially from a shared or copied artifact, not only from
the operator's own suite YAML. Severity is bounded (local, config/provenance
sourced, not a network surface) but it is a real sanitizer gap in a function
whose whole job is containment. (Pre-existing; the file is in scope and only
its datetime/`on_non_fatal` lines changed this phase.)

**Fix:** reject or rewrite path-special segments explicitly, e.g. after the
char filter map `{"", ".", ".."}` to a safe placeholder:

```python
cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in str(value))
if cleaned in {"", ".", ".."}:
    return "_" + cleaned  # ".." -> "_.." ; "." -> "_." ; "" -> "_"
return cleaned
```

and extend the test to assert `cache_path(..., tool_id="..")` stays under root.

## Info

### IN-01: `PassDiagnostics.merge` and `merge_kind_counts` are dead code

**File:** `src/geodispbench3d/diagnostics.py:42-54`

**Issue:** Both the `merge` method and the module-level `merge_kind_counts`
helper (the latter exported in `__all__`) have zero call sites across `src`
and `tests` (`grep` for `merge_kind_counts` / `.merge(` finds only unrelated
`PointCloudData.merge` / `OmegaConf.merge`). The diagnostics threading in this
phase uses one `PassDiagnostics` per pass with direct `add(...)` calls and
never folds two instances together. Speculative API added without a consumer
widens the public surface for a publication-readiness milestone.

**Fix:** drop `merge` / `merge_kind_counts` (and the `Mapping` import they
need) until a multi-instance fold is actually required, or add a consumer.
If retained deliberately as a seam, note it as such in the module docstring.

### IN-02: `hash_file` is now unused after `yaml_hash` removal

**File:** `src/geodispbench3d/sweep/trial_record.py:338-350`

**Issue:** F-30 removed `ToolProvenance.yaml_hash` and its
`hash_file(yaml_path)` call in `from_yaml_path`. `hash_file` now has no caller
in `src`/`tests`; it survives only in its own definition and `__all__`.

**Fix:** remove `hash_file` (and its `import hashlib`) if no longer part of the
intended public API, or document why it is retained as an exported helper.
Low priority — it is exported, so removal is an API decision rather than a pure
cleanup.

---

_Reviewed: 2026-06-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
