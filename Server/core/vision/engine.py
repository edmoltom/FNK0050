import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

import numpy as np

from .detectors.contours import ContourDetector
from .detectors.base import DetectionResult, DetectionContext
from .dynamics import DynamicAdjuster
from .imgproc import mask_to_roi
from .config import VisionConfig, EngineConfig, DetectorConfig

if TYPE_CHECKING:  # pragma: no cover
    from .logger import VizLogger


@dataclass
class EngineResult:
    """Aggregate result produced by :class:`VisionEngine`."""

    ok: bool
    bbox: Optional[Tuple[int, int, int, int]] = None
    score: Optional[float] = None
    fill: Optional[float] = None
    bbox_ratio: Optional[float] = None
    life: Optional[float] = None
    center: Optional[Tuple[float, float]] = None
    space: Optional[Tuple[int, int]] = None
    overlay: Optional[np.ndarray] = None


@dataclass
class DynamicParams:
    """Runtime update for dynamic adjusters."""

    which: str
    params: Dict[str, Any] = field(default_factory=dict)


class VisionEngine:
    """Thread safe vision engine wrapping contour detectors."""

    class _StableState:
        def __init__(self) -> None:
            self.last_bbox: Optional[Tuple[int, int, int, int]] = None
            self.score_ema: Optional[float] = None
            self.miss_count: int = 0

    def __init__(
        self,
        config: Optional[VisionConfig] = None,
        adjuster_cls=DynamicAdjuster,
        logger: Optional["VizLogger"] = None,
    ) -> None:
        self._lock = threading.Lock()
        self.config: VisionConfig = config if config is not None else VisionConfig()
        self.dynamic: Dict[str, Dict[str, Any]] = {"big": {}, "small": {}}
        self._det_big: Optional[ContourDetector] = None
        self._det_small: Optional[ContourDetector] = None
        self._adj_big: Optional[DynamicAdjuster] = None
        self._adj_small: Optional[DynamicAdjuster] = None
        self._st_big = self._StableState()
        self._st_small = self._StableState()
        self._last_result: Optional[EngineResult] = None
        # Allow dependency injection of the dynamic adjuster
        self._adj_cls = adjuster_cls
        # Optional logger that receives every processed frame
        self.logger: Optional["VizLogger"] = logger

    # ---- internal helpers ----
    def _knobs(self, config: Optional[EngineConfig]) -> Dict[str, Any]:
        cfg = config or EngineConfig()
        return dict(
            stable=bool(cfg.stable),
            on_th=float(cfg.on_th),
            off_th=float(cfg.off_th),
            stick_k=int(cfg.stick_k),
            miss_m=int(cfg.miss_m),
            roi_fact=float(cfg.roi_factor),
            ema_a=float(cfg.ema),
        )

    def _ensure_detectors(self) -> None:
        if self._det_big is None:
            cfg: DetectorConfig = self.config.detectors.big
            self._adj_big = self._adj_cls(cfg.canny)
            self._det_big = ContourDetector(adjuster=self._adj_big)
            self._det_big.configure({
                "proc": cfg.proc,
                "morph": cfg.morph,
                "geo": cfg.geo,
                "w": cfg.w,
                "premorph": cfg.premorph,
                "color": cfg.color,
            })
        if self._det_small is None:
            cfg: DetectorConfig = self.config.detectors.small
            self._adj_small = self._adj_cls(cfg.canny)
            self._det_small = ContourDetector(adjuster=self._adj_small)
            self._det_small.configure({
                "proc": cfg.proc,
                "morph": cfg.morph,
                "geo": cfg.geo,
                "w": cfg.w,
                "premorph": cfg.premorph,
                "color": cfg.color,
            })

    def _ref_size(self, det: ContourDetector) -> Tuple[int, int]:
        return det.proc.proc_w, det.proc.proc_h

    def _export(self, res: DetectionResult, det: ContourDetector, score_override: Optional[float] = None) -> EngineResult:
        ref = self._ref_size(det)
        if not res.ok:
            return EngineResult(ok=False, life=getattr(res, "life_canny_pct", 0.0), space=ref)
        return EngineResult(
            ok=True,
            bbox=res.bbox,
            score=float(score_override if score_override is not None else res.score),
            fill=res.fill,
            bbox_ratio=res.bbox_ratio,
            life=res.life_canny_pct,
            center=res.center,
            space=ref,
            overlay=res.overlay if res.overlay is not None else None,
        )

    def _step(
        self,
        det: ContourDetector,
        st: "VisionEngine._StableState",
        frame: np.ndarray,
        knobs: Dict[str, Any],
        return_overlay: bool,
    ) -> Tuple[bool, EngineResult]:
        ref_w, ref_h = self._ref_size(det)
        if not knobs["stable"] or st.last_bbox is None:
            res = det.infer(frame, DetectionContext(return_overlay=return_overlay))
            if not res.ok:
                st.miss_count = min(knobs["miss_m"], st.miss_count + 1)
                return False, self._export(res, det)
            st.score_ema = (
                res.score if st.score_ema is None else (knobs["ema_a"] * st.score_ema + (1.0 - knobs["ema_a"]) * res.score)
            )
            if st.score_ema >= knobs["on_th"]:
                st.last_bbox = res.bbox
                st.miss_count = 0
                return True, self._export(res, det, st.score_ema)
            out = self._export(res, det, st.score_ema)
            out.ok = False
            return False, out

        roi_frame = mask_to_roi(frame, st.last_bbox, knobs["roi_fact"], self._ref_size(det))
        res_roi = det.infer(roi_frame, DetectionContext(return_overlay=return_overlay))
        if res_roi.ok:
            st.score_ema = (
                res_roi.score if st.score_ema is None else (knobs["ema_a"] * st.score_ema + (1.0 - knobs["ema_a"]) * res_roi.score)
            )
            if st.score_ema >= knobs["off_th"]:
                st.last_bbox = res_roi.bbox
                st.miss_count = 0
                return True, self._export(res_roi, det, st.score_ema)
            st.miss_count += 1
        else:
            st.miss_count += 1

        if st.miss_count >= knobs["miss_m"]:
            st.last_bbox = None
            st.score_ema = None
            res_global = det.infer(frame, DetectionContext(return_overlay=return_overlay))
            ok = bool(res_global.ok)
            if ok:
                st.last_bbox = res_global.bbox
                st.score_ema = res_global.score
                st.miss_count = 0
            return ok, self._export(res_global, det)
        if st.last_bbox is not None:
            return True, EngineResult(ok=True, bbox=st.last_bbox, score=float(st.score_ema or 0.0), space=(ref_w, ref_h))
        return False, EngineResult(ok=False, space=(ref_w, ref_h))

    # ---- public API ----
    def process(self, frame: np.ndarray) -> EngineResult:
        """Run the detection pipeline on a frame.

        Args:
            frame: BGR image to analyse.

        Returns:
            EngineResult with detection information.
        """
        with self._lock:
            knobs = self._knobs(self.config.engine)
            self._ensure_detectors()
            return_overlay = bool(self.config.engine.return_overlay)
            ok_big, out_big = self._step(self._det_big, self._st_big, frame, knobs, return_overlay)
            if ok_big:
                res = out_big
            else:
                ok_small, out_small = self._step(self._det_small, self._st_small, frame, knobs, return_overlay)
                if ok_small:
                    res = out_small
                else:
                    sb = float(out_big.score or 0.0)
                    ss = float(out_small.score or 0.0)
                    res = out_big if sb >= ss else out_small
            self._last_result = res

        if self.logger is not None:
            try:
                self.logger.log(frame, res)
            except Exception:
                pass
        return res

    def update_dynamic(self, params: DynamicParams) -> None:
        """Update dynamic parameters at runtime.

        Args:
            params: Parameter update specification.
        """
        with self._lock:
            which = params.which
            self.dynamic[which] = dict(params.params)
            if which == "big" and self._adj_big is not None:
                self._adj_big.update(**params.params)
            elif which == "small" and self._adj_small is not None:
                self._adj_small.update(**params.params)

    def reload_config(self) -> None:
        """Reload detector configuration from current settings."""
        with self._lock:
            self._det_big = None
            self._det_small = None
            self._adj_big = None
            self._adj_small = None
            self._st_big = self._StableState()
            self._st_small = self._StableState()
            knobs = self._knobs(self.config.engine)
            self._ensure_detectors()

    def get_last_result(self) -> Optional[EngineResult]:
        """Return the most recent result produced by :meth:`process`."""
        with self._lock:
            return self._last_result

    # utility for logger/tests
    def get_detectors(self) -> Tuple[Optional[ContourDetector], Optional[ContourDetector]]:
        """Return internal detectors for inspection or testing."""
        with self._lock:
            return self._det_big, self._det_small

    def set_logger(self, logger: Optional["VizLogger"]) -> None:
        """Attach or replace the logger used for dumping results."""
        self.logger = logger
