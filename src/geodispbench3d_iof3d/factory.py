"""Factory used by ``geodispbench3d`` tool.yaml ``kind: factory`` to build the
iof3D adapter from a Hydra-style base config + the YAML's hyperparameters.

The generic loader cannot construct :class:`Iof3dCallableAdapter` directly
because the adapter requires a fully-resolved ``AppConfig``, which in turn
needs to be parsed out of iof3D's Hydra config tree. The factory takes a
small set of well-known options (``base_app_config:`` path, optional
``run_kwargs:`` mapping) and does that wiring on iof3D's behalf.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from iof3D.v2.cli_hydra import _build_app_config
from omegaconf import DictConfig, OmegaConf

from geodispbench3d.sweep.parameters import SweepParameter

from .adapter import Iof3dCallableAdapter

_DEFAULT_BASE_APP_CONFIG = "pkg://iof3D.conf/app/base.yaml"


def build_iof3d_adapter(
    *,
    base_app_config: str | None = None,
    run_kwargs: Mapping[str, Any] | None = None,
    objective_name: str = "runtime_seconds",
    minimize: bool = True,
    overrides: Mapping[str, Any] | None = None,
    hyperparameters: Sequence[Mapping[str, Any]] | None = None,
    yaml_path: Path | None = None,
    logger: logging.Logger | None = None,
    **_: Any,
) -> Iof3dCallableAdapter:
    """Build an :class:`Iof3dCallableAdapter` for use in a suite-driven sweep.

    Parameters
    ----------
    base_app_config : str, optional
        Path to a YAML containing the iof3D ``app`` section (matches the
        structure of ``iof3D/conf/app/base.yaml``). May be a filesystem path
        (resolved relative to the tool YAML if not absolute) or a
        ``pkg://iof3D.conf/app/base.yaml`` reference. Defaults to the
        packaged ``base.yaml`` shipped with iof3D.
    run_kwargs : mapping, optional
        Forwarded to ``run_flow_pipeline`` per trial. Same shape as the
        ``run:`` section consumed by the legacy ``iof3d-ax`` Hydra CLI:
        ``cache_dir``, ``work_root``, ``max_feature_workers``, ...
    objective_name, minimize : Ax objective wiring.
    overrides : mapping, optional
        Inline patch applied on top of ``base_app_config`` before it is
        materialized into an :class:`AppConfig`. Useful for quickly switching
        the input PCD directory in a suite without forking the whole base
        config.
    hyperparameters : sequence, optional
        The tool YAML's ``hyperparameters:`` block (raw mapping form). Passed
        through to the adapter so its parameter→AppConfig resolution sees the
        same definitions Ax samples from.
    yaml_path : Path, optional
        Tool YAML location, used to resolve ``base_app_config`` if it is a
        relative filesystem path.
    """

    base_cfg = _load_base_app_dictconfig(base_app_config, yaml_path)
    if overrides:
        patch = OmegaConf.create(_to_plain(overrides))
        base_cfg = OmegaConf.merge(base_cfg, patch)

    app_cfg = _build_app_config(base_cfg)
    param_defs = [SweepParameter.from_mapping(entry) for entry in (hyperparameters or [])]

    return Iof3dCallableAdapter(
        base_config=app_cfg,
        param_defs=param_defs,
        pipeline_kwargs=dict(run_kwargs or {}),
        objective_name=objective_name,
        minimize=minimize,
        logger=logger,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _load_base_app_dictconfig(ref: str | None, yaml_path: Path | None) -> DictConfig:
    """Load the iof3D ``app:`` section from a YAML reference."""

    if ref is None:
        ref = _DEFAULT_BASE_APP_CONFIG

    yaml_path_str = _resolve_yaml_path(ref, yaml_path)
    raw = OmegaConf.load(yaml_path_str)
    if not isinstance(raw, DictConfig):
        raise TypeError(f"base_app_config at {yaml_path_str} did not parse to a mapping")
    return raw


def _resolve_yaml_path(ref: str, yaml_path: Path | None) -> str:
    if ref.startswith("pkg://"):
        # pkg://iof3D.conf/app/base.yaml -> resolve via importlib.resources
        module_path, _, sub = ref[len("pkg://") :].partition("/")
        from importlib import resources

        try:
            traversable = resources.files(module_path).joinpath(sub)
        except ModuleNotFoundError as exc:
            raise FileNotFoundError(
                f"Cannot resolve {ref!r}: package {module_path!r} is not importable"
            ) from exc
        return str(traversable)

    p = Path(ref)
    if not p.is_absolute() and yaml_path is not None:
        p = (yaml_path.parent / p).resolve()
    if not p.exists():
        raise FileNotFoundError(f"base_app_config {ref!r} not found at {p}")
    return str(p)


def _to_plain(obj: Any) -> Any:
    if isinstance(obj, DictConfig):
        return OmegaConf.to_container(obj, resolve=True)
    if isinstance(obj, Mapping):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


__all__ = ["build_iof3d_adapter"]
