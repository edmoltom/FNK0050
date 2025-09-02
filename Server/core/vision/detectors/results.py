from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from numpy.typing import NDArray


@dataclass
class DetectionResult:
    """Generic detection output returned by detectors.

    Attributes:
        ok: Whether a valid detection was found.
        bbox: Bounding box ``(x, y, w, h)`` in pixels.
        score: Optional score describing detection confidence.
        center: Optional center point ``(x, y)``.
        overlay: Optional visualization image.
        fill: Percent fill of contour (contour detectors).
        bbox_ratio: Aspect ratio of bounding box (contour detectors).
        used_rescue: Whether rescue thresholding was used.
        life_canny_pct: Life percentage from the dynamic adjuster.
        chosen_ck: Closing kernel size chosen.
        chosen_dk: Dilation kernel size chosen.
        t1: Low Canny threshold chosen.
        t2: High Canny threshold chosen.
        color_cover_pct: Percent of color mask coverage.
        color_used: Whether the color gate was applied.
    """

    ok: bool
    bbox: Optional[Tuple[int, int, int, int]] = None
    score: Optional[float] = None
    center: Optional[Tuple[int, int]] = None
    overlay: Optional[NDArray] = None

    # Contour-specific optional fields
    fill: Optional[float] = None
    bbox_ratio: Optional[float] = None
    used_rescue: Optional[bool] = None
    life_canny_pct: Optional[float] = None
    chosen_ck: Optional[int] = None
    chosen_dk: Optional[int] = None
    t1: Optional[float] = None
    t2: Optional[int] = None
    color_cover_pct: Optional[float] = None
    color_used: Optional[bool] = None
