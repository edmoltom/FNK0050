"""Contour detection pipeline with optional color gating and scoring.

Design notes:
    preprocess (resize+blur) -> auto-canny with rescue -> optional color-gate
    (LAB/HSV) with coverage thresholds -> premorph patches (bottom margin,
    despeckle, fill-from-edges) -> iterative morphology (close/dilate) ->
    contour features -> scoring -> selection -> export overlay/metrics.

    Score formula used in ``imgproc._score_contour``::

        score = area*W_AREA + fill*W_FILL + solidity*W_SOLID +
                circular*W_CIRC + rect*W_RECT + ar*W_AR -
                (dist * center_bias * W_DIST)

    Key metrics tracked include ``t1``/``t2``/``life``, ``chosen_ck``/``dk``,
    ``bbox_ratio``, ``fill``, ``color_cover_pct`` and ``used_rescue``.
"""

import os, json, time
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Dict, Any, Union

import cv2
import numpy as np

from ..config_defaults import (
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
    BOTTOM_MARGIN_MAX,
)
from ..imgproc import (
    pct_on,
    despeckle,
    _preprocess,
    _color_gate,
    _try_with_margins,
    _draw_overlay,
)
from ..dynamic_adjuster import CannyConfig
from .base_detector import BaseDetector
from .results import DetectionResult

NDArray = np.ndarray

# ----------------------- configs -----------------------
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
    center_bias: float = WEIGHT_CENTER_BIAS      # factor applied to dist
    dist: float = WEIGHT_DIST             # distance weight

@dataclass
class ProcConfig:
    proc_w: int = REF_SIZE[0]
    proc_h: int = REF_SIZE[1]
    blur_k: int = BLUR_KERNEL
    border_margin: int = BORDER_MARGIN

@dataclass
class PreMorphPatches:
    bottom_margin_pct: int = PREMORPH_BOTTOM_MARGIN_PCT  # crop bottom X% before morph
    min_blob_px: int = PREMORPH_MIN_BLOB_PX       # despeckle
    fill_from_edges: bool = PREMORPH_FILL_FROM_EDGES # fill strokes to regions

@dataclass
class ColorGateConfig:
    enabled: bool = COLORGATE_ENABLED
    mode: str = COLORGATE_MODE        # 'lab_bg' or 'hsv'
    ab_thresh: int = COLORGATE_AB_THRESH         # Lab distance from global background (a,b)
    hsv_lo: Tuple[int,int,int] = COLORGATE_HSV_LO   # H,S,V (0..179,0..255,0..255)
    hsv_hi: Tuple[int,int,int] = COLORGATE_HSV_HI
    combine: str = COLORGATE_COMBINE         # 'OR' or 'AND' with edges
    min_cover_pct: float = COLORGATE_MIN_COVER_PCT  # ignore if mask <0.5% or >60% of frame
    max_cover_pct: float = COLORGATE_MAX_COVER_PCT


def configs_from_profile(data: Dict[str, Any]) -> Tuple[Dict[str, Any], CannyConfig]:
    """Translate raw profile dict into detector kwargs and CannyConfig."""
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

# ----------------------- detector -----------------------
class ContourDetector(BaseDetector):
    "Contour pipeline + pre-morph patches + optional color-gate + JSON profiles."
    def __init__(
        self,
        proc: ProcConfig = ProcConfig(),
        morph: MorphConfig = MorphConfig(),
        geo: GeoFilters = GeoFilters(),
        w: Weights = Weights(),
        premorph: PreMorphPatches = PreMorphPatches(),
        color: ColorGateConfig = ColorGateConfig(),
        adjuster: Optional["DynamicAdjuster"] = None,
    ) -> None:
        """Initialize the detector with configuration objects.

        Args:
            proc: Preprocessing parameters such as working size and blur.
            morph: Kernel ranges and steps for closing/dilation.
            geo: Geometric filters applied to candidate contours.
            w: Weights used in contour scoring.
            premorph: Patch rules applied before morphology.
            color: Color-gate parameters.
            adjuster: Optional dynamic Canny adjuster; default uses
                :class:`~Server.core.vision.dynamic_adjuster.DynamicAdjuster`.
        """
        self.proc = proc
        self.morph_cfg = morph
        self.geo = geo
        self.w = w
        self.premorph = premorph
        self.color = color
        # DynamicAdjuster injected; if None, use default
        if adjuster is None:
            from ..dynamic_adjuster import DynamicAdjuster, CannyConfig
            adjuster = DynamicAdjuster(CannyConfig())
        self.adjuster = adjuster

    def to_profile_dict(self) -> Dict[str, Any]:
        """Return the current configuration as a JSON-serializable dict."""
        return {
            "proc": asdict(self.proc),
            "canny": asdict(self.adjuster.cfg),
            "morph": asdict(self.morph_cfg),
            "geo": asdict(self.geo),
            "weights": asdict(self.w),
            "premorph": asdict(self.premorph),
            "color_gate": asdict(self.color),
        }

    # ----------------------------- Public API -----------------------------
    def detect(
        self,
        frame: Union[str, NDArray],
        state: Optional[Dict[str, Any]] = None,
        knobs: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """Run the contour detector on a frame.

        Args:
            frame: Image array or path to image file.
            state: Mutable state dictionary (unused).
            knobs: Optional runtime overrides such as ``save_dir`` or
                ``return_overlay``.

        Returns:
            DetectionResult: Structured information about the best contour and
            processing statistics.

        Raises:
            FileNotFoundError: If ``frame`` cannot be loaded.
        """
        if knobs is None:
            knobs = {}
        save_dir = knobs.get("save_dir")
        stamp = knobs.get("stamp")
        save_profile = knobs.get("save_profile", True)
        return_overlay = knobs.get("return_overlay", True)

        img = self._load_image(frame)
        if img is None:
            raise FileNotFoundError(str(frame))

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        if stamp is None:
            stamp = time.strftime("%Y%m%d_%H%M%S")

        # ----- Preprocess -----
        proc, gray = _preprocess(img, self.proc)

        # ----- Dynamic adjuster (auto canny + rescue) -----
        edges, canny, t1, t2, life, used_rescue = self.adjuster.apply(gray)
        if save_dir is not None and used_rescue:
            th = cv2.bitwise_xor(edges, canny)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_thresc.png"), th)

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_canny.png"), canny)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_original.png"), img)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_proc.png"), proc)

        # ----- Color gate (optional) -----
        color_mask = None
        color_cover = 0.0
        color_used = False
        if self.color.enabled:
            color_mask = _color_gate(proc, self.color)
            color_cover = pct_on(color_mask)
            # sanity check: ignore if too small/too big
            if (color_cover < self.color.min_cover_pct) or (color_cover > self.color.max_cover_pct):
                color_mask = None
            else:
                color_used = True
            if save_dir is not None:
                cv2.imwrite(os.path.join(save_dir, f"{stamp}_color_mask.png"),
                            color_mask if color_mask is not None else np.zeros_like(edges))

        # ----- Pre-morph patches -----
        H, W = edges.shape[:2]
        edges2 = edges.copy()
        crop = int(max(0, min(BOTTOM_MARGIN_MAX, self.premorph.bottom_margin_pct)) * H / 100.0)
        if crop > 0:
            edges2[-crop:, :] = 0

        edges2 = despeckle(edges2, int(self.premorph.min_blob_px))

        if self.premorph.fill_from_edges:
            filled = np.zeros_like(edges2)
            cnts, _ = cv2.findContours(edges2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(filled, cnts, -1, 255, thickness=cv2.FILLED)
            edges2 = filled

        # apply same crop/despeckle to color and combine
        if color_mask is not None:
            cm = color_mask.copy()
            if crop > 0:
                cm[-crop:, :] = 0
            cm = despeckle(cm, int(self.premorph.min_blob_px // 2))
            if self.color.combine.upper() == "AND":
                edges2 = cv2.bitwise_and(edges2, cm)
            else:
                edges2 = cv2.bitwise_or(edges2, cm)

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_edges_patched.png"), edges2)

        # ----- Main selection -----
        best, e_used = _try_with_margins(edges2, self.proc, self.morph_cfg, self.geo, self.w)
        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_edges_used.png"), e_used)

        if best is None:
            if save_dir is not None:
                cv2.imwrite(os.path.join(save_dir, f"{stamp}_mask_final.png"), e_used)
            return DetectionResult(
                ok=False,
                used_rescue=used_rescue,
                life_canny_pct=float(life),
                t1=float(t1), t2=int(t2),
                color_cover_pct=float(color_cover),
                color_used=bool(color_used),
            )

        mask_final, info, chosen_ck, chosen_dk = best
        overlay, center = _draw_overlay(proc, info, mask_final, self.color.enabled)

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_mask_final.png"), mask_final)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_overlay.png"), overlay)

        result = DetectionResult(
            ok=True,
            used_rescue=used_rescue,
            life_canny_pct=float(life),
            bbox=tuple(int(v) for v in info["bbox"]),
            score=float(info["score"]),
            fill=float(info["fill"]),
            bbox_ratio=float(info["bbox_ratio"]),
            chosen_ck=int(chosen_ck),
            chosen_dk=int(chosen_dk),
            center=center,
            overlay=overlay if return_overlay else None,
            t1=float(t1), t2=int(t2),
            color_cover_pct=float(color_cover),
            color_used=bool(color_used),
        )

        # ---- save profile snapshot ----
        if save_dir is not None and save_profile:
            prof = {
                "algo": "canny(P)->rescue(thresh OR)->color_gate(OR/AND)->premorph(crop+despeckle+fill)->morph+shape_score",
                "input": {"image": os.path.basename(str(frame)), "proc_size": [self.proc.proc_w, self.proc.proc_h]},
                "params": self.to_profile_dict(),
                "metrics": {
                    "life_canny_%": float(result.life_canny_pct),
                    "used_rescue": bool(result.used_rescue),
                    "bbox_ratio": float(info["bbox_ratio"]),
                    "fill_ratio": float(info["fill"]),
                    "score": float(info["score"]),
                    "color_cover_%": float(color_cover),
                    "color_used": bool(color_used),
                }
            }
            with open(os.path.join(save_dir, f"{stamp}_profile.json"), "w", encoding="utf-8") as f:
                json.dump(prof, f, ensure_ascii=False, indent=2)

        return result

    # --------------------------- Internals ---------------------------
    def _load_image(self, img_or_path: Union[str, NDArray]) -> Optional[NDArray]:
        if isinstance(img_or_path, str):
            return cv2.imread(img_or_path)
        if isinstance(img_or_path, np.ndarray):
            if img_or_path.ndim == 2:
                return cv2.cvtColor(img_or_path, cv2.COLOR_GRAY2BGR)
            return img_or_path.copy()
        return None

# ----------------------- CLI helper -----------------------
def run_file(
    image_path: str,
    profile: Optional[str] = None,
    out_dir: Optional[str] = "results",
) -> DetectionResult:
    """Convenience entry-point for running the detector from CLI.

    Args:
        image_path: Path to the input image.
        profile: Optional JSON profile path with parameters.
        out_dir: Directory to store artifacts.

    Returns:
        DetectionResult: Result of the detection run.
    """
    if profile:
        from ..profile_manager import load_profile, get_config
        from ..dynamic_adjuster import DynamicAdjuster

        load_profile("cli", profile)
        cfg_dict = get_config("cli")
        det_cfg, canny_cfg = configs_from_profile(cfg_dict)
        det = ContourDetector(adjuster=DynamicAdjuster(canny_cfg), **det_cfg)
    else:
        det = ContourDetector()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    res = det.detect(image_path, knobs={"save_dir": out_dir, "stamp": stamp})
    return res

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Contour detector with optional color-gate + JSON profiles")
    p.add_argument("image", help="Path to input image")
    p.add_argument("--profile", default=None, help="Path to JSON profile with params")
    p.add_argument("--out", default="results", help="Output directory for artifacts")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    r = run_file(args.image, args.profile, args.out)
    if r.ok:
        print(f"✅ bbox={r.bbox}, score={r.score:.3f}, fill={r.fill:.2f}, ratio={r.bbox_ratio:.3f}")
    else:
        print("⚠️  No candidates.")
