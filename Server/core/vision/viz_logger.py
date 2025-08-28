import os, csv, time
from typing import Optional, Tuple
import numpy as np

from .engine import VisionEngine
from .detectors.contour_detector import ContourDetector, DetectionResult

def _ref_size(det: ContourDetector) -> Tuple[int,int]:
    return det.proc.proc_w, det.proc.proc_h

class VisionLogger:
    """
    Registra por frame:
    idx, ts, det_tag, ref_w, ref_h, t1, t2, life, rescue, color_cover, color_used,
    ck, dk, bbox(x,y,w,h), score, fill, bbox_ratio.
    Guarda artefactos (original, canny, color_mask, edges_patched, mask_final, overlay, etc.)
    cada `stride` frames usando el propio detector.
    """
    def __init__(self, engine: VisionEngine, output_dir: Optional[str] = None, stride: int = 5):
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.run_dir = output_dir or os.path.join("runs", "vision", ts)
        os.makedirs(self.run_dir, exist_ok=True)
        self.csv_path = os.path.join(self.run_dir, "log.csv")
        self.csv = open(self.csv_path, "w", newline="", encoding="utf-8")
        self.w = csv.writer(self.csv)
        self.w.writerow([
            "frame","ts","det","ref_w","ref_h","t1","t2","life","rescue",
            "color_cover_pct","color_used","ck","dk","x","y","w","h",
            "score","fill","bbox_ratio"
        ])
        self.stride = max(1,int(stride))
        self.idx = 0
        self.engine = engine
        self.det_big, self.det_small = self.engine.get_detectors()

    def log_only(self, frame_bgr, out=None):
        """Usa el resultado ya calculado (out) y SOLO cada 'stride' guarda artefactos/CSV."""
        self.idx += 1
        tag = "big"
        if out and "space" in out:
            tag, det = self._which(tuple(out["space"]))
        else:
            tag, det = "big", self.det_big
        stamp = f"f{self.idx:06d}"

        if (self.idx % self.stride) != 0:
            return  # no hacer nada este frame

        res = det.detect(frame_bgr, save_dir=self.run_dir, stamp=stamp,
                         save_profile=True, return_overlay=False)

        x=y=w=h=0
        if res.bbox: x,y,w,h = res.bbox
        self.w.writerow([
            self.idx, f"{time.time():.3f}", tag,
            det.proc.proc_w, det.proc.proc_h,
            f"{(res.t1 or 0.0):.1f}", int(res.t2 or 0),
            f"{res.life_canny_pct:.2f}", int(bool(res.used_rescue)),
            f"{(res.color_cover_pct or 0.0):.2f}", int(bool(res.color_used)),
            int(res.chosen_ck or 0), int(res.chosen_dk or 0),
            x,y,w,h,
            f"{(res.score or 0.0):.4f}", f"{(res.fill or 0.0):.4f}", f"{(res.bbox_ratio or 0.0):.4f}",
        ])
        self.csv.flush()

    def _which(self, space):
        # refresco perezoso
        if self.det_big is None or self.det_small is None:
            self.det_big, self.det_small = self.engine.get_detectors()
        # si siguen a None (muy raro), fallback seguro
        if self.det_big is None and self.det_small is None:
            return "big", None
        # tamaños de referencia (con guardas)
        rb = _ref_size(self.det_big) if self.det_big else (0,0)
        rs = _ref_size(self.det_small) if self.det_small else (0,0)
        if tuple(space) == tuple(rb): return "big", self.det_big
        if tuple(space) == tuple(rs): return "small", self.det_small
        return "big", (self.det_big or self.det_small)

    def step(self, frame_bgr: np.ndarray):
        """Procesa un frame, devuelve overlay para visualizar."""
        self.idx += 1
        out = self.engine.process(frame_bgr)
        tag, det = self._which(tuple(out.get("space", (0,0))))
        stamp = f"f{self.idx:06d}"
        save_dir = self.run_dir if (self.idx % self.stride == 0) else None

        # Ejecutamos el detector elegido sobre el frame completo para logging.
        res: DetectionResult = det.detect(
            frame_bgr, save_dir=save_dir, stamp=stamp,
            save_profile=True, return_overlay=True
        )

        # Escribir CSV
        x=y=w=h=0
        if res.bbox: x,y,w,h = res.bbox
        self.w.writerow([
            self.idx, f"{time.time():.3f}", tag,
            det.proc.proc_w, det.proc.proc_h,
            f"{(res.t1 or 0.0):.1f}", int(res.t2 or 0),
            f"{res.life_canny_pct:.2f}", int(bool(res.used_rescue)),
            f"{(res.color_cover_pct or 0.0):.2f}", int(bool(res.color_used)),
            int(res.chosen_ck or 0), int(res.chosen_dk or 0),
            x,y,w,h,
            f"{(res.score or 0.0):.4f}", f"{(res.fill or 0.0):.4f}", f"{(res.bbox_ratio or 0.0):.4f}",
        ])
        self.csv.flush()
        # Preferimos overlay del API si vino, si no, el del detector
        return out.get("overlay", res.overlay)

    def close(self):
        try: self.csv.close()
        except: pass

# Uso rápido (bucle de cámara):
if __name__ == "__main__":
    import cv2
    eng = VisionEngine({"stable": True, "roi_factor":1.8, "ema":0.7})
    eng.reload_config()
    cap = cv2.VideoCapture(0)
    logger = VisionLogger(engine=eng, stride=5)
    try:
        while True:
            ok, frame = cap.read()
            if not ok: break
            overlay = logger.step(frame)
            if overlay is not None:
                cv2.imshow("overlay", overlay)
            if (cv2.waitKey(1) & 0xFF) == 27:  # ESC
                break
    finally:
        logger.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Run guardado en:", logger.run_dir)