"""
@file imgproc.py
@brief Reusable vision utilities.
Reusable image processing helpers shared across detectors.
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import Any, Dict, Optional, Tuple

NDArray = np.ndarray


def pct_on(mask: NDArray) -> float:
    """
    @brief Return percentage of non-zero pixels in mask.
    @param mask NDArray Binary mask to analyze.
    @return float Percentage of active pixels.
    """
    return 100.0 * float((mask > 0).sum()) / float(mask.size)


def despeckle(bin_img: NDArray, min_px: int) -> NDArray:
    """
    @brief Remove connected components smaller than a threshold.
    @param bin_img NDArray Binary image containing components.
    @param min_px int Minimum pixel area to retain.
    @return NDArray Image with small components removed.
    """
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
    """
    @brief Return ROI of ``frame_bgr`` around ``bbox`` scaled by ``factor``.
    @param frame_bgr NDArray Source frame in BGR format.
    @param bbox Tuple[int,int,int,int] Bounding box (x,y,w,h) in reference coordinates.
    @param factor float Scale factor relative to the bounding box size.
    @param ref_size Tuple[int,int] Reference size (width, height) to resize the frame.
    @return NDArray Masked ROI image in reference size.
    """
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


# ----------------------- utilities -----------------------

def _odd(k: int) -> int:
    """
    @brief Ensure a kernel size is odd.
    @param k int Original kernel size.
    @return int Odd kernel size (k or k+1).
    @note Returns ``k+1`` when ``k`` is even.
    """
    k = int(k)
    return k if (k % 2 == 1) else k + 1


def _clip01(x: float) -> float:
    """
    @brief Clamp value to the ``[0,1]`` range.
    @param x float Value to clamp.
    @return float Clamped value.
    """
    return float(max(0.0, min(1.0, x)))


# ----------------------- core imgproc helpers -----------------------

def _preprocess(img: NDArray, proc_cfg: "ProcConfig") -> Tuple[NDArray, NDArray]:
    """
    @brief Resize and blur an image according to processing config.
    @param img NDArray Source BGR image.
    @param proc_cfg ProcConfig Processing configuration.
    @return Tuple[NDArray,NDArray] Tuple ``(proc_bgr, gray_blurred)``.
    """
    proc = cv2.resize(img, (proc_cfg.proc_w, proc_cfg.proc_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (_odd(proc_cfg.blur_k), _odd(proc_cfg.blur_k)), 0)
    return proc, gray


def _run_morph(edges: NDArray, ck: int, dk: int, opening: bool = False) -> NDArray:
    """
    @brief Apply closing and dilation to edge image.
    @param edges NDArray Binary edge image.
    @param ck int Closing kernel size.
    @param dk int Dilation kernel size.
    @param opening bool Whether to apply an opening first.
    @return NDArray Morphologically processed image.
    """
    m = edges.copy()
    if opening:
        k0 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k0, iterations=1)
    k1 = cv2.getStructuringElement(cv2.MORPH_RECT, (_odd(ck), _odd(ck)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k1, iterations=1)
    k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (_odd(dk), _odd(dk)))
    m = cv2.dilate(m, k2, iterations=1)
    return m


def _ar_score(ar: float, geo_cfg: "GeoFilters") -> float:
    """
    @brief Score aspect ratio based on geometric filters.
    @param ar float Aspect ratio ``w/h``.
    @param geo_cfg GeoFilters Geometric filter configuration.
    @return float Normalized score for the aspect ratio.
    """
    lo, hi = geo_cfg.ar_min, geo_cfg.ar_max
    mid = 1.0
    span = max(mid - lo, hi - mid)
    return float(max(0.0, 1.0 - abs(ar - mid) / span))


def _shape_features(cnt: NDArray, W: int, H: int, geo_cfg: "GeoFilters") -> Dict[str, Any]:
    """
    @brief Compute shape features for a contour.
    @param cnt NDArray Contour points.
    @param W int Image width.
    @param H int Image height.
    @param geo_cfg GeoFilters Geometric filter configuration.
    @return Dict[str,Any] Dictionary with contour features.
    """
    area = cv2.contourArea(cnt)
    per = max(1e-6, cv2.arcLength(cnt, True))
    x, y, w, h = cv2.boundingRect(cnt)
    hull = cv2.convexHull(cnt)
    a_hull = max(1e-6, cv2.contourArea(hull))
    solidity = float(area / a_hull)
    circular = float(min(1.0, 4.0 * np.pi * area / (per * per)))
    rectangularity = float(area / (w * h))
    ar = w / max(1.0, h)
    ar_s = _ar_score(ar, geo_cfg)
    bbox_ratio = (w * h) / (W * H)
    fill = rectangularity
    return {
        "area": area,
        "per": per,
        "bbox": (x, y, w, h),
        "ar": ar,
        "solidity": solidity,
        "circular": circular,
        "rect": rectangularity,
        "ar_s": ar_s,
        "bbox_ratio": bbox_ratio,
        "fill": fill,
    }


def _score_contour(feat: Dict[str, Any], cx_img: float, cy_img: float, W: int, H: int, weights: "Weights") -> Tuple[float, float]:
    """
    @brief Compute weighted score for a contour's features.
    @param feat Dict[str,Any] Contour feature dictionary.
    @param cx_img float Image center X.
    @param cy_img float Image center Y.
    @param W int Image width.
    @param H int Image height.
    @param weights Weights Weight configuration.
    @return Tuple[float,float] Tuple ``(score, dist_norm)``.
    """
    x, y, w, h = feat["bbox"]
    area_norm = feat["area"] / (W * H)
    cx = x + w / 2.0
    cy = y + h / 2.0
    dist = np.hypot(cx - cx_img, cy - cy_img) / np.hypot(cx_img, cy_img)
    sc = (
        weights.area * area_norm +
        weights.fill * feat["fill"] +
        weights.solidity * feat["solidity"] +
        weights.circular * feat["circular"] +
        weights.rect * feat["rect"] +
        weights.ar * feat["ar_s"] -
        (weights.dist * weights.center_bias) * dist
    )
    return float(sc), float(dist)


def _select_best(mask: NDArray, min_area_px: int, W: int, H: int, geo_cfg: "GeoFilters", weights: "Weights") -> Optional[Dict[str, Any]]:
    """
    @brief Choose the best contour according to geometric and weight criteria.
    @param mask NDArray Binary mask with candidate contours.
    @param min_area_px int Minimum contour area in pixels.
    @param W int Image width.
    @param H int Image height.
    @param geo_cfg GeoFilters Geometric filter configuration.
    @param weights Weights Weight configuration.
    @return Optional[Dict[str,Any]] Best contour information or ``None`` if not found.
    """
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    cx_img, cy_img = W / 2.0, H / 2.0
    best, best_s = None, -1e9
    for c in cnts:
        a = cv2.contourArea(c)
        if a < min_area_px:
            continue
        x, y, w, h = cv2.boundingRect(c)
        ar = w / max(1.0, h)
        bbox_ratio = (w * h) / (W * H)
        if not (geo_cfg.ar_min <= ar <= geo_cfg.ar_max):
            continue
        if bbox_ratio > geo_cfg.bbox_hard_cap:
            continue
        feat = _shape_features(c, W, H, geo_cfg)
        s, _ = _score_contour(feat, cx_img, cy_img, W, H, weights)
        if s > best_s:
            best_s = s
            best = dict(cnt=c, score=s, **feat)
    return best


def _process_with_margin(edges: NDArray, margin: int, morph_cfg: "MorphConfig", geo_cfg: "GeoFilters", weights: "Weights") -> Tuple[Optional[Tuple[NDArray, Dict[str, Any], int, int]], NDArray]:
    """
    @brief Run morphology and contour selection with a border margin.
    @param edges NDArray Edge image.
    @param margin int Border margin in pixels to ignore.
    @param morph_cfg MorphConfig Morphological configuration.
    @param geo_cfg GeoFilters Geometric filter configuration.
    @param weights Weights Weight configuration.
    @return Tuple[Optional[Tuple[NDArray,Dict[str,Any],int,int]], NDArray] Best contour info and processed edges.
    """
    e = edges.copy()
    if margin > 0:
        e[:margin, :] = 0
        e[-margin:, :] = 0
        e[:, :margin] = 0
        e[:, -margin:] = 0

    H, W = e.shape[:2]
    min_area_px = int(geo_cfg.min_area_frac * W * H)
    ck, dk = 3, 3
    opening = False
    best = None

    for _ in range(1, morph_cfg.steps + 1):
        m = _run_morph(e, ck, dk, opening=opening)
        info = _select_best(m, min_area_px, W, H, geo_cfg, weights)
        if info is None:
            ck = min(morph_cfg.close_max, ck + 2)
            dk = min(morph_cfg.dil_max, dk + 2)
            opening = True
            continue

        best = (m, info, ck, dk)
        if (geo_cfg.bbox_min <= info["bbox_ratio"] <= geo_cfg.bbox_max) and (geo_cfg.fill_min <= info["fill"] <= geo_cfg.fill_max):
            break
        if (info["fill"] < geo_cfg.fill_min) or (info["bbox_ratio"] < geo_cfg.bbox_min):
            ck = min(morph_cfg.close_max, ck + 2)
            dk = min(morph_cfg.dil_max, dk + 2)
        elif (info["fill"] > geo_cfg.fill_max) or (info["bbox_ratio"] > geo_cfg.bbox_max):
            dk = max(morph_cfg.dil_min, dk - 2)
            ck = max(morph_cfg.close_min, ck - 1)
            opening = True

    return best, e


def _try_with_margins(edges: NDArray, proc_cfg: "ProcConfig", morph_cfg: "MorphConfig", geo_cfg: "GeoFilters", weights: "Weights") -> Tuple[Optional[Tuple[NDArray, Dict[str, Any], int, int]], NDArray]:
    """
    @brief Attempt contour selection with and without border margin.
    @param edges NDArray Edge image.
    @param proc_cfg ProcConfig Processing configuration (for margin).
    @param morph_cfg MorphConfig Morphological configuration.
    @param geo_cfg GeoFilters Geometric filter configuration.
    @param weights Weights Weight configuration.
    @return Tuple[Optional[Tuple[NDArray,Dict[str,Any],int,int]], NDArray] Best contour info and processed edges.
    """
    best, e_used = _process_with_margin(edges, proc_cfg.border_margin, morph_cfg, geo_cfg, weights)
    if best is None:
        best, e_used = _process_with_margin(edges, 0, morph_cfg, geo_cfg, weights)
    return best, e_used


def _draw_overlay(proc_bgr: NDArray, info: Dict[str, Any], mask_final: NDArray, color_enabled: bool) -> Tuple[NDArray, Tuple[int, int]]:
    """
    @brief Draw detection overlay on processed image.
    @param proc_bgr NDArray Processed BGR image.
    @param info Dict[str,Any] Selected contour information.
    @param mask_final NDArray Mask image where contour will be drawn.
    @param color_enabled bool Whether color gate is enabled.
    @return Tuple[NDArray,Tuple[int,int]] Overlay image and contour center.
    """
    overlay = proc_bgr.copy()
    x, y, w, h = info["bbox"]
    cv2.drawContours(mask_final, [info["cnt"]], -1, 255, thickness=cv2.FILLED)
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
    M = cv2.moments(info["cnt"])
    c = (x + w // 2, y + h // 2)
    if M["m00"] != 0:
        c = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
    cv2.circle(overlay, c, 4, (0, 255, 0), -1)
    tag = "color_gate" if color_enabled else "canny"
    txt = f"{tag}  fill={info['fill']:.2f}  bbox={info['bbox_ratio']:.2f}  sc={info['score']:.2f}"
    cv2.putText(overlay, txt, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return overlay, c


def _color_gate(bgr: NDArray, color_cfg: "ColorGateConfig") -> NDArray:
    """
    @brief Generate mask by filtering colors.
    @param bgr NDArray Source BGR image.
    @param color_cfg ColorGateConfig Color gate configuration.
    @return NDArray Binary mask of selected colors.
    """
    if color_cfg.mode == "hsv":
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lo = np.array(color_cfg.hsv_lo, dtype=np.uint8)
        hi = np.array(color_cfg.hsv_hi, dtype=np.uint8)
        mask = cv2.inRange(hsv, lo, hi)
        return mask
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    a = lab[:, :, 1].astype(np.float32)
    b = lab[:, :, 2].astype(np.float32)
    a0 = float(np.median(a))
    b0 = float(np.median(b))
    dist = np.sqrt((a - a0) ** 2 + (b - b0) ** 2)
    mask = (dist > float(color_cfg.ab_thresh)).astype(np.uint8) * 255
    return mask
