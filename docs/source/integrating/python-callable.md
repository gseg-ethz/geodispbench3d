# Integrating a Python callable

Use `kind: python_callable` (or its alias `callable`) when your tool is a
Python function importable in the sweep process. This avoids the per-trial
fork + Python interpreter startup cost of the CLI adapter, which matters
when individual trials are short.

## When to use it

- Your tool is already a Python library (no separate binary).
- Your tool has expensive setup that you don't want to repeat per trial
  (loading neural-network weights, opening a database connection, …).
- You're prototyping and don't want to write a CLI yet.

If your tool is a CLI binary, prefer [`kind: cli`](cli-tool.md) — subprocess
isolation is genuinely cheap and crashes in the tool don't take down the
sweep.

## The contract

Your function signature:

```python
def my_tool(parameters: Mapping[str, Any]) -> Any: ...
```

It receives the raw Ax parameterization (dotted-key mapping) and must return
one of:

- A `geodispbench3d.tool.base.TrialResult`. Most explicit; you get to fill in
  outputs, scalar metrics, and success flag yourself.
- A `geodispbench3d.tool.base.TrialOutputs`. The adapter wraps it in a
  `TrialResult` with `runtime_seconds` from its own timer.
- A plain mapping with keys `run_dir`, `predictions`, `figures`,
  `scalar_metrics`, `success`, `error`. Most ergonomic.

A minimal mapping return:

```python
def my_tool(parameters):
    out_dir = run_my_pipeline(parameters)
    return {
        "run_dir": str(out_dir),
        "predictions": [str(p) for p in out_dir.glob("*.ply")],
        "scalar_metrics": {"loss": float(measured_loss)},
    }
```

## Tool YAML

```yaml
id: my-tool
kind: python_callable
entry: my_package.module:my_tool

hyperparameters:
  - { name: alpha, type: range, value_type: float, lower: 0.0, upper: 1.0 }
  - { name: layers, type: choice, value_type: int, values: [2, 4, 8] }

# Output parser is optional; omit it if `my_tool` already returns a
# {per_point: [...]} prediction in the mapping it returns.
output_parser:
  fn: my_package.module:parse_my_outputs
  options:
    sample_radius_m: 5.0
```

## Where it runs

In the same Python process as the sweep runner. That means:

- Imports happen once (when the adapter prepares for the first trial), not
  per trial. Heavy libraries — torch, GPU drivers — only initialize once.
- An unhandled exception in your function logs the trial as failed but does
  *not* crash the sweep (the runner catches and calls `Ax.log_trial_failure`).
- A segfault, OOM, or `os._exit` *will* kill the sweep. If your tool is
  unstable, switch to [`kind: cli`](cli-tool.md).

## Sharing setup across trials

If you need expensive once-per-sweep setup, write a small custom adapter
([Custom adapter](custom-adapter.md)) and override `prepare()` /
`teardown()`. The callable adapter doesn't expose those hooks.

## Example

```python
# my_package/module.py
from pathlib import Path
import tempfile

def my_tool(parameters):
    out_dir = Path(tempfile.mkdtemp())
    # ... run the tool, write outputs into out_dir ...
    return {
        "run_dir": str(out_dir),
        "predictions": [str(out_dir / "result.ply")],
        "scalar_metrics": {"runtime_seconds": 1.23},
    }
```

```yaml
# tool.yaml
id: my-tool
kind: python_callable
entry: my_package.module:my_tool
hyperparameters:
  - { name: x, type: choice, value_type: int, values: [1, 2, 3] }
```

Then point a suite at it and run as usual.
