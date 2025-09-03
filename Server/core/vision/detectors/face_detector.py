from __future__ import annotations

from typing import Any, Dict, Optional
from numpy.typing import NDArray

from .base_detector import BaseDetector
from .results import DetectionResult


class FaceDetector(BaseDetector):
    """Example stub detector implementing :class:`BaseDetector`."""

    def detect(
        self,
        frame: NDArray,
        state: Optional[Dict[str, Any]] = None,
        knobs: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """Dummy implementation returning a negative result."""
        return DetectionResult(ok=False)
