
"""
Simple facade for robot server code.
Keeps Camera thin; exposes process_frame(frame) returning result dict and optional overlay.
"""

from typing import Optional, Dict, Any
import numpy as np

from .detectors.contour_detector import ContourDetector, DetectionResult

_detector = ContourDetector()

def process_frame(frame: np.ndarray, return_overlay: bool = True) -> Dict[str, Any]:
    """
    frame: np.ndarray (BGR). Returns a small dict for easy JSON/WS transport.
    """
    res: DetectionResult = _detector.detect(frame, save_dir=None, return_overlay=return_overlay)
    if not res.ok:
        return {"ok": False, "life": res.life_canny_pct}
    out = {
        "ok": True,
        "bbox": res.bbox,
        "score": res.score,
        "fill": res.fill,
        "bbox_ratio": res.bbox_ratio,
        "life": res.life_canny_pct,
        "center": res.center,
    }
    if return_overlay and res.overlay is not None:
        out["overlay"] = res.overlay  # ndarray; decide upstream si se envía/convierte
    return out

def get_detector() -> ContourDetector:
    return _detector
