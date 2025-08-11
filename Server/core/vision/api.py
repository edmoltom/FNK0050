"""
Robot vision API

- Keeps ContourDetector per‑frame and adds a tiny temporal layer:
  * Hysteresis: ON/OFF + misses (K)
  * ROI with fallback: focus around last bbox; global search if lost M frames
  * Score smoothing (EMA) to reduce jitter

Use exactly like before:
    from core.vision.api import process_frame
    result = process_frame(frame_bgr, return_overlay=True)

Optionally pass `config` to tweak knobs:
    result = process_frame(frame_bgr, return_overlay=True, config={
        "stable": True, "on_th":0.55, "off_th":0.45, "stick_k":5, "miss_m":8,
        "roi_factor":1.8, "ema":0.7
    })

The output dict is compatible and adds 'space': (w,h) of detector reference.
"""

from typing import Optional, Dict, Any, Tuple
import numpy as np
import cv2
import os

from .detectors.contour_detector import ContourDetector, DetectionResult

BASE = os.path.dirname(os.path.abspath(__file__))

# ----------------- estados -----------------
class _StableState:
    def __init__(self):
        self.last_bbox: Optional[Tuple[int,int,int,int]] = None
        self.score_ema: Optional[float] = None
        self.miss_count: int = 0

# dos detectores (big primero, small fallback)
_det_big: Optional[ContourDetector] = None
_det_small: Optional[ContourDetector] = None
_st_big = _StableState()
_st_small = _StableState()

# ----------------- knobs -----------------
def _knobs(config: Optional[Dict[str, Any]]):
    cfg = dict(config or {})
    p = cfg.get("profiles", {})
    return dict(
        big_profile   = p.get("big",  "profile_big_solid.json"),
        small_profile = p.get("small","profile_small_round_color.json"),
        stable   = bool(cfg.get("stable", True)),
        on_th    = float(cfg.get("on_th", 0.55)),
        off_th   = float(cfg.get("off_th", 0.45)),
        stick_k  = int(cfg.get("stick_k", 5)),
        miss_m   = int(cfg.get("miss_m", 8)),
        roi_fact = float(cfg.get("roi_factor", 1.8)),
        ema_a    = float(cfg.get("ema", 0.7)),
    )

def _resolve_profile(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(BASE, p)

def _ensure_detectors(k):
    global _det_big, _det_small
    if _det_big is None:
        big = _resolve_profile(k["big_profile"])
        _det_big = ContourDetector.from_profile(big)
    if _det_small is None:
        small = _resolve_profile(k["small_profile"])
        _det_small = ContourDetector.from_profile(small)

def _ref_size(det: ContourDetector) -> Tuple[int,int]:
    return det.proc.proc_w, det.proc.proc_h

def reset_state() -> None:
    for st in (_st_big, _st_small):
        st.last_bbox = None
        st.score_ema = None
        st.miss_count = 0

def _mask_to_roi(frame_bgr: np.ndarray, det: ContourDetector, bbox: Tuple[int,int,int,int], factor: float) -> np.ndarray:
    ref_w, ref_h = _ref_size(det)
    small = cv2.resize(frame_bgr, (ref_w, ref_h), interpolation=cv2.INTER_AREA)
    x, y, w, h = bbox
    pad_w = int(max(0.0, (factor - 1.0)) * w / 2.0)
    pad_h = int(max(0.0, (factor - 1.0)) * h / 2.0)
    rx = max(0, x - pad_w); ry = max(0, y - pad_h)
    rw = min(ref_w - rx, w + 2 * pad_w)
    rh = min(ref_h - ry, h + 2 * pad_h)
    masked = np.zeros_like(small)
    masked[ry:ry+rh, rx:rx+rw] = small[ry:ry+rh, rx:rx+rw]
    return masked

def _export(res: DetectionResult, det: ContourDetector, score_override: Optional[float]=None):
    ref = _ref_size(det)
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

def _step(det: ContourDetector, st: _StableState, frame: np.ndarray, k, return_overlay: bool):
    """Una pasada con estabilidad para UN detector."""
    ref_w, ref_h = _ref_size(det)

    # global si no hay estado o estabilidad off
    if not k["stable"] or st.last_bbox is None:
        res: DetectionResult = det.detect(frame, save_dir=None, return_overlay=return_overlay)
        if not res.ok:
            st.miss_count = min(k["miss_m"], st.miss_count + 1)
            return False, _export(res, det)  # no-ok
        st.score_ema = res.score if st.score_ema is None else (k["ema_a"]*st.score_ema + (1.0-k["ema_a"])*res.score)
        if st.score_ema >= k["on_th"]:
            st.last_bbox = res.bbox
            st.miss_count = 0
            return True, _export(res, det, st.score_ema)
        else:
            out = _export(res, det, st.score_ema); out["ok"] = False
            return False, out

    # ROI
    roi_frame = _mask_to_roi(frame, det, st.last_bbox, k["roi_fact"])
    res_roi: DetectionResult = det.detect(roi_frame, save_dir=None, return_overlay=return_overlay)
    if res_roi.ok:
        st.score_ema = res_roi.score if st.score_ema is None else (k["ema_a"]*st.score_ema + (1.0-k["ema_a"])*res_roi.score)
        if st.score_ema >= k["off_th"]:
            st.last_bbox = res_roi.bbox
            st.miss_count = 0
            return True, _export(res_roi, det, st.score_ema)
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
        return ok, _export(res_global, det)
    else:
        # mantener bbox previa como "latched" este frame
        if st.last_bbox is not None:
            return True, {"ok": True, "bbox": st.last_bbox, "score": float(st.score_ema or 0.0), "space": (ref_w, ref_h)}
        return False, {"ok": False, "space": (ref_w, ref_h)}

def process_frame(frame: np.ndarray, return_overlay: bool = True, config: Optional[Dict[str, Any]] = None):
    """
    Intenta BIG; si no, SMALL. Ambos con estabilidad propia.
    Firma compatible con versiones anteriores.
    """
    k = _knobs(config)
    _ensure_detectors(k)

    ok_big, out_big = _step(_det_big, _st_big, frame, k, return_overlay)
    if ok_big:
        return out_big

    ok_small, out_small = _step(_det_small, _st_small, frame, k, return_overlay)
    if ok_small:
        return out_small

    # ninguno estable: devolvemos el "menos malo" (mayor score si está)
    sb = float(out_big.get("score", 0.0))
    ss = float(out_small.get("score", 0.0))
    return out_big if sb >= ss else out_small

def get_detectors():
    """Útil para inspección en tests."""
    return _det_big, _det_small