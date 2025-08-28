"""Configuration models and helpers for the vision subsystem.

This module replaces the previous ``profile_manager`` mechanism by
providing structured dataclasses that describe the configuration of the
vision engine, detectors and logging facilities.  Configuration data is
expected to be provided as YAML and mapped to these structures with
strict validation (unknown keys raise ``ValueError``).
"""

from __future__ import annotations

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
    big: DetectorConfig = field(default_factory=DetectorConfig)
    small: DetectorConfig = field(default_factory=DetectorConfig)


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
        engine=_strict(EngineConfig, raw.get("engine") or {}),
        detectors=DetectorsConfig(
            big=_strict(DetectorConfig, raw.get("detectors", {}).get("big", {})),
            small=_strict(DetectorConfig, raw.get("detectors", {}).get("small", {})),
        ),
        logging=_strict(LoggingConfig, raw.get("logging") or {}),
    )
    return merge_with_defaults(cfg)

