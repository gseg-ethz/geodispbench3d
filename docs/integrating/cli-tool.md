# Integrating a CLI tool

Use `kind: cli` when your tool is a binary or script you can invoke as a
subprocess. This is the most common case and the easiest one to wire up.

## How `CliToolAdapter` builds argv

```
[entry tokens] [extra_args] [static_params] [trial parameters] [hashed run-dir flag]
```

- **entry** — the executable. Tokenised with `shlex.split`, so
  `entry: conda run -n my-env my-tool` works.
- **extra_args** — appended verbatim, before any rendered parameters.
- **static_params** — always-on parameters, rendered with the same style
  as trial parameters. Useful for input paths and global flags that aren't
  swept.
- **trial parameters** — what Ax sampled this trial.
- **hashed run-dir flag** — only if `outputs.hashed_run_dir:` is configured;
  appended last as `<arg_name> <root>/<hash>`.

## Three rendering styles

Set `invocation.style:` to one of:

| Style | Rendering | Example |
|---|---|---|
| `hydra_overrides` (default) | `key=value` | `flow.method=fft_local` |
| `kv_equals` | `key=value` (alias of above) | `alpha=0.5` |
| `argparse` | `--key value` | `--voxel_grid_size 0.4` |

Boolean values render as `true`/`false` strings — except in `argparse` style,
where parameters listed in `invocation.presence_flag_params:` render as
`--<name>` when truthy and are omitted entirely when falsy (matching argparse
`store_true` semantics).

## A minimal example

```yaml
id: hello
kind: cli
entry: /usr/local/bin/hello-tool
invocation:
  style: argparse
hyperparameters:
  - { name: greeting, type: choice, value_type: str, values: [hi, hey] }
```

Each trial fires:

```
/usr/local/bin/hello-tool --greeting hi
```

## A realistic example (F2S3)

```yaml
id: f2s3
kind: cli
entry: conda run -n f2s3-dev312 f2s3

invocation:
  style: argparse
  presence_flag_params:
    - save_interim
    - refine_results
  static_params:
    save_interim: true
    source_cloud: /scratch/00_data/IOF3D_testing/00_scans/ply/20190710_Epoch_1_PRCS.ply
    target_cloud: /scratch/00_data/IOF3D_testing/00_scans/ply/20210720_Epoch_2_PRCS.ply

hyperparameters:
  - name: voxel_grid_size
    type: choice
    value_type: float
    values: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
  - name: refine_results
    type: choice
    value_type: bool
    values: [false, true]

outputs:
  from: glob
  hashed_run_dir:
    root: /scratch/00_data/geodispbench3d/f2s3
    arg_name: --results_dir
    hash_length: 12
  predictions_glob: output/**/*.txt

output_parser:
  fn: geodispbench3d_f2s3:parse_f2s3_output
  options:
    sample_radius_m: 15.0
```

A single trial expands to:

```
conda run -n f2s3-dev312 f2s3 \
  --save_interim \
  --source_cloud /scratch/00_data/IOF3D_testing/00_scans/ply/20190710_Epoch_1_PRCS.ply \
  --target_cloud /scratch/00_data/IOF3D_testing/00_scans/ply/20210720_Epoch_2_PRCS.ply \
  --voxel_grid_size 0.4 \
  --refine_results \
  --results_dir /scratch/00_data/geodispbench3d/f2s3/<12-char-hash>
```

## Hashed run-dirs

The hash is computed from the trial parameters (canonicalized + JSON-serialized
+ SHA256). Identical parameter sets always produce the same hash, so
re-running an aborted sweep skips work the tool has already done — provided
the tool is idempotent in that directory.

To fold additional values into the hash (e.g. dataset version, scan paths),
set `outputs.hashed_run_dir.extra_inputs:` to a list — each value is JSON-serialized
into the canonical blob.

## Locating outputs

After the subprocess finishes, the adapter populates `TrialOutputs` so the
output parser knows where to look:

```yaml
outputs:
  from: stdout_json | glob | fixed_path
  predictions_glob: ...      # used when from: glob
  figures_glob: ...
```

- `stdout_json` — read the last line of stdout that parses as a JSON object
  with keys `run_dir`, `predictions`, `figures`, `scalar_metrics`. Tools you
  control can emit this. Cleanest option.
- `glob` — search the run dir using the configured glob patterns.
- `fixed_path` — the run dir alone is the output (no glob).

If `from: stdout_json` finds no JSON line, the adapter falls back to the
glob behavior, so it's safe to set both.

## Environment variables

```yaml
outputs:
  env:
    CUDA_VISIBLE_DEVICES: "0"
    OMP_NUM_THREADS: "8"
```

These are passed through to `subprocess.run`'s `env=`. If unset, the parent
process's environment is inherited.

## Running it

```bash
geodispbench3d run benchmarks/suites/<your-suite>.yaml
```

The adapter logs each trial's full argv at INFO level, which is the fastest
way to debug issues with parameter rendering or path resolution.
