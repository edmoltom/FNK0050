"""Robot vision API backed by a stateful VisionEngine."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from .engine import VisionEngine, EngineResult

_ENGINE: Optional[VisionEngine] = None


def _engine() -> VisionEngine:
    """Lazily create and return the single VisionEngine instance."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = VisionEngine()
    return _ENGINE


def reset_state() -> None:
    """Reset internal stability state."""
    _engine().reset_state()


def load_profile(which: str, path: Optional[str] = None) -> None:
    """Reload a profile ('big' or 'small') and reset state."""
    _engine().load_profile(which, path)


def update_dynamic(which: str, params: Dict[str, Any]) -> None:
    """Update dynamic adjuster parameters at runtime."""
    _engine().update_dynamic(which, params)


def process_frame(
    frame: np.ndarray,
    return_overlay: bool = True,
    config: Optional[Dict[str, Any]] = None,
):
    """Process ``frame`` and return a detection dict.

    Signature remains compatible with previous versions.
    """
    res: EngineResult = _engine().process(
        frame, return_overlay=return_overlay, config=config
    )
    return res.data


def get_last_result() -> Optional[EngineResult]:
    """Return the last EngineResult or ``None``."""
    return _engine().get_last_result()


def get_detectors():
    """Return underlying detectors for inspection in tests."""
    return _engine().get_detectors()
