# Metrics

A **metrics** file lists the metric callables a sweep can use, split into
two roles:

- **`objective_metrics:`** — scalars per trial. Eligible to be the Ax
  objective (the suite YAML picks one).
- **`record_metrics:`** — structured rows persisted to parquet for the
  dashboard. Returned as a sequence of dicts.

Both kinds dispatch the same way — by importlib resolving a
`package.module:function` reference and calling it with whichever inputs
the metric declares it `needs:`.

Metrics YAMLs live in [`benchmarks/metrics/`](../../benchmarks/metrics/).

## Anatomy

```yaml
objective_metrics:
  - id: median_displacement_error
    fn: geodispbench3d.metrics.builtins:median_displacement_error
    needs: [prediction, ground_truth]
    gt_kinds: [point_displacements]

  - id: runtime_seconds
    fn: geodispbench3d.metrics.builtins:wallclock_runtime
    needs: [trial_meta]

record_metrics:
  - id: per_point_displacement
    fn: geodispbench3d.metrics.builtins:per_point_displacement_record
    needs: [prediction, ground_truth, case_meta, trial_meta]
    gt_kinds: [point_displacements]
```

## What metric callables receive

Each entry's `needs:` list determines which inputs the runner injects:

- **`prediction`** — the `{per_point: [...]}` mapping returned by the
  tool's output parser (or whatever your custom adapter / parser produces).
- **`ground_truth`** — the loaded GT object for the case. For
  `point_displacements`, this is iterable over
  `geodispbench3d.dataset.ground_truth.PointDisplacement`.
- **`trial_meta`** — `{trial_index, duration_seconds, success, run_dir}`.
- **`case_meta`** — `{name, ...case.metadata...}`.

A metric that only needs `prediction` and `ground_truth` is the most
common shape. `wallclock_runtime` is the example of a `trial_meta`-only
metric (it doesn't care about predictions or GT).

## Built-in metrics

Defined in
[`geodispbench3d/metrics/builtins.py`](../../src/geodispbench3d/metrics/builtins.py):

| Metric | Returns | Notes |
|---|---|---|
| `wallclock_runtime` | trial duration in seconds | Reports what the adapter measured |
| `median_displacement_error` | median 3D Euclidean error (m) | Primary objective candidate |
| `mean_relative_magnitude_error` | mean of \|1 - \|pred\|/\|gt\|\| | Scale-invariant magnitude error |
| `median_angle_error_deg` | median angle (deg) between pred and gt vectors | Direction-only |
| `median_relative_vector_error` | median of \|\|gt - pred\|\| / \|\|gt\|\| | Combined magnitude+direction, scale-invariant |
| `gt_coverage` | fraction of GT labels with a non-NaN prediction | Surfaces missing-prediction failure modes |
| `per_point_displacement_record` | list of dicts (one per GT point) | Record metric — feeds the parquet store |

## Writing a custom metric

A metric is just a function. Put it in your peer package or in a separate
helper module, and reference it from your metrics YAML.

```python
# my_package/metrics.py
import numpy as np

def max_per_point_error(*, prediction, ground_truth, **_):
    gt_by_label = {p.label: p.movement_vector for p in ground_truth}
    errs = []
    for entry in prediction.get("per_point", []):
        gt_vec = gt_by_label.get(entry["label"])
        if gt_vec is None:
            continue
        pred = np.asarray(entry["vector"], dtype=float)
        errs.append(float(np.linalg.norm(pred - gt_vec)))
    return float(np.nanmax(errs)) if errs else float("nan")
```

```yaml
# benchmarks/metrics/strict.yaml
objective_metrics:
  - id: max_per_point_error
    fn: my_package.metrics:max_per_point_error
    needs: [prediction, ground_truth]
    gt_kinds: [point_displacements]
```

Always accept `**_` (or explicitly accept all four `needs` kinds) so
forward-compatibility additions don't break your function. Ignore inputs
you don't use.

## Record metrics: shape

Record metrics return either a single dict or a sequence of dicts. Each
dict becomes a row in the results parquet, with the metric's `id` added
under a `metric:` column so you can filter rows by which metric produced
them.

The built-in `per_point_displacement_record` emits one row per GT label
with diagnostic columns (`gt_label`, `gt_magnitude_m`, `pred_magnitude_m`,
`magnitude_diff_mm`, `angle_deg`, `rme`, `rve`, `cosine_similarity`).
Custom record metrics can emit whatever columns are useful for your
analysis.

## Reusing metrics across tools

The whole point of metrics being a separate file is that you wire iof3D
and F2S3 (and your tool) to the **same** metrics YAML. Both pre-built
suites point at
[`benchmarks/metrics/pointing_error.yaml`](../../benchmarks/metrics/pointing_error.yaml),
so cross-tool comparisons read identically aggregated rows from the
parquet.

If your tool reports tool-specific scalars that shouldn't appear in
cross-tool comparisons (e.g. `f2s3_n_supervoxels`), don't add them to a
shared metrics file — make a tool-specific metrics YAML for that tool's
suite.

## Validation at suite-load

The suite loader checks that the suite's `search.objective:` matches an
`id:` in `objective_metrics:`. The runner additionally checks
`gt_kinds:` against the dataset's GT kind at trial dispatch — metrics
whose kinds don't match are silently skipped, so you can build a
"superset" metrics YAML that targets multiple GT kinds and only the
applicable subset will fire on a given dataset.

## Listing available metrics

```bash
geodispbench3d list-metrics benchmarks/metrics/pointing_error.yaml
```

Prints the `id`s and `fn`s declared in each section.
