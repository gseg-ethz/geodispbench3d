"""Parameter-space grammar for sweeps.

Mirrors the grammar previously shipped with ``iof3D_analysis.ax.sweep`` so
existing hyperparameter YAML continues to work verbatim.
"""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from omegaconf import DictConfig, OmegaConf


@dataclass(frozen=True)
class SweepParameter:
    """Declarative description of a single sweep parameter."""

    name: str
    kind: str
    value_type: str
    values: Sequence[Any] | None = None
    lower: float | None = None
    upper: float | None = None
    log_scale: bool = False
    step: float | None = None
    activates_on: Mapping[str, Sequence[Any]] | None = None
    is_ordered: bool | None = None
    sort_values: bool | None = None


@dataclass(frozen=True)
class SweepConfig:
    """Full sweep definition: parameter space + search budget + objective."""

    parameters: Sequence[SweepParameter]
    max_trials: int
    sobol_trials: int
    objective_name: str
    minimize: bool


def load_sweep_config(cfg: DictConfig | Mapping[str, Any] | None) -> SweepConfig:
    """Coerce an OmegaConf node (or plain mapping) into :class:`SweepConfig`."""

    if cfg is None:
        data: dict[str, Any] = {}
    elif isinstance(cfg, DictConfig):
        data = OmegaConf.to_container(cfg, resolve=True)  # type: ignore[assignment]
    else:
        data = dict(cfg)

    raw_params = data.get("parameters", [])
    params: list[SweepParameter] = []
    for entry in raw_params:
        params.append(
            SweepParameter(
                name=str(entry["name"]),
                kind=str(entry.get("type", "choice")),
                value_type=str(entry.get("value_type", "str")),
                values=list(entry.get("values")) if entry.get("values") is not None else None,
                lower=entry.get("lower"),
                upper=entry.get("upper"),
                log_scale=bool(entry.get("log_scale", False)),
                step=entry.get("step"),
                activates_on=entry.get("activates_on"),
                is_ordered=entry.get("is_ordered"),
                sort_values=entry.get("sort_values"),
            )
        )

    search_cfg = data.get("search", {})
    return SweepConfig(
        parameters=params,
        max_trials=int(search_cfg.get("max_trials", 10)),
        sobol_trials=int(search_cfg.get("sobol_trials", 3)),
        objective_name=str(search_cfg.get("objective", "runtime_seconds")),
        minimize=bool(search_cfg.get("minimize", True)),
    )


def build_parameter_specs(cfg: SweepConfig) -> list[dict[str, Any]]:
    """Convert sweep parameters into Ax-friendly specification dictionaries."""

    return [_build_parameter_spec(param) for param in cfg.parameters]


def is_active(
    param: SweepParameter,
    trial_values: Mapping[str, Any],
    base_values: Mapping[str, Any] | None = None,
) -> bool:
    """Evaluate ``activates_on`` conditions for a parameter.

    ``base_values`` provides fallback lookups for parent parameters that are
    not part of the trial parameterization (e.g. fixed config defaults).
    """

    conditions = param.activates_on or {}
    for parent_name, allowed in conditions.items():
        parent_value = trial_values.get(parent_name)
        if parent_value is None and base_values is not None:
            parent_value = base_values.get(parent_name)
        if parent_value not in allowed:
            return False
    return True


# ---------------------------------------------------------------------------
# Internal helpers (Ax spec construction)
# ---------------------------------------------------------------------------


def _build_parameter_spec(param: SweepParameter) -> dict[str, Any]:
    kind = param.kind.lower()
    value_type = _value_type_label(param.value_type)

    if kind == "choice":
        values = _coerce_choice_values(param.values)
        if len(values) == 1:
            return {
                "name": param.name,
                "type": "fixed",
                "value": values[0],
                "value_type": value_type,
            }
        spec: dict[str, Any] = {
            "name": param.name,
            "type": "choice",
            "values": values,
            "value_type": value_type,
        }
        if param.is_ordered is not None:
            spec["is_ordered"] = bool(param.is_ordered)
        else:
            spec["is_ordered"] = value_type == "bool" or len(values) == 2
        if param.sort_values is not None:
            spec["sort_values"] = bool(param.sort_values)
        else:
            spec["sort_values"] = value_type == "bool"
        return spec

    if kind == "range":
        if param.lower is None or param.upper is None:
            raise ValueError(f"Range parameter {param.name!r} requires lower/upper bounds")
        lower, upper = param.lower, param.upper
        if value_type == "int":
            lower = int(round(lower))
            upper = int(round(upper))
        spec = {
            "name": param.name,
            "type": "range",
            "bounds": [lower, upper],
            "value_type": value_type,
        }
        if param.log_scale:
            spec["log_scale"] = True
        if param.step is not None:
            spec["step"] = float(param.step)
        return spec

    if kind == "fixed":
        values = _coerce_choice_values(param.values)
        if len(values) != 1:
            raise ValueError(f"Fixed parameter {param.name!r} expects a single value")
        return {
            "name": param.name,
            "type": "fixed",
            "value": values[0],
            "value_type": value_type,
        }

    raise ValueError(f"Unknown parameter kind {param.kind!r} for {param.name}")


def _value_type_label(value: str) -> str:
    value = value.lower()
    if value in {"int", "integer"}:
        return "int"
    if value in {"float", "double", "continuous"}:
        return "float"
    if value in {"bool", "boolean"}:
        return "bool"
    return "str"


def _coerce_choice_values(values: Sequence[Any] | None) -> list[Any]:
    if values is None or not list(values):
        raise ValueError("Choice parameters require a non-empty values list")
    out: list[Any] = []
    for value in values:
        if isinstance(value, MappingABC) and "value" in value:
            out.append(value["value"])
        else:
            out.append(value)
    return out


__all__ = [
    "SweepConfig",
    "SweepParameter",
    "build_parameter_specs",
    "is_active",
    "load_sweep_config",
]
