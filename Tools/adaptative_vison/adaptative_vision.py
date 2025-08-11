"""
--------------------------
It:
- Loads an input image (IMG_PATH)
- Downscales to PROC_W x PROC_H and blurs
- Runs auto-tuned Canny (using a simple proportional control on edge density)
- Optionally rescues with adaptive thresholding if Canny edges are too sparse
- Applies morphology in steps (close + dilate, with optional opening)
- Selects the best contour using geometric filters and a weighted score
- Writes debug images and a JSON profile with key metrics

"""

import os
import json
import time
import cv2
import numpy as np

# ---------- Paths ----------
BASE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE, "base2.png")   # or your test*.png
RES_DIR  = os.path.join(BASE, "results"); os.makedirs(RES_DIR, exist_ok=True)
stamp = time.strftime("%Y%m%d_%H%M%S")

# ---------- Config ----------
#PROC_W, PROC_H = 320, 240
PROC_W, PROC_H = 160, 120
BLUR_K = 5
BORDER_MARGIN = 6
#BORDER_MARGIN = 12           # try with larger margin; if no candidates, fallback to 0

# Canny (P-control over edge density considering ONLY Canny)
T1_INIT, T2_RATIO = 50.0, 2.5
life_MIN, life_MAX = 5.0, 10.0       # target edge density range (% of on-pixels)
RESCUE_life_MIN = 3.0                # if below this, rescue with adaptive threshold
Kp, MAX_ITER = 4.0, 25

# Morphology (auto-steps)
CLOSE_MIN, CLOSE_MAX = 3, 21
DIL_MIN,   DIL_MAX   = 3, 15
MORPH_STEPS          = 10
BBOX_MIN, BBOX_MAX   = 0.18, 0.35
FILL_MIN, FILL_MAX   = 0.60, 0.95
MIN_AREA_FRAC        = 0.03

# Geometric filters & scoring
AR_MIN, AR_MAX       = 0.40, 2.20
BBOX_HARD_CAP        = 0.50
BBOX_GROW_CAP        = 1.60
CENTER_BIAS          = 0.25   # 0..1 (lower = less bias to center)

# Score weights (sum approx. 1.0)
W_AREA = 0.35
W_FILL = 0.15
W_SOLI = 0.20
W_CIRC = 0.10
W_RECT = 0.15
W_AR   = 0.10
W_DIST = 0.20 * CENTER_BIAS   # subtracted

# ---------- Minimal new knobs ----------
BOTTOM_MARGIN_PCT = 20   # % of image height to ignore from bottom 0..40 sensible
MIN_BLOB_PX       = 100  # remove connected components smaller than this before morphology

# ---------- Small helpers ----------
def odd(k: int) -> int:
    """Return an odd integer (>= k)."""
    return int(k) if int(k) % 2 == 1 else int(k) + 1

def pct_on(mask) -> float:
    """Percentage of non-zero pixels in a binary image (0..100)."""
    return 100.0 * (mask > 0).sum() / mask.size

def adaptive_thresh(gray):
    """Adaptive threshold (mean) with inverted binary output."""
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY_INV, 11, 2)

def despeckle(bin_img, min_px: int):
    """Remove connected components smaller than min_px from a binary (0/255) image."""
    if min_px <= 0:
        return bin_img
    num, labels, stats, _ = cv2.connectedComponentsWithStats((bin_img > 0).astype('uint8'), 8)
    keep = np.zeros_like(bin_img)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_px:
            keep[labels == i] = 255
    return keep

def run_morph(edges, ck: int, dk: int, opening: bool = False):
    """Apply optional opening, then close, then dilate with given kernel sizes."""
    m = edges.copy()
    if opening:
        k0 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        m  = cv2.morphologyEx(m, cv2.MORPH_OPEN, k0, iterations=1)
    k1 = cv2.getStructuringElement(cv2.MORPH_RECT, (odd(ck), odd(ck)))
    m  = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k1, iterations=1)
    k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (odd(dk), odd(dk)))
    m  = cv2.dilate(m, k2, iterations=1)
    return m

def ar_score(ar: float, lo: float = AR_MIN, hi: float = AR_MAX) -> float:
    """
    Aspect-ratio score, peaking at ~1.0 (near square) and decreasing toward bounds.
    Returns 0..1.
    """
    mid = 1.0
    span = max(mid - lo, hi - mid)
    return float(max(0.0, 1.0 - abs(ar - mid) / span))

def shape_features(cnt, W: int, H: int):
    """Compute geometric features used for filtering and scoring."""
    area = cv2.contourArea(cnt)
    per  = max(1e-6, cv2.arcLength(cnt, True))
    x, y, w, h = cv2.boundingRect(cnt)
    hull = cv2.convexHull(cnt)
    a_hull = max(1e-6, cv2.contourArea(hull))
    solidity = float(area / a_hull)                      # 0..1
    circular = float(min(1.0, 4.0 * np.pi * area / (per * per)))  # 0..1
    rectangularity = float(area / (w * h))               # 0..1
    ar = w / max(1.0, h)
    ar_s = ar_score(ar)
    bbox_ratio = (w * h) / (W * H)
    fill = rectangularity                                 # intuitive alias
    return {
        "area": area, "per": per, "bbox": (x, y, w, h), "ar": ar,
        "solidity": solidity, "circular": circular,
        "rect": rectangularity, "ar_s": ar_s,
        "bbox_ratio": bbox_ratio, "fill": fill
    }

def score_contour(feat, cx_img: float, cy_img: float, W: int, H: int):
    """Weighted score for a contour; returns (score, dist_to_center)."""
    x, y, w, h = feat["bbox"]
    area_norm = feat["area"] / (W * H)
    # normalized distance to image center in 0..1
    cx = x + w / 2.0
    cy = y + h / 2.0
    dist = np.hypot(cx - cx_img, cy - cy_img) / np.hypot(cx_img, cy_img)
    score = (W_AREA * area_norm +
             W_FILL * feat["fill"] +
             W_SOLI * feat["solidity"] +
             W_CIRC * feat["circular"] +
             W_RECT * feat["rect"] +
             W_AR   * feat["ar_s"] -
             W_DIST * dist)
    return float(score), float(dist)

def select_best(mask, min_area_px: int, W: int, H: int, hard_cap: float = BBOX_HARD_CAP):
    """Scan external contours, filter by geometry and choose the best-scored one."""
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
        if not (AR_MIN <= ar <= AR_MAX):
            continue
        if bbox_ratio > hard_cap:
            continue
        feat = shape_features(c, W, H)
        s, dist = score_contour(feat, cx_img, cy_img, W, H)
        if s > best_s:
            best_s = s
            best   = dict(cnt=c, score=s, dist=dist, **feat)
    return best

# ---------- Load ----------
img = cv2.imread(IMG_PATH)
if img is None:
    raise FileNotFoundError(IMG_PATH)
cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_original.png"), img)

# Preprocess
proc = cv2.resize(img, (PROC_W, PROC_H), interpolation=cv2.INTER_AREA)
gray = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (odd(BLUR_K), odd(BLUR_K)), 0)

# ---------- Auto Canny ----------
t1 = float(T1_INIT)
for i in range(1, MAX_ITER + 1):
    t2 = int(np.clip(T2_RATIO * t1, 0, 255))
    canny = cv2.Canny(gray, int(max(0, t1)), int(t2))
    life = pct_on(canny)
    print(f"Iter {i:02d}  T1={t1:.1f} T2={t2:.1f}  canny_edge_density={life:.2f}%")
    if life_MIN <= life <= life_MAX:
        print("✅ Canny within target range."); break
    if life < life_MIN:
        t1 = max(1.0,  t1 - Kp * (life_MIN - life))
    else:
        t1 = min(220., t1 + Kp * (life - life_MAX))
cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_canny.png"), canny)

# ---------- Optional rescue ----------
used_rescue = False
edges = canny.copy()
if pct_on(canny) < RESCUE_life_MIN:
    th = adaptive_thresh(gray)
    edges = cv2.bitwise_or(canny, th); used_rescue = True
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_thresc.png"), th)

# ---------- NEW: bottom crop + despeckle BEFORE morphology ----------
H, W = edges.shape[:2]
crop = int(max(0, min(40, BOTTOM_MARGIN_PCT)) * H / 100.0)
edges2 = edges.copy()
if crop > 0:
    edges2[-crop:, :] = 0
edges2 = despeckle(edges2, int(MIN_BLOB_PX))
filled = np.zeros_like(edges2)
cnts,_ = cv2.findContours(edges2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(filled, cnts, -1, 255, thickness=cv2.FILLED)
edges2 = filled
cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_edges_patched.png"), edges2)

def process_with_margin(margin: int):
    """
    Apply a border margin (zero out borders), then run the morphology loop
    and select the best candidate. Returns (best_tuple, edges_used).
    """
    e = edges2.copy()  # use patched edges
    if margin > 0:
        e[:margin, :] = 0; e[-margin:, :] = 0; e[:, :margin] = 0; e[:, -margin:] = 0
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_edges_m{margin}.png"), e)

    H, W = e.shape[:2]
    min_area_px = int(MIN_AREA_FRAC * W * H)
    ck, dk = 3, 3
    opening = False
    best = None

    # morphology loop
    for step in range(1, MORPH_STEPS + 1):
        m = run_morph(e, ck, dk, opening=opening)
        info = select_best(m, min_area_px, W, H, hard_cap=BBOX_HARD_CAP)
        if info is None:
            ck = min(CLOSE_MAX, ck + 2); dk = min(DIL_MAX, dk + 2); opening = True; continue
        print(f"[Morph {step}] ck={ck} dk={dk} bbox={info['bbox_ratio']:.3f} "
              f"fill={info['fill']:.2f} score={info['score']:.3f}")
        best = (m, info, ck, dk)
        # targets
        if (BBOX_MIN <= info["bbox_ratio"] <= BBOX_MAX) and (FILL_MIN <= info["fill"] <= FILL_MAX):
            break
        # soft rules
        if (info["fill"] < FILL_MIN) or (info["bbox_ratio"] < BBOX_MIN):
            ck = min(CLOSE_MAX, ck + 2); dk = min(DIL_MAX, dk + 2)
        elif (info["fill"] > FILL_MAX) or (info["bbox_ratio"] > BBOX_MAX):
            dk = max(DIL_MIN, dk - 2); ck = max(CLOSE_MIN, ck - 1); opening = True
    return best, e

# 1) with border margin
best, e_used = process_with_margin(BORDER_MARGIN)
# 2) fallback without margin if no candidate
if best is None:
    print("↩️  Fallback: retry without margin")
    best, e_used = process_with_margin(0)

# ---------- Visuals & save ----------
if best is None:
    # nothing found: save edges and exit
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_mask_final.png"), e_used)
    print("⚠️  No candidates after fallback.")
else:
    mask_final, info, chosen_ck, chosen_dk = best
    overlay = proc.copy()
    x, y, w, h = info["bbox"]
    cv2.drawContours(mask_final, [info["cnt"]], -1, 255, thickness=cv2.FILLED)
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
    M = cv2.moments(info["cnt"])
    if M["m00"] != 0:
        c = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        cv2.circle(overlay, c, 4, (0, 255, 0), -1)
    txt = f"fill={info['fill']:.2f} bbox={info['bbox_ratio']:.2f} sc={info['score']:.2f}"
    cv2.putText(overlay, txt, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_mask_final.png"), mask_final)
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_overlay.png"), overlay)

    profile = {
      "algo": "canny(P)->rescue(if low)->bottom-crop+despeckle->morph+shape_score",
      "input": {"image": os.path.basename(IMG_PATH), "proc_size": [PROC_W, PROC_H]},
      "params": {
        "blur_k": BLUR_K, "t1": int(t1), "t2": int(np.clip(T2_RATIO * t1, 0, 255)),
        "life_target_range": [life_MIN, life_MAX], "rescue_threshold_min": RESCUE_life_MIN,
        "patched": {"bottom_margin_pct": BOTTOM_MARGIN_PCT, "min_blob_px": MIN_BLOB_PX},
        "morph": {"chosen_ck": int(chosen_ck), "chosen_dk": int(chosen_dk),
                  "targets": {"bbox_ratio": [BBOX_MIN, BBOX_MAX], "fill_ratio": [FILL_MIN, FILL_MAX]},
                  "border_margin": BORDER_MARGIN, "hard_cap": BBOX_HARD_CAP},
        "filters": {"ar_range": [AR_MIN, AR_MAX]},
        "weights": {"area": W_AREA, "fill": W_FILL, "solidity": W_SOLI, "circular": W_CIRC,
                    "rect": W_RECT, "ar": W_AR, "center_bias": CENTER_BIAS}
      },
      "metrics": {
        "life_canny_%": float(pct_on(canny)),
        "used_rescue": bool(used_rescue),
        "bbox_ratio": float(info["bbox_ratio"]),
        "fill_ratio": float(info["fill"]),
        "score": float(info["score"])
      }
    }
    with open(os.path.join(RES_DIR, f"{stamp}_profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

print("✅ Saved to:", RES_DIR)