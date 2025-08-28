import os
import time
import json
from typing import Optional, Dict, Any, TYPE_CHECKING

import cv2
import numpy as np

from .overlays import draw_engine

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .engine import EngineResult


class VizLogger:
    """Lightweight logger that stores frames, overlays and metadata.

    It receives precomputed :class:`EngineResult` dictionaries (produced by
    :class:`VisionEngine`) and, according to the configured stride, dumps
    the raw frame, the provided overlay and a JSON file with metadata.
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        stride: int = 5,
        save_raw: bool = False,
    ) -> None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.run_dir = output_dir or os.path.join("runs", "vision", ts)
        os.makedirs(self.run_dir, exist_ok=True)
        self.stride = max(1, int(stride))
        self.save_raw = bool(save_raw)
        self.idx = 0

    # ------------------------------------------------------------------
    def log(
        self,
        frame_bgr: Optional[np.ndarray],
        result: "EngineResult",
        overlay: Optional[np.ndarray] = None,
    ) -> None:
        """Log the given data if the stride condition is met."""
        self.idx += 1
        if self.idx % self.stride != 0:
            return

        stamp = f"f{self.idx:06d}"
        data: Dict[str, Any] = {"frame": self.idx, "ts": time.time()}

        # Copy result, normalising types and skipping the overlay array
        for k, v in dict(result or {}).items():
            if k == "overlay":
                continue
            if isinstance(v, np.generic):
                data[k] = v.item()
            elif isinstance(v, np.ndarray):
                data[k] = v.tolist()
            else:
                data[k] = v

        # Save raw frame if requested
        if frame_bgr is not None and self.save_raw:
            raw_name = f"{stamp}_raw.png"
            cv2.imwrite(os.path.join(self.run_dir, raw_name), frame_bgr)
            data["raw"] = raw_name

        if overlay is None and frame_bgr is not None:
            try:
                overlay = draw_engine(frame_bgr, result)
            except Exception:
                overlay = None
        if overlay is not None:
            ov_name = f"{stamp}_overlay.png"
            cv2.imwrite(os.path.join(self.run_dir, ov_name), overlay)
            data["overlay"] = ov_name

        meta_path = os.path.join(self.run_dir, f"{stamp}.json")
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def close(self) -> None:  # pragma: no cover - kept for API symmetry
        """Placeholder for compatibility with previous logger API."""
        return
