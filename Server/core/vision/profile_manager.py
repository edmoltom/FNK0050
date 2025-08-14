import json
from typing import Optional, Dict, Any

from .detectors.contour_detector import (
    ProcConfig,
    MorphConfig,
    GeoFilters,
    Weights,
    PreMorphPatches,
    ColorGateConfig,
)
from .dynamic_adjuster import CannyConfig

class ProfileManager:
    """Load detector and adjuster configuration from JSON profiles."""
    def __init__(self, path: str) -> None:
        self.path = path
        self.load()

    def load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.proc = ProcConfig(
            proc_w=int(data.get("PROC_W", ProcConfig().proc_w)),
            proc_h=int(data.get("PROC_H", ProcConfig().proc_h)),
            blur_k=int(data.get("BLUR_K", ProcConfig().blur_k)),
            border_margin=int(data.get("BORDER_MARGIN", ProcConfig().border_margin)),
        )
        self.canny = CannyConfig(
            t1_init=float(data.get("T1_INIT", CannyConfig().t1_init)),
            t2_ratio=float(data.get("T2_RATIO", CannyConfig().t2_ratio)),
            life_min=float(data.get("life_MIN", CannyConfig().life_min)),
            life_max=float(data.get("life_MAX", CannyConfig().life_max)),
            rescue_life_min=float(data.get("RESCUE_life_MIN", CannyConfig().rescue_life_min)),
            kp=float(data.get("Kp", CannyConfig().kp)),
            max_iter=int(data.get("MAX_ITER", CannyConfig().max_iter)),
        )
        self.morph = MorphConfig(
            close_min=int(data.get("CLOSE_MIN", MorphConfig().close_min)),
            close_max=int(data.get("CLOSE_MAX", MorphConfig().close_max)),
            dil_min=int(data.get("DIL_MIN", MorphConfig().dil_min)),
            dil_max=int(data.get("DIL_MAX", MorphConfig().dil_max)),
            steps=int(data.get("MORPH_STEPS", MorphConfig().steps)),
        )
        self.geo = GeoFilters(
            ar_min=float(data.get("AR_MIN", GeoFilters().ar_min)),
            ar_max=float(data.get("AR_MAX", GeoFilters().ar_max)),
            bbox_hard_cap=float(data.get("BBOX_HARD_CAP", GeoFilters().bbox_hard_cap)),
            bbox_min=float(data.get("BBOX_MIN", GeoFilters().bbox_min)),
            bbox_max=float(data.get("BBOX_MAX", GeoFilters().bbox_max)),
            fill_min=float(data.get("FILL_MIN", GeoFilters().fill_min)),
            fill_max=float(data.get("FILL_MAX", GeoFilters().fill_max)),
            min_area_frac=float(data.get("MIN_AREA_FRAC", GeoFilters().min_area_frac)),
        )
        self.w = Weights(
            area=float(data.get("W_AREA", Weights().area)),
            fill=float(data.get("W_FILL", Weights().fill)),
            solidity=float(data.get("W_SOLI", Weights().solidity)),
            circular=float(data.get("W_CIRC", Weights().circular)),
            rect=float(data.get("W_RECT", Weights().rect)),
            ar=float(data.get("W_AR", Weights().ar)),
            center_bias=float(data.get("CENTER_BIAS", Weights().center_bias)),
            dist=float(data.get("W_DIST", Weights().dist)),
        )
        self.premorph = PreMorphPatches(
            bottom_margin_pct=int(data.get("BOTTOM_MARGIN_PCT", PreMorphPatches().bottom_margin_pct)),
            min_blob_px=int(data.get("MIN_BLOB_PX", PreMorphPatches().min_blob_px)),
            fill_from_edges=bool(data.get("FILL_FROM_EDGES", PreMorphPatches().fill_from_edges)),
        )
        cg = data.get("COLOR_GATE", {}) or {}
        hsv = cg.get("hsv", {})
        self.color = ColorGateConfig(
            enabled=bool(cg.get("enable", False)),
            mode=str(cg.get("mode", "lab_bg")),
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

    def reload(self, path: Optional[str] = None) -> None:
        if path:
            self.path = path
        self.load()

    def get_detector_config(self) -> Dict[str, Any]:
        return dict(
            proc=self.proc,
            morph=self.morph,
            geo=self.geo,
            w=self.w,
            premorph=self.premorph,
            color=self.color,
        )

    def get_canny_config(self) -> CannyConfig:
        return self.canny
