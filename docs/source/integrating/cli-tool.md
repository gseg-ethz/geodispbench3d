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
  from: glob                 # the single blessed mode (default when unset)
  predictions_glob: ...      # run-dir-relative glob for prediction files
  figures_glob: ...
```

- `glob` — search the run dir using the configured glob patterns. This is the
  **blessed** path and the default when `from:` is unset.
- `stdout_json` — **deprecated.** Setting `from: stdout_json` explicitly now
  raises at load time (`outputs.from: stdout_json is no longer supported; use
  outputs.from: glob with a predictions_glob`). Migrate to `glob`.
- `fixed_path` — **removed/unsupported.** Use `glob` with a `predictions_glob`
  scoped to the run dir.

A set `predictions_glob` that matches **zero files** is treated as a failed
trial (a tool that ran but produced no output is data corruption, not success),
not a silent pass — see the [subprocess contract](#subprocess-contract) below.

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

## Subprocess contract

The `CliToolAdapter` runs one subprocess per trial and maps each failure mode to
a precise outcome:

| Failure mode | What the adapter does | `error_kind` |
|---|---|---|
| **Nonzero tool exit** | Fails the trial (`error=exit=<code>`). | `nonzero_exit` |
| **Empty output** — a set `predictions_glob` matches zero files | Fails the trial (`error=no predictions matched glob ...`); not treated as success. | `missing_output` |
| **Timeout** — `execution.timeout_seconds` exceeded | Kills the whole process tree (process-group `SIGKILL` on POSIX; direct-child fallback elsewhere) and fails the trial. | `timeout` |
| **Missing env/binary** — entry / conda env unresolvable before trial 0 | Fail-fast `ToolPreflightError` before any trial runs. | — |

**Failed-trial propagation.** A failed trial (any `success=False` result) is
reported to Ax as a **FAILED** trial via `log_trial_failure` — Ax never treats
it as a completed/scored trial — and the sweep **continues** to the next trial.
The optimizer is not fed a bogus objective for a trial that did not actually
produce one. The preflight case is the one exception: a missing env/binary
fails fast *before* trial 0, since every trial would hit the same wall.

### Timeout exit semantics

An **individual timeout is non-fatal for the run's exit code.** When a trial
times out the sweep continues, the timeout is surfaced on its own dedicated CLI
line (`N trials timed out`), and the run **exits 0** as long as at least one
trial succeeded. Do not read "a timeout fails a trial" as "a timeout makes the
run exit non-zero" — those are different concerns (the trial is failed *to Ax*;
the process exit code is driven separately).

The exit code is driven by genuine tool/eval failures (`trial_failures` /
`eval_failures`) **or** by a sweep that produced **zero successful trials**. A
sweep that optimized nothing exits 1 even if every failure was a timeout
(a timeouts-only, zero-success sweep), because there is no best trial to report.

## Package CLI exit codes

`geodispbench3d <subcommand>` follows a 0/1/2 taxonomy:

| Exit | Meaning |
|---|---|
| **0** | Success. Includes a sweep with at least one successful trial whose only other failures were timeouts (individual timeouts do **not** force exit 1). |
| **1** | Runtime / config / preflight failure: a genuine trial crash, an evaluation failure, a `ToolPreflightError`, a bad/missing config (clean `error: <msg>` line), **or** a zero-success sweep (including a timeouts-only sweep that optimized nothing). |
| **2** | argparse usage error (unknown flag, missing argument, a rescore-only flag passed to `run`). |

The exact sweep expression is
`1 if (trial_failures or eval_failures or successful_trials == 0) else 0`:
note again that an individual timeout alone does **not** force exit 1 — only a
genuine failure or a zero-success sweep does. Pass `--traceback` on any
subcommand to re-raise the original exception with its full stack instead of the
flattened `error: <msg>` line.
