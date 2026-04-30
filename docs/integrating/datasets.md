# Datasets and ground truth

A **dataset** is a list of evaluable cases. Each case has zero or more
**scans** (typically two epochs) and an optional **ground truth** record.
Datasets are tool-agnostic: the same dataset YAML serves any tool that
operates on the same scans against the same GT.

Dataset YAMLs live in [`benchmarks/datasets/`](../../benchmarks/datasets/).

## Anatomy

```yaml
id: my-site                        # unique identifier
root: ../data                      # relative paths in cases[] resolve against this
metadata:
  description: |
    Free-form description of where the data came from.
gt_kinds_supported:
  - point_displacements

cases:
  - name: my-case-2024-2025
    scans:
      - epoch: e1
        path: 2024_e1.ply
        metadata: { sensor: VZ-2000 }
      - epoch: e2
        path: 2025_e2.ply
    ground_truth:
      kind: point_displacements
      path: gt/my-case.csv
    metadata:
      site: my-site
      epochs: ["2024-08-01", "2025-08-12"]
```

The `root:` field resolves relative to the dataset YAML's location, and
all `scans[].path` and `ground_truth.path` are then resolved relative to
`root`. Paths in the YAML may also be absolute — useful when scans live
in a stable shared filesystem location and the dataset YAML is checked
into git.

## Scans

`scans:` is a list of `{epoch, path, metadata}` entries. The framework
itself doesn't read scan files — that's the tool's job. The list exists
so the adapter can find the files (e.g. F2S3's tool YAML reads them via
`static_params:`).

`scans:` may be **empty**. iof3D's dataset YAML uses `scans: []` because
iof3D resolves PCDs from its own `AppConfig.pcd_directory`. The dataset
entry is then GT-only.

## Ground-truth kinds

The framework dispatches GT loading on `kind:`. Built-in kinds:

- **`point_displacements`** — labeled 3D displacements. Loader expects a
  CSV with columns `label, x1, y1, z1, x2, y2, z2`. Returns a
  `PointDisplacements` (a sequence of `PointDisplacement` records, each
  with `label`, `xyz_epoch1`, `xyz_epoch2`, `movement_vector`,
  `movement_magnitude`).

To register a new kind, call
`geodispbench3d.dataset.ground_truth.register_gt_loader`:

```python
from geodispbench3d.dataset.ground_truth import register_gt_loader

def _load_dense_flow(spec):
    # spec.path or spec.inline → return whatever your kind needs
    ...

register_gt_loader("dense_flow", _load_dense_flow)
```

Then dataset YAMLs can reference `kind: dense_flow`. Metric callables
declare which kinds they support via `gt_kinds:` in metrics.yaml; the
runner skips metrics whose kinds don't match.

## Inline GT

Small GT can be inlined instead of pointing at a file:

```yaml
ground_truth:
  kind: point_displacements
  inline:
    points:
      - label: A
        xyz_epoch1: [0.0, 0.0, 0.0]
        xyz_epoch2: [0.1, 0.0, 0.0]
      - label: B
        xyz_epoch1: [10.0, 0.0, 0.0]
        xyz_epoch2: [10.05, 0.0, 0.0]
```

The built-in `point_displacements` loader checks `inline.points` before
falling back to `path:`. Custom loaders can do whatever fits their kind.

## Multi-case datasets

A dataset may contain multiple cases. The runner iterates over all of
them per trial and aggregates scalar metrics across cases by mean
(NaN-skipping). This is useful when you want a single sweep to optimize
performance averaged over a benchmark of several scenes.

```yaml
cases:
  - name: scene-1
    scans: [ ... ]
    ground_truth: { ... }
  - name: scene-2
    scans: [ ... ]
    ground_truth: { ... }
```

Each case can have its own GT file; the loader resolves them
independently.

## Metadata passthrough

Anything under `cases[].metadata:` flows untouched into the
`case_meta` argument that metric callables receive. Use it to record
per-case tags (rock type, sensor, weather conditions) that you want to
filter on in the dashboard.

## Where dataset YAMLs live

Put your dataset YAML in [`benchmarks/datasets/`](../../benchmarks/datasets/)
unless it's specific to one tool. Tool-specific dataset YAMLs (e.g.
F2S3's, which embeds the PRCS PLY paths in its `scans:` list because the
F2S3 CLI takes them as args) live in the same directory but with a
suffixed name, e.g. `mattertal_f2s3.yaml`.
