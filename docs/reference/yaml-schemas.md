# YAML schemas cheat sheet

The four YAML kinds at a glance. JSON Schema files live in
[`src/geodispbench3d/conf/schema/`](../../src/geodispbench3d/conf/schema/)
and provide the canonical validation rules.

## tool.yaml

```yaml
id: <string>                          # required, unique within a suite
kind: cli | python_callable | callable | custom | factory   # required

entry: <string>                       # required (semantics depend on kind)

remediation: <string>                 # optional; operator guidance appended to a
                                      #   ToolPreflightError when the env/binary
                                      #   can't be resolved before trial 0
help_url: <string>                    # optional; reference URL appended to the
                                      #   same preflight error

execution:
  mode: subprocess | in_process       # informational; semantics live in adapter
  in_process_safe: <bool>
  timeout_seconds: <number>           # optional, opt-in per-trial wall-clock cap;
                                      #   unset or <= 0 = no timeout. Distinct from
                                      #   the suite-level execution block. On expiry
                                      #   the tool process tree is killed and the
                                      #   trial is recorded as a timeout failure.

# --- kind: cli ---
invocation:
  style: hydra_overrides | argparse | kv_equals
  extra_args: [<string>]
  presence_flag_params: [<name>]      # argparse store_true names
  static_params: { <name>: <value> }  # always-on params, rendered like trial params

# --- kind: custom ---
init_kwargs: { <key>: <value> }       # passed to the class constructor

# --- kind: factory ---
factory_options: { <key>: <value> }   # passed as kwargs to the factory function

# Hyperparameter search space (all kinds)
hyperparameters:
  - name: <dotted.name>
    type: choice | range | fixed
    value_type: str | int | float | bool
    values: [...]                     # for choice / fixed
    lower: <number>                   # for range
    upper: <number>
    log_scale: <bool>
    step: <number>
    activates_on:                     # conditional activation
      <parent.name>: [<allowed values>]
    is_ordered: <bool>
    sort_values: <bool>

# Where to find / how to interpret outputs
outputs:
  from: glob                          # blessed mode, default when unset.
                                      #   stdout_json is DEPRECATED (explicit use
                                      #   raises at load); fixed_path is removed —
                                      #   use glob with a predictions_glob.
  run_dir_root: <path>                # for non-hashed flat layouts
  hashed_run_dir:
    root: <path>
    arg_name: <string>                # e.g. --results_dir
    hash_length: <int>                # default 12
    extra_inputs: [<any>]             # folded into the param hash
  predictions_glob: <glob>
  figures_glob: <glob>
  env: { <key>: <value> }             # subprocess environment overrides

# Convert raw outputs into prediction = {per_point: [...]}
output_parser:
  fn: <package.module>:<function>
  options: { <key>: <value> }
```

See [`tool.schema.json`](../../src/geodispbench3d/conf/schema/tool.schema.json).

## dataset.yaml

```yaml
id: <string>                          # required
root: <path>                          # default: directory of this YAML
metadata: { ... }                     # passthrough to case_meta

gt_kinds_supported:                   # informational; loader-validated per case
  - point_displacements

cases:
  - name: <string>                    # required
    scans:                            # may be empty
      - epoch: <string>
        path: <path>                  # relative to root, or absolute
        metadata: { ... }
    ground_truth:
      kind: <gt_kind>                 # required if ground_truth present
      path: <path>                    # OR
      inline: { ... }                 # kind-specific inline data
      options: { ... }                # kind-specific loader knobs
    metadata: { ... }                 # flows into case_meta for metrics
```

See [`dataset.schema.json`](../../src/geodispbench3d/conf/schema/dataset.schema.json).

## metrics.yaml

```yaml
objective_metrics:
  - id: <string>                      # unique within section
    fn: <package.module>:<function>
    needs: [prediction | ground_truth | trial_meta | case_meta]
    gt_kinds: [<kind>]                # optional; restricts metric to these GT kinds
    params: { ... }                   # forwarded to the function as kwargs

record_metrics:
  - id: <string>
    fn: <package.module>:<function>
    needs: [...]
    gt_kinds: [<kind>]
    params: { ... }
```

See [`metrics.schema.json`](../../src/geodispbench3d/conf/schema/metrics.schema.json).

## suite.yaml

```yaml
id: <string>                          # required
tool: <path-to-tool.yaml>             # required, relative to this YAML
dataset: <path-to-dataset.yaml>       # required
metrics: <path-to-metrics.yaml>       # required

search:
  max_trials: <int>
  sobol_trials: <int>
  objective: <metric.id>              # must match an id in objective_metrics
  minimize: <bool>

execution:
  parallel_trials: <int>              # currently 1; reserved for future
  override_tool_mode: subprocess | in_process | null

results:
  parquet_path: <path>                # where record rows accumulate
  run_dir_root: <path>                # informational; tools manage their own
```

See [`suite.schema.json`](../../src/geodispbench3d/conf/schema/suite.schema.json).

## Path resolution rules

- Relative paths in `dataset.yaml` resolve against the dataset YAML's
  `root:` (which itself defaults to the YAML's directory).
- Relative paths in `tool.yaml` (`outputs.run_dir_root`,
  `outputs.hashed_run_dir.root`, factory `base_app_config:`) resolve
  against the tool YAML's directory.
- Relative paths in `suite.yaml` (`tool:`, `dataset:`, `metrics:`,
  `results.parquet_path`, `results.run_dir_root`) resolve against the
  suite YAML's directory.

Absolute paths are honored everywhere.

## CLI

```
geodispbench3d run <suite.yaml>
  [--max-trials N]                    # cap trials regardless of suite
  [--timeout SECONDS]                 # float; overrides tool execution.timeout_seconds
  [--log-level LEVEL]                 # DEBUG | INFO | WARNING | ERROR
  [--traceback]                       # re-raise the original exception with full stack

geodispbench3d rescore <suite.yaml>   # own subcommand (was: run --rescore)
  [--reuse-parser-options]            # use the parser config recorded in summary.json
  [--use-prediction-cache]            # skip phase 2 on a predictions-cache hit
  [--pass-id ID]                      # tag this rescore pass in the parquet
  [--max-trials N]                    # warn-and-ignored in rescore mode
  [--log-level LEVEL]
  [--traceback]

geodispbench3d analyze <analysis.yaml>
  [--pass-id ID]
  [--log-level LEVEL]
  [--traceback]

geodispbench3d dashboard
  [--parquet PATH]                    # default: $GEODISPBENCH3D_PARQUET
                                      #          or ./outputs/results.parquet

geodispbench3d list-metrics <metrics.yaml>
  [--traceback]
```

Exit codes: `0` success, `1` runtime/config/preflight failure (or a
zero-success sweep), `2` argparse usage error. See
[Integrating a CLI tool → Package CLI exit codes](../integrating/cli-tool.md#package-cli-exit-codes).
