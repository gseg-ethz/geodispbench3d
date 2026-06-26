# geodispbench3d — Software Overview

## Description

`geodispbench3d` is an open-source Python framework for benchmarking
three-dimensional displacement and optical-flow tools. It provides a
declarative, YAML-driven front end in which a *suite* composes a tool, a
dataset, and a set of metrics, and then evaluates that tool — optionally
under a Bayesian hyperparameter sweep — against ground-truth displacement
fields. The framework is deliberately tool-agnostic: any program that can be
invoked through a command line or a Python callable can be wired in through a
single adapter contract, without modifying the framework core.

The software was developed at ETH Zurich to make 3D displacement-estimation
experiments reproducible and comparable across tools, and ships with two
ready-made integrations (iof3D and F2S3). It is released under the
BSD-3-Clause license.

## Main Functionality

- **Declarative benchmark definition.** Suites, datasets, metrics, and tool
  wiring are expressed as validated YAML files, so an experiment is described
  by configuration rather than code.
- **Bayesian hyperparameter sweeps.** Tool parameters are optimized with
  [Ax](https://ax.dev)-driven Bayesian optimization, turning manual parameter
  tuning into a declared search space.
- **Three execution modes over one evaluation core.** `sweep` runs the tool
  under optimization, `rescore` recomputes metrics over existing run
  directories, and `analyze` scores cached predictions without re-invoking the
  tool — all sharing a single, consistent evaluation path.
- **Pluggable tool adapters.** A small `ToolAdapter` contract supports both
  subprocess (CLI) tools and in-process Python callables; adding a new tool is
  a configuration-and-glue exercise rather than a core change.
- **Provenance-first persistence.** Every run is self-describing: results are
  appended to a columnar (parquet) store, parser outputs are cached, and each
  run directory records the tool, dataset, and parser provenance needed to
  reproduce its scoring.
- **Interactive results dashboard.** An optional Streamlit dashboard lets users
  explore sweep results visually.

## Technical Scope

- **Language and runtime.** Pure Python (CPython 3.11 / 3.12), built on the
  scientific Python stack (NumPy 2.x, pandas).
- **Core libraries.** Ax for optimization; Hydra and OmegaConf for
  configuration composition; pytest, ruff, and pyright for the quality
  toolchain.
- **Packaging.** Distributed as a standard wheel and source distribution via a
  Python package index, with optional feature "extras" that gate heavier or
  tool-specific dependencies so the framework core stays lightweight.
- **Shipped integrations.** Two reference adapters are included — iof3D
  (an in-process optical-flow-on-point-clouds pipeline) and F2S3 (a
  feature-to-supervoxel cross-correlation tool driven as an external process).
- **Boundaries.** The framework core is CPU-only and tool-agnostic; GPU/CUDA
  requirements, if any, are introduced only by the specific tool a user plugs
  in. Trial evaluation is currently single-threaded (sequential per trial).

## Intended Users and Use Cases

The primary users are **researchers and engineers in geoscience, remote
sensing, and computer vision** who need to evaluate, compare, or tune 3D
displacement-estimation and optical-flow tools against reference data.

Typical use cases include:

- **Reproducible benchmarking** — running one tool against a fixed dataset and
  metric set and obtaining provenance-stamped, reusable results.
- **Cross-tool comparison** — evaluating multiple displacement tools on a
  common dataset under identical metrics.
- **Hyperparameter optimization** — finding good tool parameters automatically
  via Bayesian sweeps instead of manual trial and error.
- **Method development** — integrating a new or in-house displacement tool
  through the adapter contract and benchmarking it alongside established ones.

The software is intended for an open-source research audience and is suitable
for both interactive exploration and scripted, batch experimentation.
