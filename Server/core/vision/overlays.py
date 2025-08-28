"""
@file overlays.py
@brief Helpers for drawing vision overlays.

This module centralises overlay rendering so that different components can
share the same drawing logic without duplicating code.
"""
from __future__ import annotations

from typing import Mapping, Any, TYPE_CHECKING
from dataclasses import asdict, is_dataclass

import cv2
import numpy as np

NDArray = np.ndarray

if TYPE_CHECKING:  # pragma: no cover
    from .engine import EngineResult
    from .detectors.base import DetectionResult


# ---------------------------------------------------------------------------

def draw_detector(frame: NDArray, det_result: Mapping[str, Any] | "DetectionResult") -> NDArray:
    """Render detector information on ``frame``.

    Args:
        frame: Base image where annotations will be drawn.
        det_result: Detection result containing at least ``bbox`` and ``score``.

    Returns:
        Overlay image.
    """
    overlay = frame.copy()
    data = asdict(det_result) if is_dataclass(det_result) else dict(det_result)
    bbox = data.get("bbox")
    if bbox is None:
        return overlay
    x, y, w, h = bbox
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)

    center = data.get("center")
    if center is not None:
        cv2.circle(overlay, tuple(int(v) for v in center), 4, (0, 255, 0), -1)

    fill = data.get("fill")
    bbox_ratio = data.get("bbox_ratio")
    score = data.get("score")
    if None not in (fill, bbox_ratio, score):
        tag = "color_gate" if data.get("color_used") else "canny"
        txt = f"{tag}  fill={float(fill):.2f}  bbox={float(bbox_ratio):.2f}  sc={float(score):.2f}"
        cv2.putText(overlay, txt, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return overlay


def draw_engine(frame: NDArray, result: Mapping[str, Any] | "EngineResult") -> NDArray:
    """Draw an engine result on top of ``frame``.

    Args:
        frame: Original BGR frame.
        result: Engine result as returned by ``VisionEngine``.

    Returns:
        Image with rendered overlay.
    """
    overlay = frame.copy()
    data = asdict(result) if is_dataclass(result) else dict(result)
    if not data or not data.get("ok"):
        return overlay

    space = data.get("space") or (frame.shape[1], frame.shape[0])
    ref_w, ref_h = space
    sx = frame.shape[1] / float(ref_w)
    sy = frame.shape[0] / float(ref_h)

    bbox = data.get("bbox")
    if bbox is None:
        return overlay
    x, y, w, h = bbox
    x2, y2, w2, h2 = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
    cv2.rectangle(overlay, (x2, y2), (x2 + w2, y2 + h2), (0, 255, 0), 2)

    center = data.get("center")
    if center is not None:
        cx, cy = center
        cv2.circle(overlay, (int(cx * sx), int(cy * sy)), 4, (0, 255, 0), -1)

    score = data.get("score")
    if score is not None:
        label_y = max(18, y2 - 6)
        cv2.putText(overlay, f"sc={float(score):.2f}", (10, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return overlay
