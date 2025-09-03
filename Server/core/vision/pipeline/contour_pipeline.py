"""Contour-based vision pipeline."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np

from ..detectors.contour_detector import ContourDetector
from ..detectors.results import DetectionResult
from ..dynamic_adjuster import DynamicAdjuster
from ..detector_registry import DetectorRegistry
from ..imgproc import mask_to_roi
from ..config_defaults import (
    DEFAULT_STABLE,
    DEFAULT_ON_THRESHOLD,
    DEFAULT_OFF_THRESHOLD,
    DEFAULT_STICK_K,
    DEFAULT_MISS_M,
    DEFAULT_ROI_FACTOR,
    DEFAULT_EMA_ALPHA,
)
from .base_pipeline import BasePipeline, Result

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _StableState:
    """Internal stability state for a detector."""

    def __init__(self) -> None:
        self.last_bbox: Optional[Tuple[int, int, int, int]] = None
        self.score_ema: Optional[float] = None
        self.miss_count: int = 0


class ContourPipeline(BasePipeline):
    """Instance-based pipeline holding contour detectors and state."""

    def __init__(
        self,
        registry: Optional[DetectorRegistry] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._lock = threading.Lock()
        self._registry = registry or DetectorRegistry()
        self._det_big: Optional[ContourDetector] = None
        self._det_small: Optional[ContourDetector] = None
        self._adj_big: Optional[DynamicAdjuster] = None
        self._adj_small: Optional[DynamicAdjuster] = None
        self._st_big = _StableState()
        self._st_small = _StableState()
        self._last_result: Optional[Result] = None
        # List of (detector, state) tuples in priority order
        self._detectors: list[tuple[ContourDetector, _StableState]] = []
        self.configure(config)

    # ----------------- internal helpers -----------------
    def _knobs(self, config: Optional[Dict[str, Any]]):
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
        return os.path.join(BASE, "profiles", p)

    def configure(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Configure detectors via the registry using ``config``."""
        k = self._knobs(config)
        big = self._resolve_profile(k["big_profile"])
        small = self._resolve_profile(k["small_profile"])
        self._det_big = self._registry.register("big", big)
        self._adj_big = self._registry.get_adjuster("big")
        self._det_small = self._registry.register("small", small)
        self._adj_small = self._registry.get_adjuster("small")
        self.reset_state()

    @staticmethod
    def _ref_size(det: ContourDetector) -> Tuple[int, int]:
        return det.proc.proc_w, det.proc.proc_h

    def reset_state(self) -> None:
        with self._lock:
            self._st_big = _StableState()
            self._st_small = _StableState()
            self._det_big = self._registry.get_detector("big")
            self._det_small = self._registry.get_detector("small")
            self._detectors = []
            if self._det_big is not None:
                self._detectors.append((self._det_big, self._st_big))
            if self._det_small is not None:
                self._detectors.append((self._det_small, self._st_small))

    def load_profile(self, which: str, path: Optional[str] = None) -> None:
        """Reload a profile ('big' or 'small') and reset state."""
        with self._lock:
            if which == "big":
                p = self._resolve_profile(path or "profile_big.json")
                self._det_big = self._registry.register("big", p)
                self._adj_big = self._registry.get_adjuster("big")
                self._st_big = _StableState()
            elif which == "small":
                p = self._resolve_profile(path or "profile_small.json")
                self._det_small = self._registry.register("small", p)
                self._adj_small = self._registry.get_adjuster("small")
                self._st_small = _StableState()
            self._detectors = []
            if self._det_big is not None:
                self._detectors.append((self._det_big, self._st_big))
            if self._det_small is not None:
                self._detectors.append((self._det_small, self._st_small))

    def update_dynamic(self, which: str, params: Dict[str, Any]) -> None:
        """Update dynamic adjuster parameters at runtime."""
        with self._lock:
            adj = self._registry.get_adjuster(which)
            if adj is not None:
                adj.update(**params)

    def get_detectors(self):
        with self._lock:
            return self._registry.get_detector("big"), self._registry.get_detector("small")

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

    def _step(self, det: ContourDetector, st: _StableState, frame: np.ndarray, k, return_overlay: bool):
        ref_w, ref_h = self._ref_size(det)
        if not k["stable"] or st.last_bbox is None:
            res: DetectionResult = det.detect(frame, knobs={"return_overlay": return_overlay})
            if not res.ok:
                st.miss_count = min(k["miss_m"], st.miss_count + 1)
                return False, self._export(res, det)
            st.score_ema = res.score if st.score_ema is None else (
                k["ema_a"] * st.score_ema + (1.0 - k["ema_a"]) * res.score
            )
            if st.score_ema >= k["on_th"]:
                st.last_bbox = res.bbox
                st.miss_count = 0
                return True, self._export(res, det, st.score_ema)
            out = self._export(res, det, st.score_ema)
            out["ok"] = False
            return False, out

        roi_frame = mask_to_roi(frame, st.last_bbox, k["roi_fact"], self._ref_size(det))
        res_roi: DetectionResult = det.detect(roi_frame, knobs={"return_overlay": return_overlay})
        if res_roi.ok:
            st.score_ema = res_roi.score if st.score_ema is None else (
                k["ema_a"] * st.score_ema + (1.0 - k["ema_a"]) * res_roi.score
            )
            if st.score_ema >= k["off_th"]:
                st.last_bbox = res_roi.bbox
                st.miss_count = 0
                return True, self._export(res_roi, det, st.score_ema)
            st.miss_count += 1
        else:
            st.miss_count += 1

        if st.miss_count >= k["miss_m"]:
            st.last_bbox = None
            st.score_ema = None
            res_global: DetectionResult = det.detect(frame, knobs={"return_overlay": return_overlay})
            ok = bool(res_global.ok)
            if ok:
                st.last_bbox = res_global.bbox
                st.score_ema = res_global.score
                st.miss_count = 0
            return ok, self._export(res_global, det)
        if st.last_bbox is not None:
            return True, {"ok": True, "bbox": st.last_bbox, "score": float(st.score_ema or 0.0), "space": (ref_w, ref_h)}
        return False, {"ok": False, "space": (ref_w, ref_h)}

    def process(self, frame: np.ndarray, config: Optional[Dict[str, Any]] = None) -> Result:
        """Process a frame and return a :class:`Result`."""
        cfg = dict(config or {})
        return_overlay = bool(cfg.pop("return_overlay", False))
        k = self._knobs(cfg)
        with self._lock:
            best_out = None
            for det, st in self._detectors:
                ok, out = self._step(det, st, frame, k, return_overlay)
                if ok:
                    best_out = out
                    break
                if best_out is None or float(out.get("score", 0.0)) > float(best_out.get("score", 0.0)):
                    best_out = out
            res = Result(best_out or {"ok": False}, time.time())
            self._last_result = res
            return res

    def get_last_result(self) -> Optional[Result]:
        with self._lock:
            return self._last_result
