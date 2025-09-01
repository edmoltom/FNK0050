import os, csv, time
from typing import Optional, Tuple, Callable
import numpy as np
import cv2

from .engine import EngineResult
from .overlays import draw_result
from .detectors.contour_detector import ContourDetector

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
    def __init__(
        self,
        output_dir: Optional[str] = None,
        stride: int = 5,
        api_config: Optional[dict] = None,
        process_frame: Optional[Callable] = None,
        get_detectors: Optional[Callable] = None,
    ):
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
        self.api_cfg = dict(api_config or {})
        self._process_frame = process_frame
        self._get_detectors = get_detectors
        self.det_big: Optional[ContourDetector]
        self.det_small: Optional[ContourDetector]
        self.det_big = self.det_small = None
        self._ensure_api()

    def _ensure_api(self) -> None:
        """Lazily import vision API helpers and detectors."""
        if self._process_frame is None or self._get_detectors is None:
            from . import api as _api
            if self._process_frame is None:
                self._process_frame = _api.process_frame
            if self._get_detectors is None:
                self._get_detectors = _api.get_detectors
        if (self.det_big is None or self.det_small is None) and self._get_detectors:
            self.det_big, self.det_small = self._get_detectors()

    def log(self, frame_bgr: np.ndarray, result: EngineResult) -> None:
        """Log detection ``result`` for ``frame_bgr`` and save artefacts."""
        self._ensure_api()
        self.idx += 1
        space = tuple(result.data.get("space", (0, 0)))
        tag, _det = self._which(space)
        ref_w, ref_h = space
        stamp = f"f{self.idx:06d}"
        data = result.data
        x, y, w, h = data.get("bbox", (0, 0, 0, 0))
        row = [
            self.idx,
            f"{result.timestamp:.3f}",
            tag,
            ref_w,
            ref_h,
            data.get("t1", 0),
            data.get("t2", 0),
            data.get("life", 0),
            data.get("rescue", data.get("used_rescue", 0)),
            data.get("color_cover_pct", data.get("color_cover", 0)),
            data.get("color_used", 0),
            data.get("ck", data.get("chosen_ck", 0)),
            data.get("dk", data.get("chosen_dk", 0)),
            x,
            y,
            w,
            h,
            data.get("score", 0),
            data.get("fill", 0),
            data.get("bbox_ratio", 0),
        ]
        self.w.writerow(row)
        self.csv.flush()

        if self.idx % self.stride == 0:
            cv2.imwrite(os.path.join(self.run_dir, f"{stamp}_orig.jpg"), frame_bgr)

        overlay = data.get("overlay")
        if overlay is None:
            overlay = draw_result(frame_bgr.copy(), result)
        cv2.imwrite(os.path.join(self.run_dir, f"{stamp}_overlay.jpg"), overlay)

    def log_only(self, frame_bgr, out=None):
        """Backward-compatible alias forwarding to :meth:`log`."""
        if isinstance(out, EngineResult):
            result = out
        else:
            result = EngineResult(out or {}, time.time())
        self.log(frame_bgr, result)

    def _which(self, space):
        self._ensure_api()
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
        """Procesa un frame y devuelve overlay para visualizar."""
        self._ensure_api()
        self._process_frame(frame_bgr, return_overlay=True, config=self.api_cfg)
        from . import api as _api
        result = _api.get_last_result() or EngineResult({}, time.time())
        self.log(frame_bgr, result)
        return result.data.get("overlay") or draw_result(frame_bgr.copy(), result)

    def close(self):
        try: self.csv.close()
        except: pass


def create_logger(
    *, enable: bool, stride: int = 5, output_dir: Optional[str] = None
) -> Optional["VisionLogger"]:
    """Create a :class:`VisionLogger` when ``enable`` is ``True``.

    Parameters
    ----------
    enable:
        When ``False`` return ``None`` instead of a logger instance.
    stride:
        Optional frame stride for artefact logging.
    output_dir:
        Optional directory for logged artefacts.
    """

    if not enable:
        return None
    return VisionLogger(output_dir=output_dir, stride=stride, api_config={"stable": True})

# Uso rápido (bucle de cámara):
if __name__ == "__main__":
    import cv2
    cap = cv2.VideoCapture(0)
    logger = VisionLogger(stride=5, api_config={"stable": True, "roi_factor":1.8, "ema":0.7})
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
