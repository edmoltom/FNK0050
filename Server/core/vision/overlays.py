"""
@file overlays.py
@brief Helpers for drawing vision overlays.

This module centralises overlay rendering so that different components can
share the same drawing logic without duplicating code.
"""
from __future__ import annotations

from typing import Mapping, Any

import cv2
import numpy as np

NDArray = np.ndarray


# ---------------------------------------------------------------------------

def draw_detector(frame: NDArray, det_result: Mapping[str, Any]) -> NDArray:
    """
    @brief Render detector information on ``frame``.
    @param frame NDArray Base image where annotations will be drawn.
    @param det_result Mapping[str,Any] Detection result containing at least
                      ``bbox``, ``center``, ``fill``, ``bbox_ratio`` and
                      ``score`` keys.
    @return NDArray Overlay image.
    """
    overlay = frame.copy()
    bbox = det_result.get("bbox")
    if bbox is None:
        return overlay
    x, y, w, h = bbox
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)

    center = det_result.get("center")
    if center is not None:
        cv2.circle(overlay, tuple(int(v) for v in center), 4, (0, 255, 0), -1)

    fill = det_result.get("fill")
    bbox_ratio = det_result.get("bbox_ratio")
    score = det_result.get("score")
    if None not in (fill, bbox_ratio, score):
        tag = "color_gate" if det_result.get("color_used") else "canny"
        txt = f"{tag}  fill={float(fill):.2f}  bbox={float(bbox_ratio):.2f}  sc={float(score):.2f}"
        cv2.putText(overlay, txt, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return overlay


def draw_engine(frame: NDArray, result: Mapping[str, Any]) -> NDArray:
    """
    @brief Draw an engine result on top of ``frame``.
    @param frame NDArray Original BGR frame.
    @param result Mapping[str,Any] Engine result as returned by ``VisionEngine``.
    @return NDArray Image with rendered overlay.
    """
    overlay = frame.copy()
    if not result or not result.get("ok"):
        return overlay

    space = result.get("space") or (frame.shape[1], frame.shape[0])
    ref_w, ref_h = space
    sx = frame.shape[1] / float(ref_w)
    sy = frame.shape[0] / float(ref_h)

    bbox = result.get("bbox")
    if bbox is None:
        return overlay
    x, y, w, h = bbox
    x2, y2, w2, h2 = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
    cv2.rectangle(overlay, (x2, y2), (x2 + w2, y2 + h2), (0, 255, 0), 2)

    center = result.get("center")
    if center is not None:
        cx, cy = center
        cv2.circle(overlay, (int(cx * sx), int(cy * sy)), 4, (0, 255, 0), -1)

    score = result.get("score")
    if score is not None:
        label_y = max(18, y2 - 6)
        cv2.putText(overlay, f"sc={float(score):.2f}", (10, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return overlay
