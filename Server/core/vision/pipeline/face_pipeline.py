"""Stub face detection pipeline to validate modularity."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import time
import numpy as np

from .base_pipeline import BasePipeline, Result


class FacePipeline(BasePipeline):
    """Placeholder pipeline for face detection."""

    def process(self, frame: np.ndarray, config: Optional[Dict[str, Any]] = None) -> Result:
        # This stub simply returns a not-implemented result.
        data: Dict[str, Any] = {"ok": False, "reason": "face detection not implemented"}
        return Result(data, time.time())

    def reset_state(self) -> None:  # pragma: no cover - stub
        return None

    def load_profile(self, which: str, path: Optional[str] = None) -> None:  # pragma: no cover - stub
        return None

    def update_dynamic(self, which: str, params: Dict[str, Any]) -> None:  # pragma: no cover - stub
        return None

    def get_last_result(self) -> Optional[Result]:  # pragma: no cover - stub
        return None

    def get_detectors(self) -> Tuple[Any, Any]:  # pragma: no cover - stub
        return (None, None)
