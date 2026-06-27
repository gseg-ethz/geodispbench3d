"""F-20 characterization net for ``geodispbench3d.sweep.runner``.

This test pins the CURRENT observable behavior of :class:`AxSweepRunner` so the
F-01 / F-13 / F-05 / F-08 changes in later waves land against a deterministic,
Ax-free safety net. It is a characterization (regression) test: every
assertion encodes today's behavior of the UNMODIFIED runner, not an aspiration.

Harness design (mirrors ``tests/core/test_rescore.py``):

* ``FakeAxClient`` — a 5-method duck-typed stand-in for ``ax_client.AxClient``.
  It is installed by monkeypatching ``geodispbench3d.sweep.runner.AxClient``
  BEFORE the runner is constructed, because the runner calls ``AxClient(...)``
  unconditionally in ``__init__`` (runner.py:69). ``create_experiment`` carries
  an EXPLICIT keyword signature (``parameters``, ``name``, ``objective_name``,
  ``minimize``) so the runner's ``inspect.signature`` dispatch (runner.py:76-136)
  exercises the real ``parameters`` / ``objective_name`` / ``minimize`` branch
  rather than the unsupported-signature fallback.
* ``StubAdapter`` — a ``ToolAdapter`` returning a canned ``TrialResult`` whose
  per-case ``prediction`` is supplied by the test, and which records that its
  ``prepare`` / ``teardown`` lifecycle hooks ran.
* An inline-YAML suite built in ``tmp_path`` (one ``runner_stub_pkg:parse``
  parser that simply echoes the adapter's canned prediction).

No real ``AxClient`` is used (heavy + nondeterministic). No literal ``"Z"``
timestamp suffix is asserted anywhere — F-09 will switch isoformat output to
``+00:00`` (see 02-RESEARCH Pitfall 2).
"""

from __future__ import annotations

import json
import sys
import textwrap
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from geodispbench3d.metrics.registry import MetricRegistry
from geodispbench3d.suite.loader import load_suite
from geodispbench3d.sweep import runner as runner_mod
from geodispbench3d.sweep.parameters import SweepConfig, SweepParameter, build_parameter_specs
from geodispbench3d.sweep.runner import AxSweepRunner, _normalize_trial_data
from geodispbench3d.tool.base import ToolAdapter, TrialOutputs, TrialRequest, TrialResult

# ---------------------------------------------------------------------------
# Fakes / stubs
# ---------------------------------------------------------------------------


class FakeAxClient:
    """Deterministic, Ax-free stand-in for the five methods the runner uses."""

    def __init__(self, *, verbose_logging: bool = False, **_: Any) -> None:
        self.verbose_logging = verbose_logging
        self.created_with: dict[str, Any] | None = None
        self.next_trial_calls = 0
        self.completed: list[dict[str, Any]] = []
        self.failures: list[int] = []
        self.best_sentinel = SimpleNamespace(label="best-trial")

    def create_experiment(
        self,
        *,
        parameters: Any = None,
        name: str | None = None,
        objective_name: str | None = None,
        minimize: bool | None = None,
        **kwargs: Any,
    ) -> None:
        # Explicit keyword names so the runner's inspect.signature dispatch
        # (runner.py:84-136) takes the real ``parameters`` / ``objective_name``
        # / ``minimize`` branch. A bare *args/**kwargs fake would fail that
        # parameter-name detection and silently skip the branch under test.
        self.created_with = {
            "parameters": parameters,
            "name": name,
            "objective_name": objective_name,
            "minimize": minimize,
        }

    def get_next_trial(self) -> tuple[int, dict[str, Any]]:
        index = self.next_trial_calls
        self.next_trial_calls += 1
        return index, {"alpha": 0.5}

    def complete_trial(self, *, trial_index: int, raw_data: Any) -> None:
        self.completed.append({"trial_index": trial_index, "raw_data": raw_data})

    def log_trial_failure(self, *, trial_index: int) -> None:
        self.failures.append(trial_index)

    def get_best_trial(self) -> Any:
        return self.best_sentinel


class StubAdapter(ToolAdapter):
    """ToolAdapter returning a per-case canned prediction via outputs.extras."""

    id = "stub-adapter"
    in_process_safe = True

    def __init__(self, *, run_root: Path, predictions: Mapping[str, list[dict[str, Any]]]) -> None:
        self._run_root = run_root
        self._predictions = predictions
        self.prepare_called = False
        self.teardown_called = False
        self.run_dirs: dict[str, Path] = {}
        self._counter = 0

    def prepare(self) -> None:
        self.prepare_called = True

    def teardown(self) -> None:
        self.teardown_called = True

    def run_trial(self, request: TrialRequest) -> TrialResult:
        case = request.case_name or "no-case"
        self._counter += 1
        run_dir = self._run_root / f"run-{case}-{self._counter}"
        run_dir.mkdir(parents=True, exist_ok=True)
        self.run_dirs[case] = run_dir
        per_point = list(self._predictions.get(case, []))
        outputs = TrialOutputs(run_dir=run_dir, extras={"prediction": {"per_point": per_point}})
        return TrialResult(outputs=outputs, scalar_metrics={}, duration_seconds=0.01)


# ---------------------------------------------------------------------------
# Suite bootstrap (inline YAML in tmp_path, mirrors test_rescore.py)
# ---------------------------------------------------------------------------


def _bootstrap_suite(tmp_path: Path, case_names: list[str]) -> Any:
    """Build a minimal multi-case suite. Each case GT is one point P:(0,0,0)->(1,0,0)."""

    # Per-case ground-truth CSV: single labeled point, movement (1,0,0), |v|=1.
    for case in case_names:
        (tmp_path / f"gt_{case}.csv").write_text("label,x1,y1,z1,x2,y2,z2\nP,0,0,0,1,0,0\n")

    cases_yaml = "".join(
        textwrap.dedent(f"""\
          - name: {case}
            scans: []
            ground_truth: {{kind: point_displacements, path: gt_{case}.csv}}
        """)
        for case in case_names
    )
    (tmp_path / "dataset.yaml").write_text("id: stub-dataset\ncases:\n" + cases_yaml)

    (tmp_path / "metrics.yaml").write_text(
        textwrap.dedent("""\
        objective_metrics:
          - id: median_displacement_error
            fn: geodispbench3d.metrics.builtins:median_displacement_error
            needs: [prediction, ground_truth]
            gt_kinds: [point_displacements]
        record_metrics:
          - id: per_point
            fn: geodispbench3d.metrics.builtins:per_point_displacement_record
            needs: [prediction, ground_truth, case_meta, trial_meta]
            gt_kinds: [point_displacements]
        """)
    )

    # Stub parser package: echo the adapter's canned prediction from extras.
    # Distinct name from test_rescore's ``stub_pkg`` so the two modules never
    # collide in sys.modules (import-cache cross-contamination).
    pkg_dir = tmp_path / "runner_stub_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text(
        "def parse(*, outputs, ground_truth, options=None, **_):\n"
        "    return outputs.extras.get('prediction', {'per_point': []})\n"
    )
    if str(tmp_path) not in sys.path:
        sys.path.insert(0, str(tmp_path))

    (tmp_path / "tool.yaml").write_text(
        textwrap.dedent("""\
        id: stub-tool
        kind: cli
        entry: /bin/true
        invocation: {style: argparse}
        output_parser:
          fn: runner_stub_pkg:parse
          options: {}
        """)
    )
    suite_yaml = tmp_path / "suite.yaml"
    suite_yaml.write_text(
        textwrap.dedent("""\
        id: stub-suite
        tool: tool.yaml
        dataset: dataset.yaml
        metrics: metrics.yaml
        search:
          max_trials: 2
          sobol_trials: 1
          objective: median_displacement_error
          minimize: true
        results:
          run_dir_root: runs
          predictions_root: pcache
        """)
    )
    return load_suite(suite_yaml)


def _make_runner(
    monkeypatch: pytest.MonkeyPatch, adapter: ToolAdapter
) -> tuple[AxSweepRunner, FakeAxClient]:
    """Install FakeAxClient BEFORE construction, then build the runner over it."""

    monkeypatch.setattr(runner_mod, "AxClient", FakeAxClient)
    sweep_config = SweepConfig(
        parameters=[
            SweepParameter(name="alpha", kind="range", value_type="float", lower=0.0, upper=1.0)
        ],
        max_trials=2,
        sobol_trials=1,
        objective_name="median_displacement_error",
        minimize=True,
    )
    parameter_specs = build_parameter_specs(sweep_config)
    runner = AxSweepRunner(
        adapter=adapter,
        sweep_config=sweep_config,
        parameter_specs=parameter_specs,
        objective_name="median_displacement_error",
        minimize=True,
    )
    fake = runner._ax  # the FakeAxClient the constructor built
    assert isinstance(fake, FakeAxClient)
    return runner, fake


# ---------------------------------------------------------------------------
# Task 1: trial loop + adapter teardown + _normalize_trial_data shapes
# ---------------------------------------------------------------------------


def test_create_experiment_dispatch_takes_named_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The runner's inspect.signature dispatch routes through the named branch."""

    adapter = StubAdapter(run_root=tmp_path / "out", predictions={})
    _runner, fake = _make_runner(monkeypatch, adapter)

    assert fake.created_with is not None
    assert fake.created_with["objective_name"] == "median_displacement_error"
    assert fake.created_with["minimize"] is True
    assert fake.created_with["name"] == "geodispbench3d_sweep"
    # The parameter specs flowed through the ``parameters=`` keyword branch.
    assert isinstance(fake.created_with["parameters"], list)
    assert fake.created_with["parameters"][0]["name"] == "alpha"


def test_trial_loop_happy_path_and_teardown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N trials flow get_next_trial -> executor -> complete_trial; teardown runs."""

    suite = _bootstrap_suite(tmp_path, ["only"])
    adapter = StubAdapter(
        run_root=tmp_path / "out",
        predictions={"only": [{"label": "P", "vector": [1.4, 0.0, 0.0]}]},
    )
    runner, fake = _make_runner(monkeypatch, adapter)

    best = runner.run_with_suite(suite=suite, max_trials=3)

    # Prepare ran once before the loop; teardown ran via the finally even on
    # the all-success path (runner.py:218-219).
    assert adapter.prepare_called is True
    assert adapter.teardown_called is True

    # Three trials, three completions, zero failures.
    assert fake.next_trial_calls == 3
    assert len(fake.completed) == 3
    assert fake.failures == []

    # Each completion carried the aggregated scalar dict (single-case
    # short-circuit -> that case's objective, error |1.4 - 1| = 0.4).
    for entry in fake.completed:
        assert "median_displacement_error" in entry["raw_data"]
        assert entry["raw_data"]["median_displacement_error"] == pytest.approx(0.4)

    # get_best_trial's return propagates out of run_with_suite unchanged.
    assert best is fake.best_sentinel


def test_normalize_trial_data_tuple_int_dict() -> None:
    """The (int, dict) tuple shape -> (index, params)."""

    index, params = _normalize_trial_data((7, {"alpha": 0.25}))
    assert index == 7
    assert params == {"alpha": 0.25}


def test_normalize_trial_data_object_attributes() -> None:
    """Objects exposing .trial_index / .parameters are normalized.

    The runner walks the items of the trial-data tuple; one item carries
    ``.trial_index`` (runner.py:393) and the other ``.parameters``
    (runner.py:399).
    """

    ti_obj = SimpleNamespace(trial_index=3)
    params_obj = SimpleNamespace(parameters={"alpha": 0.9})
    index, params = _normalize_trial_data((ti_obj, params_obj))
    assert index == 3
    assert params == {"alpha": 0.9}


def test_normalize_trial_data_unparseable_raises_type_error() -> None:
    """Input the runner cannot resolve to (index, params) raises TypeError."""

    with pytest.raises(TypeError):
        _normalize_trial_data(object())


# ---------------------------------------------------------------------------
# Task 2: cross-case aggregation, partial-failure NaN path, provenance stamping
# ---------------------------------------------------------------------------

# Predictions chosen so the objective (median_displacement_error vs GT |v|=1)
# is the exact error of the single labeled point P:
#   vector (1.4,0,0) -> error 0.4 ; (1.6,0,0) -> error 0.6 ; [] -> NaN.
_PRED_ERR_04 = [{"label": "P", "vector": [1.4, 0.0, 0.0]}]
_PRED_ERR_06 = [{"label": "P", "vector": [1.6, 0.0, 0.0]}]
_PRED_NAN: list[dict[str, Any]] = []  # no labeled points -> metric returns NaN


def test_single_case_aggregation_short_circuits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One case -> _evaluate_across_cases returns that case's scalar dict unchanged."""

    suite = _bootstrap_suite(tmp_path, ["solo"])
    adapter = StubAdapter(run_root=tmp_path / "out", predictions={"solo": _PRED_ERR_04})
    runner, _fake = _make_runner(monkeypatch, adapter)

    aggregated = runner._evaluate_across_cases(
        {"alpha": 0.5}, list(suite.dataset.cases), suite, MetricRegistry(), 0, None
    )

    assert set(aggregated) == {"median_displacement_error"}
    assert aggregated["median_displacement_error"] == pytest.approx(0.4)


def test_multi_case_aggregation_means_finite_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-case all-finite -> per-key mean across cases (0.4, 0.6 -> 0.5)."""

    suite = _bootstrap_suite(tmp_path, ["c1", "c2"])
    adapter = StubAdapter(
        run_root=tmp_path / "out",
        predictions={"c1": _PRED_ERR_04, "c2": _PRED_ERR_06},
    )
    runner, _fake = _make_runner(monkeypatch, adapter)

    aggregated = runner._evaluate_across_cases(
        {"alpha": 0.5}, list(suite.dataset.cases), suite, MetricRegistry(), 0, None
    )

    assert aggregated["median_displacement_error"] == pytest.approx(0.5)


def test_multi_case_partial_failure_ignores_nan_survivor_mean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Partial failure: one NaN case is dropped; mean is taken over finite survivors.

    REGRESSION ANCHOR: this pins the CURRENT NaN-ignoring-mean behavior. F-05
    (plan 02-03) and F-08 (plan 02-05) will EXTEND this path to surface the
    finite-case count / partial-failure signal — when they land, this test is
    the contract they must consciously update. Assert ONLY today's behavior.
    """

    suite = _bootstrap_suite(tmp_path, ["good", "bad"])
    adapter = StubAdapter(
        run_root=tmp_path / "out",
        predictions={"good": _PRED_ERR_04, "bad": _PRED_NAN},
    )
    runner, _fake = _make_runner(monkeypatch, adapter)

    aggregated = runner._evaluate_across_cases(
        {"alpha": 0.5}, list(suite.dataset.cases), suite, MetricRegistry(), 0, None
    )

    # The NaN survivor is silently dropped; the mean is the good case alone.
    # (Today there is NO signal that a case failed — that is the F-05/F-08 gap.)
    import math

    value = aggregated["median_displacement_error"]
    assert not math.isnan(value)
    assert value == pytest.approx(0.4)


def test_provenance_blocks_stamped_into_summary_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A healthy run stamps tool/dataset/parser provenance into summary.json."""

    suite = _bootstrap_suite(tmp_path, ["solo"])
    adapter = StubAdapter(run_root=tmp_path / "out", predictions={"solo": _PRED_ERR_04})
    runner, _fake = _make_runner(monkeypatch, adapter)

    runner._evaluate_across_cases(
        {"alpha": 0.5}, list(suite.dataset.cases), suite, MetricRegistry(), 0, None
    )

    summary_path = adapter.run_dirs["solo"] / "ax_trial" / "summary.json"
    assert summary_path.is_file()
    record = json.loads(summary_path.read_text(encoding="utf-8"))

    assert record["tool"]["id"] == "stub-tool"
    assert record["dataset"]["id"] == "stub-dataset"
    assert record["dataset"]["case"] == "solo"
    assert "parse" in record["parser"]["fn"]
