# Output parsers

An **output parser** turns the tool's raw outputs into the
`{per_point: [...]}` shape that built-in pointing-error metrics consume.
You need one whenever your tool produces a dense displacement field rather
than already-sampled-at-GT predictions.

The two pre-built tools both use parsers. Their structure is essentially
the same — only the file format and field names differ — so they make good
templates.

## The contract

```python
def parse_my_outputs(
    *,
    outputs: TrialOutputs,                  # what the adapter reported
    ground_truth: PointDisplacements,       # GT for the case (or None)
    options: Mapping[str, Any] | None = None,  # from tool.yaml's parser.options
    logger: logging.Logger | None = None,
    **_: Any,                               # forward-compatibility
) -> Mapping[str, Any]:
    return {
        "per_point": [
            {"label": gt.label, "vector": [dx, dy, dz], "source_count": N},
            # one entry per GT label
        ],
        "source": {                          # diagnostics, optional
            "n_points_total": ...,
            "sample_radius_m": ...,
        },
    }
```

The shape of `per_point` is what every pointing-error metric expects:

- `label: str` — must match a GT label exactly.
- `vector: [float, float, float]` — predicted displacement (`x2 - x1, y2 - y1, z2 - z1`).
- `source_count: int` — how many points your tool produced inside the GT
  search radius. Used by `gt_coverage` to identify failed predictions.

For GT labels where your tool produced nothing, emit `vector: [NaN, NaN, NaN]`
and `source_count: 0`. Don't omit them.

## The standard recipe

For tools that output a dense set of points with displacement vectors as
scalar fields (or a tile of them), the recipe is:

1. Glob the per-tile output files in the trial's run directory.
2. Load each via [`pchandler.load_file`](https://github.com/gseg-ethz/PCHandler)
   (or `Csv.load` for ASCII formats).
3. Merge with `PointCloudData.merge`.
4. For each GT point, sample with `SphereFilter(center=gt.xyz_epoch1, radius=R)`.
5. Take the component-wise median (or mean) of the sampled displacement
   vectors. Emit one entry per label.

Both the iof3D and F2S3 parsers follow this recipe verbatim — only the
loading step differs.

## Working examples

### F2S3 — ASCII tiles

```python
# geodispbench3d_f2s3/output_parser.py
from pchandler.data_io import Csv
from pchandler import PointCloudData
from pchandler.filters import SphereFilter

F2S3_COLUMNS = ["x", "y", "z", "x2", "y2", "z2", "magnitude"]

def parse_f2s3_output(*, outputs, ground_truth, options=None, **_):
    options = options or {}
    radius = options.get("sample_radius_m", 15.0)
    tile_dir = outputs.run_dir / "output" / "refined_results"
    if not tile_dir.is_dir():
        tile_dir = outputs.run_dir / "output"

    pcds = []
    for tile in sorted(tile_dir.glob("*.txt")):
        pcds.append(Csv.load(tile, scalar_fields=F2S3_COLUMNS, column_names_row=-1))
    merged = PointCloudData.merge(*pcds)

    per_point = []
    for gt in ground_truth:
        sampled = SphereFilter(sphere_center=gt.xyz_epoch1, radius=radius).sample(merged)
        if sampled.nbPoints == 0:
            per_point.append({"label": gt.label, "vector": [float("nan")] * 3, "source_count": 0})
            continue
        sf = sampled.scalar_fields
        src = sampled.xyz
        tgt = np.column_stack([sf["x2"], sf["y2"], sf["z2"]])
        vec = np.nanmedian(tgt - src, axis=0)
        per_point.append({
            "label": gt.label,
            "vector": [float(v) for v in vec],
            "source_count": int(sampled.nbPoints),
        })

    return {"per_point": per_point}
```

### iof3D — PLY leaves with displacement scalar fields

```python
# geodispbench3d_iof3d/output_parser.py
from pchandler import PointCloudData, load_file
from pchandler.filters import SphereFilter

def parse_iof3d_output(*, outputs, ground_truth, options=None, **_):
    options = options or {}
    radius = options.get("sample_radius_m", 15.0)
    leaf_dir = outputs.run_dir / "leaf_pointclouds"

    pcds = [load_file(p) for p in sorted(leaf_dir.glob("*.ply"))]
    merged = PointCloudData.merge(*pcds)

    per_point = []
    for gt in ground_truth:
        sampled = SphereFilter(sphere_center=gt.xyz_epoch1, radius=radius).sample(merged)
        if sampled.nbPoints == 0:
            per_point.append({"label": gt.label, "vector": [float("nan")] * 3, "source_count": 0})
            continue
        sf = sampled.scalar_fields
        vec = np.column_stack([sf["delta_x"], sf["delta_y"], sf["delta_z"]])
        agg = np.nanmedian(vec, axis=0)
        per_point.append({
            "label": gt.label,
            "vector": [float(v) for v in agg],
            "source_count": int(sampled.nbPoints),
        })

    return {"per_point": per_point}
```

## Wiring the parser into a tool YAML

```yaml
output_parser:
  fn: my_package.module:parse_my_outputs
  options:
    sample_radius_m: 12.0
    aggregation: median
```

The framework resolves `fn:` via importlib (same `package.module:function`
convention used elsewhere). `options:` is passed as the `options=` kwarg
to your function — define whatever knobs your parser needs.

## Common pitfalls

- **Forgetting NaN entries for missing labels.** Every GT label needs a
  `per_point` entry, even when your tool produced nothing nearby. Otherwise
  `gt_coverage` and the per-point record metrics see fewer rows than the GT
  defines, which silently skews aggregates.
- **Sampling at the wrong epoch.** GT carries both `xyz_epoch1` and
  `xyz_epoch2`. The convention is to sample the source cloud at
  `xyz_epoch1` (the position before displacement). Sampling at epoch 2
  will miss the points the tool actually predicts displacement for.
- **Coordinate-frame mismatch.** Make sure GT and tool output are in the
  same frame. The Mattertal CSV is in canonical (post-rotation) PRCS; the
  legacy in-code GT had to apply a `(-x, -y, z)` rotation for the first 6
  entries — that has been baked into the CSV, so don't re-apply it in your
  parser.
- **Heavy parsers.** Loading and merging tens of GB of PLY per trial is
  expensive. If trials produce a lot of dense data, consider a streaming
  per-GT-radius read — `pchandler.filters.SphereFilter` is fast enough that
  you usually don't need to.
