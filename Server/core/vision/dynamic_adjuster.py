import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional

from .config_defaults import (
    CANNY_T1_INIT,
    CANNY_T2_RATIO,
    CANNY_LIFE_MIN,
    CANNY_LIFE_MAX,
    CANNY_RESCUE_LIFE_MIN,
    CANNY_KP,
    CANNY_MAX_ITER,
    ADAPTIVE_BLOCK_SIZE,
    ADAPTIVE_C,
)
from .vision_utils import pct_on

NDArray = np.ndarray


def _adaptive_thresh(gray: NDArray) -> NDArray:
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_BLOCK_SIZE,
        ADAPTIVE_C,
    )

@dataclass
class CannyConfig:
    t1_init: float = CANNY_T1_INIT
    t2_ratio: float = CANNY_T2_RATIO
    life_min: float = CANNY_LIFE_MIN
    life_max: float = CANNY_LIFE_MAX
    rescue_life_min: float = CANNY_RESCUE_LIFE_MIN
    kp: float = CANNY_KP
    max_iter: int = CANNY_MAX_ITER

class DynamicAdjuster:
    """Auto-Canny and rescue logic applied before detection."""
    def __init__(self, cfg: Optional[CannyConfig] = None) -> None:
        self.cfg = cfg if cfg is not None else CannyConfig()

    def update(self, **kwargs) -> None:
        """Update configuration values at runtime."""
        for k, v in kwargs.items():
            if hasattr(self.cfg, k):
                current = getattr(self.cfg, k)
                try:
                    setattr(self.cfg, k, type(current)(v))
                except Exception:
                    setattr(self.cfg, k, v)

    def apply(self, gray: NDArray) -> Tuple[NDArray, NDArray, float, int, float, bool]:
        """Return (edges, canny, t1, t2, life, used_rescue)."""
        cfg = self.cfg
        t1 = float(cfg.t1_init)
        life = 0.0
        for _ in range(1, cfg.max_iter + 1):
            t2 = int(np.clip(cfg.t2_ratio * t1, 0, 255))
            canny = cv2.Canny(gray, int(max(0, t1)), int(t2))
            life = pct_on(canny)
            if cfg.life_min <= life <= cfg.life_max:
                break
            if life < cfg.life_min:
                t1 = max(1.0, t1 - cfg.kp * (cfg.life_min - life))
            else:
                t1 = min(220.0, t1 + cfg.kp * (life - cfg.life_max))
        t2 = int(np.clip(cfg.t2_ratio * t1, 0, 255))
        used_rescue = False
        edges = canny.copy()
        if life < cfg.rescue_life_min:
            th = _adaptive_thresh(gray)
            edges = cv2.bitwise_or(canny, th)
            used_rescue = True
        return edges, canny, float(t1), int(t2), float(life), bool(used_rescue)

