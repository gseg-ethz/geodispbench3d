# Integrating via a factory

Use `kind: factory` when constructing your `ToolAdapter` needs more than
dataclass-style kwargs. Examples:

- The adapter must first parse a Hydra config tree to assemble its base
  configuration (this is how iof3D plugs in).
- The adapter must load a model checkpoint or open a database connection
  before its first trial.
- The adapter needs the tool YAML's `hyperparameters:` block visible to its
  internal parameter→config translator.

If a plain `__init__(**kwargs)` would suffice, use [`kind: custom`](custom-adapter.md)
instead. If your tool is a CLI binary or an importable function, use
[`kind: cli`](cli-tool.md) or [`kind: python_callable`](python-callable.md).

## The contract

Your factory function:

```python
def build_my_adapter(
    *,
    yaml_path: Path,                 # path of the tool YAML (for relative-path resolution)
    hyperparameters: Sequence[Mapping[str, Any]],  # raw hparam list from the YAML
    # ...everything else under factory_options: in tool.yaml...
) -> ToolAdapter:
    ...
```

It must return a `ToolAdapter` instance. The loader passes:

1. `yaml_path` — the absolute path of the tool YAML, useful for resolving
   relative filesystem references in your factory options.
2. `hyperparameters` — the raw list from the tool YAML's `hyperparameters:`
   block, in case your adapter's logic depends on them (the iof3D adapter,
   for instance, uses them to validate that swept parameter names map to
   real `AppConfig` fields).
3. Anything else you declare under `factory_options:` in the tool YAML —
   spread as keyword arguments.

## Tool YAML

```yaml
id: my-tool
kind: factory
entry: my_package.module:build_my_adapter

factory_options:
  base_config: pkg://my_package.conf/defaults.yaml
  device: cuda
  overrides:
    learning_rate: 0.001

hyperparameters:
  - { name: alpha, type: range, value_type: float, lower: 0.0, upper: 1.0 }
```

The loader calls:

```python
build_my_adapter(
    yaml_path=Path("/.../my-tool.yaml"),
    hyperparameters=[{"name": "alpha", "type": "range", ...}],
    base_config="pkg://my_package.conf/defaults.yaml",
    device="cuda",
    overrides={"learning_rate": 0.001},
)
```

## Worked example: how iof3D uses it

```python
# geodispbench3d_iof3d/factory.py
from omegaconf import OmegaConf
from iof3D.v2.cli_hydra import _build_app_config
from .adapter import Iof3dCallableAdapter

def build_iof3d_adapter(
    *,
    base_app_config: str | None = None,
    run_kwargs: dict | None = None,
    objective_name: str = "runtime_seconds",
    minimize: bool = True,
    overrides: dict | None = None,
    hyperparameters,
    yaml_path,
    **_,
):
    base_cfg = OmegaConf.load(_resolve(base_app_config, yaml_path))
    if overrides:
        base_cfg = OmegaConf.merge(base_cfg, OmegaConf.create(overrides))
    app_cfg = _build_app_config(base_cfg)
    return Iof3dCallableAdapter(
        base_config=app_cfg,
        param_defs=[_coerce(p) for p in hyperparameters],
        pipeline_kwargs=run_kwargs or {},
        objective_name=objective_name,
        minimize=minimize,
    )
```

The factory pattern keeps all iof3D-specific wiring inside the
`geodispbench3d_iof3d` peer package — the generic loader has zero iof3D
imports.

## `pkg://` references

The iof3D factory accepts `pkg://iof3D.conf/app/base.yaml` for its base
config. The convention is implemented by the factory itself (using
`importlib.resources`), not by the framework — it's just a useful trick
when you want to ship default configs inside your installable wheel.

## Tips

- **Validate early.** A factory runs once at suite-load time, so failures
  (missing config files, bad references, unsupported parameters) surface
  immediately rather than mid-sweep.
- **Don't do per-trial work in the factory.** It runs once. Per-trial setup
  belongs in the adapter's `prepare()` or `run_trial()` methods.
- **Keep the factory tight.** Anything more than ~50 lines is probably
  doing too much; put the heavy lifting in the adapter class.
