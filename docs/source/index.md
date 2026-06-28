# geodispbench3d

A small framework for benchmarking 3D displacement / optical-flow tools against
ground-truth point displacements, with built-in Bayesian hyperparameter sweeps
via [Ax](https://ax.dev).

It ships with two pre-built tool integrations:

- **iof3D** — the optical-flow-on-point-clouds pipeline this repo originated from.
- **F2S3** — the feature-to-supervoxel cross-correlation tool, driven via
  its CLI in a separate conda env.

Adding a new tool is a YAML-and-glue exercise; see the integration guide below.

:::{toctree}
:hidden:
:caption: Read me first
:maxdepth: 1

quickstart
concepts
rescoring-and-analysis
:::

:::{toctree}
:hidden:
:caption: Pre-built tools
:maxdepth: 1

tools/iof3d
tools/f2s3
:::

:::{toctree}
:hidden:
:caption: Integrating your own tool
:maxdepth: 1

integrating/index
integrating/cli-tool
integrating/python-callable
integrating/factory
integrating/custom-adapter
integrating/output-parsers
integrating/datasets
integrating/metrics
:::

:::{toctree}
:hidden:
:caption: Reference
:maxdepth: 1

reference/yaml-schemas
:::

## Read me first

- [Quickstart](quickstart.md) — run a sweep in five minutes against a pre-built tool.
- [Concepts](concepts.md) — what the four YAML files describe and how they fit together.
- [Rescoring and analysis](rescoring-and-analysis.md) — re-evaluate existing runs without re-running the tool, or score cached predictions across tools.

## Pre-built tools

- [iof3D](tools/iof3d.md)
- [F2S3](tools/f2s3.md)

## Integrating your own tool

- [Overview & decision matrix](integrating/index.md) — pick the adapter kind that fits.
- [CLI tool](integrating/cli-tool.md) — the most common case (subprocess + argv).
- [Python callable](integrating/python-callable.md) — for in-process tools.
- [Factory](integrating/factory.md) — when adapter construction needs more than dataclass kwargs.
- [Custom adapter](integrating/custom-adapter.md) — subclass `ToolAdapter` directly.
- [Output parsers](integrating/output-parsers.md) — turn raw outputs into the prediction shape metrics consume.
- [Datasets and ground truth](integrating/datasets.md)
- [Metrics](integrating/metrics.md)

## Reference

- [YAML schemas cheat sheet](reference/yaml-schemas.md)
