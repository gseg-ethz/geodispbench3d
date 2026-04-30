# Writing a custom adapter

Use `kind: custom` when you need full control over how a trial runs but the
adapter's constructor takes plain dataclass-style kwargs. Subclassing
`ToolAdapter` lets you override `prepare()`, `run_trial()`, and `teardown()`.

If your adapter needs a non-trivial *constructor* (parsed config trees,
loaded models), see [Factory](factory.md). If a function-with-side-effects
is all you need, see [Python callable](python-callable.md).

## The `ToolAdapter` interface

```python
from geodispbench3d.tool import ToolAdapter, TrialRequest, TrialResult, TrialOutputs

class ToolAdapter(ABC):
    id: str = "tool-adapter"
    in_process_safe: bool = False     # True ⇒ may run inside the sweep process

    @abstractmethod
    def run_trial(self, request: TrialRequest) -> TrialResult: ...

    def prepare(self) -> None: ...    # called once before the sweep
    def teardown(self) -> None: ...   # called once after the sweep
```

`TrialRequest`, `TrialResult`, and `TrialOutputs` are
`@dataclass(frozen=True)` types defined in
`geodispbench3d.tool.base`. Their fields:

```python
TrialRequest:
  parameters: Mapping[str, Any]      # raw Ax parameterization
  case_name: str | None              # which dataset case this trial targets
  work_dir: Path | None              # optional pre-created run directory

TrialOutputs:
  run_dir: Path
  predictions: Sequence[Path] = ()
  figures: Sequence[Path] = ()
  extras: Mapping[str, Any] = {}     # arbitrary passthrough

TrialResult:
  outputs: TrialOutputs
  scalar_metrics: Mapping[str, float]   # adapter-reported scalars (e.g. runtime)
  duration_seconds: float
  success: bool = True
  error: str | None = None
```

## A minimal custom adapter

```python
# my_package/adapter.py
from pathlib import Path
import time

from geodispbench3d.tool import ToolAdapter, TrialOutputs, TrialRequest, TrialResult


class MyAdapter(ToolAdapter):
    id = "my-tool"
    in_process_safe = True            # don't fork

    def __init__(self, *, output_root: str, alpha_default: float = 0.5) -> None:
        self._output_root = Path(output_root)
        self._alpha_default = alpha_default

    def prepare(self) -> None:
        self._output_root.mkdir(parents=True, exist_ok=True)
        # ... load any once-per-sweep state here ...

    def run_trial(self, request: TrialRequest) -> TrialResult:
        params = dict(request.parameters)
        alpha = float(params.get("alpha", self._alpha_default))
        run_dir = self._output_root / f"trial_{int(time.time() * 1e6)}"
        run_dir.mkdir()

        start = time.perf_counter()
        result_path = my_pipeline(alpha, run_dir)   # your tool's actual work
        duration = time.perf_counter() - start

        return TrialResult(
            outputs=TrialOutputs(
                run_dir=run_dir,
                predictions=(result_path,),
            ),
            scalar_metrics={"runtime_seconds": duration},
            duration_seconds=duration,
            success=True,
        )

    def teardown(self) -> None:
        # ... close models, free GPU memory ...
        pass
```

## Tool YAML

```yaml
id: my-tool
kind: custom
entry: my_package.adapter:MyAdapter

init_kwargs:
  output_root: /scratch/my-runs
  alpha_default: 0.5

hyperparameters:
  - { name: alpha, type: range, value_type: float, lower: 0.0, upper: 1.0 }

output_parser:
  fn: my_package:parse_outputs
  options: { sample_radius_m: 10.0 }
```

The loader calls `MyAdapter(**init_kwargs)`; `init_kwargs:` is a literal
mapping of constructor arguments. If you need to pre-process those values
(load config files, resolve relative paths), graduate to
[`kind: factory`](factory.md).

## When to override what

- **`prepare()`** — once-per-sweep work that benefits all trials. Loading a
  neural-network checkpoint, opening a database connection, JIT-compiling
  CUDA kernels.
- **`teardown()`** — clean up what `prepare()` allocated.
- **`run_trial()`** — the actual per-trial work. Required.

If your adapter sets `in_process_safe = False`, the sweep runner won't fork
a subprocess for you — that's the CLI adapter's job. The flag is purely
informational; what matters is whether your code crashes the parent process
on bad inputs.

## Reusing the CLI / callable adapters as building blocks

If your adapter mostly wants to delegate to a CLI but with custom argv
shaping, **subclass `CliToolAdapter`** and override `_build_argv` /
`_collect_outputs`. Same for `CallableToolAdapter` if your needs are
adjacent to its semantics.

```python
from geodispbench3d.tool.cli_adapter import CliToolAdapter

class MyCli(CliToolAdapter):
    def _build_argv(self, request, run_dir):
        argv = super()._build_argv(request, run_dir)
        # ... mutate argv with custom logic ...
        return argv
```

This is often a much smaller change than writing a full `ToolAdapter`.

## Reporting failures vs raising

If the trial completes (subprocess exited, function returned) but the
*tool* failed, return a `TrialResult` with `success=False` and a useful
`error=` message. The sweep runner reports the trial as failed to Ax but
keeps going.

If your adapter itself crashes (uncaught exception), the runner logs it and
calls `Ax.log_trial_failure` — no different in effect, but the failure
manifests in the sweep's logs as a stack trace, not a trial record.
