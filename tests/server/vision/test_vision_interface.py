import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Server"))
sys.path.insert(0, str(ROOT))

# Provide a minimal cv2 stub for tests if OpenCV is unavailable
cv2_stub = types.SimpleNamespace(
    COLOR_RGB2BGR=0,
    cvtColor=lambda frame, code: frame,
    imencode=lambda ext, frame: (True, b"data"),
)
numpy_stub = types.SimpleNamespace(ndarray=object)
sys.modules.setdefault("cv2", cv2_stub)
sys.modules.setdefault("numpy", numpy_stub)

from Server.core.VisionInterface import VisionInterface
from Server.core.vision.engine import EngineResult


def _dummy_result():
    return EngineResult({"ok": True, "bbox": (1, 1, 2, 2), "space": (10, 10)}, time.time())


def test_snapshot_runs_pipeline_once_and_logs():
    frame = object()
    camera = MagicMock()
    camera.capture_rgb.return_value = frame
    logger = MagicMock()
    result = _dummy_result()

    with patch("Server.core.VisionInterface.api.process_frame") as process, \
         patch("Server.core.VisionInterface.api.get_last_result", return_value=result) as get_last, \
         patch("Server.core.VisionInterface.draw_result", side_effect=lambda f, r: f) as draw:
        vi = VisionInterface(camera=camera, logger=logger)
        encoded = vi.snapshot()

        assert encoded is not None
        process.assert_called_once()
        args, kwargs = process.call_args
        assert kwargs["return_overlay"] is True
        assert kwargs["config"] == vi._config
        assert get_last.call_count == 2
        logger.log.assert_called_once()
        draw.assert_called_once()


def test_start_stream_runs_pipeline_once_and_logs():
    frame = object()
    camera = MagicMock()
    camera.capture_rgb.return_value = frame
    logger = MagicMock()
    result = _dummy_result()

    with patch("Server.core.VisionInterface.api.process_frame") as process, \
         patch("Server.core.VisionInterface.api.get_last_result", return_value=result) as get_last, \
         patch("Server.core.VisionInterface.draw_result", side_effect=lambda f, r: f) as draw:
        vi = VisionInterface(camera=camera, logger=logger)
        vi.start_stream(interval_sec=10)

        deadline = time.time() + 2
        while vi.get_last_processed_encoded() is None and time.time() < deadline:
            time.sleep(0.01)
        vi.stop()

        assert vi.get_last_processed_encoded() is not None
        process.assert_called_once()
        args, kwargs = process.call_args
        assert kwargs["return_overlay"] is True
        assert kwargs["config"] == vi._config
        assert get_last.call_count == 2
        logger.log.assert_called_once()
        draw.assert_called_once()

def main():
    import pytest
    raise SystemExit(pytest.main([__file__]))

if __name__ == "__main__":
    main()


