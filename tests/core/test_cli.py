"""Adapter-level subprocess + package-CLI behavioral coverage (CLI-01/02/03).

Per D-12 these tests use REAL tiny stub executables in ``tmp_path`` (faithful
subprocess / timeout / glob mechanics) and drive three layers:

* the adapter — ``CliToolAdapter.run_trial`` against stubs (nonzero exit,
  timeout, descendant cleanup, termination race, empty/populated glob) and
  ``prepare()`` preflight with the conda enumerator MONKEYPATCHED (hermetic — no
  real conda env);
* the loader — ``load_tool_config`` output-mode validation (explicit
  ``stdout_json`` -> error, unset -> glob, unsupported value -> error);
* the package CLI — ``geodispbench3d.cli.main([...])`` exit-code taxonomy
  (usage 2, clean-error 1, sweep crash exit-1 end-to-end, sweep timeout exit-0,
  all-failed exit-1, rescore/analyze exits, --timeout override, --traceback,
  the narrow clean-error boundary, and rescore --max-trials warn-and-ignore).

The runner/Ax failed-trial -> ``log_trial_failure`` contract is covered in
``tests/core/test_runner_failure.py``; the SWEEP_EXIT_1 test here is a TRUE
end-to-end check driving the REAL ``AxSweepRunner`` + REAL ``CliToolAdapter``
against a real stub ``entry`` (review MEDIUM: not a fully-mocked Ax loop).
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import textwrap
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from geodispbench3d import cli
from geodispbench3d.sweep.runner import SweepRunSummary
from geodispbench3d.sweep.trial_record import (
    DatasetProvenance,
    ToolProvenance,
    trial_record_path,
    write_trial_record,
)
from geodispbench3d.tool.base import ToolPreflightError, TrialRequest
from geodispbench3d.tool.cli_adapter import CliInvocationSpec, CliToolAdapter, HashedRunDirSpec
from geodispbench3d.tool.loader import load_tool_config

requires_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash required for stub executables"
)

# ---------------------------------------------------------------------------
# Stub-executable + polling helpers
# ---------------------------------------------------------------------------


def _write_stub(path: Path, body: str) -> Path:
    """Write a `chmod +x` bash stub with a shebang (D-12 / 03-PATTERNS)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -u\n" + body)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def wait_until_process_dead(pid: int, deadline: float) -> bool:
    """Poll ``os.kill(pid, 0)`` until the process is gone or ``deadline`` passes.

    Termination / reaping is asynchronous (review MEDIUM: an immediate
    ``os.kill(pid, 0)`` right after a timeout is flaky), so this bounded poll
    treats ``ProcessLookupError`` / ESRCH ``OSError`` as "dead" and returns
    ``True`` the moment the descendant disappears.
    """

    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, OSError):
            return True
        time.sleep(0.05)
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OSError):
        return True
    return False


# ---------------------------------------------------------------------------
# Section A (Task 2): adapter-level subprocess contract
# ---------------------------------------------------------------------------


@requires_bash
def test_run_trial_nonzero_exit_is_failure(tmp_path: Path) -> None:
    stub = _write_stub(tmp_path / "crash.sh", "exit 3\n")
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(stub), style="argparse"),
    )
    result = adapter.run_trial(TrialRequest(parameters={}))
    assert result.success is False
    assert result.error_kind == "nonzero_exit"
    assert "3" in (result.error or "")


@requires_bash
def test_run_trial_timeout_is_failure(tmp_path: Path) -> None:
    stub = _write_stub(tmp_path / "slow.sh", "sleep 5\n")
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(stub), style="argparse"),
        timeout=0.5,
    )
    result = adapter.run_trial(TrialRequest(parameters={}))
    assert result.success is False
    assert result.error == "timeout"
    assert result.error_kind == "timeout"


@requires_bash
def test_run_trial_timeout_reaps_descendant_process(tmp_path: Path) -> None:
    """A wrapper stub that spawns a child (approximating conda-run topology) must
    have its descendant reaped on timeout — asserted via a bounded poll, not an
    immediate os.kill (review MEDIUM: async reaping is flaky)."""

    childpid_file = tmp_path / "childpid.txt"
    stub = _write_stub(
        tmp_path / "wrapper.sh",
        f'sleep 30 &\necho $! > "{childpid_file}"\nwait\n',
    )
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(stub), style="argparse"),
        timeout=0.5,
    )
    result = adapter.run_trial(TrialRequest(parameters={}))
    assert result.success is False
    assert result.error_kind == "timeout"

    assert childpid_file.is_file(), "wrapper stub never recorded its child pid"
    child_pid = int(childpid_file.read_text().strip())
    # The process-group SIGKILL must have reaped the descendant sleep.
    assert wait_until_process_dead(child_pid, deadline=time.monotonic() + 5.0), (
        f"descendant pid {child_pid} survived the timeout kill"
    )


@requires_bash
def test_run_trial_timeout_robust_to_process_lookup_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If termination itself races (os.killpg raises ProcessLookupError because
    the group already exited), run_trial STILL returns a clean timeout failure
    and no exception escapes (guards the swallow added in Plan 01)."""

    import geodispbench3d.tool.cli_adapter as cli_adapter_mod

    def _raise_plE(*_args: Any, **_kwargs: Any) -> None:
        raise ProcessLookupError("group already exited")

    monkeypatch.setattr(cli_adapter_mod.os, "killpg", _raise_plE)

    # A short sleep so the swallowed-kill path's follow-up communicate() (no
    # timeout) returns promptly when the stub exits on its own.
    stub = _write_stub(tmp_path / "slow.sh", "sleep 1\n")
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(stub), style="argparse"),
        timeout=0.3,
    )
    result = adapter.run_trial(TrialRequest(parameters={}))
    assert result.success is False
    assert result.error == "timeout"
    assert result.error_kind == "timeout"


@requires_bash
def test_run_trial_empty_glob_fails_populated_glob_succeeds(tmp_path: Path) -> None:
    """A configured predictions_glob matching zero files fails the trial (D-07);
    a populated glob succeeds, and an empty figures_glob stays non-fatal."""

    # (a) empty glob -> missing_output
    noop = _write_stub(tmp_path / "noop.sh", "exit 0\n")
    adapter_empty = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(noop), style="argparse"),
        hashed_run_dir=HashedRunDirSpec(root=tmp_path / "runs_empty", arg_name="--out"),
        predictions_glob="*.pred",
    )
    empty = adapter_empty.run_trial(TrialRequest(parameters={}))
    assert empty.success is False
    assert empty.error_kind == "missing_output"

    # (b) populated predictions glob + empty figures glob -> success
    writer = _write_stub(
        tmp_path / "writer.sh",
        'out=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in\n'
        '    --out) out="$2"; shift 2;;\n'
        "    *) shift;;\n"
        "  esac\n"
        "done\n"
        'echo "{}" > "$out/result.pred"\n',
    )
    adapter_ok = CliToolAdapter(
        invocation=CliInvocationSpec(entry=str(writer), style="argparse"),
        hashed_run_dir=HashedRunDirSpec(root=tmp_path / "runs_ok", arg_name="--out"),
        predictions_glob="*.pred",
        figures_glob="*.fig",
    )
    ok = adapter_ok.run_trial(TrialRequest(parameters={}))
    assert ok.success is True
    assert len(ok.outputs.predictions) == 1
    assert ok.outputs.figures == ()


# ---------------------------------------------------------------------------
# Section B (Task 2): hermetic preflight (conda enumerator monkeypatched)
# ---------------------------------------------------------------------------


def test_prepare_missing_binary_raises_preflight_error() -> None:
    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="/nonexistent/tool", style="argparse"),
        remediation="install the tool",
    )
    with pytest.raises(ToolPreflightError) as ei:
        adapter.prepare()
    msg = str(ei.value)
    assert "not found on PATH" in msg
    assert "install the tool" in msg  # remediation surfaced via __str__


def test_prepare_missing_conda_env_raises_preflight_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A conda-run entry naming an absent env raises ToolPreflightError with the
    enumerator MONKEYPATCHED — no real conda required (review MEDIUM, D-12)."""

    monkeypatch.setattr(
        "geodispbench3d.tool.cli_adapter.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    monkeypatch.setattr(CliToolAdapter, "_conda_env_names", lambda self: {"base"})

    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="conda run -n no-such-env mytool", style="argparse"),
        remediation="conda env create -f env.yml",
    )
    with pytest.raises(ToolPreflightError) as ei:
        adapter.prepare()
    msg = str(ei.value)
    assert "no-such-env" in msg
    assert "conda env create" in msg


@pytest.mark.parametrize("failure", ["nonzero", "malformed_json", "timeout"])
def test_conda_enumerator_failure_modes_map_to_preflight_error(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Every conda-enumeration failure mode (nonzero exit / malformed JSON /
    TimeoutExpired) maps to ToolPreflightError — no raw subprocess/JSON exception
    escapes (review MEDIUM)."""

    import subprocess as sp

    import geodispbench3d.tool.cli_adapter as cli_adapter_mod

    monkeypatch.setattr(
        "geodispbench3d.tool.cli_adapter.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Proc:
        def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(*_args: Any, **_kwargs: Any) -> Any:
        if failure == "nonzero":
            return _Proc(returncode=1, stdout="", stderr="conda boom")
        if failure == "malformed_json":
            return _Proc(returncode=0, stdout="not json {[")
        raise sp.TimeoutExpired(cmd="conda env list --json", timeout=30.0)

    monkeypatch.setattr(cli_adapter_mod.subprocess, "run", fake_run)

    adapter = CliToolAdapter(
        invocation=CliInvocationSpec(entry="conda run -n some-env mytool", style="argparse"),
    )
    with pytest.raises(ToolPreflightError):
        adapter.prepare()


# ---------------------------------------------------------------------------
# Section C (Task 2): loader output-mode validation
# ---------------------------------------------------------------------------


def _write_tool_yaml(path: Path, outputs_block: str) -> Path:
    path.write_text(
        "id: stub-tool\n"
        "kind: cli\n"
        "entry: /bin/true\n"
        "invocation: {style: argparse}\n" + outputs_block
    )
    return path


def test_loader_unset_outputs_from_defaults_to_glob(tmp_path: Path) -> None:
    yaml_path = _write_tool_yaml(tmp_path / "tool.yaml", "outputs:\n  predictions_glob: '*.json'\n")
    config = load_tool_config(yaml_path)
    assert isinstance(config.adapter, CliToolAdapter)
    assert config.adapter._outputs_from == "glob"


def test_loader_explicit_stdout_json_is_rejected(tmp_path: Path) -> None:
    yaml_path = _write_tool_yaml(tmp_path / "tool.yaml", "outputs:\n  from: stdout_json\n")
    with pytest.raises(ValueError) as ei:
        load_tool_config(yaml_path)
    assert "stdout_json" in str(ei.value)
    assert "glob" in str(ei.value)


def test_loader_unsupported_fixed_path_is_rejected(tmp_path: Path) -> None:
    yaml_path = _write_tool_yaml(tmp_path / "tool.yaml", "outputs:\n  from: fixed_path\n")
    with pytest.raises(ValueError) as ei:
        load_tool_config(yaml_path)
    assert "fixed_path" in str(ei.value)


# ---------------------------------------------------------------------------
# Shared suite / run-dir builders for the main()-level tests (Task 3)
# ---------------------------------------------------------------------------

_GT = "label,x1,y1,z1,x2,y2,z2\nP,0,0,0,1,0,0\n"
_DATASET_ONE = textwrap.dedent("""\
    id: stub-dataset
    cases:
      - name: only-case
        scans: []
        ground_truth: {kind: point_displacements, path: gt.csv}
    """)
_METRICS = textwrap.dedent("""\
    objective_metrics:
      - id: median_displacement_error
        fn: geodispbench3d.metrics.builtins:median_displacement_error
        needs: [prediction, ground_truth]
        gt_kinds: [point_displacements]
    record_metrics: []
    """)

# Perfect parser: echoes GT as the prediction (objective error 0 -> finite).
_GOOD_PARSER = (
    "def parse(*, outputs, ground_truth, options=None, **_):\n"
    "    return {'per_point': [\n"
    "        {'label': p.label, 'vector': list(p.movement_vector), 'source_count': 1}\n"
    "        for p in ground_truth\n"
    "    ]}\n"
)
# Parser that produces nothing usable -> drives a rescore parser-miss.
_NONE_PARSER = "def parse(*, outputs, ground_truth, options=None, **_):\n    return None\n"


def _install_parser_pkg(tmp_path: Path, name: str, body: str) -> str:
    pkg = tmp_path / name
    if not pkg.exists():
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(body)
    if str(tmp_path) not in sys.path:
        sys.path.insert(0, str(tmp_path))
    return name


def _build_e2e_sweep_suite(
    root: Path,
    entry: str,
    *,
    timeout_seconds: float | None = None,
    remediation: str | None = None,
    max_trials: int = 2,
    parser_pkg: str = "e2e_good_parser_pkg",
    parser_body: str = _GOOD_PARSER,
) -> Path:
    """A real sweep suite: tool.yaml ``entry`` points at a stub; hashed run dir
    feeds ``--out`` to the stub; predictions are collected by glob."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "gt.csv").write_text(_GT)
    (root / "dataset.yaml").write_text(_DATASET_ONE)
    (root / "metrics.yaml").write_text(_METRICS)
    _install_parser_pkg(root, parser_pkg, parser_body)

    exec_block = (
        f"execution:\n  timeout_seconds: {timeout_seconds}\n" if timeout_seconds is not None else ""
    )
    remediation_block = f"remediation: {remediation!r}\n" if remediation is not None else ""
    (root / "tool.yaml").write_text(
        "id: stub-tool\n"
        "kind: cli\n"
        f"entry: {entry}\n"
        "invocation: {style: argparse}\n"
        "outputs:\n"
        "  hashed_run_dir: {root: runs, arg_name: --out}\n"
        '  predictions_glob: "*.pred"\n'
        + exec_block
        + remediation_block
        # A real range parameter gives Ax a non-degenerate search space (an empty
        # space exhausts Sobol after one draw). The stubs ignore the rendered
        # --alpha flag.
        + "hyperparameters:\n"
        + "  - name: alpha\n"
        + "    type: range\n"
        + "    value_type: float\n"
        + "    lower: 0.0\n"
        + "    upper: 1.0\n"
        + f"output_parser:\n  fn: {parser_pkg}:parse\n  options: {{}}\n"
    )
    suite_path = root / "suite.yaml"
    suite_path.write_text(
        "id: stub-suite\n"
        "tool: tool.yaml\n"
        "dataset: dataset.yaml\n"
        "metrics: metrics.yaml\n"
        "search:\n"
        f"  max_trials: {max_trials}\n"
        f"  sobol_trials: {max_trials}\n"
        "  objective: median_displacement_error\n"
        "  minimize: true\n"
        "results:\n"
        "  run_dir_root: runs\n"
    )
    return suite_path


def _build_rescore_suite(root: Path, *, parser_pkg: str, parser_body: str) -> Path:
    """A suite (no real tool entry needed — rescore skips the tool) over which we
    fabricate run dirs by hand."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "gt.csv").write_text(_GT)
    (root / "dataset.yaml").write_text(_DATASET_ONE)
    (root / "metrics.yaml").write_text(_METRICS)
    _install_parser_pkg(root, parser_pkg, parser_body)
    (root / "tool.yaml").write_text(
        "id: stub-tool\n"
        "kind: cli\n"
        "entry: /bin/true\n"
        "invocation: {style: argparse}\n"
        f"output_parser:\n  fn: {parser_pkg}:parse\n  options: {{}}\n"
    )
    suite_path = root / "suite.yaml"
    suite_path.write_text(
        "id: stub-suite\n"
        "tool: tool.yaml\n"
        "dataset: dataset.yaml\n"
        "metrics: metrics.yaml\n"
        "search:\n"
        "  max_trials: 1\n"
        "  sobol_trials: 1\n"
        "  objective: median_displacement_error\n"
        "  minimize: true\n"
        "results:\n"
        "  run_dir_root: runs\n"
    )
    return suite_path


def _fabricate_run_dir(root: Path, run_hash: str, *, status: str) -> Path:
    run_dir = root / "runs" / run_hash
    run_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "status": status,
        "parameters": {"alpha": 0.5},
        "metrics": {"median_displacement_error": 0.1},
        "runtime_seconds": 1.0,
        "run_hash": run_hash,
        "predictions": [],
        "figures": [],
        "tool": asdict(ToolProvenance(id="stub-tool")),
        "dataset": asdict(DatasetProvenance(id="stub-dataset", case="only-case")),
        "parser": {"fn": "x:parse", "options": {}},
    }
    if status != "success":
        record["error"] = "boom"
    write_trial_record(trial_record_path(run_dir), record)
    return run_dir


# ---------------------------------------------------------------------------
# Section D (Task 3): usage / clean-error / traceback / subcommand
# ---------------------------------------------------------------------------


def test_unknown_flag_is_usage_error_exit_2() -> None:
    with pytest.raises(SystemExit) as ei:
        cli.main(["run", "x", "--badflag"])
    assert ei.value.code == 2


def test_missing_suite_is_clean_error_exit_1(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["run", "/nonexistent/suite.yaml"])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("error:") or "\nerror:" in err
    # A clean one-line error, not a raw traceback.
    assert "Traceback (most recent call last)" not in err


def test_traceback_flag_reraises_loader_error() -> None:
    with pytest.raises(FileNotFoundError):
        cli.main(["run", "/nonexistent/suite.yaml", "--traceback"])


def test_rescore_only_flag_rejected_on_run_accepted_on_rescore(tmp_path: Path) -> None:
    suite = _build_rescore_suite(
        tmp_path / "sub", parser_pkg="e2e_good_parser_pkg", parser_body=_GOOD_PARSER
    )
    _fabricate_run_dir(tmp_path / "sub", "aaaaaaaaaaaa", status="success")

    # run does NOT accept a rescore-only flag -> argparse usage error (exit 2).
    with pytest.raises(SystemExit) as ei:
        cli.main(["run", str(suite), "--use-prediction-cache"])
    assert ei.value.code == 2

    # rescore DOES accept it and completes with an int exit code.
    rc = cli.main(["rescore", str(suite), "--use-prediction-cache"])
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# Section E (Task 3): rescore / analyze exit codes (F-06)
# ---------------------------------------------------------------------------


def test_rescore_over_failed_trial_exits_0(tmp_path: Path) -> None:
    """A pre-existing skipped_failed run dir is NOT an error of this pass; a
    healthy run dir scores cleanly -> exit 0 (F-06)."""

    suite = _build_rescore_suite(
        tmp_path / "ok", parser_pkg="e2e_good_parser_pkg", parser_body=_GOOD_PARSER
    )
    _fabricate_run_dir(tmp_path / "ok", "aaaaaaaaaaaa", status="success")
    _fabricate_run_dir(tmp_path / "ok", "bbbbbbbbbbbb", status="failure")
    rc = cli.main(["rescore", str(suite)])
    assert rc == 0


def test_rescore_genuine_parser_miss_exits_1(tmp_path: Path) -> None:
    """A genuine parser miss (the suite parser produces nothing) -> exit 1."""

    suite = _build_rescore_suite(
        tmp_path / "miss", parser_pkg="e2e_none_parser_pkg", parser_body=_NONE_PARSER
    )
    _fabricate_run_dir(tmp_path / "miss", "aaaaaaaaaaaa", status="success")
    rc = cli.main(["rescore", str(suite)])
    assert rc == 1


def test_rescore_max_trials_warns_and_completes(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """`rescore --max-trials N` logs the warn-and-ignore line and still completes
    (no run-dir cap; review LOW / D-09)."""

    import logging

    suite = _build_rescore_suite(
        tmp_path / "mt", parser_pkg="e2e_good_parser_pkg", parser_body=_GOOD_PARSER
    )
    _fabricate_run_dir(tmp_path / "mt", "aaaaaaaaaaaa", status="success")
    with caplog.at_level(logging.WARNING, logger="geodispbench3d.cli"):
        rc = cli.main(["rescore", str(suite), "--max-trials", "5"])
    assert rc in (0, 1)
    assert any("max-trials" in r.getMessage() for r in caplog.records)


def _build_analyze_config(
    root: Path, *, case_names: list[str], predictions: list[dict[str, Any]]
) -> Path:
    """An analysis.yaml + a pcache populated with the given prediction specs.

    Each prediction spec is ``{tool, run_hash, prov_case, corrupt}``; a corrupt
    spec writes invalid JSON (skipped_unreadable), otherwise a valid prediction
    is written with provenance dataset.case = ``prov_case``.
    """

    from geodispbench3d.results.predictions_cache import write_prediction

    root.mkdir(parents=True, exist_ok=True)
    (root / "gt.csv").write_text(_GT)
    cases_yaml = "".join(
        f"  - name: {c}\n    scans: []\n    ground_truth: {{kind: point_displacements, path: gt.csv}}\n"
        for c in case_names
    )
    (root / "dataset.yaml").write_text("id: stub-dataset\ncases:\n" + cases_yaml)
    (root / "metrics.yaml").write_text(_METRICS)

    pcache = root / "pcache"
    for spec in predictions:
        if spec.get("corrupt"):
            d = pcache / spec["tool"] / "stub-dataset" / case_names[0]
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{spec['run_hash']}.json").write_text("{ not valid json", encoding="utf-8")
            continue
        write_prediction(
            pcache,
            tool_id=spec["tool"],
            dataset_id="stub-dataset",
            case=case_names[0],
            run_hash=spec["run_hash"],
            prediction={
                "per_point": [{"label": "P", "vector": [1.0, 0.0, 0.0], "source_count": 1}]
            },
            provenance={
                "tool": {"id": spec["tool"]},
                "dataset": {"id": "stub-dataset", "case": spec["prov_case"]},
            },
        )

    analysis_path = root / "analysis.yaml"
    analysis_path.write_text(
        "id: postanalysis-stub\n"
        "dataset: dataset.yaml\n"
        "metrics: metrics.yaml\n"
        "predictions:\n"
        "  - root: pcache\n"
        "pass_id: smoke\n"
    )
    return analysis_path


def test_analyze_skipped_no_case_exits_0(tmp_path: Path) -> None:
    """A benign skipped_no_case (prediction for an unknown case in a multi-case
    dataset) does NOT make analyze exit 1."""

    analysis = _build_analyze_config(
        tmp_path / "nocase",
        case_names=["case-a", "case-b"],
        predictions=[{"tool": "toolx", "run_hash": "r1", "prov_case": "ghost"}],
    )
    rc = cli.main(["analyze", str(analysis)])
    assert rc == 0


def test_analyze_skipped_unreadable_exits_1(tmp_path: Path) -> None:
    """A corrupt (unreadable) prediction makes analyze exit 1."""

    analysis = _build_analyze_config(
        tmp_path / "unreadable",
        case_names=["only-case"],
        predictions=[{"tool": "toolx", "run_hash": "r1", "corrupt": True}],
    )
    rc = cli.main(["analyze", str(analysis)])
    assert rc == 1


# ---------------------------------------------------------------------------
# Section F (Task 3): TRUE end-to-end sweep exit codes (review HIGH #3 + MEDIUM)
# ---------------------------------------------------------------------------


@requires_bash
def test_sweep_crash_exits_1_clean_exits_0(tmp_path: Path) -> None:
    """TRUE end-to-end: REAL AxSweepRunner + REAL CliToolAdapter against a real
    stub entry. A genuine CRASH trial (nonzero exit) after preflight succeeds
    returns 1; a clean sweep (stub writes valid predictions) returns 0."""

    crash = _write_stub(tmp_path / "crash" / "crash.sh", "exit 3\n")
    crash_suite = _build_e2e_sweep_suite(tmp_path / "crash", str(crash), parser_pkg="e2e_crash_pkg")
    assert cli.main(["run", str(crash_suite)]) == 1

    writer = _write_stub(
        tmp_path / "clean" / "writer.sh",
        'out=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in --out) out="$2"; shift 2;; *) shift;; esac\n'
        "done\n"
        'echo "{}" > "$out/result.pred"\n',
    )
    clean_suite = _build_e2e_sweep_suite(
        tmp_path / "clean", str(writer), parser_pkg="e2e_clean_pkg"
    )
    assert cli.main(["run", str(clean_suite)]) == 0


@requires_bash
def test_sweep_some_success_plus_timeout_exits_0(tmp_path: Path) -> None:
    """SWEEP_TIMEOUT_EXIT_0 (D-05): a sweep with at least one successful trial AND
    a timeout trial returns 0 — an individual timeout is non-fatal for exit."""

    root = tmp_path / "mix"
    marker = root / "marker.flag"
    # First invocation creates the marker and hangs (-> timeout); every later
    # invocation finds the marker and writes a valid prediction (-> success).
    stub = _write_stub(
        root / "mixed.sh",
        'out=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in --out) out="$2"; shift 2;; *) shift;; esac\n'
        "done\n"
        f'marker="{marker}"\n'
        'if [ ! -f "$marker" ]; then touch "$marker"; sleep 30; fi\n'
        'echo "{}" > "$out/result.pred"\n',
    )
    suite = _build_e2e_sweep_suite(root, str(stub), parser_pkg="e2e_mix_pkg", max_trials=2)
    # --timeout 1 kills the first (hanging) trial after ~1s; the second succeeds.
    assert cli.main(["run", str(suite), "--timeout", "1"]) == 0


@requires_bash
def test_sweep_all_failed_and_timeouts_only_exit_1(tmp_path: Path) -> None:
    """SWEEP_ALL_FAILED_EXIT_1 (RESOLVED-A): every-trial-fails returns 1, and a
    timeouts-only-zero-success sweep also returns 1 (main() does not crash on the
    no-best-trial path)."""

    crash = _write_stub(tmp_path / "allfail" / "crash.sh", "exit 4\n")
    allfail_suite = _build_e2e_sweep_suite(
        tmp_path / "allfail", str(crash), parser_pkg="e2e_allfail_pkg"
    )
    assert cli.main(["run", str(allfail_suite)]) == 1

    sleeper = _write_stub(tmp_path / "alltimeout" / "slow.sh", "sleep 30\n")
    timeout_suite = _build_e2e_sweep_suite(
        tmp_path / "alltimeout", str(sleeper), parser_pkg="e2e_alltimeout_pkg", max_trials=2
    )
    assert cli.main(["run", str(timeout_suite), "--timeout", "1"]) == 1


def test_run_missing_conda_env_exits_1_with_remediation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """main(): a suite whose entry names a missing conda env exits 1 with the
    remediation in stderr (enumerator monkeypatched, no real conda)."""

    monkeypatch.setattr(
        "geodispbench3d.tool.cli_adapter.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    monkeypatch.setattr(CliToolAdapter, "_conda_env_names", lambda self: {"base"})

    suite = _build_e2e_sweep_suite(
        tmp_path / "preflight",
        "conda run -n no-such-env mytool",
        remediation="conda env create -f env.yml",
        parser_pkg="e2e_preflight_pkg",
    )
    rc = cli.main(["run", str(suite)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no-such-env" in err
    assert "conda env create" in err


# ---------------------------------------------------------------------------
# Section G (Task 3): --timeout override seam + narrow clean-error boundary
# ---------------------------------------------------------------------------


def test_timeout_override_reaches_adapter_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run --timeout N` overrides the YAML execution.timeout_seconds via
    set_timeout_override, and `--timeout 0` resolves to no-timeout (D-04). The
    resolved adapter timeout is asserted via the public seam (the Ax loop is
    stubbed so no real sweep runs)."""

    captured: list[float | None] = []

    class _CapturingRunner:
        def __init__(self, *, adapter: Any, **_kwargs: Any) -> None:
            captured.append(getattr(adapter, "_timeout", "missing"))  # type: ignore[arg-type]

        def run_with_suite(self, *, suite: Any, max_trials: int, on_record_rows: Any = None) -> Any:
            return SweepRunSummary(
                best_trial=object(),
                objective_name="median_displacement_error",
                successful_trials=1,
            )

    monkeypatch.setattr("geodispbench3d.sweep.runner.AxSweepRunner", _CapturingRunner)

    # YAML sets a sentinel 999; --timeout 5 must win.
    suite5 = _build_e2e_sweep_suite(
        tmp_path / "to5", "/bin/true", timeout_seconds=999, parser_pkg="e2e_to5_pkg"
    )
    assert cli.main(["run", str(suite5), "--timeout", "5"]) == 0
    assert captured[-1] == 5.0

    # --timeout 0 is honored (is-not-None precedence) and means no timeout.
    suite0 = _build_e2e_sweep_suite(
        tmp_path / "to0", "/bin/true", timeout_seconds=999, parser_pkg="e2e_to0_pkg"
    )
    assert cli.main(["run", str(suite0), "--timeout", "0"]) == 0
    assert captured[-1] == 0.0
    # 0.0 resolves to "no timeout" under the adapter's <= 0 semantics.
    effective = captured[-1] if (captured[-1] is not None and captured[-1] > 0) else None
    assert effective is None


def test_unexpected_runtime_valueerror_keeps_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NARROW_WRAPPER_BOUNDARY (review MEDIUM): an UNEXPECTED ValueError raised
    AFTER loaders/preflight succeed is NOT flattened to a one-line exit-1 — it
    propagates with its traceback (without --traceback), proving the clean-error
    wrapper is scoped to loaders/preflight only."""

    class _BoomRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def run_with_suite(self, *, suite: Any, max_trials: int, on_record_rows: Any = None) -> Any:
            raise ValueError("unexpected runtime boom from a metric/Ax")

    monkeypatch.setattr("geodispbench3d.sweep.runner.AxSweepRunner", _BoomRunner)

    suite = _build_e2e_sweep_suite(tmp_path / "boom", "/bin/true", parser_pkg="e2e_boom_pkg")
    with pytest.raises(ValueError, match="unexpected runtime boom"):
        cli.main(["run", str(suite)])
