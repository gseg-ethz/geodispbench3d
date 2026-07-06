# geodispbench3d

A benchmark framework for 3D displacement / optical-flow tools, with
Bayesian hyperparameter sweeps via [Ax](https://ax.dev) and pluggable
adapters for any tool that can be invoked via CLI or Python.

Ships with two pre-built tool integrations:

- **iof3D** — the optical-flow-on-point-clouds pipeline.
- **F2S3** — feature-to-supervoxel cross-correlation.

Adding a new tool is a YAML-and-glue exercise; see the
[integration guide](docs/integrating/index.md).

## Install

The framework alone (no tool deps):

```bash
pip install geodispbench3d
```

With the iof3D adapter (transitively pulls in iof3D and its dependencies):

```bash
pip install 'geodispbench3d[iof3d]'
```

> **Note:** the `[iof3d]` extra is currently unavailable on public PyPI until
> iof3D is published publicly. The iof3D adapter ships in the wheel but stays
> dormant until then. iof3D is still under active development — if you would
> like to use it for research in the meantime, contact Nicholas Meyer at
> <meyernic@ethz.ch> directly.

With the F2S3 adapter:

```bash
pip install 'geodispbench3d[f2s3]'
```

With the Streamlit dashboard:

```bash
pip install 'geodispbench3d[dashboard]'
```

Combinable: `pip install 'geodispbench3d[f2s3,dashboard]'`.

## Quickstart

```bash
# Run a sweep
geodispbench3d run benchmarks/suites/f2s3_voxel_refine.yaml

# Inspect results
geodispbench3d dashboard --parquet outputs/f2s3_voxel_refine.parquet

# Inspect a metrics file
geodispbench3d list-metrics benchmarks/metrics/pointing_error.yaml
```

See [docs/quickstart.md](docs/quickstart.md) for a five-minute walkthrough,
[docs/concepts.md](docs/concepts.md) for the architecture, and
[docs/integrating/index.md](docs/integrating/index.md) when you want to plug
in your own tool.

## Repository layout

```
src/
├── geodispbench3d/                  framework (no tool deps)
├── geodispbench3d_iof3d/            iof3D adapter (ships in the wheel; dormant until iof3D is public)
└── geodispbench3d_f2s3/             F2S3 adapter (gated by [f2s3] extra)

benchmarks/
├── data/                            ground-truth files
├── datasets/                        dataset YAMLs (tool-agnostic)
├── metrics/                         metric definitions
└── suites/                          composed sweeps you actually run

docs/                                user documentation
examples/                            small synthetic walkthroughs
tests/                               core / iof3d / f2s3 test suites
```

## License

Released under the BSD-3-Clause license — see `LICENSE`.
