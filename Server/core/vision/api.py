"""Lightweight façade for the :mod:`core.vision` engine.

This module provides a minimal interface around :class:`~core.vision.engine.VisionEngine`
so that the rest of the application does not need to manage engine instances
explicitly.  It replaces the previous global orchestration logic with three
simple helpers:

``create_engine_from_config``
    Instantiate a :class:`VisionEngine` from a YAML configuration file and
    store it for subsequent calls.

``set_dynamic``
    Forward dynamic parameter updates to the internal engine.

``get_last_result``
    Retrieve the most recent :class:`~core.vision.engine.EngineResult` produced
    by the engine.
"""
from __future__ import annotations

from typing import Optional

from dataclasses import asdict

from .engine import VisionEngine, DynamicParams, EngineResult
from .config import load_config
from .logger import VizLogger

_engine: Optional[VisionEngine] = None


def _require_engine() -> VisionEngine:
    """Return the currently active engine or raise if none was created."""
    if _engine is None:  # pragma: no cover - defensive branch
        raise RuntimeError("Vision engine not initialised; call create_engine_from_config().")
    return _engine


def create_engine_from_config(path: Optional[str] = None) -> VisionEngine:
    """Create and store a :class:`VisionEngine` from the given YAML file.

    Parameters
    ----------
    path:
        Optional location of the YAML configuration file. If ``None`` or a
        relative path is provided, the default configuration bundled with the
        package is used.
    """
    global _engine
    cfg = load_config(path)
    logger = VizLogger(**asdict(cfg.logging))
    _engine = VisionEngine(cfg, logger=logger)
    return _engine


def set_dynamic(params: DynamicParams) -> None:
    """Update the engine's dynamic parameters."""
    engine = _require_engine()
    engine.update_dynamic(params)


def get_last_result() -> EngineResult:
    """Return the last result computed by the engine.

    Returns:
        EngineResult: Last result or an empty negative result if none.
    """
    engine = _require_engine()
    result = engine.get_last_result()
    return result or EngineResult(ok=False)
