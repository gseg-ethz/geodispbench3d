# iof3D

iof3D is the optical-flow-on-point-clouds pipeline this repo originated from.
The bench wiring lives in
[`src/geodispbench3d_iof3d/`](https://github.com/gseg-ethz/geodispbench3d/tree/main/src/geodispbench3d_iof3d/).

## Run the default suite

```bash
conda run -n iof3d_cosicorr3d-dev312 \
  geodispbench3d run benchmarks/suites/iof3d_mattertal.yaml
```

This runs a 10-trial sweep over the iof3D flow parameters declared in the
tool YAML, minimizing wallclock runtime. Outputs accumulate at
`outputs/iof3d_mattertal.parquet`.

## What the suite uses

| Component | File |
|---|---|
| Tool YAML  | [`src/geodispbench3d_iof3d/conf/tool/iof3d.yaml`](https://github.com/gseg-ethz/geodispbench3d/blob/main/src/geodispbench3d_iof3d/conf/tool/iof3d.yaml) |
| Dataset    | [`benchmarks/datasets/mattertal.yaml`](https://github.com/gseg-ethz/geodispbench3d/blob/main/benchmarks/datasets/mattertal.yaml) |
| Metrics    | [`benchmarks/metrics/pointing_error.yaml`](https://github.com/gseg-ethz/geodispbench3d/blob/main/benchmarks/metrics/pointing_error.yaml) |
| Suite      | [`benchmarks/suites/iof3d_mattertal.yaml`](https://github.com/gseg-ethz/geodispbench3d/blob/main/benchmarks/suites/iof3d_mattertal.yaml) |

## How iof3D plugs in

iof3D needs a fully-resolved `AppConfig` (parsed out of its own Hydra config
tree) before its pipeline can run. The tool YAML uses `kind: factory` to
delegate construction to
[`geodispbench3d_iof3d.factory.build_iof3d_adapter`](https://github.com/gseg-ethz/geodispbench3d/blob/main/src/geodispbench3d_iof3d/factory.py),
which:

1. Loads `iof3D/conf/app/base.yaml` (referenced via `pkg://iof3D.conf/...`).
2. Optionally merges an inline `overrides:` patch from the tool YAML.
3. Materializes an `AppConfig`.
4. Returns an `Iof3dCallableAdapter` configured for in-process trial
   execution (`in_process_safe = True`).

The factory pattern keeps all iof3D-specific logic inside
`geodispbench3d_iof3d`; the generic loader has zero iof3D imports.

## Output parsing

Each trial writes leaf-tile PLYs to
`<run_dir>/leaf_pointclouds/*.ply`. Each PLY carries scalar fields
`delta_x`, `delta_y`, `delta_z`, `magnitude` — i.e. the predicted 3D
displacement vector per reprojected source point.

The output parser
[`parse_iof3d_output`](https://github.com/gseg-ethz/geodispbench3d/blob/main/src/geodispbench3d_iof3d/output_parser.py)
loads all leaves with `pchandler.load_file`, merges them with
`PointCloudData.merge`, and at each GT point samples points within
`sample_radius_m` (default 15 m) using `SphereFilter`. The component-wise
median of the sampled `(delta_x, delta_y, delta_z)` becomes the predicted
vector for that GT label.

## Hyperparameter space

The tool YAML declares the same grammar previously used in
`iof3D_analysis/conf/hparam/ax.yaml`. Defaults sweep `flow.method`,
`flow.feature`, and FFT-local parameters; conditional parameters use
`activates_on:` so e.g. `flow.fft.step` is only active when
`flow.method ∈ {fft_local_v2}`.

To extend the search space, edit the `hyperparameters:` block of the
tool YAML. The grammar:

```yaml
- name: flow.<dotted.path>
  type: choice         # choice | range | fixed
  value_type: int      # str | int | float | bool
  values: [...]        # for choice / fixed
  lower: ...           # for range
  upper: ...
  log_scale: true      # for range
  step: ...
  activates_on:        # conditional activation
    flow.method: [fft_local_v2]
```

## Customizing the base AppConfig

To point iof3D at a different scan directory or override any field of
`AppConfig` without forking the whole base YAML, add `overrides:` to the
factory options:

```yaml
factory_options:
  base_app_config: pkg://iof3D.conf/app/base.yaml
  overrides:
    pcd_directory: /path/to/your/scans
    image:
      img_res: { width: 1200, height: 800 }
```

The override is `OmegaConf.merge`'d on top of the base before the AppConfig
is materialized.

## Legacy entry point

The previous `iof3d-ax` Hydra CLI still works **when iof3D is installed**, for
users not yet on the suite-driven workflow. It now delegates to
[`geodispbench3d_iof3d.cli`](https://github.com/gseg-ethz/geodispbench3d/blob/main/src/geodispbench3d_iof3d/cli.py), a thin
launcher that lazily imports the hydra-decorated implementation from
`_sweep_cli.py` and constructs the same adapter the suite path uses. Note the
public wheel ships the iof3D adapter **dormant**: the `[iof3d]` extra is
disabled until iof3D is publicly available, so on a public install `iof3d-ax`
exits with an actionable "iof3D not yet publicly available" message rather than
running.
