"""tool.yaml loader: constructs a :class:`ToolAdapter` from YAML.

Supports the two built-in adapter kinds (``cli``, ``python_callable``) plus a
``custom`` escape hatch that imports an adapter class by dotted path. The
hyperparameters block is also parsed here so ``tool.yaml`` can be a
self-contained description of a tool's search space.

A tool.yaml may also reference an **output parser** — a callable that turns
the tool's raw outputs (in the trial's run directory) into the
``prediction = {per_point: [...]}`` shape consumed by metrics. The runner
invokes the parser between the adapter and the metric registry; tools whose
output is already in that shape can omit it.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

from geodispbench3d.sweep.parameters import SweepParameter

from .base import ToolAdapter
from .callable_adapter import CallableSpec, CallableToolAdapter
from .cli_adapter import (
    CliInvocationSpec,
    CliToolAdapter,
    HashedRunDirSpec,
)


@dataclass(frozen=True)
class ToolConfig:
    """In-memory representation of a tool.yaml file."""

    id: str
    kind: str
    adapter: ToolAdapter
    hyperparameters: Sequence[SweepParameter] = ()
    output_parser: Callable[..., Any] | None = None
    output_parser_options: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


def load_tool_config(path: str | Path) -> ToolConfig:
    """Load a tool.yaml and construct the adapter it describes."""

    yaml_path = Path(path).resolve()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Tool YAML not found: {yaml_path}")

    loaded = OmegaConf.to_container(OmegaConf.load(str(yaml_path)), resolve=True)
    if not isinstance(loaded, dict):
        raise ValueError(f"Tool YAML at {yaml_path} must be a mapping")
    raw: dict[str, Any] = {str(key): value for key, value in loaded.items()}

    kind = str(raw.get("kind", "cli")).lower()
    tool_id = str(raw.get("id", yaml_path.stem))

    adapter = _build_adapter(kind, raw, yaml_path)
    hparams = _load_hyperparameters(raw.get("hyperparameters") or [])

    parser_raw = raw.get("output_parser") or {}
    parser_fn: Callable[..., Any] | None = None
    parser_options: Mapping[str, Any] = {}
    if parser_raw:
        parser_fn = _resolve_callable(str(parser_raw["fn"]))
        parser_options = dict(parser_raw.get("options") or {})

    return ToolConfig(
        id=tool_id,
        kind=kind,
        adapter=adapter,
        hyperparameters=tuple(hparams),
        output_parser=parser_fn,
        output_parser_options=parser_options,
        raw=raw,
        source_path=yaml_path,
    )


def _build_adapter(kind: str, raw: Mapping[str, Any], yaml_path: Path) -> ToolAdapter:
    if kind == "cli":
        return _build_cli_adapter(raw, yaml_path)
    if kind in {"python_callable", "callable"}:
        return _build_callable_adapter(raw)
    if kind == "custom":
        return _build_custom_adapter(raw)
    if kind == "factory":
        return _build_factory_adapter(raw, yaml_path)
    raise ValueError(f"Unknown tool kind {kind!r} in {yaml_path}")


def _build_cli_adapter(raw: Mapping[str, Any], yaml_path: Path) -> CliToolAdapter:
    invocation_raw = raw.get("invocation") or {}
    entry = str(raw.get("entry", invocation_raw.get("entry", "")))
    if not entry:
        raise ValueError(f"tool.yaml at {yaml_path} missing 'entry' for cli kind")

    spec = CliInvocationSpec(
        entry=entry,
        style=str(invocation_raw.get("style", "hydra_overrides")),
        extra_args=tuple(invocation_raw.get("extra_args") or ()),
        presence_flag_params=tuple(invocation_raw.get("presence_flag_params") or ()),
        static_params=dict(invocation_raw.get("static_params") or {}),
    )

    outputs_raw = raw.get("outputs") or {}
    run_dir_root_raw = outputs_raw.get("run_dir_root")
    run_dir_root = _resolve_path(run_dir_root_raw, yaml_path) if run_dir_root_raw else None

    hashed_raw = outputs_raw.get("hashed_run_dir")
    hashed_spec: HashedRunDirSpec | None = None
    if hashed_raw:
        root_raw = hashed_raw.get("root", run_dir_root_raw)
        if not root_raw:
            raise ValueError(
                f"tool.yaml at {yaml_path}: hashed_run_dir requires 'root' "
                "(or outputs.run_dir_root)"
            )
        hashed_spec = HashedRunDirSpec(
            root=_resolve_path(root_raw, yaml_path),
            arg_name=str(hashed_raw.get("arg_name", "--results_dir")),
            hash_length=int(hashed_raw.get("hash_length", 12)),
            extra_inputs=tuple(hashed_raw.get("extra_inputs") or ()),
        )

    # Output-collection contract (D-06): ``glob`` is the single blessed path.
    # Read the RAW value BEFORE defaulting so an unset block defaults to glob
    # while an *explicitly* set ``stdout_json`` (deprecated) or an unsupported
    # value is rejected at load with an actionable message.
    outputs_from_raw = outputs_raw.get("from")
    if outputs_from_raw is None:
        outputs_from = "glob"
    elif outputs_from_raw == "glob":
        outputs_from = "glob"
    elif outputs_from_raw == "stdout_json":
        raise ValueError(
            f"tool.yaml at {yaml_path}: outputs.from: stdout_json is no longer "
            "supported; use outputs.from: glob with a predictions_glob"
        )
    else:
        raise ValueError(
            f"tool.yaml at {yaml_path}: unsupported outputs.from value "
            f"{outputs_from_raw!r}; the only supported value is 'glob'"
        )

    # Opt-in per-trial timeout (D-04/F-32): read the TOOL-level execution block
    # (NOT suite.execution / ExecutionConfig — RESEARCH Pitfall 5). Unset leaves
    # the timeout disabled.
    execution_raw = raw.get("execution") or {}
    timeout_seconds = execution_raw.get("timeout_seconds")
    timeout = float(timeout_seconds) if timeout_seconds is not None else None

    # Operator-facing preflight guidance (F-16): surfaced inside a
    # ToolPreflightError when the env/binary cannot be resolved before trial 0.
    remediation_raw = raw.get("remediation")
    help_url_raw = raw.get("help_url")
    remediation = str(remediation_raw) if remediation_raw is not None else None
    help_url = str(help_url_raw) if help_url_raw is not None else None

    return CliToolAdapter(
        invocation=spec,
        outputs_from=outputs_from,
        run_dir_root=run_dir_root,
        hashed_run_dir=hashed_spec,
        predictions_glob=outputs_raw.get("predictions_glob"),
        figures_glob=outputs_raw.get("figures_glob"),
        # ``env`` is an execution concern, not an output-collection one: read it
        # from the tool-level ``execution`` block (WR-02). The adapter merges
        # these over ``os.environ`` rather than replacing the whole environment.
        env=execution_raw.get("env"),
        timeout=timeout,
        remediation=remediation,
        help_url=help_url,
    )


def _build_callable_adapter(raw: Mapping[str, Any]) -> CallableToolAdapter:
    entry = str(raw.get("entry", ""))
    if not entry:
        raise ValueError("python_callable tool.yaml missing 'entry'")
    return CallableToolAdapter(spec=CallableSpec(entry=entry))


def _build_custom_adapter(raw: Mapping[str, Any]) -> ToolAdapter:
    entry = str(raw.get("entry", ""))
    if not entry or ":" not in entry:
        raise ValueError("custom tool.yaml 'entry' must be 'package.module:ClassName'")
    cls = _resolve_callable(entry)
    if not isinstance(cls, type):
        raise ImportError(f"Cannot resolve adapter class {entry!r}")
    init_kwargs = raw.get("init_kwargs") or {}
    instance = cls(**init_kwargs)
    if not isinstance(instance, ToolAdapter):
        raise TypeError(f"Custom adapter {entry!r} must be a ToolAdapter subclass instance")
    return instance


def _build_factory_adapter(raw: Mapping[str, Any], yaml_path: Path) -> ToolAdapter:
    """Build an adapter via a user-supplied factory callable.

    Use this when constructing the adapter requires more than dataclass-style
    kwargs (e.g. the iof3D adapter must first parse a Hydra config tree to
    produce its base AppConfig). The factory receives the tool YAML's
    ``factory_options`` mapping plus ``yaml_path`` for path resolution.
    """

    entry = str(raw.get("entry", ""))
    if not entry or ":" not in entry:
        raise ValueError(
            "factory tool.yaml 'entry' must be 'package.module:function' returning a ToolAdapter"
        )
    factory = _resolve_callable(entry)
    if not callable(factory):
        raise TypeError(f"Factory {entry!r} is not callable")
    options = dict(raw.get("factory_options") or {})
    options.setdefault("yaml_path", yaml_path)
    options.setdefault("hyperparameters", raw.get("hyperparameters") or [])
    instance = factory(**options)
    if not isinstance(instance, ToolAdapter):
        raise TypeError(f"Factory {entry!r} must return a ToolAdapter instance")
    return instance


def _load_hyperparameters(raw: Sequence[Mapping[str, Any]]) -> list[SweepParameter]:
    return [SweepParameter.from_mapping(entry) for entry in raw]


def _resolve_callable(entry: str) -> Any:
    if ":" not in entry:
        raise ValueError(f"Reference must be 'package.module:attr', got {entry!r}")
    module_path, attr = entry.split(":", 1)
    module = importlib.import_module(module_path)
    target = getattr(module, attr, None)
    if target is None:
        raise ImportError(f"Cannot resolve {entry!r}")
    return target


def _resolve_path(value: Any, yaml_path: Path) -> Path:
    p = Path(str(value))
    if p.is_absolute():
        return p
    return (yaml_path.parent / p).resolve()


__all__ = ["ToolConfig", "load_tool_config"]
