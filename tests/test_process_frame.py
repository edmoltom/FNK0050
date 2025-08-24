import sys
import types

numpy_stub = types.ModuleType("numpy")
class _NDArray:  # minimal placeholder
    pass
numpy_stub.ndarray = _NDArray
sys.modules.setdefault("numpy", numpy_stub)
sys.modules.setdefault("cv2", types.ModuleType("cv2"))

from core.vision.system import VisionSystem


def test_process_frame_detector_selection(monkeypatch):
    vs = VisionSystem()

    # Avoid initializing real detectors
    monkeypatch.setattr(vs, "_ensure_detectors", lambda: None)
    calls = []

    def fake_step(det, which, frame, return_overlay):
        calls.append(which)
        px = int(frame[0][0][0])
        if which == "big":
            if px == 1:
                return True, {"ok": True, "score": 0.9}
            return False, {"ok": False, "score": 0.4}
        else:  # small detector
            if px == 2:
                return True, {"ok": True, "score": 0.8}
            return False, {"ok": False, "score": 0.5}

    monkeypatch.setattr(vs, "_step", fake_step)

    # Big detector succeeds
    frame_big = [[[1]]]
    out = vs.process_frame(frame_big)
    assert out["score"] == 0.9
    assert calls == ["big"]

    # Small detector used when big fails
    calls.clear()
    frame_small = [[[2]]]
    out = vs.process_frame(frame_small)
    assert out["score"] == 0.8
    assert calls == ["big", "small"]

    # Choose detector with higher score when both fail
    calls.clear()
    frame_none = [[[0]]]
    out = vs.process_frame(frame_none)
    assert out["score"] == 0.5
    assert calls == ["big", "small"]
