from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
import numpy as np
import os

from .detectors.contour_detector import ContourDetector, DetectionResult, configs_from_profile
from .profile_manager import load_profile as pm_load_profile, get_config
from .dynamic_adjuster import DynamicAdjuster
from .imgproc import mask_to_roi
from .config_defaults import (
    DEFAULT_STABLE,
    DEFAULT_ON_THRESHOLD,
    DEFAULT_OFF_THRESHOLD,
    DEFAULT_STICK_K,
    DEFAULT_MISS_M,
    DEFAULT_ROI_FACTOR,
    DEFAULT_EMA_ALPHA,
)

BASE = os.path.dirname(os.path.abspath(__file__))


class VisionSystem:
    """Encapsulated vision processing with its own detectors and state."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = dict(config or {})
        p = cfg.get("profiles", {})
        self.k = dict(
            big_profile=p.get("big", "profile_big.json"),
            small_profile=p.get("small", "profile_small.json"),
            stable=bool(cfg.get("stable", DEFAULT_STABLE)),
            on_th=float(cfg.get("on_th", DEFAULT_ON_THRESHOLD)),
            off_th=float(cfg.get("off_th", DEFAULT_OFF_THRESHOLD)),
            stick_k=int(cfg.get("stick_k", DEFAULT_STICK_K)),
            miss_m=int(cfg.get("miss_m", DEFAULT_MISS_M)),
            roi_fact=float(cfg.get("roi_factor", DEFAULT_ROI_FACTOR)),
            ema_a=float(cfg.get("ema", DEFAULT_EMA_ALPHA)),
        )

        self.det_big: Optional[ContourDetector] = None
        self.det_small: Optional[ContourDetector] = None
        self.adj_big: Optional[DynamicAdjuster] = None
        self.adj_small: Optional[DynamicAdjuster] = None

        # Stability state for big detector
        self.last_bbox_big: Optional[Tuple[int, int, int, int]] = None
        self.score_ema_big: Optional[float] = None
        self.miss_count_big: int = 0

        # Stability state for small detector
        self.last_bbox_small: Optional[Tuple[int, int, int, int]] = None
        self.score_ema_small: Optional[float] = None
        self.miss_count_small: int = 0

    # ------------------------------------------------------------------ utils
    def _resolve_profile(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(BASE, "profiles", path)

    def _ensure_detectors(self) -> None:
        if self.det_big is None:
            big = self._resolve_profile(self.k["big_profile"])
            pm_load_profile("big", big)
            cfg, canny = configs_from_profile(get_config("big"))
            self.adj_big = DynamicAdjuster(canny)
            self.det_big = ContourDetector(adjuster=self.adj_big, **cfg)
        if self.det_small is None:
            small = self._resolve_profile(self.k["small_profile"])
            pm_load_profile("small", small)
            cfg, canny = configs_from_profile(get_config("small"))
            self.adj_small = DynamicAdjuster(canny)
            self.det_small = ContourDetector(adjuster=self.adj_small, **cfg)

    def _ref_size(self, det: ContourDetector) -> Tuple[int, int]:
        return det.proc.proc_w, det.proc.proc_h

    def reset_state(self) -> None:
        self.last_bbox_big = None
        self.score_ema_big = None
        self.miss_count_big = 0
        self.last_bbox_small = None
        self.score_ema_small = None
        self.miss_count_small = 0

    def load_profile(self, which: str, path: Optional[str] = None) -> None:
        if which == "big":
            p = self._resolve_profile(path or "profile_big.json")
            pm_load_profile("big", p)
            cfg, canny = configs_from_profile(get_config("big"))
            self.adj_big = DynamicAdjuster(canny)
            self.det_big = ContourDetector(adjuster=self.adj_big, **cfg)
            self.last_bbox_big = None
            self.score_ema_big = None
            self.miss_count_big = 0
        elif which == "small":
            p = self._resolve_profile(path or "profile_small.json")
            pm_load_profile("small", p)
            cfg, canny = configs_from_profile(get_config("small"))
            self.adj_small = DynamicAdjuster(canny)
            self.det_small = ContourDetector(adjuster=self.adj_small, **cfg)
            self.last_bbox_small = None
            self.score_ema_small = None
            self.miss_count_small = 0

    def update_dynamic(self, which: str, params: Dict[str, Any]) -> None:
        if which == "big" and self.adj_big is not None:
            self.adj_big.update(**params)
        elif which == "small" and self.adj_small is not None:
            self.adj_small.update(**params)

    def _export(self, res: DetectionResult, det: ContourDetector, score_override: Optional[float] = None):
        ref = self._ref_size(det)
        if not res.ok:
            return {"ok": False, "life": getattr(res, "life_canny_pct", 0.0), "space": ref}
        out = {
            "ok": True,
            "bbox": res.bbox,
            "score": float(score_override if score_override is not None else res.score),
            "fill": res.fill,
            "bbox_ratio": res.bbox_ratio,
            "life": res.life_canny_pct,
            "center": res.center,
            "space": ref,
        }
        if res.overlay is not None:
            out["overlay"] = res.overlay
        return out

    def _step(self, det: ContourDetector, which: str, frame: np.ndarray, return_overlay: bool):
        ref_w, ref_h = self._ref_size(det)
        last_bbox = getattr(self, f"last_bbox_{which}")
        score_ema = getattr(self, f"score_ema_{which}")
        miss_count = getattr(self, f"miss_count_{which}")

        if not self.k["stable"] or last_bbox is None:
            res: DetectionResult = det.detect(frame, save_dir=None, return_overlay=return_overlay)
            if not res.ok:
                miss_count = min(self.k["miss_m"], miss_count + 1)
                setattr(self, f"miss_count_{which}", miss_count)
                return False, self._export(res, det)
            score_ema = res.score if score_ema is None else (self.k["ema_a"] * score_ema + (1.0 - self.k["ema_a"]) * res.score)
            if score_ema >= self.k["on_th"]:
                last_bbox = res.bbox
                miss_count = 0
                setattr(self, f"last_bbox_{which}", last_bbox)
                setattr(self, f"score_ema_{which}", score_ema)
                setattr(self, f"miss_count_{which}", miss_count)
                return True, self._export(res, det, score_ema)
            else:
                out = self._export(res, det, score_ema)
                out["ok"] = False
                setattr(self, f"score_ema_{which}", score_ema)
                setattr(self, f"miss_count_{which}", miss_count)
                return False, out

        # ROI
        roi_frame = mask_to_roi(frame, last_bbox, self.k["roi_fact"], self._ref_size(det))
        res_roi: DetectionResult = det.detect(roi_frame, save_dir=None, return_overlay=return_overlay)
        if res_roi.ok:
            score_ema = res_roi.score if score_ema is None else (self.k["ema_a"] * score_ema + (1.0 - self.k["ema_a"]) * res_roi.score)
            if score_ema >= self.k["off_th"]:
                last_bbox = res_roi.bbox
                miss_count = 0
                setattr(self, f"last_bbox_{which}", last_bbox)
                setattr(self, f"score_ema_{which}", score_ema)
                setattr(self, f"miss_count_{which}", miss_count)
                return True, self._export(res_roi, det, score_ema)
            else:
                miss_count += 1
        else:
            miss_count += 1

        if miss_count >= self.k["miss_m"]:
            last_bbox = None
            score_ema = None
            res_global: DetectionResult = det.detect(frame, save_dir=None, return_overlay=return_overlay)
            ok = bool(res_global.ok)
            if ok:
                last_bbox = res_global.bbox
                score_ema = res_global.score
                miss_count = 0
            setattr(self, f"last_bbox_{which}", last_bbox)
            setattr(self, f"score_ema_{which}", score_ema)
            setattr(self, f"miss_count_{which}", miss_count)
            return ok, self._export(res_global, det)
        else:
            setattr(self, f"miss_count_{which}", miss_count)
            if last_bbox is not None:
                return True, {"ok": True, "bbox": last_bbox, "score": float(score_ema or 0.0), "space": (ref_w, ref_h)}
            return False, {"ok": False, "space": (ref_w, ref_h)}

    def process_frame(self, frame: np.ndarray, return_overlay: bool = True):
        self._ensure_detectors()
        ok_big, out_big = self._step(self.det_big, "big", frame, return_overlay)
        if ok_big:
            return out_big
        ok_small, out_small = self._step(self.det_small, "small", frame, return_overlay)
        if ok_small:
            return out_small
        sb = float(out_big.get("score", 0.0))
        ss = float(out_small.get("score", 0.0))
        return out_big if sb >= ss else out_small

    def get_detectors(self):
        return self.det_big, self.det_small

