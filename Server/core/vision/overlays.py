"""Drawing utilities for vision engine results."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from .engine import EngineResult
from .config_defaults import REF_SIZE


def _get_reference_resolution(meta: dict) -> Tuple[float, float]:
    """Return reference resolution from result metadata.

    Falls back to :data:`REF_SIZE` if the information is missing or
    malformed.
    """
    if isinstance(meta.get("space"), (tuple, list)) and len(meta["space"]) == 2:
        ref_w, ref_h = meta["space"]
    elif (
        isinstance(meta.get("space"), dict)
        and "width" in meta["space"]
        and "height" in meta["space"]
    ):
        ref_w, ref_h = meta["space"]["width"], meta["space"]["height"]
    elif isinstance(meta.get("input_size"), (tuple, list)) and len(meta["input_size"]) == 2:
        ref_w, ref_h = meta["input_size"]
    else:
        ref_w, ref_h = REF_SIZE

    if not (
        isinstance(ref_w, (int, float))
        and isinstance(ref_h, (int, float))
        and ref_w > 0
        and ref_h > 0
    ):
        ref_w, ref_h = REF_SIZE

    return float(ref_w), float(ref_h)


def draw_result(frame: np.ndarray, result: EngineResult) -> np.ndarray:
    """Draw detection information from ``result`` onto ``frame``.

    The drawing logic mirrors the overlay produced by
    :meth:`VisionInterface._apply_pipeline`.  The input frame is modified
    in-place and returned for convenience.
    """
    if result is None or not isinstance(result, EngineResult):
        return frame

    res = result.data or {}
    if not res.get("ok"):
        return frame

    ref_w, ref_h = _get_reference_resolution(res)
    sx = frame.shape[1] / ref_w
    sy = frame.shape[0] / ref_h

    if (
        "bbox" in res
        and isinstance(res["bbox"], (tuple, list))
        and len(res["bbox"]) == 4
    ):
        x, y, w, h = res["bbox"]
        x2, y2, w2, h2 = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
        cv2.rectangle(frame, (x2, y2), (x2 + w2, y2 + h2), (0, 255, 0), 2)
    if (
        "center" in res
        and isinstance(res["center"], (tuple, list))
        and len(res["center"]) == 2
    ):
        cx, cy = res["center"]
        cv2.circle(frame, (int(cx * sx), int(cy * sy)), 4, (0, 255, 0), -1)
    if "score" in res:
        label_y = max(18, (locals().get("y2", 10)) - 6)
        cv2.putText(
            frame,
            f"sc={res['score']:.2f}",
            (10, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
    return frame
