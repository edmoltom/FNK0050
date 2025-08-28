from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, Tuple

import numpy as np


@dataclass
class DetectionResult:
    """Structured result returned by a detector."""

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


@dataclass
class DetectionContext:
    """Execution context passed to detectors.

    Attributes:
        save_dir: Directory where intermediate images will be stored.
        stamp: Prefix for saved files within ``save_dir``.
        save_profile: Whether to persist profile snapshots.
        return_overlay: Whether detectors should return overlay images.
    """

    save_dir: Optional[str] = None
    stamp: Optional[str] = None
    save_profile: bool = True
    return_overlay: bool = True


class Detector(Protocol):
    """Interface for vision detectors."""

    name: str

    def configure(self, cfg: Any) -> None:
        """Configure detector using a configuration object or dictionary."""

    def infer(self, frame: np.ndarray, ctx: Optional[DetectionContext] = None) -> DetectionResult:
        """Run detection on ``frame``.

        Args:
            frame: BGR image in NumPy array format.
            ctx: Optional execution context.

        Returns:
            DetectionResult: Structured detection output.
        """
