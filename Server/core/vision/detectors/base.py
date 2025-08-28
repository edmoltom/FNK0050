from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, Tuple

import numpy as np


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
    overlay: Optional[np.ndarray] = None
    t1: Optional[float] = None
    t2: Optional[int] = None
    color_cover_pct: Optional[float] = None
    color_used: Optional[bool] = None


class Detector(Protocol):
    """Interface for vision detectors."""

    name: str

    def configure(self, cfg: Any) -> None:
        """Configure detector using a configuration object or dict."""

    def infer(self, frame: np.ndarray, ctx: Optional[Any] = None) -> DetectionResult:
        """Run detection on a frame and return a :class:`DetectionResult`."""
