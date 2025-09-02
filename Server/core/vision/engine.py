"""Compatibility layer exposing pipeline classes under legacy names."""

from .pipeline.contour_pipeline import ContourPipeline as VisionEngine
from .pipeline.base_pipeline import Result as EngineResult

__all__ = ["VisionEngine", "EngineResult"]
