import os
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, TypedDict

import numpy as np

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


class EngineResult(TypedDict, total=False):
    ok: bool
    bbox: Tuple[int, int, int, int]
    score: float
    fill: float
    bbox_ratio: float
    life: float
    center: Tuple[float, float]
    space: Tuple[int, int]
    overlay: np.ndarray


@dataclass
class DynamicParams:
    which: str
    params: Dict[str, Any] = field(default_factory=dict)


class VisionEngine:
    """Thread safe vision engine wrapping contour detectors."""

    class _StableState:
        def __init__(self) -> None:
            self.last_bbox: Optional[Tuple[int, int, int, int]] = None
            self.score_ema: Optional[float] = None
            self.miss_count: int = 0

    BASE = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._lock = threading.Lock()
        self.config: Dict[str, Any] = dict(config or {})
        self.dynamic: Dict[str, Dict[str, Any]] = {"big": {}, "small": {}}
        self._det_big: Optional[ContourDetector] = None
        self._det_small: Optional[ContourDetector] = None
        self._adj_big: Optional[DynamicAdjuster] = None
        self._adj_small: Optional[DynamicAdjuster] = None
        self._st_big = self._StableState()
        self._st_small = self._StableState()
        self._last_result: Optional[EngineResult] = None

    # ---- internal helpers ----
    def _knobs(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        cfg = dict(config or {})
        p = cfg.get("profiles", {})
        return dict(
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

    def _resolve_profile(self, p: str) -> str:
        if os.path.isabs(p):
            return p
        return os.path.join(self.BASE, "profiles", p)

    def _ensure_detectors(self, k: Dict[str, Any]) -> None:
        if self._det_big is None:
            big = self._resolve_profile(k["big_profile"])
            pm_load_profile("big", big)
            cfg, canny = configs_from_profile(get_config("big"))
            self._adj_big = DynamicAdjuster(canny)
            self._det_big = ContourDetector(adjuster=self._adj_big, **cfg)
        if self._det_small is None:
            small = self._resolve_profile(k["small_profile"])
            pm_load_profile("small", small)
            cfg, canny = configs_from_profile(get_config("small"))
            self._adj_small = DynamicAdjuster(canny)
            self._det_small = ContourDetector(adjuster=self._adj_small, **cfg)

    def _ref_size(self, det: ContourDetector) -> Tuple[int, int]:
        return det.proc.proc_w, det.proc.proc_h

    def _export(self, res: DetectionResult, det: ContourDetector, score_override: Optional[float] = None) -> EngineResult:
        ref = self._ref_size(det)
        if not res.ok:
            return {"ok": False, "life": getattr(res, "life_canny_pct", 0.0), "space": ref}
        out: EngineResult = {
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

    def _step(self, det: ContourDetector, st: "VisionEngine._StableState", frame: np.ndarray, k: Dict[str, Any], return_overlay: bool) -> Tuple[bool, EngineResult]:
        ref_w, ref_h = self._ref_size(det)
        if not k["stable"] or st.last_bbox is None:
            res: DetectionResult = det.detect(frame, save_dir=None, return_overlay=return_overlay)
            if not res.ok:
                st.miss_count = min(k["miss_m"], st.miss_count + 1)
                return False, self._export(res, det)
            st.score_ema = res.score if st.score_ema is None else (k["ema_a"] * st.score_ema + (1.0 - k["ema_a"]) * res.score)
            if st.score_ema >= k["on_th"]:
                st.last_bbox = res.bbox
                st.miss_count = 0
                return True, self._export(res, det, st.score_ema)
            else:
                out = self._export(res, det, st.score_ema)
                out["ok"] = False
                return False, out

        roi_frame = mask_to_roi(frame, st.last_bbox, k["roi_fact"], self._ref_size(det))
        res_roi: DetectionResult = det.detect(roi_frame, save_dir=None, return_overlay=return_overlay)
        if res_roi.ok:
            st.score_ema = res_roi.score if st.score_ema is None else (k["ema_a"] * st.score_ema + (1.0 - k["ema_a"]) * res_roi.score)
            if st.score_ema >= k["off_th"]:
                st.last_bbox = res_roi.bbox
                st.miss_count = 0
                return True, self._export(res_roi, det, st.score_ema)
            else:
                st.miss_count += 1
        else:
            st.miss_count += 1

        if st.miss_count >= k["miss_m"]:
            st.last_bbox = None
            st.score_ema = None
            res_global: DetectionResult = det.detect(frame, save_dir=None, return_overlay=return_overlay)
            ok = bool(res_global.ok)
            if ok:
                st.last_bbox = res_global.bbox
                st.score_ema = res_global.score
                st.miss_count = 0
            return ok, self._export(res_global, det)
        else:
            if st.last_bbox is not None:
                return True, {"ok": True, "bbox": st.last_bbox, "score": float(st.score_ema or 0.0), "space": (ref_w, ref_h)}
            return False, {"ok": False, "space": (ref_w, ref_h)}

    # ---- public API ----
    def process(self, frame: np.ndarray) -> EngineResult:
        with self._lock:
            k = self._knobs(self.config)
            self._ensure_detectors(k)
            return_overlay = bool(self.config.get("return_overlay", False))
            ok_big, out_big = self._step(self._det_big, self._st_big, frame, k, return_overlay)
            if ok_big:
                self._last_result = out_big
                return out_big
            ok_small, out_small = self._step(self._det_small, self._st_small, frame, k, return_overlay)
            if ok_small:
                self._last_result = out_small
                return out_small
            sb = float(out_big.get("score", 0.0))
            ss = float(out_small.get("score", 0.0))
            res = out_big if sb >= ss else out_small
            self._last_result = res
            return res

    def update_dynamic(self, params: DynamicParams) -> None:
        with self._lock:
            which = params.which
            self.dynamic[which] = dict(params.params)
            if which == "big" and self._adj_big is not None:
                self._adj_big.update(**params.params)
            elif which == "small" and self._adj_small is not None:
                self._adj_small.update(**params.params)

    def reload_config(self) -> None:
        with self._lock:
            self._det_big = None
            self._det_small = None
            self._adj_big = None
            self._adj_small = None
            self._st_big = self._StableState()
            self._st_small = self._StableState()
            k = self._knobs(self.config)
            self._ensure_detectors(k)

    def get_last_result(self) -> Optional[EngineResult]:
        with self._lock:
            return self._last_result

    # utility for logger/tests
    def get_detectors(self) -> Tuple[Optional[ContourDetector], Optional[ContourDetector]]:
        with self._lock:
            return self._det_big, self._det_small
