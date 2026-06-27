"""CliToolAdapter argv assembly + hashed run-dir tests.

Validates the most-used adapter behaviors without spawning real subprocesses:
parameter rendering for each style, presence-only flags, hashed run-dirs,
static_params merging.
"""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

import pytest

from geodispbench3d.tool import (
    CliInvocationSpec,
    CliToolAdapter,
    HashedRunDirSpec,
    TrialRequest,
    hash_parameters,
)


def test_argparse_style_renders_kv_pairs() -> None:
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="/bin/true", style="argparse"),
    )
    request = TrialRequest(parameters={"alpha": 0.5, "beta": 3})
    argv = adapter._build_argv(request, run_dir=None)
    assert argv == ["/bin/true", "--alpha", "0.5", "--beta", "3"]


def test_argparse_presence_flags_omit_when_false() -> None:
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(
            entry="/bin/true",
            style="argparse",
            presence_flag_params=("verbose", "debug"),
        ),
    )
    request = TrialRequest(parameters={"verbose": True, "debug": False, "threads": 4})
    argv = adapter._build_argv(request, run_dir=None)
    assert "--verbose" in argv
    assert "--debug" not in argv
    assert "--threads" in argv and "4" in argv


def test_static_params_render_before_trial_params() -> None:
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(
            entry="/bin/true",
            style="argparse",
            static_params={"input": "/data/scan.ply"},
        ),
    )
    request = TrialRequest(parameters={"alpha": 0.5})
    argv = adapter._build_argv(request, run_dir=None)
    # static first, trial second
    assert argv.index("--input") < argv.index("--alpha")


def test_hydra_overrides_style() -> None:
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="/bin/true", style="hydra_overrides"),
    )
    request = TrialRequest(parameters={"flow.method": "fft", "flow.alpha": 0.5})
    argv = adapter._build_argv(request, run_dir=None)
    assert "flow.method=fft" in argv
    assert "flow.alpha=0.5" in argv


def test_entry_is_shlex_split() -> None:
    """Entry strings like 'conda run -n env tool' must split into multiple tokens."""

    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(
            entry="conda run -n my-env mytool",
            style="argparse",
        ),
    )
    request = TrialRequest(parameters={})
    argv = adapter._build_argv(request, run_dir=None)
    assert argv[:5] == ["conda", "run", "-n", "my-env", "mytool"]


def test_hashed_run_dir_is_deterministic(tmp_path: Path) -> None:
    spec = HashedRunDirSpec(root=tmp_path, arg_name="--out")
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="/bin/true", style="argparse"),
        hashed_run_dir=spec,
    )
    request = TrialRequest(parameters={"alpha": 0.5, "beta": 3})
    a = adapter._resolve_run_dir(request)
    b = adapter._resolve_run_dir(request)
    assert a == b
    assert a is not None and a.parent == tmp_path
    assert len(a.name) == 12


def test_hash_parameters_is_order_invariant() -> None:
    a = hash_parameters([{"alpha": 0.5, "beta": 3}])
    b = hash_parameters([{"beta": 3, "alpha": 0.5}])
    assert a == b


def test_hashed_run_dir_appends_arg_to_argv(tmp_path: Path) -> None:
    spec = HashedRunDirSpec(root=tmp_path, arg_name="--results_dir")
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="/bin/true", style="argparse"),
        hashed_run_dir=spec,
    )
    request = TrialRequest(parameters={"alpha": 0.5})
    run_dir = adapter._resolve_run_dir(request)
    argv = adapter._build_argv(request, run_dir=run_dir)
    assert "--results_dir" in argv
    assert str(run_dir) in argv


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required for the stub executable")
def test_real_subprocess_success_collects_glob_predictions(tmp_path: Path) -> None:
    """End-to-end over a REAL subprocess: a stub that writes a predictions file
    into the injected hashed run dir yields success with the glob collected."""

    stub = tmp_path / "writer.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        'out=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in --out) out="$2"; shift 2;; *) shift;; esac\n'
        "done\n"
        'echo "{}" > "$out/result.pred"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(stub), style="argparse"),
        hashed_run_dir=HashedRunDirSpec(root=tmp_path / "runs", arg_name="--out"),
        predictions_glob="*.pred",
    )
    result = adapter.run_trial(TrialRequest(parameters={"alpha": 0.5}))

    assert result.success is True
    assert len(result.outputs.predictions) == 1
    assert result.outputs.predictions[0].name == "result.pred"
