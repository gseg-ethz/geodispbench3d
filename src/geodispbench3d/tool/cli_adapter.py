"""Subprocess-based tool adapter.

The CLI adapter launches the tool under test as a subprocess for each trial.
It is the default adapter because isolation is cheap and crashes in the tool
don't take down the sweep.

Two trial-isolation strategies are supported:

* **Inline parameters only** — every trial shares the same working directory.
  Cheapest but assumes the tool itself partitions its outputs.
* **Hashed run dir** — for each trial, hash the parameter set into a stable
  subfolder under ``run_dir_root`` and inject that path into argv as the
  configured ``run_dir_arg``. The folder name is reproducible from parameters,
  so re-running an identical trial reuses the same directory.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import ToolAdapter, ToolPreflightError, TrialOutputs, TrialRequest, TrialResult


@dataclass(frozen=True)
class CliInvocationSpec:
    """How to turn a trial into a CLI invocation.

    ``entry`` is the executable (or wrapper) used as ``argv[0]``. ``extra_args``
    are appended verbatim before the rendered parameters. ``style`` controls
    how trial parameters are serialized.

    For boolean parameters under ``argparse`` style, names listed in
    ``presence_flag_params`` are rendered as ``--<name>`` when the value is
    truthy and omitted entirely when falsy (matching argparse
    ``store_true`` semantics). Other params are rendered as ``--name value``.
    """

    entry: str
    style: str = "hydra_overrides"  # | "argparse" | "kv_equals"
    extra_args: Sequence[str] = ()
    presence_flag_params: Sequence[str] = ()
    static_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HashedRunDirSpec:
    """Configures per-trial output isolation via a hashed subdirectory.

    The trial's parameters are hashed into a deterministic subfolder name
    under ``root``. The path is injected into argv via the configured
    ``arg_name`` (e.g. ``"--results_dir"``). Re-running an identical trial
    reuses the same directory, which is convenient for resuming sweeps.
    """

    root: Path
    arg_name: str
    hash_length: int = 12
    extra_inputs: Sequence[Any] = ()  # additional values folded into the hash


class CliToolAdapter(ToolAdapter):
    """Launches the tool under test via subprocess, once per trial."""

    id = "cli"
    in_process_safe = False

    #: Bounded wall-clock timeout for the conda-enumeration preflight probe.
    _CONDA_LIST_TIMEOUT = 30.0

    #: Grace period (seconds) for the post-timeout reap. After the process tree
    #: is SIGKILLed we drain stdout/stderr with this bound so an escaped
    #: descendant (daemonized/re-parented out of the process group) that still
    #: holds the inherited pipe fds cannot block the sweep indefinitely (WR-03).
    _REAP_GRACE_SECONDS = 10.0

    def __init__(
        self,
        *,
        invocation: CliInvocationSpec,
        outputs_from: str = "glob",
        run_dir_root: Path | None = None,
        hashed_run_dir: HashedRunDirSpec | None = None,
        predictions_glob: str | None = None,
        figures_glob: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        remediation: str | None = None,
        help_url: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._invocation = invocation
        self._outputs_from = outputs_from
        self._run_dir_root = Path(run_dir_root) if run_dir_root is not None else None
        self._hashed_run_dir = hashed_run_dir
        self._predictions_glob = predictions_glob
        self._figures_glob = figures_glob
        # Merge overrides over the inherited environment rather than replacing
        # it (WR-02): ``Popen(env=...)`` replaces the child env wholesale, so a
        # partial dict like ``{"OMP_NUM_THREADS": "4"}`` would otherwise strip
        # PATH/HOME/CONDA_*/LD_LIBRARY_PATH and break ``conda run`` resolution.
        self._env = {**os.environ, **env} if env else None
        # ``None`` or any value ``<= 0`` means "no timeout" (opt-in, D-04).
        self._timeout = timeout
        self._remediation = remediation
        self._help_url = help_url
        self._logger = logger or logging.getLogger("geodispbench3d.tool.cli")

    def prepare(self) -> None:
        """Fail-fast env/binary preflight before trial 0 (F-16, D-02/D-10).

        Resolves the leading executable (``shutil.which``) and, for a
        ``conda run`` entry, that the named env (``-n``/``--name``) or prefix
        (``-p``/``--prefix``) resolves. Raises :class:`ToolPreflightError`
        (carrying this adapter's remediation/help_url) on any failure.

        ACCEPTED LIMITATION (D-02): the preflight DELIBERATELY does not validate
        the trailing in-env binary (e.g. ``f2s3`` inside ``conda run -n env
        f2s3``) — it neither spawns the env nor runs ``conda run ... which``.
        A binary missing inside the env is surfaced by trial 0's existing
        nonzero-exit / FileNotFoundError handling.
        """

        tokens = shlex.split(self._invocation.entry)
        if not tokens:
            raise self._preflight_error("tool entry is empty; nothing to invoke")

        leader = tokens[0]
        if shutil.which(leader) is None:
            raise self._preflight_error(
                f"tool executable {leader!r} not found on PATH"
            )

        if tokens[:2] == ["conda", "run"]:
            self._preflight_conda_env(tokens)

    def _preflight_error(self, message: str) -> ToolPreflightError:
        return ToolPreflightError(
            message, remediation=self._remediation, help_url=self._help_url
        )

    def _preflight_conda_env(self, tokens: Sequence[str]) -> None:
        env_name, env_prefix = _parse_conda_target(tokens)
        if env_prefix is not None:
            prefix_path = Path(env_prefix).expanduser()
            try:
                prefix_path = prefix_path.resolve()
            except OSError:  # pragma: no cover - exotic FS error
                pass
            if not prefix_path.exists():
                raise self._preflight_error(
                    f"conda prefix {env_prefix!r} does not exist"
                )
            return
        if env_name is None:
            # `conda run` with neither -n nor -p: nothing further to resolve.
            return
        names = self._conda_env_names()
        if env_name not in names:
            raise self._preflight_error(
                f"conda env {env_name!r} not found (available: {sorted(names)})"
            )

    def _conda_env_names(self) -> set[str]:
        """Enumerate conda env names via ``conda env list --json``.

        Thin, monkeypatchable seam (Plan 03 stubs this for hermetic tests).
        Maps EVERY failure mode — nonzero return, malformed/non-JSON output,
        and a bounded-timeout expiry — to :class:`ToolPreflightError` so a raw
        subprocess / JSON exception never escapes the preflight.
        """

        try:
            proc = subprocess.run(
                ["conda", "env", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=self._CONDA_LIST_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise self._preflight_error(
                "timed out enumerating conda environments "
                f"(`conda env list --json` exceeded {self._CONDA_LIST_TIMEOUT}s)"
            ) from exc
        if proc.returncode != 0:
            raise self._preflight_error(
                f"`conda env list --json` failed (exit={proc.returncode}): "
                f"{proc.stderr.strip()}"
            )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise self._preflight_error(
                "could not parse `conda env list --json` output"
            ) from exc
        return _parse_conda_env(payload)

    def set_timeout_override(self, timeout: float | None) -> None:
        """Public seam for overriding the per-trial timeout (e.g. a CLI flag).

        Plan 02 uses this instead of mutating the private ``_timeout`` field.
        ``None`` or any value ``<= 0`` disables the timeout.
        """

        self._timeout = timeout

    def run_trial(self, request: TrialRequest) -> TrialResult:
        run_dir = self._resolve_run_dir(request)
        if run_dir is not None:
            run_dir.mkdir(parents=True, exist_ok=True)

        argv = self._build_argv(request, run_dir)
        self._logger.info("CLI trial: %s", " ".join(shlex.quote(a) for a in argv))

        timeout = self._timeout if (self._timeout is not None and self._timeout > 0) else None

        start = time.perf_counter()
        try:
            # ``start_new_session=True`` puts the tool (and any descendants it
            # spawns, e.g. the real binary under ``conda run``) in its own
            # process group so a timeout can reap the whole tree, not just the
            # direct child. ``Popen`` + ``communicate`` preserves every guarantee
            # the prior ``subprocess.run`` call gave: piped+captured text output
            # and the adapter's custom environment.
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._env,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            duration = time.perf_counter() - start
            return TrialResult(
                outputs=TrialOutputs(run_dir=run_dir or Path.cwd()),
                scalar_metrics={"runtime_seconds": duration},
                duration_seconds=duration,
                success=False,
                error=f"Tool entry not found: {exc}",
                error_kind="entry_not_found",
            )

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Kill the whole process group (incl. conda-run descendants) so a
            # hung tool cannot stall the sweep or orphan a GPU job, then reap.
            self._terminate_process_tree(proc)
            # The SIGKILL reaps the leader and any descendant still in the
            # process group, but a daemonized/re-parented grandchild can escape
            # it and keep the inherited stdout/stderr fds open. Bound the drain
            # so that escaped descendant cannot re-introduce the very hang the
            # timeout exists to prevent (WR-03).
            try:
                stdout, stderr = proc.communicate(timeout=self._REAP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                self._logger.warning(
                    "timed-out trial left an escaped descendant holding "
                    "stdout/stderr; abandoning the reap after %ss: %s",
                    self._REAP_GRACE_SECONDS,
                    argv[0],
                )
                stdout, stderr = "", ""
            duration = time.perf_counter() - start
            self._logger.warning(
                "CLI trial timed out after %ss: %s", self._timeout, argv[0]
            )
            return TrialResult(
                outputs=TrialOutputs(run_dir=run_dir or self._run_dir_root or Path.cwd()),
                scalar_metrics={"runtime_seconds": duration},
                duration_seconds=duration,
                success=False,
                error="timeout",
                error_kind="timeout",
            )

        duration = time.perf_counter() - start
        returncode = proc.returncode

        if returncode != 0:
            self._logger.error(
                "CLI trial returned %s\nstdout:\n%s\nstderr:\n%s",
                returncode,
                stdout,
                stderr,
            )
            return TrialResult(
                outputs=TrialOutputs(run_dir=run_dir or self._run_dir_root or Path.cwd()),
                scalar_metrics={"runtime_seconds": duration},
                duration_seconds=duration,
                success=False,
                error=f"exit={returncode}",
                error_kind="nonzero_exit",
            )

        outputs, scalar_metrics = self._collect_outputs(stdout, run_dir)

        # D-07: a configured ``predictions_glob`` matching zero files is a
        # flagged failure — the tool exited 0 but produced no usable output.
        # An empty ``figures_glob`` stays non-fatal (figures are optional).
        if self._predictions_glob and not outputs.predictions:
            return TrialResult(
                outputs=outputs,
                scalar_metrics={"runtime_seconds": duration},
                duration_seconds=duration,
                success=False,
                error=f"no predictions matched glob {self._predictions_glob!r}",
                error_kind="missing_output",
            )

        metrics = dict(scalar_metrics)
        metrics.setdefault("runtime_seconds", duration)
        return TrialResult(
            outputs=outputs,
            scalar_metrics=metrics,
            duration_seconds=duration,
            success=True,
        )

    # ------------------------------------------------------------------

    def _terminate_process_tree(self, proc: subprocess.Popen[str]) -> None:
        """Kill a timed-out subprocess and its descendants; never raise.

        On POSIX the child runs in its own session/process group (set via
        ``start_new_session=True``), so killing the whole group reaps
        descendants spawned via ``conda run`` — a direct ``proc.kill()`` would
        leave the real tool orphaned. On non-POSIX, fall back to ``proc.kill()``.
        A ``ProcessLookupError`` (the group/process already exited between the
        timeout and the kill) is swallowed and treated as already-dead; the
        termination path must never raise out of ``run_trial``.
        """

        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:  # pragma: no cover - non-POSIX fallback
                proc.kill()
        except ProcessLookupError:  # pragma: no cover - benign kill/exit race
            pass

    def _resolve_run_dir(self, request: TrialRequest) -> Path | None:
        """Return the per-trial run directory, hashed if configured."""

        if self._hashed_run_dir is not None:
            digest_input: list[Any] = list(self._hashed_run_dir.extra_inputs)
            digest_input.append(request.parameters)
            return self._hashed_run_dir.root / hash_parameters(
                digest_input, length=self._hashed_run_dir.hash_length
            )
        if request.work_dir is not None:
            return Path(request.work_dir)
        return None

    def _build_argv(self, request: TrialRequest, run_dir: Path | None) -> list[str]:
        argv: list[str] = shlex.split(self._invocation.entry)
        argv.extend(self._invocation.extra_args)
        if self._invocation.static_params:
            argv.extend(
                _render_parameters(
                    self._invocation.static_params,
                    self._invocation.style,
                    self._invocation.presence_flag_params,
                )
            )
        argv.extend(
            _render_parameters(
                request.parameters, self._invocation.style, self._invocation.presence_flag_params
            )
        )
        if self._hashed_run_dir is not None and run_dir is not None:
            argv.extend([self._hashed_run_dir.arg_name, str(run_dir)])
        return argv

    def _collect_outputs(
        self, stdout: str, run_dir: Path | None
    ) -> tuple[TrialOutputs, Mapping[str, float]]:
        if self._outputs_from == "stdout_json":
            for line in reversed(stdout.splitlines()):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                return _outputs_from_payload(payload), _metrics_from_payload(payload)
            # Fall through if stdout had no JSON line.

        effective_run_dir = run_dir or self._run_dir_root
        if effective_run_dir is not None:
            predictions = (
                tuple(sorted(effective_run_dir.glob(self._predictions_glob)))
                if self._predictions_glob
                else ()
            )
            figures = (
                tuple(sorted(effective_run_dir.glob(self._figures_glob)))
                if self._figures_glob
                else ()
            )
            return (
                TrialOutputs(
                    run_dir=effective_run_dir,
                    predictions=predictions,
                    figures=figures,
                ),
                {},
            )

        return TrialOutputs(run_dir=Path.cwd()), {}


def hash_parameters(inputs: Sequence[Any], *, length: int = 12) -> str:
    """Stable short hash for a sequence of JSON-serializable inputs.

    Used to derive deterministic per-trial subdirectory names. ``length`` is
    truncated from the hex digest; defaults match git's short-SHA convention.
    """

    blob = json.dumps(_canonicalize(inputs), sort_keys=True, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return digest[: max(4, length)]


def _canonicalize(obj: Any) -> Any:
    if isinstance(obj, MappingABC):
        return {str(k): _canonicalize(obj[k]) for k in sorted(obj, key=str)}
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(v) for v in obj]
    return obj


def _render_parameters(
    parameters: Mapping[str, Any],
    style: str,
    presence_flag_params: Sequence[str] = (),
) -> list[str]:
    if style in {"hydra_overrides", "kv_equals"}:
        return [f"{k}={_format_scalar(v)}" for k, v in parameters.items()]
    if style == "argparse":
        presence = set(presence_flag_params)
        out: list[str] = []
        for k, v in parameters.items():
            if k in presence:
                if bool(v):
                    out.append(f"--{k}")
                continue
            out.extend([f"--{k}", _format_scalar(v)])
        return out
    raise ValueError(f"Unknown invocation style: {style!r}")


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _outputs_from_payload(payload: Mapping[str, Any]) -> TrialOutputs:
    run_dir = Path(payload.get("run_dir", "."))
    predictions = tuple(Path(p) for p in payload.get("predictions", []))
    figures = tuple(Path(p) for p in payload.get("figures", []))
    extras = {
        k: v
        for k, v in payload.items()
        if k not in {"run_dir", "predictions", "figures", "scalar_metrics"}
    }
    return TrialOutputs(run_dir=run_dir, predictions=predictions, figures=figures, extras=extras)


def _parse_conda_target(tokens: Sequence[str]) -> tuple[str | None, str | None]:
    """Extract ``(env_name, env_prefix)`` from a ``conda run ...`` token list.

    Recognizes ``-n``/``--name NAME`` and ``-p``/``--prefix PATH`` (both the
    space-separated and ``--name=NAME`` / ``--prefix=PATH`` forms). Returns
    ``(None, None)`` when neither flag is present (e.g. a bare ``conda run``).
    """

    rest = list(tokens[2:])
    for i, tok in enumerate(rest):
        if tok in {"-n", "--name"} and i + 1 < len(rest):
            return rest[i + 1], None
        if tok in {"-p", "--prefix"} and i + 1 < len(rest):
            return None, rest[i + 1]
        if tok.startswith("--name="):
            return tok.split("=", 1)[1], None
        if tok.startswith("--prefix="):
            return None, tok.split("=", 1)[1]
    return None, None


def _parse_conda_env(payload: Mapping[str, Any]) -> set[str]:
    """Map a ``conda env list --json`` payload to a set of env names.

    Named envs live under an ``envs/`` directory, so their basename is the env
    name. Any other entry is the conda root prefix and maps to ``"base"`` (so a
    ``conda run -n base ...`` entry resolves correctly).
    """

    envs = payload.get("envs") or []
    names: set[str] = set()
    for env_path in envs:
        p = Path(str(env_path))
        if p.parent.name == "envs":
            names.add(p.name)
        else:
            names.add("base")
    return names


def _metrics_from_payload(payload: Mapping[str, Any]) -> Mapping[str, float]:
    metrics = payload.get("scalar_metrics")
    if not isinstance(metrics, Mapping):
        return {}
    out: dict[str, float] = {}
    for k, v in metrics.items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return out


__all__ = [
    "CliInvocationSpec",
    "CliToolAdapter",
    "HashedRunDirSpec",
    "hash_parameters",
]
