"""Backward compatibility wrappers for the vision engine."""

from typing import Any, Dict, Optional, Tuple
import numpy as np

from .engine import VisionEngine, DynamicParams

_engine = VisionEngine()


def process_frame(frame: np.ndarray, return_overlay: bool = True, config: Optional[Dict[str, Any]] = None):
    """Compatibility layer calling :class:`VisionEngine`."""
    if config is not None:
        _engine.config = dict(config)
        _engine.config["return_overlay"] = return_overlay
        _engine.reload_config()
    else:
        _engine.config["return_overlay"] = return_overlay
    return _engine.process(frame)


def update_dynamic(which: str, params: Dict[str, Any]) -> None:
    _engine.update_dynamic(DynamicParams(which, params))


def reload_config() -> None:
    _engine.reload_config()


def get_detectors() -> Tuple[Any, Any]:
    return _engine.get_detectors()

