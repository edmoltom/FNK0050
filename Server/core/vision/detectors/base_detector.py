from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from numpy.typing import NDArray

from .results import DetectionResult


class BaseDetector(ABC):
    """Abstract interface for vision detectors."""

    @abstractmethod
    def detect(
        self,
        frame: NDArray,
        state: Optional[Dict[str, Any]] = None,
        knobs: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """Run detection on *frame*.

        Args:
            frame: Image frame in BGR color space.
            state: Mutable state carried between calls.
            knobs: Runtime configuration overrides.

        Returns:
            DetectionResult: Outcome of the detector.
        """
        raise NotImplementedError
