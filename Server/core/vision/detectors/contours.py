
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
)
from ..overlays import draw_detector
from ..dynamics import CannyConfig
from .base import Detector, DetectionResult, DetectionContext

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


# ----------------------- detector -----------------------
class ContourDetector(Detector):
    """Contour pipeline with pre-morph patches and optional color-gate."""

    name = "contours"

    def __init__(self, adjuster: Optional["DynamicAdjuster"] = None) -> None:
        self.proc = ProcConfig()
        self.morph_cfg = MorphConfig()
        self.geo = GeoFilters()
        self.weights = Weights()
        self.premorph = PreMorphPatches()
        self.color = ColorGateConfig()
        if adjuster is None:
            from ..dynamics import DynamicAdjuster, CannyConfig
            adjuster = DynamicAdjuster(CannyConfig())
        self.adjuster = adjuster

    def configure(self, cfg: Dict[str, Any]) -> None:
        if cfg is None:
            return
        if "proc" in cfg:
            p = cfg["proc"]
            self.proc = p if isinstance(p, ProcConfig) else ProcConfig(**p)
        if "morph" in cfg:
            m = cfg["morph"]
            self.morph_cfg = m if isinstance(m, MorphConfig) else MorphConfig(**m)
        if "geo" in cfg:
            g = cfg["geo"]
            self.geo = g if isinstance(g, GeoFilters) else GeoFilters(**g)
        if "w" in cfg:
            w = cfg["w"]
            self.weights = w if isinstance(w, Weights) else Weights(**w)
        if "premorph" in cfg:
            pm = cfg["premorph"]
            self.premorph = pm if isinstance(pm, PreMorphPatches) else PreMorphPatches(**pm)
        if "color" in cfg:
            c = cfg["color"]
            self.color = c if isinstance(c, ColorGateConfig) else ColorGateConfig(**c)

    def to_profile_dict(self) -> Dict[str, Any]:
        return {
            "proc": asdict(self.proc),
            "canny": asdict(self.adjuster.cfg),
            "morph": asdict(self.morph_cfg),
            "geo": asdict(self.geo),
            "weights": asdict(self.weights),
            "premorph": asdict(self.premorph),
            "color_gate": asdict(self.color),
        }

    # ----------------------------- Public API -----------------------------
    def infer(
        self,
        img_or_path: Union[str, NDArray],
        ctx: Optional[DetectionContext] = None,
    ) -> DetectionResult:
        ctx = ctx or DetectionContext()
        save_dir = ctx.save_dir
        stamp = ctx.stamp
        save_profile = bool(ctx.save_profile)
        return_overlay = bool(ctx.return_overlay)

        img = self._load_image(img_or_path)
        if img is None:
            raise FileNotFoundError(str(img_or_path))

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
                cv2.imwrite(
                    os.path.join(save_dir, f"{stamp}_color_mask.png"),
                    color_mask if color_mask is not None else np.zeros_like(edges),
                )

        # ----- Pre-morph patches -----
        height, width = edges.shape[:2]
        edges2 = edges.copy()
        crop = int(max(0, min(BOTTOM_MARGIN_MAX, self.premorph.bottom_margin_pct)) * height / 100.0)
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
        best, e_used = _try_with_margins(edges2, self.proc, self.morph_cfg, self.geo, self.weights)
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
        x, y, w, h = info["bbox"]
        cv2.drawContours(mask_final, [info["cnt"]], -1, 255, thickness=cv2.FILLED)
        M = cv2.moments(info["cnt"])
        center = (x + w // 2, y + h // 2)
        if M["m00"] != 0:
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

        det_fields = {
            "bbox": (x, y, w, h),
            "center": center,
            "fill": info["fill"],
            "bbox_ratio": info["bbox_ratio"],
            "score": info["score"],
            "color_used": bool(color_used),
        }
        overlay = draw_detector(proc, det_fields) if return_overlay else None

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_mask_final.png"), mask_final)
            if overlay is not None:
                cv2.imwrite(os.path.join(save_dir, f"{stamp}_overlay.png"), overlay)

        result = DetectionResult(
            ok=True,
            used_rescue=used_rescue,
            life_canny_pct=float(life),
            bbox=det_fields["bbox"],
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
                "input": {"image": os.path.basename(str(img_or_path)), "proc_size": [self.proc.proc_w, self.proc.proc_h]},
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

    # Legacy API ------------------------------------------------------------
    def detect(
        self,
        img_or_path: Union[str, NDArray],
        save_dir: Optional[str] = None,
        stamp: Optional[str] = None,
        save_profile: bool = True,
        return_overlay: bool = True,
    ) -> DetectionResult:
        ctx = DetectionContext(
            save_dir=save_dir,
            stamp=stamp,
            save_profile=save_profile,
            return_overlay=return_overlay,
        )
        return self.infer(img_or_path, ctx)

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
def run_file(image_path: str, config: Optional[str] = None, out_dir: Optional[str] = "results"):
    if config:
        from ..config import load_config
        from ..dynamics import DynamicAdjuster

        cfg = load_config(config)
        det_cfg = cfg.detectors.big
        det = ContourDetector(adjuster=DynamicAdjuster(det_cfg.canny))
        det.configure({
            "proc": det_cfg.proc,
            "morph": det_cfg.morph,
            "geo": det_cfg.geo,
            "w": det_cfg.w,
            "premorph": det_cfg.premorph,
            "color": det_cfg.color,
        })
    else:
        det = ContourDetector()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    res = det.detect(image_path, save_dir=out_dir, stamp=stamp)
    return res

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Contour detector with optional color-gate")
    p.add_argument("image", help="Path to input image")
    p.add_argument("--config", default=None, help="Path to YAML config file")
    p.add_argument("--out", default="results", help="Output directory for artifacts")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    r = run_file(args.image, args.config, args.out)
    if r.ok:
        print(f"✅ bbox={r.bbox}, score={r.score:.3f}, fill={r.fill:.2f}, ratio={r.bbox_ratio:.3f}")
    else:
        print("⚠️  No candidates.")
