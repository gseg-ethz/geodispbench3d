"""Runner/Ax failure-propagation tests (review HIGH #3 — the core defect).

These tests close the central gap the Codex review flagged: NO test asserted
that a ``TrialResult(success=False)`` reaches Ax as a *failed* trial
(``log_trial_failure``) rather than being scored (``complete_trial``). They are
hermetic and fast — a duck-typed :class:`FakeAxClient` stands in for the real
``AxClient`` (installed by monkeypatching ``runner.AxClient`` BEFORE the runner
is constructed, because the runner calls ``AxClient(...)`` unconditionally in
``__init__``), and a configurable :class:`StubFailAdapter` returns canned
``TrialResult`` values with explicit ``error_kind`` discriminators. No real Ax,
no subprocess.

Covered:

* For BOTH a timeout and a crash first-trial: ``log_trial_failure`` is called and
  ``complete_trial`` is NOT, the sweep CONTINUES (a later success is completed),
  ``evaluate_trial`` is never invoked for the failed case, and the typed counter
  split holds (``timeout`` -> ``timeouts``; ``nonzero_exit`` -> ``trial_failures``).
* RESOLVED-A — a DISTINCT all-trials-failed sweep (and a timeouts-only-zero-
  success variant) returns a valid ``SweepRunSummary`` with ``best_trial is None``
  and ``successful_trials == 0`` and NO unhandled ``get_best_trial`` exception.
* RESOLVED-B — the legacy ``run()`` / ``_default_executor`` path reports a
  ``success=False`` result via ``log_trial_failure`` and returns cleanly.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from geodispbench3d.suite.loader import load_suite
from geodispbench3d.sweep import evaluation as evaluation_mod
from geodispbench3d.sweep import runner as runner_mod
from geodispbench3d.sweep.parameters import SweepConfig, SweepParameter, build_parameter_specs
from geodispbench3d.sweep.runner import AxSweepRunner, SweepRunSummary
from geodispbench3d.tool.base import ToolAdapter, TrialOutputs, TrialRequest, TrialResult

# ---------------------------------------------------------------------------
# Fakes / stubs
# ---------------------------------------------------------------------------


class FakeAxClient:
    """Ax-free recording double for the five methods the runner calls.

    Records which completion method each trial index invoked so a test can
    assert ``log_trial_failure`` (not ``complete_trial``) was called for a
    failed trial. ``get_best_trial`` raises when ``_best_raises`` is set, mirroring
    real Ax in the all-failed state (no completed trial to optimize over).
    """

    def __init__(self, *, verbose_logging: bool = False, **_: Any) -> None:
        self.verbose_logging = verbose_logging
        self.created_with: dict[str, Any] | None = None
        self.next_trial_calls = 0
        self.completed: list[int] = []
        self.failures: list[int] = []
        self.best_sentinel = SimpleNamespace(label="best-trial")
        # Tests flip this to mimic real Ax raising when nothing completed.
        self._best_raises = False

    def create_experiment(
        self,
        *,
        parameters: Any = None,
        name: str | None = None,
        objective_name: str | None = None,
        minimize: bool | None = None,
        **_kwargs: Any,
    ) -> None:
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
        self.completed.append(trial_index)

    def log_trial_failure(self, *, trial_index: int) -> None:
        self.failures.append(trial_index)

    def get_best_trial(self) -> Any:
        if self._best_raises:
            raise RuntimeError("no completed trials; Ax has no best trial")
        return self.best_sentinel


class StubFailAdapter(ToolAdapter):
    """ToolAdapter returning a per-call canned ``TrialResult``.

    ``outcomes`` is a list of ``(success, error_kind)`` consumed one entry per
    ``run_trial`` call. After it is exhausted, trials succeed. A successful
    trial carries a canned ``prediction`` in ``outputs.extras`` so the echo
    parser produces a finite objective.
    """

    id = "stub-fail-adapter"
    in_process_safe = True

    def __init__(
        self,
        *,
        run_root: Path,
        outcomes: list[tuple[bool, str | None]],
        prediction: list[dict[str, Any]] | None = None,
    ) -> None:
        self._run_root = run_root
        self._outcomes = list(outcomes)
        self._prediction = list(prediction or [{"label": "P", "vector": [1.0, 0.0, 0.0]}])
        self._i = 0
        self.prepare_called = False
        self.teardown_called = False

    def prepare(self) -> None:
        self.prepare_called = True

    def teardown(self) -> None:
        self.teardown_called = True

    def run_trial(self, request: TrialRequest) -> TrialResult:
        idx = self._i
        self._i += 1
        success, error_kind = self._outcomes[idx] if idx < len(self._outcomes) else (True, None)
        run_dir = self._run_root / f"run-{idx}"
        run_dir.mkdir(parents=True, exist_ok=True)
        if not success:
            return TrialResult(
                outputs=TrialOutputs(run_dir=run_dir),
                scalar_metrics={},
                duration_seconds=0.0,
                success=False,
                error=error_kind or "trial failed",
                error_kind=error_kind,
            )
        outputs = TrialOutputs(
            run_dir=run_dir, extras={"prediction": {"per_point": list(self._prediction)}}
        )
        return TrialResult(outputs=outputs, scalar_metrics={}, duration_seconds=0.01, success=True)


# ---------------------------------------------------------------------------
# Suite bootstrap (inline YAML in tmp_path; echo parser reads outputs.extras)
# ---------------------------------------------------------------------------


def _bootstrap_suite(tmp_path: Path) -> Any:
    """Single-case suite whose parser echoes the adapter's canned prediction."""

    (tmp_path / "gt.csv").write_text("label,x1,y1,z1,x2,y2,z2\nP,0,0,0,1,0,0\n")
    (tmp_path / "dataset.yaml").write_text(
        textwrap.dedent("""\
        id: stub-dataset
        cases:
          - name: only
            scans: []
            ground_truth: {kind: point_displacements, path: gt.csv}
        """)
    )
    (tmp_path / "metrics.yaml").write_text(
        textwrap.dedent("""\
        objective_metrics:
          - id: median_displacement_error
            fn: geodispbench3d.metrics.builtins:median_displacement_error
            needs: [prediction, ground_truth]
            gt_kinds: [point_displacements]
        record_metrics: []
        """)
    )

    pkg_dir = tmp_path / "failprop_stub_pkg"
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
          fn: failprop_stub_pkg:parse
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
    fake = runner._ax
    assert isinstance(fake, FakeAxClient)
    return runner, fake


def _spy_evaluate_trial(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Wrap the runner's ``evaluate_trial`` to record how many times it ran.

    A failed trial raises BEFORE ``evaluate_trial`` (the success guard fires in
    ``_evaluate_across_cases``), so the call count proves the failed case was
    never scored.
    """

    calls: list[int] = []
    real = evaluation_mod.evaluate_trial

    def spy(**kwargs: Any) -> Any:
        calls.append(1)
        return real(**kwargs)

    monkeypatch.setattr(runner_mod, "evaluate_trial", spy)
    return calls


# ---------------------------------------------------------------------------
# HIGH #3 — a failed trial is reported (log_trial_failure), never scored, and
# the sweep continues; the timeout/crash counter split holds.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error_kind", "expect_timeouts", "expect_trial_failures"),
    [
        ("timeout", 1, 0),
        ("nonzero_exit", 0, 1),
    ],
)
def test_failed_first_trial_is_logged_not_completed_and_sweep_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_kind: str,
    expect_timeouts: int,
    expect_trial_failures: int,
) -> None:
    """A success=False first trial -> log_trial_failure (not complete_trial);
    the sweep continues and a later success IS completed; evaluate_trial is
    never invoked for the failed case; the typed counter split is correct."""

    suite = _bootstrap_suite(tmp_path)
    adapter = StubFailAdapter(
        run_root=tmp_path / "out",
        # Trial 0 fails (the kind under test); trial 1 succeeds.
        outcomes=[(False, error_kind), (True, None)],
    )
    runner, fake = _make_runner(monkeypatch, adapter)
    eval_calls = _spy_evaluate_trial(monkeypatch)

    result = runner.run_with_suite(suite=suite, max_trials=2)

    # (a) The failed trial 0 went to log_trial_failure, NOT complete_trial.
    assert 0 in fake.failures
    assert 0 not in fake.completed
    # (b) The sweep continued: trial 1 succeeded and was completed.
    assert 1 in fake.completed
    assert fake.completed == [1]
    # (c) evaluate_trial ran ONLY for the surviving success (failed case skipped
    # scoring because the success guard raised before evaluate_trial).
    assert len(eval_calls) == 1

    # The typed counter split (D-05 / review Warning 1).
    assert isinstance(result, SweepRunSummary)
    assert result.timeouts == expect_timeouts
    assert result.trial_failures == expect_trial_failures
    assert result.successful_trials == 1
    # The success path still yields a best trial via the fake sentinel.
    assert result.best_trial is fake.best_sentinel

    assert adapter.prepare_called is True
    assert adapter.teardown_called is True


# ---------------------------------------------------------------------------
# RESOLVED-A — a DISTINCT all-trials-failed sweep returns a valid summary with
# best_trial=None / successful_trials=0 and NO unhandled get_best_trial throw.
# ---------------------------------------------------------------------------


def test_all_trials_failed_crash_returns_valid_summary_no_best_trial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every trial crashes: a valid SweepRunSummary is returned (best_trial is
    None, successful_trials == 0), get_best_trial does NOT escape, and all trials
    are routed to log_trial_failure. The existing fake-Ax test follows a failure
    with a success, so it CANNOT reach this no-best-trial path (RESOLVED-A)."""

    suite = _bootstrap_suite(tmp_path)
    adapter = StubFailAdapter(
        run_root=tmp_path / "out",
        outcomes=[(False, "nonzero_exit"), (False, "nonzero_exit")],
    )
    runner, fake = _make_runner(monkeypatch, adapter)
    # Mimic real Ax: get_best_trial raises when nothing completed.
    fake._best_raises = True

    result = runner.run_with_suite(suite=suite, max_trials=2)

    assert isinstance(result, SweepRunSummary)
    assert result.best_trial is None  # _resolve_best_trial swallowed the raise
    assert result.successful_trials == 0
    assert result.trial_failures == 2
    assert result.timeouts == 0
    assert fake.completed == []
    assert sorted(fake.failures) == [0, 1]


def test_all_trials_timed_out_zero_success_returns_valid_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A timeouts-only-zero-success sweep also returns a valid summary
    (successful_trials == 0, best_trial is None). Plan 02 turns this input into
    exit 1 even though every failure was a (normally non-fatal) timeout."""

    suite = _bootstrap_suite(tmp_path)
    adapter = StubFailAdapter(
        run_root=tmp_path / "out",
        outcomes=[(False, "timeout"), (False, "timeout")],
    )
    runner, fake = _make_runner(monkeypatch, adapter)
    fake._best_raises = True

    result = runner.run_with_suite(suite=suite, max_trials=2)

    assert isinstance(result, SweepRunSummary)
    assert result.best_trial is None
    assert result.successful_trials == 0
    assert result.timeouts == 2
    assert result.trial_failures == 0
    assert fake.completed == []
    assert sorted(fake.failures) == [0, 1]


# ---------------------------------------------------------------------------
# RESOLVED-B — the legacy run() / _default_executor path also reports a
# success=False result via log_trial_failure (the shared guard covers both
# entry points), and run() returns cleanly when all trials failed.
# ---------------------------------------------------------------------------


def test_legacy_run_path_reports_failure_via_log_trial_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run() (legacy _default_executor) with a success=False stub records
    log_trial_failure (not complete_trial) and returns None when all failed."""

    adapter = StubFailAdapter(
        run_root=tmp_path / "out",
        outcomes=[(False, "nonzero_exit")],
    )
    runner, fake = _make_runner(monkeypatch, adapter)
    fake._best_raises = True

    best = runner.run(max_trials=1)

    # The failure was reported to Ax, not scored.
    assert fake.failures == [0]
    assert fake.completed == []
    # run() returned cleanly (no get_best_trial throw): None when nothing won.
    assert best is None
    assert adapter.prepare_called is True
    assert adapter.teardown_called is True
