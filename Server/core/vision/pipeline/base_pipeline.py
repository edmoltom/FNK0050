"""Base interface for vision pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import time
import numpy as np


@dataclass
class Result:
    """Result of one pipeline processing step."""
    data: Dict[str, Any]
    timestamp: float


class BasePipeline:
    """Abstract vision pipeline."""

    def process(self, frame: np.ndarray, config: Optional[Dict[str, Any]] = None) -> Result:
        """Process ``frame`` using optional ``config`` and return a :class:`Result`."""
        raise NotImplementedError

    # Optional helpers for subclasses ---------------------------------
    def reset_state(self) -> None:
        """Reset internal state."""
        return None

    def load_profile(self, which: str, path: Optional[str] = None) -> None:
        """Load detector profile if supported."""
        return None

    def update_dynamic(self, which: str, params: Dict[str, Any]) -> None:
        """Update dynamic parameters if supported."""
        return None

    def get_last_result(self) -> Optional[Result]:
        """Return the last :class:`Result` produced."""
        return None

    def get_detectors(self) -> Tuple[Any, Any]:
        """Return underlying detectors if available."""
        return (None, None)
