from __future__ import annotations

from typing import Any, Optional

import numpy as np

from .base import Detector, DetectionResult, DetectionContext


class FaceDetector(Detector):
    """Placeholder face detector using Haar or DNN classifiers."""

    name = "face"

    def __init__(self) -> None:
        self.cascade = None
        self.net = None

    def configure(self, cfg: Any) -> None:
        """Configure the detector.

        Args:
            cfg: Arbitrary configuration mapping.
        """
        if isinstance(cfg, dict):
            self.cascade = cfg.get("cascade")
            self.net = cfg.get("net")

    def infer(self, frame: np.ndarray, ctx: Optional[DetectionContext] = None) -> DetectionResult:
        """Run detection on ``frame``.

        Args:
            frame: BGR image to analyse.
            ctx: Optional execution context (unused).

        Returns:
            DetectionResult: Always a negative placeholder result.
        """
        return DetectionResult(ok=False, used_rescue=False, life_canny_pct=0.0)
