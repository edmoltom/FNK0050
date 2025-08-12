import os, sys, json, time
import cv2, numpy as np

# ---------- Paths ----------
BASE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE, "base2.png")
RES_DIR  = os.path.join(BASE, "results"); os.makedirs(RES_DIR, exist_ok=True)
stamp = time.strftime("%Y%m%d_%H%M%S")

# ---------- Defaults (overridable by profile) ----------
PROC_W, PROC_H = 160, 120
BLUR_K = 5
BORDER_MARGIN = 6

T1_INIT, T2_RATIO = 50.0, 2.5
life_MIN, life_MAX = 5.0, 10.0
RESCUE_life_MIN = 3.0
Kp, MAX_ITER = 4.0, 25

CLOSE_MIN, CLOSE_MAX = 3, 21
DIL_MIN,   DIL_MAX   = 3, 15
MORPH_STEPS          = 10
BBOX_MIN, BBOX_MAX   = 0.18, 0.35
FILL_MIN, FILL_MAX   = 0.60, 0.95
MIN_AREA_FRAC        = 0.03

AR_MIN, AR_MAX       = 0.40, 2.20
BBOX_HARD_CAP        = 0.50
CENTER_BIAS          = 0.25

W_AREA = 0.35; W_FILL = 0.15; W_SOLI = 0.20; W_CIRC = 0.10; W_RECT = 0.15; W_AR = 0.10
W_DIST = 0.20 * CENTER_BIAS

BOTTOM_MARGIN_PCT = 20
MIN_BLOB_PX       = 100

COLOR_GATE = { "enable": False }  # filled by profile if needed

# ---------- Profile loader ----------
def load_profile_json(path: str):
    if not path or not os.path.isfile(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_profile(p: dict):
    g = globals()
    for k, v in p.items():
        if k in g:
            g[k] = v

PROFILE_JSON = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "profile_big_solid.json")
if os.path.isfile(PROFILE_JSON):
    apply_profile(load_profile_json(PROFILE_JSON))

# ---------- Helpers ----------
def odd(k: int) -> int: return int(k) if int(k) % 2 == 1 else int(k) + 1
def pct_on(mask) -> float: return 100.0 * (mask > 0).sum() / mask.size
def adaptive_thresh(gray):
    return cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY_INV,11,2)

def despeckle(bin_img, min_px: int):
    if min_px <= 0: return bin_img
    num, labels, stats, _ = cv2.connectedComponentsWithStats((bin_img>0).astype('uint8'), 8)
    keep = np.zeros_like(bin_img)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_px:
            keep[labels==i] = 255
    return keep

def run_morph(edges, ck:int, dk:int, opening:bool=False):
    m = edges.copy()
    if opening:
        m  = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)), iterations=1)
    m  = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT,(odd(ck),odd(ck))), iterations=1)
    m  = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_RECT,(odd(dk),odd(dk))), iterations=1)
    return m

def ar_score(ar: float, lo: float = AR_MIN, hi: float = AR_MAX) -> float:
    mid=1.0; span=max(mid-lo,hi-mid); return float(max(0.0, 1.0-abs(ar-mid)/span))

def shape_features(cnt, W:int, H:int):
    area=cv2.contourArea(cnt); per=max(1e-6,cv2.arcLength(cnt,True))
    x,y,w,h=cv2.boundingRect(cnt)
    hull=cv2.convexHull(cnt); a_h=max(1e-6,cv2.contourArea(hull))
    solidity=float(area/a_h); circular=float(min(1.0,4.0*np.pi*area/(per*per)))
    rect=float(area/max(1,w*h)); ar=w/max(1.0,h); ar_s=ar_score(ar)
    bbox_ratio=(w*h)/(W*H); fill=rect
    return dict(area=area, per=per, bbox=(x,y,w,h), ar=ar, solidity=solidity,
                circular=circular, rect=rect, ar_s=ar_s, bbox_ratio=bbox_ratio, fill=fill)

def score_contour(feat, cx_img, cy_img, W:int, H:int):
    x,y,w,h=feat["bbox"]; area_norm=feat["area"]/(W*H)
    cx=x+w/2.0; cy=y+h/2.0
    dist=np.hypot(cx-cx_img,cy-cy_img)/np.hypot(cx_img,cy_img)
    score=(W_AREA*area_norm + W_FILL*feat["fill"] + W_SOLI*feat["solidity"] +
           W_CIRC*feat["circular"] + W_RECT*feat["rect"] + W_AR*feat["ar_s"] - W_DIST*dist)
    return float(score), float(dist)

def select_best(mask, min_area_px:int, W:int, H:int, hard_cap:float=BBOX_HARD_CAP):
    cnts,_=cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts: return None
    cx_img, cy_img = W/2.0, H/2.0
    best, best_s = None, -1e9
    for c in cnts:
        a=cv2.contourArea(c)
        if a < min_area_px: continue
        x,y,w,h=cv2.boundingRect(c)
        ar=w/max(1.0,h); bbox_ratio=(w*h)/(W*H)
        if not (AR_MIN<=ar<=AR_MAX): continue
        if bbox_ratio > hard_cap: continue
        feat=shape_features(c, W, H)
        s,_=score_contour(feat, cx_img, cy_img, W, H)
        if s>best_s:
            best_s=s; best=dict(cnt=c, score=s, **feat)
    return best

def color_gate(proc_bgr, profile: dict):
    if not profile or not profile.get("enable", False):
        return None
    mode = profile.get("mode", "lab_bg")
    H, W, _ = proc_bgr.shape
    mask = np.zeros((H,W), np.uint8)

    if mode == "lab_bg":
        lab = cv2.cvtColor(proc_bgr, cv2.COLOR_BGR2Lab)
        a = lab[...,1].astype(np.float32)
        b = lab[...,2].astype(np.float32)
        border = int(profile.get("lab", {}).get("border_px", 12))
        # robust background color from image border
        rim = np.zeros((H,W), np.uint8)
        rim[:border,:]=255; rim[-border:,:]=255; rim[:,:border]=255; rim[:,-border:]=255
        ab_stack = np.stack([a[rim>0], b[rim>0]], axis=1)
        if ab_stack.size == 0:
            return None
        a_bg = np.median(ab_stack[:,0]); b_bg = np.median(ab_stack[:,1])
        d = np.sqrt((a - a_bg)**2 + (b - b_bg)**2).astype(np.float32)
        thr = float(profile.get("lab", {}).get("ab_thresh", 20.0))
        mask = np.uint8((d >= thr) * 255)

    elif mode == "hsv_band":
        hsv = cv2.cvtColor(proc_bgr, cv2.COLOR_BGR2HSV)
        h = hsv[...,0]; s = hsv[...,1]; v = hsv[...,2]
        h_low = int(profile.get("hsv", {}).get("h_low", 10))
        h_high= int(profile.get("hsv", {}).get("h_high", 30))
        s_min = int(profile.get("hsv", {}).get("s_min", 60))
        v_min = int(profile.get("hsv", {}).get("v_min", 40))
        # wrap-around safe
        if h_low <= h_high:
            mask_h = (h>=h_low) & (h<=h_high)
        else:
            mask_h = (h>=h_low) | (h<=h_high)
        mask = np.uint8((mask_h & (s>=s_min) & (v>=v_min)) * 255)

    # light post
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)), 1)
    return mask

# ---------- Load ----------
img = cv2.imread(IMG_PATH)
if img is None: raise FileNotFoundError(IMG_PATH)
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
    if life < life_MIN: t1 = max(1.0,  t1 - Kp * (life_MIN - life))
    else:               t1 = min(220., t1 + Kp * (life - life_MAX))
cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_canny.png"), canny)

# ---------- Optional rescue ----------
used_rescue = False
edges = canny.copy()
if pct_on(canny) < RESCUE_life_MIN:
    th = adaptive_thresh(gray)
    edges = cv2.bitwise_or(canny, th); used_rescue = True
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_thresc.png"), th)

# ---------- Color gate (optional) ----------
color_mask = color_gate(proc, COLOR_GATE) if isinstance(COLOR_GATE, dict) else None
if color_mask is not None:
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_color_mask.png"), color_mask)
    if COLOR_GATE.get("combine", "OR").upper() == "AND":
        edges = cv2.bitwise_and(edges, color_mask)
    else:
        edges = cv2.bitwise_or(edges, color_mask)

# ---------- Bottom crop + despeckle + fill ----------
H, W = edges.shape[:2]
crop = int(max(0, min(40, BOTTOM_MARGIN_PCT)) * H / 100.0)
edges2 = edges.copy()
if crop > 0: edges2[-crop:, :] = 0
edges2 = despeckle(edges2, int(MIN_BLOB_PX))

filled = np.zeros_like(edges2)
cnts,_ = cv2.findContours(edges2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(filled, cnts, -1, 255, thickness=cv2.FILLED)
edges2 = filled
cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_edges_patched.png"), edges2)

def process_with_margin(margin: int):
    e = edges2.copy()
    if margin > 0:
        e[:margin, :] = 0; e[-margin:, :] = 0; e[:, :margin] = 0; e[:, -margin:] = 0
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_edges_m{margin}.png"), e)

    H, W = e.shape[:2]
    min_area_px = int(MIN_AREA_FRAC * W * H)
    ck, dk = 3, 3; opening = False; best = None

    for step in range(1, MORPH_STEPS + 1):
        m = run_morph(e, ck, dk, opening=opening)
        info = select_best(m, min_area_px, W, H, hard_cap=BBOX_HARD_CAP)
        if info is None:
            ck = min(CLOSE_MAX, ck + 2); dk = min(DIL_MAX, dk + 2); opening = True; continue
        print(f"[Morph {step}] ck={ck} dk={dk} bbox={info['bbox_ratio']:.3f} "
              f"fill={info['fill']:.2f} score={info['score']:.3f}")
        best = (m, info, ck, dk)
        if (BBOX_MIN <= info["bbox_ratio"] <= BBOX_MAX) and (FILL_MIN <= info["fill"] <= FILL_MAX): break
        if (info["fill"] < FILL_MIN) or (info["bbox_ratio"] < BBOX_MIN):
            ck = min(CLOSE_MAX, ck + 2); dk = min(DIL_MAX, dk + 2)
        elif (info["fill"] > FILL_MAX) or (info["bbox_ratio"] > BBOX_MAX):
            dk = max(DIL_MIN, dk - 2); ck = max(CLOSE_MIN, ck - 1); opening = True
    return best, e

best, e_used = process_with_margin(BORDER_MARGIN)
if best is None:
    print("↩️  Fallback: retry without margin")
    best, e_used = process_with_margin(0)

# ---------- Save ----------
if best is None:
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
    if color_mask is not None:
        cv2.putText(overlay, "color_gate", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_mask_final.png"), mask_final)
    cv2.imwrite(os.path.join(RES_DIR, f"{stamp}_overlay.png"), overlay)

    profile = {
      "algo": "canny(P)->rescue(if low)->color_gate(optional)->bottom-crop+despeckle->morph+shape_score",
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
                    "rect": W_RECT, "ar": W_AR, "center_bias": CENTER_BIAS},
        "color_gate": COLOR_GATE
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
