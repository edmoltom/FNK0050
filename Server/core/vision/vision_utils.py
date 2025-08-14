"""Common image processing utilities for detectors."""
from typing import Tuple
import cv2
import numpy as np

NDArray = np.ndarray


def pct_on(mask: NDArray) -> float:
    """Return percentage of non-zero pixels in mask."""
    return 100.0 * float((mask > 0).sum()) / float(mask.size)


def despeckle(bin_img: NDArray, min_px: int) -> NDArray:
    """Remove connected components smaller than ``min_px``."""
    if min_px <= 0:
        return bin_img
    lab = (bin_img > 0).astype("uint8")
    num, labels, stats, _ = cv2.connectedComponentsWithStats(lab, 8)
    keep = np.zeros_like(bin_img)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_px:
            keep[labels == i] = 255
    return keep


def mask_to_roi(frame_bgr: NDArray, bbox: Tuple[int, int, int, int], factor: float, ref_size: Tuple[int, int]) -> NDArray:
    """Return ROI of ``frame_bgr`` around ``bbox`` scaled by ``factor`` in reference size."""
    ref_w, ref_h = ref_size
    small = cv2.resize(frame_bgr, (ref_w, ref_h), interpolation=cv2.INTER_AREA)
    x, y, w, h = bbox
    pad_w = int(max(0.0, (factor - 1.0)) * w / 2.0)
    pad_h = int(max(0.0, (factor - 1.0)) * h / 2.0)
    rx = max(0, x - pad_w)
    ry = max(0, y - pad_h)
    rw = min(ref_w - rx, w + 2 * pad_w)
    rh = min(ref_h - ry, h + 2 * pad_h)
    masked = np.zeros_like(small)
    masked[ry:ry + rh, rx:rx + rw] = small[ry:ry + rh, rx:rx + rw]
    return masked
