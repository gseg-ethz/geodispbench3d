# Concepts

geodispbench3d composes a benchmark from four small YAML files. Each describes
one orthogonal concern; the suite YAML wires the others together.

```
suite.yaml ──┬── tool.yaml      "how do I run the thing under test?"
             ├── dataset.yaml   "what cases do I evaluate against?"
             └── metrics.yaml   "what do I measure?"
```

You point the CLI at the suite, and the framework does the rest:

```bash
geodispbench3d run benchmarks/suites/<suite>.yaml
```

## The four pieces

### Tool

A **tool** is anything that takes input scans and produces displacement
predictions. The tool YAML declares **how** to invoke it — CLI subprocess,
in-process Python callable, or a factory function — plus the **hyperparameter
search space** and an optional **output parser** that turns the tool's raw
outputs into the shape metrics expect.

Tool YAMLs live with the tool's bench-wiring code. iof3D's lives in
[`src/geodispbench3d_iof3d/conf/tool/iof3d.yaml`](../src/geodispbench3d_iof3d/conf/tool/iof3d.yaml);
F2S3's in
[`src/geodispbench3d_f2s3/conf/tool/f2s3.yaml`](../src/geodispbench3d_f2s3/conf/tool/f2s3.yaml).

### Dataset

A **dataset** is a list of evaluable **cases**. Each case has one or more scans
(typically two epochs) and ground truth. Datasets are tool-agnostic — the same
Mattertal GT serves iof3D and F2S3 with no duplication.

Dataset YAMLs live in [`benchmarks/datasets/`](../benchmarks/datasets/).

### Metrics

A **metrics** file lists the scalar metrics that can serve as the Ax objective
(`objective_metrics:`) and the structured-row metrics that get persisted to
parquet for the dashboard (`record_metrics:`). Each metric is a Python
callable resolved by importlib via a `package.module:function` reference,
so users can register their own metrics in their own packages.

Metrics YAMLs live in [`benchmarks/metrics/`](../benchmarks/metrics/).

### Suite

A **suite** is the composition: it references one tool, one dataset, one
metrics file, and declares the search budget plus which scalar metric is the
Ax objective.

Suite YAMLs live in [`benchmarks/suites/`](../benchmarks/suites/).

## How a trial flows through the framework

```
Ax samples parameters
        │
        ▼
ToolAdapter.run_trial(parameters)         ← from tool.yaml
        │
        ▼
TrialResult { run_dir, predictions, scalar_metrics, ... }
        │
        ▼
output_parser(outputs, ground_truth)      ← optional, from tool.yaml
        │
        ▼
prediction = { per_point: [{label, vector}, ...] }
        │
        ▼
metric callables dispatched per `needs:`  ← from metrics.yaml
        │
        ▼
{ scalar_metrics → Ax }   { record_rows → parquet }
```

If your tool already produces predictions in the `{per_point: [...]}` shape,
you can skip the parser. Most real tools need one, because their native output
is a dense field of points or per-tile files.

## Where the framework draws the line

What's **generic** (lives in `src/geodispbench3d/`):

- The Ax sweep runner.
- The CLI / callable / custom / factory adapter implementations.
- The dataset / metrics / suite loaders.
- Built-in pointing-error metric functions.
- The parquet results store and the Streamlit dashboard.

What's **tool-specific** (lives in `src/geodispbench3d_<tool>/`):

- Output parsers (different file formats, different sampling strategies).
- Adapter factories (only when adapter construction is non-trivial).
- The tool YAML itself.

What's **shared across tools** (lives in `benchmarks/`):

- Datasets.
- Metrics definitions.
- Suite YAMLs.

This split is intentional: the reason `geodispbench3d` is a separate package
from `iof3D` is that someone benchmarking a different tool can install the
framework without dragging iof3D's deps along.
