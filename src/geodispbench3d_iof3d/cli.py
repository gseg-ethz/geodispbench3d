"""Console entrypoint for iof3D-flavored geodispbench3d sweeps.

Replaces the previous ``iof3d-ax`` CLI. Reads an iof3D ``AppConfig`` via the
existing Hydra plumbing in ``iof3D.v2.cli_hydra``, then constructs an
:class:`~geodispbench3d_iof3d.adapter.Iof3dCallableAdapter` and runs the sweep
through :class:`geodispbench3d.sweep.runner.AxSweepRunner`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from iof3D.v2.cli_hydra import _build_app_config, _to_path
from omegaconf import DictConfig

from geodispbench3d.sweep.parameters import (
    build_parameter_specs,
    load_sweep_config,
)
from geodispbench3d.sweep.runner import AxSweepRunner

from .adapter import Iof3dCallableAdapter


def _collect_run_kwargs(run_cfg: Mapping[str, object] | None) -> dict[str, object]:
    cfg = run_cfg or {}
    if isinstance(cfg, Mapping):
        getter = cfg.get  # type: ignore[assignment]
    else:  # pragma: no cover - defensive

        def getter(_k, default=None):  # type: ignore[no-redef]
            return default

    pcd_paths_cfg = getter("pcd_paths")
    pcd_paths: list[Path] | None = None
    if pcd_paths_cfg:
        pcd_paths = []
        if isinstance(pcd_paths_cfg, (str, Path)):
            candidates = [Path(pcd_paths_cfg)]
        else:
            try:
                candidates = [Path(p) for p in pcd_paths_cfg]
            except TypeError:
                candidates = [Path(pcd_paths_cfg)]

        logger = logging.getLogger("geodispbench3d_iof3d.cli")
        for candidate in candidates:
            if candidate.is_dir():
                ply_files = sorted(candidate.glob("*.ply"))
                if not ply_files:
                    logger.warning("No PLY files found in %s", candidate)
                pcd_paths.extend(ply_files)
            else:
                pcd_paths.append(candidate)

        if not pcd_paths:
            pcd_paths = None

    features = list(getter("features", []) or [])
    if not features:
        features = None

    return {
        "pcd_paths": pcd_paths,
        "features": features,
        "cache_dir": _to_path(getter("cache_dir")),
        "work_root": _to_path(getter("work_root")),
        "max_feature_workers": int(getter("max_feature_workers", 16)),
    }


@hydra.main(version_base=None, config_path="conf", config_name="config_ax")
def main(cfg: DictConfig) -> None:
    run_section = cfg.get("run") or {}
    log_level_name = str(run_section.get("log_level", "INFO")).upper()
    root_level_name = str(run_section.get("root_log_level", log_level_name)).upper()

    log_level = getattr(logging, log_level_name, logging.INFO)
    root_level = getattr(logging, root_level_name, log_level)

    logger = logging.getLogger("geodispbench3d_iof3d.cli")
    logger.setLevel(log_level)
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    if not logger.handlers and not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] - %(message)s")
        )
        logger.addHandler(handler)

    app_cfg = _build_app_config(cfg.get("app"))
    sweep_cfg = load_sweep_config(cfg.get("hparam"))
    run_kwargs = _collect_run_kwargs(run_section)

    parameter_specs = build_parameter_specs(sweep_cfg)

    try:
        output_dir = HydraConfig.get().runtime.output_dir
    except Exception:  # pragma: no cover - hydra runtime absent
        output_dir = str(Path.cwd())
    trial_log_path = Path(output_dir) / "trial_hashes.txt"

    adapter = Iof3dCallableAdapter(
        base_config=app_cfg,
        param_defs=sweep_cfg.parameters,
        pipeline_kwargs=run_kwargs,
        objective_name=sweep_cfg.objective_name,
        minimize=sweep_cfg.minimize,
        logger=logger,
    )

    runner = AxSweepRunner(
        adapter=adapter,
        sweep_config=sweep_cfg,
        parameter_specs=parameter_specs,
        objective_name=sweep_cfg.objective_name,
        minimize=sweep_cfg.minimize,
        logger=logger,
        trial_log_path=trial_log_path,
        experiment_name="iof3d_ax_sweep",
    )

    logger.info(
        "Starting Ax sweep (max_trials=%d, objective=%s)",
        sweep_cfg.max_trials,
        sweep_cfg.objective_name,
    )
    best = runner.run(max_trials=sweep_cfg.max_trials)
    logger.info("Best trial: %s", best)


if __name__ == "__main__":  # pragma: no cover
    main()
