# Quickstart

Run a benchmark sweep against one of the pre-built tools.

## Prerequisites

- The `iof3d_cosicorr3d-dev312` conda env (or a wheel install with the right
  extras) — see [`AGENTS.md`](https://github.com/gseg-ethz/geodispbench3d/blob/main/AGENTS.md). All Python invocations below go
  through `conda run -n iof3d_cosicorr3d-dev312`.
- For F2S3: a working `f2s3` binary in the `f2s3-dev312` env.

## 1. Pick a suite

Suites live in [`benchmarks/suites/`](https://github.com/gseg-ethz/geodispbench3d/tree/main/benchmarks/suites/):

- `iof3d_mattertal.yaml` — iof3D on the Mattertal GT, optimizing runtime.
- `f2s3_voxel_refine.yaml` — F2S3 voxel-grid + refine sweep on Mattertal,
  optimizing median 3D displacement error.

## 2. Run it

```bash
conda run -n iof3d_cosicorr3d-dev312 \
  geodispbench3d run benchmarks/suites/f2s3_voxel_refine.yaml
```

The CLI:

1. Loads tool, dataset, metrics, and search settings from the suite.
2. Constructs the Ax experiment with the tool's parameter space.
3. For each trial, invokes the tool, parses outputs, computes metrics,
   and reports the objective back to Ax.
4. Appends record rows to the parquet path declared in the suite's
   `results.parquet_path:` (if set).

## 3. Inspect results

```bash
conda run -n iof3d_cosicorr3d-dev312 \
  geodispbench3d dashboard --parquet outputs/f2s3_voxel_refine.parquet
```

The dashboard is a Streamlit app for filtering and plotting metric columns
across trials.

To list the metrics declared in a metrics file:

```bash
conda run -n iof3d_cosicorr3d-dev312 \
  geodispbench3d list-metrics benchmarks/metrics/pointing_error.yaml
```

## Common overrides

```bash
# Cap trial count without editing the suite
geodispbench3d run <suite> --max-trials 4

# Verbose logging
geodispbench3d run <suite> --log-level DEBUG
```

## Next steps

- Read [Concepts](concepts.md) for the full picture of how the four YAML
  files compose.
- See [iof3D](tools/iof3d.md) or [F2S3](tools/f2s3.md) for tool-specific
  details (parameter space, output layout, sampling defaults).
- See [Integrating your own tool](integrating/index.md) when you want to
  benchmark something else.
