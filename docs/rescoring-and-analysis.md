# Rescoring and analysis

Once a sweep has run, it's almost always cheaper to evaluate cached
outputs than to re-run the tool. geodispbench3d offers two distinct
verbs for this:

| Need | Use |
|---|---|
| You changed a metric (or the sampling radius) and want to update the parquet without re-running the tool. | `geodispbench3d rescore <suite.yaml>` |
| You have cached predictions from many tools and want to compare them against the same metrics on the same GT. | `geodispbench3d analyze <analysis.yaml>` |

Both share the underlying machinery, and both write to the same parquet
schema (with a `mode:` column to discriminate `sweep` / `rescore` /
`analyze` rows), so the dashboard works for everything.

> **Migration note (pre-public CLI break).** Rescore used to be a `--rescore`
> flag on the `run` subcommand. It is now its own first-class `rescore`
> subcommand. The old `--rescore` flag is gone, and the rescore-only flags
> (`--reuse-parser-options`, `--use-prediction-cache`, `--pass-id`) are rejected
> on `run` — pass them to `rescore` instead. Update any scripts that drove
> rescoring through `run` to call `geodispbench3d rescore <suite.yaml>`.

## The three phases of a trial

```
[1] tool runs   → tool-specific outputs in a run dir
[2] parse+sample → tool-specific parser turns those into predictions in
                   the common shape {per_point: [{label, vector,
                   source_count}, ...]}
[3] score      → metrics consume per_point + GT, emit scalars + records
```

A normal `geodispbench3d run` does all three. After step 1 every trial's
run directory carries provenance in `<run_dir>/ax_trial/summary.json`
(tool, dataset case, parser configuration), and after step 2 the
prediction is cached at
`<predictions_root>/<tool_id>/<dataset_id>/<case>/<run_hash>.json`.
The two new verbs reuse those artifacts.

## `rescore`: skip phase 1, optionally skip phase 2

```bash
geodispbench3d rescore benchmarks/suites/iof3d_mattertal.yaml
```

Walks every run directory under the suite's `results.run_dir_root`
that carries a `summary.json`, runs phase 2 + phase 3 against the
existing outputs, and appends parquet rows tagged `mode: "rescore"`.
The tool is never invoked.

### Flags

`rescore` with no extra flags uses the suite's **current** parser options, so a
freshly-edited `sample_radius_m` takes effect immediately. Pair with:

`--reuse-parser-options`
: Re-run phase 2 with the parser configuration recorded in the run's
  `summary.json` instead of the suite's current options. Useful when
  the suite YAML has drifted away from what produced the run, and you
  only want to add a metric without reproducing the original
  predictions exactly.

`--use-prediction-cache`
: Look up the prediction in the predictions cache by run hash. On
  cache hit, skip phase 2 entirely. On cache miss, run the parser per
  the configured options and write the result to the cache.

`--pass-id <id>`
: Tag this rescore pass in the parquet rows so multiple re-scoring
  rounds against the same suite stay distinguishable. Auto-generated
  when omitted.

### Audit trail

Every rescore pass appends an entry to the run's
`ax_trial/summary.json` under a `rescore_log:` array (pass_id,
rescored_at timestamp, parser_source, parser_options, scalar metrics).
You can read these later to see how a run's metrics evolved.

### Example: change the sampling radius and re-score

```bash
# 1. Edit the suite YAML's output_parser.options.sample_radius_m,
#    or the parser options in the tool YAML, then:
geodispbench3d rescore benchmarks/suites/iof3d_mattertal.yaml \
    --pass-id radius-25
```

The parquet now contains `mode=sweep` rows (original) plus
`mode=rescore, pass_id=radius-25` rows (new radius). Filter by
`pass_id` in the dashboard to compare.

### Example: add a metric without re-parsing

```bash
# 1. Edit metrics.yaml to add the new metric.
# 2. Re-score using cached predictions, no parser invocation:
geodispbench3d rescore benchmarks/suites/iof3d_mattertal.yaml \
    --reuse-parser-options --use-prediction-cache --pass-id new-metric
```

Cache hits in the log let you confirm the parser never ran.

## `analyze`: skip phase 1 and phase 2 entirely

```bash
geodispbench3d analyze benchmarks/analyses/<analysis.yaml>
```

Walks the cached predictions referenced by the analysis YAML, runs
phase 3 only, and appends parquet rows tagged `mode: "analyze"`. No
tool reference; the predictions are already in the common per-point
shape, so a single analysis can mix iof3D, F2S3, and any other
tool's runs.

### `analysis.yaml` schema

```yaml
id: postanalysis-iof3d-vs-f2s3
dataset: ../datasets/mattertal.yaml
metrics: ../metrics/pointing_error.yaml

predictions:
  # Three ways to declare prediction sources, mix-and-match in any order.
  # Each entry resolves to a list of cached prediction JSON files.
  - path: outputs/predictions/iof3d-v2/mattertal/mattertal-all/abc1.json
  - glob: outputs/predictions/f2s3/**/*.json
  - root: outputs/predictions
    filter:
      tool_id: iof3d-v2
      dataset_id: mattertal
      case: mattertal-all

results:
  parquet_path: outputs/postanalysis.parquet

pass_id: iof3d-vs-f2s3-2026-05  # optional; auto-generated otherwise
```

`path` / `glob` / `root` are mutually exclusive within one entry.
`root` walks the cache layout `<root>/<tool_id>/<dataset_id>/<case>/
<run_hash>.json`; each segment of `filter:` is optional, with `None`
matching anything.

### When to use `analyze` vs `rescore`

- **`rescore`** when the tool's outputs still exist and you want to
  re-run the parser (e.g. with a larger sampling radius). The parser
  is tool-specific.
- **`analyze`** when the predictions are all you have, or when you
  want to compare predictions from different tools without re-running
  any of them. Doesn't touch the parser.

## The parquet schema

Every record row carries:

| column | meaning |
|---|---|
| `mode` | `sweep` / `rescore` / `analyze` |
| `pass_id` | Discriminator for multiple passes against the same parquet. Sweep rows get the trial index; rescore/analyze rows get the user-supplied or auto-generated pass id. |
| `tool_id` | Which tool produced the run (from provenance). |
| `dataset_id` | Which dataset the case belongs to. |
| `case` | Dataset case name. |
| `trial_index` | The Ax trial index for sweep rows; the run hash / file stem for rescore / analyze rows. |
| `metric` | Which `record_metric` produced the row. |
| (metric-specific columns) | e.g. `gt_label`, `gt_magnitude_m`, `magnitude_diff_mm`, `angle_deg`, ... |

Filter on `mode` and `pass_id` in the dashboard to slice between the
original sweep and any number of subsequent rescoring or analysis
passes.

## Predictions cache layout

```
<predictions_root>/
    <tool_id>/<dataset_id>/<case>/<run_hash>.json
```

Each file:

```json
{
  "schema_version": 1,
  "prediction": { "per_point": [...], "source": {...} },
  "provenance": {
    "tool":    {"id": "...", "yaml_path": "...", "yaml_hash": "sha256:..."},
    "dataset": {"id": "...", "case": "..."},
    "parser":  {"fn": "package.module:fn", "options": {...}},
    "run_dir": "...",
    "cached_at": "..."
  }
}
```

The cache is populated automatically by every `run` and updated by
the `rescore` pass (when phase 2 runs). The default location is
`<suite-dir>/outputs/predictions/`; override with
`results.predictions_root:` in the suite YAML if you want it elsewhere
(for example, on slower-but-larger storage so cleaning up run dirs is
safe).
