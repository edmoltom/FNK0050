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

import yaml

from .engine import VisionEngine, DynamicParams, EngineResult

_engine: Optional[VisionEngine] = None


def _require_engine() -> VisionEngine:
    """Return the currently active engine or raise if none was created."""
    if _engine is None:  # pragma: no cover - defensive branch
        raise RuntimeError("Vision engine not initialised; call create_engine_from_config().")
    return _engine


def create_engine_from_config(path: str = "configs/vision.yaml") -> VisionEngine:
    """Create and store a :class:`VisionEngine` from the given YAML file.

    Parameters
    ----------
    path:
        Location of the YAML configuration file. The default mirrors the
        previous behaviour of looking for ``configs/vision.yaml`` relative to
        the working directory.
    """
    global _engine
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    _engine = VisionEngine(config)
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
