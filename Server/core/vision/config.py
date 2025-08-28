"""Configuration models and helpers for the vision subsystem.

This module replaces the previous ``profile_manager`` mechanism by
providing structured dataclasses that describe the configuration of the
vision engine, detectors and logging facilities.  Configuration data is
expected to be provided as YAML and mapped to these structures with
strict validation (unknown keys raise ``ValueError``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from .config_defaults import (
    DEFAULT_STABLE,
    DEFAULT_ON_THRESHOLD,
    DEFAULT_OFF_THRESHOLD,
    DEFAULT_STICK_K,
    DEFAULT_MISS_M,
    DEFAULT_ROI_FACTOR,
    DEFAULT_EMA_ALPHA,
)
try:  # pragma: no cover - optional dependency
    from .dynamics import CannyConfig
except Exception:  # pragma: no cover
    @dataclass
    class CannyConfig:  # type: ignore
        t1_init: float = 50.0
        t2_ratio: float = 2.5
        life_min: float = 5.0
        life_max: float = 10.0
        rescue_life_min: float = 3.0
        kp: float = 4.0
        max_iter: int = 25
from .config_defaults import (
    MORPH_CLOSE_MIN,
    MORPH_CLOSE_MAX,
    MORPH_DIL_MIN,
    MORPH_DIL_MAX,
    MORPH_STEPS,
    GEO_AR_MIN,
    GEO_AR_MAX,
    GEO_BBOX_HARD_CAP,
    GEO_BBOX_MIN,
    GEO_BBOX_MAX,
    GEO_FILL_MIN,
    GEO_FILL_MAX,
    GEO_MIN_AREA_FRAC,
    WEIGHT_AREA,
    WEIGHT_FILL,
    WEIGHT_SOLIDITY,
    WEIGHT_CIRCULAR,
    WEIGHT_RECT,
    WEIGHT_AR,
    WEIGHT_CENTER_BIAS,
    WEIGHT_DIST,
    REF_SIZE,
    BLUR_KERNEL,
    BORDER_MARGIN,
    PREMORPH_BOTTOM_MARGIN_PCT,
    PREMORPH_MIN_BLOB_PX,
    PREMORPH_FILL_FROM_EDGES,
    COLORGATE_ENABLED,
    COLORGATE_MODE,
    COLORGATE_AB_THRESH,
    COLORGATE_HSV_LO,
    COLORGATE_HSV_HI,
    COLORGATE_COMBINE,
    COLORGATE_MIN_COVER_PCT,
    COLORGATE_MAX_COVER_PCT,
)

# ---------------------------------------------------------------------------
# Helper utilities

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROFILE_DIR = os.path.join(BASE_DIR, "profiles")
_DEFAULT_BIG = os.path.join(_PROFILE_DIR, "profile_big.json")
_DEFAULT_SMALL = os.path.join(_PROFILE_DIR, "profile_small.json")
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config", "vision.yaml")


@dataclass
class MorphConfig:
    close_min: int = MORPH_CLOSE_MIN
    close_max: int = MORPH_CLOSE_MAX
    dil_min: int = MORPH_DIL_MIN
    dil_max: int = MORPH_DIL_MAX
    steps: int = MORPH_STEPS


@dataclass
class GeoFilters:
    ar_min: float = GEO_AR_MIN
    ar_max: float = GEO_AR_MAX
    bbox_hard_cap: float = GEO_BBOX_HARD_CAP
    bbox_min: float = GEO_BBOX_MIN
    bbox_max: float = GEO_BBOX_MAX
    fill_min: float = GEO_FILL_MIN
    fill_max: float = GEO_FILL_MAX
    min_area_frac: float = GEO_MIN_AREA_FRAC


@dataclass
class Weights:
    area: float = WEIGHT_AREA
    fill: float = WEIGHT_FILL
    solidity: float = WEIGHT_SOLIDITY
    circular: float = WEIGHT_CIRCULAR
    rect: float = WEIGHT_RECT
    ar: float = WEIGHT_AR
    center_bias: float = WEIGHT_CENTER_BIAS
    dist: float = WEIGHT_DIST


@dataclass
class ProcConfig:
    proc_w: int = REF_SIZE[0]
    proc_h: int = REF_SIZE[1]
    blur_k: int = BLUR_KERNEL
    border_margin: int = BORDER_MARGIN


@dataclass
class PreMorphPatches:
    bottom_margin_pct: int = PREMORPH_BOTTOM_MARGIN_PCT
    min_blob_px: int = PREMORPH_MIN_BLOB_PX
    fill_from_edges: bool = PREMORPH_FILL_FROM_EDGES


@dataclass
class ColorGateConfig:
    enabled: bool = COLORGATE_ENABLED
    mode: str = COLORGATE_MODE
    ab_thresh: int = COLORGATE_AB_THRESH
    hsv_lo: tuple[int, int, int] = COLORGATE_HSV_LO
    hsv_hi: tuple[int, int, int] = COLORGATE_HSV_HI
    combine: str = COLORGATE_COMBINE
    min_cover_pct: float = COLORGATE_MIN_COVER_PCT
    max_cover_pct: float = COLORGATE_MAX_COVER_PCT


def configs_from_profile(data: Dict[str, Any]) -> tuple[Dict[str, Any], CannyConfig]:
    proc = ProcConfig(
        proc_w=int(data.get("PROC_W", ProcConfig().proc_w)),
        proc_h=int(data.get("PROC_H", ProcConfig().proc_h)),
        blur_k=int(data.get("BLUR_K", ProcConfig().blur_k)),
        border_margin=int(data.get("BORDER_MARGIN", ProcConfig().border_margin)),
    )
    canny = CannyConfig(
        t1_init=float(data.get("T1_INIT", CannyConfig().t1_init)),
        t2_ratio=float(data.get("T2_RATIO", CannyConfig().t2_ratio)),
        life_min=float(data.get("life_MIN", CannyConfig().life_min)),
        life_max=float(data.get("life_MAX", CannyConfig().life_max)),
        rescue_life_min=float(data.get("RESCUE_life_MIN", CannyConfig().rescue_life_min)),
        kp=float(data.get("Kp", CannyConfig().kp)),
        max_iter=int(data.get("MAX_ITER", CannyConfig().max_iter)),
    )
    morph = MorphConfig(
        close_min=int(data.get("CLOSE_MIN", MorphConfig().close_min)),
        close_max=int(data.get("CLOSE_MAX", MorphConfig().close_max)),
        dil_min=int(data.get("DIL_MIN", MorphConfig().dil_min)),
        dil_max=int(data.get("DIL_MAX", MorphConfig().dil_max)),
        steps=int(data.get("MORPH_STEPS", MorphConfig().steps)),
    )
    geo = GeoFilters(
        ar_min=float(data.get("AR_MIN", GeoFilters().ar_min)),
        ar_max=float(data.get("AR_MAX", GeoFilters().ar_max)),
        bbox_hard_cap=float(data.get("BBOX_HARD_CAP", GeoFilters().bbox_hard_cap)),
        bbox_min=float(data.get("BBOX_MIN", GeoFilters().bbox_min)),
        bbox_max=float(data.get("BBOX_MAX", GeoFilters().bbox_max)),
        fill_min=float(data.get("FILL_MIN", GeoFilters().fill_min)),
        fill_max=float(data.get("FILL_MAX", GeoFilters().fill_max)),
        min_area_frac=float(data.get("MIN_AREA_FRAC", GeoFilters().min_area_frac)),
    )
    w = Weights(
        area=float(data.get("W_AREA", Weights().area)),
        fill=float(data.get("W_FILL", Weights().fill)),
        solidity=float(data.get("W_SOLI", Weights().solidity)),
        circular=float(data.get("W_CIRC", Weights().circular)),
        rect=float(data.get("W_RECT", Weights().rect)),
        ar=float(data.get("W_AR", Weights().ar)),
        center_bias=float(data.get("CENTER_BIAS", Weights().center_bias)),
        dist=float(data.get("W_DIST", Weights().dist)),
    )
    premorph = PreMorphPatches(
        bottom_margin_pct=int(data.get("BOTTOM_MARGIN_PCT", PreMorphPatches().bottom_margin_pct)),
        min_blob_px=int(data.get("MIN_BLOB_PX", PreMorphPatches().min_blob_px)),
        fill_from_edges=bool(data.get("FILL_FROM_EDGES", PreMorphPatches().fill_from_edges)),
    )
    cg = data.get("COLOR_GATE", {}) or {}
    hsv = cg.get("hsv", {})
    color = ColorGateConfig(
        enabled=bool(cg.get("enable", ColorGateConfig().enabled)),
        mode=str(cg.get("mode", ColorGateConfig().mode)),
        ab_thresh=int(cg.get("lab", {}).get("ab_thresh", ColorGateConfig().ab_thresh)),
        hsv_lo=(
            int(hsv.get("h_low", ColorGateConfig().hsv_lo[0])),
            int(hsv.get("s_min", ColorGateConfig().hsv_lo[1])),
            int(hsv.get("v_min", ColorGateConfig().hsv_lo[2])),
        ),
        hsv_hi=(
            int(hsv.get("h_high", ColorGateConfig().hsv_hi[0])),
            ColorGateConfig().hsv_hi[1],
            ColorGateConfig().hsv_hi[2],
        ),
        combine=str(cg.get("combine", ColorGateConfig().combine)),
        min_cover_pct=float(cg.get("min_cover_pct", ColorGateConfig().min_cover_pct)),
        max_cover_pct=float(cg.get("max_cover_pct", ColorGateConfig().max_cover_pct)),
    )
    det_cfg = dict(
        proc=proc,
        morph=morph,
        geo=geo,
        w=w,
        premorph=premorph,
        color=color,
    )
    return det_cfg, canny


def _load_profile(path: str) -> "DetectorConfig":
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    det_cfg, canny_cfg = configs_from_profile(data)
    return DetectorConfig(
        canny=canny_cfg,
        proc=det_cfg["proc"],
        morph=det_cfg["morph"],
        geo=det_cfg["geo"],
        w=det_cfg["w"],
        premorph=det_cfg["premorph"],
        color=det_cfg["color"],
    )

def _strict(cls, data: Dict[str, Any]):
    """Instantiate ``cls`` ensuring ``data`` contains only known keys."""

    try:
        return cls(**data)
    except TypeError as e:  # pragma: no cover - defensive
        raise ValueError(f"Invalid keys for {cls.__name__}: {e}") from e


# ---------------------------------------------------------------------------
# Dataclass models


@dataclass
class EngineConfig:
    stable: bool = DEFAULT_STABLE
    on_th: float = DEFAULT_ON_THRESHOLD
    off_th: float = DEFAULT_OFF_THRESHOLD
    stick_k: int = DEFAULT_STICK_K
    miss_m: int = DEFAULT_MISS_M
    roi_factor: float = DEFAULT_ROI_FACTOR
    ema: float = DEFAULT_EMA_ALPHA
    return_overlay: bool = False


@dataclass
class DetectorConfig:
    canny: CannyConfig = field(default_factory=CannyConfig)
    proc: ProcConfig = field(default_factory=ProcConfig)
    morph: MorphConfig = field(default_factory=MorphConfig)
    geo: GeoFilters = field(default_factory=GeoFilters)
    w: Weights = field(default_factory=Weights)
    premorph: PreMorphPatches = field(default_factory=PreMorphPatches)
    color: ColorGateConfig = field(default_factory=ColorGateConfig)


@dataclass
class DetectorsConfig:
    big: DetectorConfig = field(default_factory=lambda: _load_profile(_DEFAULT_BIG))
    small: DetectorConfig = field(default_factory=lambda: _load_profile(_DEFAULT_SMALL))


@dataclass
class LoggingConfig:
    output_dir: Optional[str] = None
    stride: int = 5
    save_raw: bool = False


@dataclass
class VisionConfig:
    engine: EngineConfig = field(default_factory=EngineConfig)
    detectors: DetectorsConfig = field(default_factory=DetectorsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def merge_with_defaults(self) -> "VisionConfig":
        """Return a copy with missing fields filled from defaults."""

        return merge_with_defaults(self)


# ---------------------------------------------------------------------------
# Public helpers


def merge_with_defaults(cfg: Optional[VisionConfig] = None) -> VisionConfig:
    """Merge ``cfg`` on top of the built-in defaults and return the result."""

    base = VisionConfig()
    if cfg is None:
        return base

    def _merge(dst: Any, src: Any) -> Any:
        if not is_dataclass(dst):
            return src
        for f in fields(dst):
            sv = getattr(src, f.name)
            if sv is None:
                continue
            dv = getattr(dst, f.name)
            if is_dataclass(dv):
                setattr(dst, f.name, _merge(dv, sv))
            else:
                setattr(dst, f.name, sv)
        return dst

    return _merge(base, cfg)


def load_config(path: Optional[str] = None) -> VisionConfig:
    """Load a YAML configuration file and return a ``VisionConfig`` instance.

    Parameters
    ----------
    path:
        Optional path to the configuration file. If ``None`` or a relative
        path, the file is resolved relative to ``DEFAULT_CONFIG_PATH``.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH
    elif not os.path.isabs(path):
        path = os.path.join(os.path.dirname(DEFAULT_CONFIG_PATH), path)

    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if yaml is None:
        raw = {}
    else:
        raw = yaml.safe_load(text) or {}

    cfg = VisionConfig(
        engine=_strict(EngineConfig, raw.get("engine", {})),
        detectors=DetectorsConfig(
            big=_strict(DetectorConfig, raw.get("detectors", {}).get("big", {})),
            small=_strict(DetectorConfig, raw.get("detectors", {}).get("small", {})),
        ),
        logging=_strict(LoggingConfig, raw.get("logging", {})),
    )
    return merge_with_defaults(cfg)

