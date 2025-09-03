"""Robot vision API backed by modular pipelines."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

import numpy as np

from .pipeline import BasePipeline, ContourPipeline, FacePipeline, Result

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from .viz_logger import VisionLogger

_FACE_DEFAULTS: Dict[str, Any] = dict(
    scale_factor=1.1,
    min_neighbors=5,
    min_size=(40, 40),
    equalize_hist=True,
    resize_ratio=1.0,
)

_PIPELINES: Dict[str, BasePipeline] = {
    "object": ContourPipeline(),
    "face": FacePipeline(_FACE_DEFAULTS),
}
_CURRENT: str = "object"


def _pipeline() -> BasePipeline:
    return _PIPELINES[_CURRENT]


def reset_state() -> None:
    """Reset internal stability state."""
    _pipeline().reset_state()


def load_profile(which: str, path: Optional[str] = None) -> None:
    """Reload a profile ('big' or 'small') and reset state."""
    _pipeline().load_profile(which, path)


def update_dynamic(which: str, params: Dict[str, Any]) -> None:
    """Update dynamic adjuster parameters at runtime."""
    _pipeline().update_dynamic(which, params)


def register_pipeline(name: str, pipeline: BasePipeline) -> None:
    """Register a new pipeline under ``name``."""
    _PIPELINES[name] = pipeline


def select_pipeline(name: str) -> None:
    """Select vision pipeline by ``name``."""
    global _CURRENT
    if name not in _PIPELINES:
        raise ValueError("unknown pipeline")
    _CURRENT = name


def process(
    frame: np.ndarray,
    return_overlay: bool = True,
    config: Optional[Dict[str, Any]] = None,
):
    """Process ``frame`` and return a detection dict."""
    cfg = dict(config or {})
    cfg["return_overlay"] = return_overlay
    res: Result = _pipeline().process(frame, cfg)
    return res.data


# VisionLogger fetches the latest detection result through this helper.
def get_last_result() -> Optional[Result]:
    """Return the most recent Result produced by :func:`process`."""
    return _pipeline().get_last_result()


def get_detectors():
    """Return underlying detectors for inspection in tests."""
    return _pipeline().get_detectors()


def create_logger_from_env() -> Optional["VisionLogger"]:
    """Create a VisionLogger instance using environment configuration."""
    from .viz_logger import create_logger_from_env as _create_logger_from_env

    return _create_logger_from_env()


# Backwards compatibility for older imports
select_detector = select_pipeline
process_frame = process
