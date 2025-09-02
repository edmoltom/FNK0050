"""Registry for vision detectors and associated profiles."""

from __future__ import annotations

from typing import Dict, Optional

from .detectors.contour_detector import ContourDetector, configs_from_profile
from .dynamic_adjuster import DynamicAdjuster
from .profile_manager import load_profile as pm_load_profile, get_config


class DetectorRegistry:
    """Manage creation and storage of vision detectors by key."""

    def __init__(self) -> None:
        self._detectors: Dict[str, ContourDetector] = {}
        self._adjusters: Dict[str, DynamicAdjuster] = {}

    def register(self, key: str, profile_path: str) -> ContourDetector:
        """Register a detector under ``key`` using the profile at ``profile_path``."""
        pm_load_profile(key, profile_path)
        cfg, canny = configs_from_profile(get_config(key))
        adj = DynamicAdjuster(canny)
        det = ContourDetector(adjuster=adj, **cfg)
        self._detectors[key] = det
        self._adjusters[key] = adj
        return det

    def get_detector(self, key: str) -> Optional[ContourDetector]:
        """Return detector registered under ``key`` if present."""
        return self._detectors.get(key)

    def get_adjuster(self, key: str) -> Optional[DynamicAdjuster]:
        """Return adjuster associated with ``key`` if present."""
        return self._adjusters.get(key)

    def all_detectors(self) -> Dict[str, ContourDetector]:
        """Return a copy of all registered detectors."""
        return dict(self._detectors)
