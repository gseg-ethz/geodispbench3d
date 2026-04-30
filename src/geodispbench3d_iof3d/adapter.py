"""iof3D ToolAdapter for geodispbench3d sweeps.

This module is the only place in the new package layout that imports from
``iof3D.*``. It translates Ax trial parameters into an :class:`AppConfig`,
invokes ``run_flow_pipeline`` in-process, and reports outputs back as a
:class:`~geodispbench3d.tool.base.TrialResult`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping as MappingABC
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from omegaconf import OmegaConf

from geodispbench3d.sweep.parameters import SweepParameter, is_active
from geodispbench3d.sweep.trial_record import (
    initialize_trial_record,
    store_trial_failure,
    store_trial_metadata,
)
from geodispbench3d.tool.base import ToolAdapter, TrialOutputs, TrialRequest, TrialResult

from iof3D.v2.api.pipeline_runner import (
    FlowPipelineError,
    FlowPipelineResult,
    run_flow_pipeline,
)
from iof3D.v2.config.settings import AppConfig, FlowSettings, sanitize_interp_params
from pc2img.core import ImgRes
from pchandler.geometry.spherical import Angle


class Iof3dCallableAdapter(ToolAdapter):
    """In-process adapter calling :func:`run_flow_pipeline` per trial."""

    id = "iof3d"
    in_process_safe = True

    def __init__(
        self,
        *,
        base_config: AppConfig,
        param_defs: Sequence[SweepParameter],
        pipeline_kwargs: Mapping[str, Any] | None = None,
        objective_name: str = "runtime_seconds",
        minimize: bool = True,
        logger: logging.Logger | None = None,
    ) -> None:
        self._base_config = base_config
        self._param_defs = list(param_defs)
        self._pipeline_kwargs = dict(pipeline_kwargs or {})
        self._objective_name = objective_name
        self._minimize = minimize
        self._logger = logger or logging.getLogger("geodispbench3d_iof3d.adapter")

    def run_trial(self, request: TrialRequest) -> TrialResult:
        applied_cfg = build_app_config_from_parameters(
            self._base_config, request.parameters, self._param_defs
        )

        run_dir_holder: dict[str, Path] = {}

        def _record_run_dir(run_dir: Path) -> None:
            run_dir_holder["path"] = run_dir
            initialize_trial_record(run_dir, request.parameters, run_hash=run_dir.name)

        start = time.perf_counter()
        try:
            result = run_flow_pipeline(
                applied_cfg,
                logger=self._logger,
                run_dir_callback=_record_run_dir,
                **self._pipeline_kwargs,
            )
        except FlowPipelineError as exc:
            duration = time.perf_counter() - start
            failure_dir = run_dir_holder.get("path") or exc.run_dir
            store_trial_failure(
                failure_dir, request.parameters, duration, exc.cause
            )
            return TrialResult(
                outputs=TrialOutputs(run_dir=Path(failure_dir)),
                scalar_metrics={"runtime_seconds": duration},
                duration_seconds=duration,
                success=False,
                error=str(exc.cause),
            )

        duration = time.perf_counter() - start
        outputs = _outputs_from_result(result, run_dir_holder.get("path"))
        objective_value = duration if self._minimize else -duration
        scalar_metrics = {
            "runtime_seconds": duration,
            self._objective_name: objective_value,
        }
        store_trial_metadata(
            outputs.run_dir,
            request.parameters,
            scalar_metrics,
            duration,
            predictions=outputs.predictions,
            figures=outputs.figures,
            extras={
                "active_parameters": _extract_active_parameters(
                    request.parameters, self._param_defs, self._base_config
                ),
                "hydra_config": _write_hydra_config(
                    outputs.run_dir, applied_cfg, self._pipeline_kwargs
                ),
            },
        )
        return TrialResult(
            outputs=outputs,
            scalar_metrics=scalar_metrics,
            duration_seconds=duration,
            success=True,
        )


# ---------------------------------------------------------------------------
# Parameter → AppConfig translation
# ---------------------------------------------------------------------------


def build_app_config_from_parameters(
    base: AppConfig,
    parameters: Mapping[str, Any],
    param_defs: Sequence[SweepParameter],
) -> AppConfig:
    """Return a copy of ``base`` with sweep parameters injected.

    Mirrors the previous ``iof3D_analysis.ax.sweep.apply_parameters`` so any
    existing hyperparameter YAML continues to work verbatim.
    """

    values = dict(parameters)
    lookup = {p.name: p for p in param_defs}

    def _resolve(name: str, default: Any) -> Any:
        param_def = lookup.get(name)
        if param_def is None:
            return values.get(name, default)
        if not is_active(param_def, values, _BaseConfigLookup(base)):
            return default
        return values.get(name, default)

    def _resolve_alias(names: tuple[str, ...], default: Any) -> Any:
        for name in names:
            if name in values:
                return _resolve(name, default)
        return default

    width_default = base.image.img_res.width
    height_default = base.image.img_res.height
    angular_default = base.image.angular_res
    resolution_override = _resolve("image.img_res.resolution", None)
    if resolution_override is not None:
        try:
            img_width, img_height = _coerce_image_resolution(resolution_override)
        except ValueError as exc:
            raise ValueError(
                f"Invalid image resolution override: {resolution_override!r}"
            ) from exc
    else:
        img_width = int(_resolve("image.img_res.width", width_default))
        img_height = int(_resolve("image.img_res.height", height_default))
    angular_override = _resolve("image.angular_res", angular_default)
    if isinstance(angular_override, Angle):
        angular_res = angular_override
    else:
        angular_res = Angle.parse(str(angular_override))
    raw_interp_key = _resolve("image.interp_key", base.image.interp_key)
    interp_key = (
        str(raw_interp_key) if raw_interp_key is not None else base.image.interp_key
    )
    interp_params = sanitize_interp_params(base.image.interp_params, interp_key)
    image_cfg = replace(
        base.image,
        img_res=ImgRes(img_width, img_height),
        angular_res=angular_res,
        interp_key=interp_key,
        interp_params=interp_params,
    )

    opencv_detector = _resolve_alias(
        ("flow.opencv.detector", "flow.opencv_detector"), base.flow.opencv_detector
    )
    if isinstance(opencv_detector, str):
        opencv_detector = opencv_detector.lower()
    if opencv_detector not in {"sift", "kaze"}:
        opencv_detector = base.flow.opencv_detector

    opencv_matcher = _resolve_alias(
        ("flow.opencv.matcher", "flow.opencv_matcher"), base.flow.opencv_matcher
    )
    if isinstance(opencv_matcher, str):
        opencv_matcher = opencv_matcher.lower()
    if opencv_matcher not in {"bf"}:
        opencv_matcher = base.flow.opencv_matcher

    ratio_value = _resolve_alias(
        ("flow.opencv.ratio_test", "flow.opencv_ratio_test"), base.flow.opencv_ratio_test
    )
    try:
        opencv_ratio_test = float(ratio_value)
    except (TypeError, ValueError):
        opencv_ratio_test = base.flow.opencv_ratio_test
    else:
        if not (0.0 < opencv_ratio_test < 1.0):
            opencv_ratio_test = base.flow.opencv_ratio_test

    opencv_cross_check = bool(
        _resolve_alias(
            ("flow.opencv.cross_check", "flow.opencv_cross_check"),
            base.flow.opencv_cross_check,
        )
    )

    max_feat_value = _resolve_alias(
        ("flow.opencv.max_features", "flow.opencv_max_features"),
        base.flow.opencv_max_features,
    )
    if max_feat_value is None:
        opencv_max_features = None
    else:
        try:
            parsed = int(max_feat_value)
            opencv_max_features = parsed if parsed > 0 else None
        except (TypeError, ValueError):
            opencv_max_features = base.flow.opencv_max_features

    method_value = _resolve("flow.method", base.flow.method)
    if method_value == "fft":
        method_value = "fft_local"
    elif method_value == "opencv":
        method_value = "opencv_feature_match"

    flow_cfg = FlowSettings(
        method=method_value,
        feature=_resolve("flow.feature", base.flow.feature),
        of_model=base.flow.of_model,
        of_ckpt_path=base.flow.of_ckpt_path,
        ptl_memory_fallback_scale=_resolve(
            "flow.ptl_memory_fallback_scale", base.flow.ptl_memory_fallback_scale
        ),
        ptl_memory_fallback_attempts=_resolve(
            "flow.ptl_memory_fallback_attempts", base.flow.ptl_memory_fallback_attempts
        ),
        ptl_memory_min_scale_factor=_resolve(
            "flow.ptl_memory_min_scale_factor", base.flow.ptl_memory_min_scale_factor
        ),
        ptl_memory_min_size=_resolve(
            "flow.ptl_memory_min_size", base.flow.ptl_memory_min_size
        ),
        ptl_memory_clear_cache=_resolve(
            "flow.ptl_memory_clear_cache", base.flow.ptl_memory_clear_cache
        ),
        ptl_interpolation_mode=_resolve(
            "flow.ptl_interpolation_mode", base.flow.ptl_interpolation_mode
        ),
        fft_patch_size=_resolve_alias(
            ("flow.fft.patch_size", "flow.fft_patch_size"), base.flow.fft_patch_size
        ),
        fft_step=_resolve_alias(("flow.fft.step", "flow.fft_step"), base.flow.fft_step),
        fft_device=_resolve_alias(
            ("flow.fft.device", "flow.fft_device"), base.flow.fft_device
        ),
        fft_strategy=_resolve_alias(
            ("flow.fft.strategy", "flow.fft_strategy"), base.flow.fft_strategy
        ),
        fft_weight=_resolve_alias(
            ("flow.fft.weight", "flow.fft_weight"), base.flow.fft_weight
        ),
        fft_keep_confidence=bool(
            _resolve_alias(
                ("flow.fft.keep_confidence", "flow.fft_keep_confidence"),
                base.flow.fft_keep_confidence,
            )
        ),
        fft_upsample_factor=_resolve_alias(
            ("flow.fft.upsample_factor", "flow.fft_upsample_factor"),
            base.flow.fft_upsample_factor,
        ),
        fft_levels=_resolve_alias(
            ("flow.fft.levels", "flow.fft_levels"), base.flow.fft_levels
        ),
        fft_scale_factor=_resolve_alias(
            ("flow.fft.scale_factor", "flow.fft_scale_factor"), base.flow.fft_scale_factor
        ),
        fft_warp=bool(
            _resolve_alias(("flow.fft.warp_right", "flow.fft_warp"), base.flow.fft_warp)
        ),
        fft_n_jobs=_resolve("flow.fft_n_jobs", base.flow.fft_n_jobs),
        geocosi_patch_size=_resolve(
            "flow.geocosi_patch_size", base.flow.geocosi_patch_size
        ),
        geocosi_levels=_resolve("flow.geocosi_levels", base.flow.geocosi_levels),
        geocosi_step=_resolve("flow.geocosi_step", base.flow.geocosi_step),
        geocosi_border_refine_enabled=bool(
            _resolve(
                "flow.geocosi_border_refine_enabled",
                base.flow.geocosi_border_refine_enabled,
            )
        ),
        geocosi_border_refine_strip_width=_resolve(
            "flow.geocosi_border_refine_strip_width",
            base.flow.geocosi_border_refine_strip_width,
        ),
        geocosi_border_refine_patch_size=_resolve(
            "flow.geocosi_border_refine_patch_size",
            base.flow.geocosi_border_refine_patch_size,
        ),
        geocosi_border_refine_levels=_resolve(
            "flow.geocosi_border_refine_levels",
            base.flow.geocosi_border_refine_levels,
        ),
        geocosi_border_refine_step=_resolve(
            "flow.geocosi_border_refine_step",
            base.flow.geocosi_border_refine_step,
        ),
        geocosi_border_refine_mask_threshold=_resolve(
            "flow.geocosi_border_refine_mask_threshold",
            base.flow.geocosi_border_refine_mask_threshold,
        ),
        geocosi_border_refine_pad=_resolve(
            "flow.geocosi_border_refine_pad",
            base.flow.geocosi_border_refine_pad,
        ),
        convert_features_to_image=_resolve(
            "flow.convert_features_to_image",
            base.flow.convert_features_to_image,
        ),
        color_max_quantile=_resolve(
            "flow.color_max_quantile", base.flow.color_max_quantile
        ),
        mapping_mode=_resolve("flow.mapping_mode", base.flow.mapping_mode),
        opencv_detector=opencv_detector,
        opencv_matcher=opencv_matcher,
        opencv_ratio_test=opencv_ratio_test,
        opencv_cross_check=opencv_cross_check,
        opencv_max_features=opencv_max_features,
    )

    preset = _resolve("flow.ptlflow_preset", None)
    if preset:
        flow_cfg = _apply_ptlflow_preset(flow_cfg, str(preset))

    replace_nan = _resolve("replace_nan_strategy", base.replace_nan_strategy)

    return AppConfig(
        pcd_directory=base.pcd_directory,
        image=image_cfg,
        tiling=base.tiling,
        flow=flow_cfg,
        replace_nan_strategy=replace_nan,
        save_images=base.save_images,
        image_dir=base.image_dir,
        save_flow_image=base.save_flow_image,
        optimize_memory=base.optimize_memory,
        cache_path=base.cache_path,
        memory_pressure_watchdog=base.memory_pressure_watchdog,
    )


def _apply_ptlflow_preset(flow: FlowSettings, preset: str) -> FlowSettings:
    if ":" not in preset:
        model, ckpt = preset, flow.of_ckpt_path or "things"
    else:
        model, ckpt = preset.split(":", 1)
    return FlowSettings(
        method="ptlflow",
        feature=flow.feature,
        of_model=model,
        of_ckpt_path=ckpt,
        ptl_memory_fallback_scale=flow.ptl_memory_fallback_scale,
        ptl_memory_fallback_attempts=flow.ptl_memory_fallback_attempts,
        ptl_memory_min_scale_factor=flow.ptl_memory_min_scale_factor,
        ptl_memory_min_size=flow.ptl_memory_min_size,
        ptl_memory_clear_cache=flow.ptl_memory_clear_cache,
        ptl_interpolation_mode=flow.ptl_interpolation_mode,
        fft_patch_size=flow.fft_patch_size,
        fft_n_jobs=flow.fft_n_jobs,
        geocosi_patch_size=flow.geocosi_patch_size,
        geocosi_levels=flow.geocosi_levels,
        geocosi_step=flow.geocosi_step,
        geocosi_border_refine_enabled=flow.geocosi_border_refine_enabled,
        geocosi_border_refine_strip_width=flow.geocosi_border_refine_strip_width,
        geocosi_border_refine_patch_size=flow.geocosi_border_refine_patch_size,
        geocosi_border_refine_levels=flow.geocosi_border_refine_levels,
        geocosi_border_refine_step=flow.geocosi_border_refine_step,
        geocosi_border_refine_mask_threshold=flow.geocosi_border_refine_mask_threshold,
        geocosi_border_refine_pad=flow.geocosi_border_refine_pad,
        convert_features_to_image=flow.convert_features_to_image,
        color_max_quantile=flow.color_max_quantile,
    )


# ---------------------------------------------------------------------------
# Helpers for trial output / metadata
# ---------------------------------------------------------------------------


class _BaseConfigLookup:
    """Adapter that exposes dotted-path lookups against an AppConfig."""

    def __init__(self, base: AppConfig) -> None:
        self._base = base

    def get(self, dotted: str, default: Any = None) -> Any:
        parts = dotted.split(".")
        current: Any = self._base
        for part in parts:
            current = getattr(current, part, default)
            if current is default:
                return default
        return current


def _outputs_from_result(
    result: FlowPipelineResult, run_dir_override: Path | None
) -> TrialOutputs:
    run_dir = Path(run_dir_override or result.run_dir)
    return TrialOutputs(
        run_dir=run_dir,
        predictions=tuple(Path(p) for p in result.leaf_pointclouds)
        + tuple(Path(p) for p in result.merged_pointclouds),
        figures=tuple(Path(p) for p in result.flow_figures),
    )


def _extract_active_parameters(
    parameters: Mapping[str, Any],
    param_defs: Sequence[SweepParameter] | None,
    base_cfg: AppConfig | None,
) -> dict[str, Any]:
    if not param_defs or base_cfg is None:
        return dict(parameters)
    lookup_obj = _BaseConfigLookup(base_cfg)
    lookup = {param.name: param for param in param_defs}
    active: dict[str, Any] = {}
    for name, value in parameters.items():
        param_def = lookup.get(name)
        if param_def is None:
            active[name] = value
            continue
        if is_active(param_def, parameters, lookup_obj):
            active[name] = value
    return active


def _write_hydra_config(
    run_dir: Path,
    app_cfg: AppConfig,
    run_kwargs: Mapping[str, Any] | None,
) -> str:
    payload: dict[str, Any] = {"app": _build_hydra_app_config(app_cfg)}
    run_section = _build_hydra_run_config(run_kwargs)
    if run_section:
        payload["run"] = run_section
    out_dir = Path(run_dir) / "ax_trial"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "config.yaml"
    OmegaConf.save(OmegaConf.create(payload), str(path))
    try:
        return str(path.relative_to(run_dir))
    except ValueError:
        return str(path)


def _build_hydra_app_config(app_cfg: AppConfig) -> dict[str, Any]:
    image_cfg = {
        "img_res": {
            "width": int(app_cfg.image.img_res.width),
            "height": int(app_cfg.image.img_res.height),
        },
        "angular_res": str(app_cfg.image.angular_res),
        "proj_key": app_cfg.image.proj_key,
        "interp_key": app_cfg.image.interp_key,
    }
    if app_cfg.image.proj_params:
        image_cfg["proj_params"] = _serialize_value_for_config(app_cfg.image.proj_params)
    if app_cfg.image.interp_params:
        image_cfg["interp_params"] = _serialize_value_for_config(
            app_cfg.image.interp_params
        )

    tiling_cfg = {
        "remove_empty": bool(app_cfg.tiling.remove_empty),
        "n_jobs": int(app_cfg.tiling.n_jobs),
        "method": app_cfg.tiling.method,
    }

    flow_cfg = app_cfg.flow.to_nested_dict()

    app_section: dict[str, Any] = {
        "pcd_directory": str(app_cfg.pcd_directory),
        "image": image_cfg,
        "tiling": tiling_cfg,
        "flow": flow_cfg,
        "replace_nan_strategy": str(app_cfg.replace_nan_strategy),
        "save_images": bool(app_cfg.save_images),
        "save_flow_image": bool(app_cfg.save_flow_image),
        "optimize_memory": bool(app_cfg.optimize_memory),
    }

    if app_cfg.image_dir is not None:
        app_section["image_dir"] = str(app_cfg.image_dir)
    if app_cfg.cache_path is not None:
        app_section["cache_path"] = str(app_cfg.cache_path)

    watchdog_cfg = app_cfg.memory_pressure_watchdog
    if watchdog_cfg is not None:
        app_section["memory_pressure_watchdog"] = {
            "enabled": bool(watchdog_cfg.enabled),
            "some_avg10_threshold": watchdog_cfg.some_avg10_threshold,
            "full_avg10_threshold": watchdog_cfg.full_avg10_threshold,
            "sample_interval_s": watchdog_cfg.sample_interval_s,
            "min_sleep_s": watchdog_cfg.min_sleep_s,
            "max_sleep_s": watchdog_cfg.max_sleep_s,
            "backoff_factor": watchdog_cfg.backoff_factor,
            "recovery_factor": watchdog_cfg.recovery_factor,
            "throttle_log_every_s": watchdog_cfg.throttle_log_every_s,
            "pressure_file": str(watchdog_cfg.pressure_file)
            if watchdog_cfg.pressure_file
            else None,
        }

    return app_section


def _build_hydra_run_config(run_kwargs: Mapping[str, Any] | None) -> dict[str, Any]:
    if not run_kwargs:
        return {}
    data = dict(run_kwargs)
    run_section: dict[str, Any] = {}

    pcd_paths = data.get("pcd_paths")
    if pcd_paths:
        run_section["pcd_paths"] = [str(Path(p)) for p in pcd_paths]

    features = data.get("features")
    if features:
        run_section["features"] = list(features)

    cache_dir = data.get("cache_dir")
    if cache_dir is not None:
        run_section["cache_dir"] = str(Path(cache_dir))

    work_root = data.get("work_root")
    if work_root is not None:
        run_section["work_root"] = str(Path(work_root))

    if "max_feature_workers" in data and data["max_feature_workers"] is not None:
        run_section["max_feature_workers"] = int(data["max_feature_workers"])

    if "memory_log_threshold_pct" in data and data["memory_log_threshold_pct"] is not None:
        run_section["memory_log_threshold_pct"] = data["memory_log_threshold_pct"]

    return run_section


def _serialize_value_for_config(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Angle):
        return str(value)
    if isinstance(value, MappingABC):
        return {str(k): _serialize_value_for_config(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialize_value_for_config(v) for v in value]
    return value


def _coerce_image_resolution(value: Any) -> tuple[int, int]:
    if isinstance(value, ImgRes):
        return int(value.width), int(value.height)
    if isinstance(value, MappingABC):
        mapping = dict(value)
        width = mapping.get("width") or mapping.get("w")
        height = mapping.get("height") or mapping.get("h")
        if width is None or height is None:
            raise ValueError("Mapping must include width and height")
        return int(width), int(height)
    if isinstance(value, str):
        token = value.lower().replace(" ", "")
        separator = "x" if "x" in token else ","
        parts = token.split(separator)
        if len(parts) != 2:
            raise ValueError(
                f"Expected '<width>x<height>' or '<width>,<height>', got {value!r}"
            )
        return int(parts[0]), int(parts[1])
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        seq = list(value)
        if len(seq) < 2:
            raise ValueError("Sequence must provide width and height")
        return int(seq[0]), int(seq[1])
    raise ValueError(f"Unsupported resolution format: {value!r}")


__all__ = ["Iof3dCallableAdapter", "build_app_config_from_parameters"]
