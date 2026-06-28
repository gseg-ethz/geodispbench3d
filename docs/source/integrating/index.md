# Integrating your own tool

A tool integration in geodispbench3d is at most three things:

1. A **tool YAML** describing how to invoke the tool and its hyperparameter space.
2. (Often) an **output parser** that turns the tool's raw outputs into the
   `{per_point: [...]}` shape metrics consume.
3. (Sometimes) a small Python module to host the parser, a custom adapter, or
   a factory function. Lives in a peer package
   `src/geodispbench3d_<tool>/`.

The dataset, metrics, and suite YAMLs you'll use are typically already in
[`benchmarks/`](https://github.com/gseg-ethz/geodispbench3d/tree/main/benchmarks/) — datasets and metrics are tool-agnostic
on purpose.

## Decision matrix: which adapter kind?

| Your tool is… | Use `kind:` | See |
|---|---|---|
| A CLI binary you want to `subprocess.run` | `cli` | [CLI tool](cli-tool.md) |
| A Python function importable in the sweep process | `python_callable` | [Python callable](python-callable.md) |
| A Python class needing dataclass-style kwargs to instantiate | `custom` | [Custom adapter](custom-adapter.md) |
| A Python adapter whose constructor needs *more* (parsed config tree, models loaded) | `factory` | [Factory](factory.md) |

If unsure, start with `cli`. Subprocess isolation is cheap, the CLI adapter
already handles hashed run-dirs, presence-only flags, and glob-based output
collection. Move to `python_callable` only if startup cost (importing your
tool every trial) is dominating runtime.

## The minimum viable integration

For a CLI tool that already produces output in `{per_point: [...]}` form
(one displacement vector per labeled GT point), the entire integration is
a single `tool.yaml`:

```yaml
id: my-tool
kind: cli
entry: my_tool_cli
invocation:
  style: argparse
hyperparameters:
  - { name: alpha, type: range, value_type: float, lower: 0.0, upper: 1.0 }
outputs:
  from: glob                  # the blessed output-collection mode
  predictions_glob: "*.json"  # run-dir-relative glob for the tool's output
```

`outputs.from: glob` is the single blessed output-collection mode (and the
default when `from:` is unset). The older `stdout_json` mode is **deprecated** —
setting it explicitly now raises at load time. See
[Locating outputs](cli-tool.md#locating-outputs) for the migration.

Most real tools produce dense displacement fields and need a parser to sample at
GT points. See [Output parsers](output-parsers.md).

## What lives where

```
src/geodispbench3d_<tool>/        ← your peer package
├── __init__.py                     re-exports what users reference from YAML
├── output_parser.py                (optional) parse-and-sample
├── adapter.py                      (optional) custom ToolAdapter subclass
├── factory.py                      (optional) factory function for kind: factory
└── conf/tool/<tool>.yaml           the tool YAML itself
```

The peer package contains *only* tool-specific code and its tool YAML.
Datasets, metrics, and suites belong in [`benchmarks/`](https://github.com/gseg-ethz/geodispbench3d/tree/main/benchmarks/) so
they can be reused across tools (e.g. comparing your tool to iof3D on the
same Mattertal GT).

## Suite that uses your tool

Once the tool YAML exists, write a suite YAML in `benchmarks/suites/`:

```yaml
id: my-tool-mattertal
tool: ../../src/geodispbench3d_<tool>/conf/tool/<tool>.yaml
dataset: ../datasets/mattertal.yaml
metrics: ../metrics/pointing_error.yaml

search:
  max_trials: 20
  sobol_trials: 5
  objective: median_displacement_error
  minimize: true

results:
  parquet_path: outputs/my-tool-mattertal.parquet
```

Then:

```bash
geodispbench3d run benchmarks/suites/my-tool-mattertal.yaml
```

That's the whole loop.
