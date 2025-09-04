"""Lightweight face detection pipeline using OpenCV Haar cascades."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from .base_pipeline import BasePipeline, Result


class FacePipeline(BasePipeline):
    """Haar-cascade based face detection pipeline."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize pipeline with optional configuration.

        Parameters
        ----------
        config:
            Optional dictionary overriding default parameters.
        """

        cascades_dir = Path(__file__).resolve().parents[1] / "cascades"
        path = cascades_dir / "haarcascade_frontalface_default.xml"
        if not path.exists():
            raise RuntimeError(f"Haar cascade not found: {path}")
        self._cascade_path = str(path)
        self._cascade: Optional[cv2.CascadeClassifier] = None

        self.cfg: Dict[str, Any] = {
            "scale_factor": 1.1,
            "min_neighbors": 5,
            "min_size": (40, 40),
            "equalize_hist": True,
            "resize_ratio": 0.5,
        }
        if config:
            self.cfg.update(config)

        self._last_result: Optional[Result] = None

    # ------------------------------------------------------------------
    def _get_cascade(self) -> cv2.CascadeClassifier:
        if self._cascade is None:
            self._cascade = cv2.CascadeClassifier(self._cascade_path)
            if self._cascade.empty():
                raise RuntimeError(
                    f"Failed to load Haar cascade: {self._cascade_path}"
                )
        return self._cascade

    # ------------------------------------------------------------------
    def process(
        self,
        frame: np.ndarray,
        config: Optional[Dict[str, Any]] = None,
        ts: Optional[float] = None,
        roi: Optional[Tuple[int, int, int, int]] = None,
    ) -> Result:
        """Detect faces in ``frame``.

        Parameters
        ----------
        frame:
            BGR image to process.
        config:
            Optional overrides for detector parameters.
        roi:
            Optional region of interest ``(x, y, w, h)`` limiting the search.
        ts:
            Optional timestamp propagated into the result.
        """

        cfg = dict(self.cfg)
        if config:
            cfg.update(config)
        return_overlay = bool(cfg.pop("return_overlay", False))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if cfg.get("equalize_hist", True):
            gray = cv2.equalizeHist(gray)

        if roi is not None:
            x0, y0, w0, h0 = roi
            gray_roi = gray[y0 : y0 + h0, x0 : x0 + w0]
        else:
            gray_roi = gray

        ratio = float(cfg.get("resize_ratio", 0.5))
        work = gray_roi
        if 0 < ratio < 1.0:
            work = cv2.resize(gray_roi, None, fx=ratio, fy=ratio)

        cascade = self._get_cascade()
        rects = cascade.detectMultiScale(
            work,
            scaleFactor=float(cfg.get("scale_factor", 1.1)),
            minNeighbors=int(cfg.get("min_neighbors", 5)),
            minSize=tuple(cfg.get("min_size", (40, 40))),
        )

        if 0 < ratio < 1.0:
            inv = 1.0 / ratio
            rects = [
                (int(x * inv), int(y * inv), int(w * inv), int(h * inv))
                for (x, y, w, h) in rects
            ]

        if roi is not None:
            ox, oy = roi[0], roi[1]
            rects = [(x + ox, y + oy, w, h) for (x, y, w, h) in rects]

        faces = [
            {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            for (x, y, w, h) in rects
        ]

        data: Dict[str, Any] = {
            "ok": True,
            "type": "face",
            "faces": faces,
            "count": len(faces),
            "ts": ts,
            "space": (frame.shape[1], frame.shape[0]),
        }
        if return_overlay:
            data["overlay"] = self.draw_result(frame.copy(), data)

        res = Result(data, ts if ts is not None else time.time())
        self._last_result = res
        return res

    # ------------------------------------------------------------------
    def draw_result(self, frame: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
        """Draw detection ``result`` onto ``frame``."""
        faces = result.get("faces") or []
        for box in faces:
            x = int(box.get("x", 0))
            y = int(box.get("y", 0))
            w = int(box.get("w", 0))
            h = int(box.get("h", 0))
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                "face",
                (x, max(10, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )
        return frame

    # ------------------------------------------------------------------
    def reset_state(self) -> None:
        """No internal state to reset."""
        return None

    def load_profile(self, which: str, path: Optional[str] = None) -> None:
        """Profiles not supported for face detection."""
        return None

    def update_dynamic(self, which: str, params: Dict[str, Any]) -> None:
        """Dynamic parameters not supported for face detection."""
        return None

    def get_last_result(self) -> Optional[Result]:
        """Return the last :class:`Result`."""
        return self._last_result

    def get_detectors(self) -> Tuple[Any, Any]:
        """Return the underlying detector (cascade classifier)."""
        return (self._cascade, None)

