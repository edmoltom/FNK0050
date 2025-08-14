from __future__ import annotations

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any

NDArray = np.ndarray

# ----------------------- utilities -----------------------

def _odd(k: int) -> int:
    k = int(k)
    return k if (k % 2 == 1) else k + 1

def _clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

# ----------------------- core imgproc helpers -----------------------

def _preprocess(img: NDArray, proc_cfg: "ProcConfig") -> Tuple[NDArray, NDArray]:
    proc = cv2.resize(img, (proc_cfg.proc_w, proc_cfg.proc_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (_odd(proc_cfg.blur_k), _odd(proc_cfg.blur_k)), 0)
    return proc, gray

def _run_morph(edges: NDArray, ck: int, dk: int, opening: bool = False) -> NDArray:
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
    lo, hi = geo_cfg.ar_min, geo_cfg.ar_max
    mid = 1.0
    span = max(mid - lo, hi - mid)
    return float(max(0.0, 1.0 - abs(ar - mid) / span))

def _shape_features(cnt: NDArray, W: int, H: int, geo_cfg: "GeoFilters") -> Dict[str, Any]:
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
    best, e_used = _process_with_margin(edges, proc_cfg.border_margin, morph_cfg, geo_cfg, weights)
    if best is None:
        best, e_used = _process_with_margin(edges, 0, morph_cfg, geo_cfg, weights)
    return best, e_used

def _draw_overlay(proc_bgr: NDArray, info: Dict[str, Any], mask_final: NDArray, color_enabled: bool) -> Tuple[NDArray, Tuple[int, int]]:
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
