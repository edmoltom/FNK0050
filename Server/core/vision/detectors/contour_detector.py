import os, json, time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union

import cv2
import numpy as np

NDArray = np.ndarray

def _odd(k: int) -> int:
    k = int(k)
    return k if (k % 2 == 1) else k + 1

def _pct_on(mask: NDArray) -> float:
    return 100.0 * float((mask > 0).sum()) / float(mask.size)

def _adaptive_thresh(gray: NDArray) -> NDArray:
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

def _despeckle(bin_img: NDArray, min_px: int) -> NDArray:
    """Remove connected components smaller than min_px (0/255 image)."""
    if min_px <= 0:
        return bin_img
    lab = (bin_img > 0).astype("uint8")
    num, labels, stats, _ = cv2.connectedComponentsWithStats(lab, 8)
    keep = np.zeros_like(bin_img)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_px:
            keep[labels == i] = 255
    return keep

@dataclass
class MorphConfig:
    close_min: int = 3
    close_max: int = 21   # was 15
    dil_min: int = 3
    dil_max: int = 15     # was 11
    steps: int = 10       # was 6

@dataclass
class CannyConfig:
    t1_init: float = 50.0
    t2_ratio: float = 2.5
    life_min: float = 5.0
    life_max: float = 10.0
    rescue_life_min: float = 3.0
    kp: float = 4.0
    max_iter: int = 25

@dataclass
class GeoFilters:
    ar_min: float = 0.40
    ar_max: float = 2.20
    bbox_hard_cap: float = 0.50
    bbox_min: float = 0.18   # was 0.05 → fuerza cuerpo
    bbox_max: float = 0.35
    fill_min: float = 0.60
    fill_max: float = 0.95
    min_area_frac: float = 0.03  # was 0.01

@dataclass
class Weights:
    area: float = 0.35   # + área
    fill: float = 0.15   # - fill
    solidity: float = 0.20
    circular: float = 0.10
    rect: float = 0.15
    ar: float = 0.10
    center_bias: float = 0.25
    dist: float = 0.20

@dataclass
class ProcConfig:
    proc_w: int = 160
    proc_h: int = 120
    blur_k: int = 5
    border_margin: int = 6

@dataclass
class PreMorphPatches:
    bottom_margin_pct: int = 20  # 0..40 sensato
    min_blob_px: int = 100       # despeckle previo
    fill_from_edges: bool = True # rellenar contornos antes de morfología

@dataclass
class DetectionResult:
    ok: bool
    used_rescue: bool
    life_canny_pct: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    score: Optional[float] = None
    fill: Optional[float] = None
    bbox_ratio: Optional[float] = None
    chosen_ck: Optional[int] = None
    chosen_dk: Optional[int] = None
    center: Optional[Tuple[int, int]] = None
    overlay: Optional[NDArray] = None

class ContourDetector:
    """
    Stable 160x120 contour pipeline + minimal pre-morph patches:
    - bottom crop (floor/cable)
    - despeckle (remove tiny blobs)
    - fill-from-edges (turn strokes into solid regions)
    """
    def __init__(
        self,
        proc: ProcConfig = ProcConfig(),
        canny: CannyConfig = CannyConfig(),
        morph: MorphConfig = MorphConfig(),
        geo: GeoFilters = GeoFilters(),
        w: Weights = Weights(),
        premorph: PreMorphPatches = PreMorphPatches()
    ) -> None:
        self.proc = proc
        self.canny_cfg = canny
        self.morph_cfg = morph
        self.geo = geo
        self.w = w
        self.premorph = premorph

    # ----------------------------- Public API -----------------------------
    def detect(
        self,
        img_or_path: Union[str, NDArray],
        save_dir: Optional[str] = None,
        stamp: Optional[str] = None,
        save_profile: bool = True,
        return_overlay: bool = True,
    ) -> DetectionResult:
        img = self._load_image(img_or_path)
        if img is None:
            raise FileNotFoundError(str(img_or_path))

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        if stamp is None:
            stamp = time.strftime("%Y%m%d_%H%M%S")

        # ----- Preprocess -----
        proc, gray = self._preprocess(img)

        # ----- Auto Canny -----
        canny, t1, t2, life = self._auto_canny(gray)

        used_rescue = False
        edges = canny.copy()
        if _pct_on(canny) < self.canny_cfg.rescue_life_min:
            th = _adaptive_thresh(gray)
            edges = cv2.bitwise_or(canny, th)
            used_rescue = True
            if save_dir is not None:
                cv2.imwrite(os.path.join(save_dir, f"{stamp}_thresc.png"), th)

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_canny.png"), canny)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_original.png"), img)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_proc.png"), proc)

        # ----- Pre-morph patches (NEW) -----
        H, W = edges.shape[:2]
        edges2 = edges.copy()
        crop = int(max(0, min(40, self.premorph.bottom_margin_pct)) * H / 100.0)
        if crop > 0:
            edges2[-crop:, :] = 0

        edges2 = _despeckle(edges2, int(self.premorph.min_blob_px))

        if self.premorph.fill_from_edges:
            filled = np.zeros_like(edges2)
            cnts, _ = cv2.findContours(edges2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(filled, cnts, -1, 255, thickness=cv2.FILLED)
            edges2 = filled

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_edges_patched.png"), edges2)

        # ----- Main selection -----
        best, e_used = self._try_with_margins(edges2)
        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_edges_used.png"), e_used)

        if best is None:
            if save_dir is not None:
                cv2.imwrite(os.path.join(save_dir, f"{stamp}_mask_final.png"), e_used)
            return DetectionResult(
                ok=False,
                used_rescue=used_rescue,
                life_canny_pct=float(_pct_on(canny)),
            )

        mask_final, info, chosen_ck, chosen_dk = best
        overlay, center = self._draw_overlay(proc, info, mask_final)

        if save_dir is not None:
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_mask_final.png"), mask_final)
            cv2.imwrite(os.path.join(save_dir, f"{stamp}_overlay.png"), overlay)

        result = DetectionResult(
            ok=True,
            used_rescue=used_rescue,
            life_canny_pct=float(_pct_on(canny)),
            bbox=tuple(int(v) for v in info["bbox"]),
            score=float(info["score"]),
            fill=float(info["fill"]),
            bbox_ratio=float(info["bbox_ratio"]),
            chosen_ck=int(chosen_ck),
            chosen_dk=int(chosen_dk),
            center=center,
            overlay=overlay if return_overlay else None,
        )

        if save_dir is not None and save_profile:
            prof = self._make_profile(info, t1, t2, stamp, os.path.basename(str(img_or_path)))
            prof["params"]["morph"]["chosen_ck"] = int(chosen_ck)
            prof["params"]["morph"]["chosen_dk"] = int(chosen_dk)
            prof["params"]["patched"] = {
                "bottom_margin_pct": int(self.premorph.bottom_margin_pct),
                "min_blob_px": int(self.premorph.min_blob_px),
                "fill_from_edges": bool(self.premorph.fill_from_edges),
            }
            prof["metrics"]["life_canny_%"] = float(result.life_canny_pct)
            prof["metrics"]["used_rescue"] = bool(result.used_rescue)
            with open(os.path.join(save_dir, f"{stamp}_profile.json"), "w", encoding="utf-8") as f:
                json.dump(prof, f, ensure_ascii=False, indent=2)

        return result

    # --------------------------- Internals ---------------------------
    def _load_image(self, img_or_path: Union[str, NDArray]) -> Optional[NDArray]:
        if isinstance(img_or_path, str):
            return cv2.imread(img_or_path)
        if isinstance(img_or_path, np.ndarray):
            if img_or_path.ndim == 2:
                return cv2.cvtColor(img_or_path, cv2.COLOR_GRAY2BGR)
            return img_or_path.copy()
        return None

    def _preprocess(self, img: NDArray):
        proc = cv2.resize(
            img, (self.proc.proc_w, self.proc.proc_h), interpolation=cv2.INTER_AREA
        )
        gray = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (_odd(self.proc.blur_k), _odd(self.proc.blur_k)), 0)
        return proc, gray

    def _auto_canny(self, gray: NDArray):
        cfg = self.canny_cfg
        t1 = float(cfg.t1_init)
        life = 0.0
        for _ in range(1, cfg.max_iter + 1):
            t2 = int(np.clip(cfg.t2_ratio * t1, 0, 255))
            canny = cv2.Canny(gray, int(max(0, t1)), int(t2))
            life = _pct_on(canny)
            if cfg.life_min <= life <= cfg.life_max:
                break
            if life < cfg.life_min:
                t1 = max(1.0, t1 - cfg.kp * (cfg.life_min - life))
            else:
                t1 = min(220.0, t1 + cfg.kp * (life - cfg.life_max))
        return canny, t1, int(np.clip(cfg.t2_ratio * t1, 0, 255)), life

    def _run_morph(self, edges: NDArray, ck: int, dk: int, opening: bool = False) -> NDArray:
        m = edges.copy()
        if opening:
            k0 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k0, iterations=1)
        k1 = cv2.getStructuringElement(cv2.MORPH_RECT, (_odd(ck), _odd(ck)))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k1, iterations=1)
        k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (_odd(dk), _odd(dk)))
        m = cv2.dilate(m, k2, iterations=1)
        return m

    def _ar_score(self, ar: float) -> float:
        lo, hi = self.geo.ar_min, self.geo.ar_max
        mid = 1.0
        span = max(mid - lo, hi - mid)
        return float(max(0.0, 1.0 - abs(ar - mid) / span))

    def _shape_features(self, cnt: NDArray, W: int, H: int) -> Dict[str, Any]:
        area = cv2.contourArea(cnt)
        per = max(1e-6, cv2.arcLength(cnt, True))
        x, y, w, h = cv2.boundingRect(cnt)
        hull = cv2.convexHull(cnt)
        a_hull = max(1e-6, cv2.contourArea(hull))
        solidity = float(area / a_hull)
        circular = float(min(1.0, 4.0 * np.pi * area / (per * per)))
        rectangularity = float(area / (w * h))
        ar = w / max(1.0, h)
        ar_s = self._ar_score(ar)
        bbox_ratio = (w * h) / (W * H)
        fill = rectangularity
        return {
            "area": area, "per": per, "bbox": (x, y, w, h), "ar": ar,
            "solidity": solidity, "circular": circular, "rect": rectangularity,
            "ar_s": ar_s, "bbox_ratio": bbox_ratio, "fill": fill
        }

    def _score_contour(self, feat: Dict[str, Any], cx_img: float, cy_img: float, W: int, H: int):
        x, y, w, h = feat["bbox"]
        area_norm = feat["area"] / (W * H)
        cx = x + w / 2.0
        cy = y + h / 2.0
        dist = np.hypot(cx - cx_img, cy - cy_img) / np.hypot(cx_img, cy_img)
        sc = (
            self.w.area * area_norm +
            self.w.fill * feat["fill"] +
            self.w.solidity * feat["solidity"] +
            self.w.circular * feat["circular"] +
            self.w.rect * feat["rect"] +
            self.w.ar * feat["ar_s"] -
            (self.w.dist * self.w.center_bias) * dist
        )
        return float(sc), float(dist)

    def _select_best(self, mask: NDArray, min_area_px: int, W: int, H: int, hard_cap: float):
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
            if not (self.geo.ar_min <= ar <= self.geo.ar_max):
                continue
            if bbox_ratio > hard_cap:
                continue
            feat = self._shape_features(c, W, H)
            s, _ = self._score_contour(feat, cx_img, cy_img, W, H)
            if s > best_s:
                best_s = s
                best = dict(cnt=c, score=s, **feat)
        return best

    def _process_with_margin(self, edges: NDArray, margin: int):
        e = edges.copy()
        if margin > 0:
            e[:margin, :] = 0
            e[-margin:, :] = 0
            e[:, :margin] = 0
            e[:, -margin:] = 0

        H, W = e.shape[:2]
        min_area_px = int(self.geo.min_area_frac * W * H)
        ck, dk = 3, 3
        opening = False
        best = None

        for _ in range(1, self.morph_cfg.steps + 1):
            m = self._run_morph(e, ck, dk, opening=opening)
            info = self._select_best(m, min_area_px, W, H, self.geo.bbox_hard_cap)
            if info is None:
                ck = min(self.morph_cfg.close_max, ck + 2)
                dk = min(self.morph_cfg.dil_max, dk + 2)   # un paso más agresivo
                opening = True
                continue

            best = (m, info, ck, dk)
            if (self.geo.bbox_min <= info["bbox_ratio"] <= self.geo.bbox_max) and (self.geo.fill_min <= info["fill"] <= self.geo.fill_max):
                break
            if (info["fill"] < self.geo.fill_min) or (info["bbox_ratio"] < self.geo.bbox_min):
                ck = min(self.morph_cfg.close_max, ck + 2)
                dk = min(self.morph_cfg.dil_max, dk + 2)
            elif (info["fill"] > self.geo.fill_max) or (info["bbox_ratio"] > self.geo.bbox_max):
                dk = max(self.morph_cfg.dil_min, dk - 2)
                ck = max(self.morph_cfg.close_min, ck - 1)
                opening = True

        return best, e

    def _try_with_margins(self, edges: NDArray):
        best, e_used = self._process_with_margin(edges, self.proc.border_margin)
        if best is None:
            best, e_used = self._process_with_margin(edges, 0)
        return best, e_used

    def _draw_overlay(self, proc: NDArray, info: Dict[str, Any], mask_final: NDArray):
        overlay = proc.copy()
        x, y, w, h = info["bbox"]
        cv2.drawContours(mask_final, [info["cnt"]], -1, 255, thickness=cv2.FILLED)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
        M = cv2.moments(info["cnt"])
        c = (x + w // 2, y + h // 2)
        if M["m00"] != 0:
            c = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        cv2.circle(overlay, c, 4, (0, 255, 0), -1)
        txt = f"fill={info['fill']:.2f} bbox={info['bbox_ratio']:.2f} sc={info['score']:.2f}"
        cv2.putText(overlay, txt, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return overlay, c

    def _make_profile(self, info: Dict[str, Any], t1: float, t2: int, stamp: str, image_name: str):
        return {
            "algo": "canny(P)->rescue(thresh OR)->premorph(crop+despeckle+fill)->morph+shape_score",
            "input": {"image": image_name, "proc_size": [self.proc.proc_w, self.proc.proc_h]},
            "params": {
                "blur_k": self.proc.blur_k,
                "t1": int(t1),
                "t2": int(t2),
                "life_target_range": [self.canny_cfg.life_min, self.canny_cfg.life_max],
                "rescue_threshold_min": self.canny_cfg.rescue_life_min,
                "morph": {
                    "targets": {"bbox_ratio": [self.geo.bbox_min, self.geo.bbox_max], "fill_ratio": [self.geo.fill_min, self.geo.fill_max]},
                    "border_margin": self.proc.border_margin,
                    "hard_cap": self.geo.bbox_hard_cap,
                    "limits": {"close_max": self.morph_cfg.close_max, "dil_max": self.morph_cfg.dil_max, "steps": self.morph_cfg.steps}
                },
                "filters": {"ar_range": [self.geo.ar_min, self.geo.ar_max], "min_area_frac": self.geo.min_area_frac},
                "weights": {
                    "area": self.w.area, "fill": self.w.fill, "solidity": self.w.solidity,
                    "circular": self.w.circular, "rect": self.w.rect, "ar": self.w.ar, "center_bias": self.w.center_bias
                }
            },
            "metrics": {
                "life_canny_%": None,
                "used_rescue": None,
                "bbox_ratio": float(info["bbox_ratio"]),
                "fill_ratio": float(info["fill"]),
                "score": float(info["score"]),
            }
        }

# CLI helper
def run_file(image_path: str, out_dir: Optional[str] = "results"):
    det = ContourDetector()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    res = det.detect(image_path, save_dir=out_dir, stamp=stamp)
    if res.ok and out_dir:
        prof_path = os.path.join(out_dir, f"{stamp}_profile.json")
        if os.path.exists(prof_path):
            with open(prof_path, "r", encoding="utf-8") as f:
                prof = json.load(f)
            prof["metrics"]["life_canny_%"] = float(res.life_canny_pct)
            prof["metrics"]["used_rescue"] = bool(res.used_rescue)
            with open(prof_path, "w", encoding="utf-8") as f:
                json.dump(prof, f, ensure_ascii=False, indent=2)
    return res

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Contour-based detector (stable 160x120 pipeline + premorph patches)")
    p.add_argument("image", help="Path to input image (e.g., base.png)")
    p.add_argument("--out", default="results", help="Output directory for artifacts")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    r = run_file(args.image, args.out)
    if r.ok:
        print(f"✅ bbox={r.bbox}, score={r.score:.3f}, fill={r.fill:.2f}, ratio={r.bbox_ratio:.3f}")
    else:
        print("⚠️  No candidates.")
