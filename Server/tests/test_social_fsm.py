from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
import types
from unittest.mock import Mock

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

cv2_stub = types.ModuleType("cv2")
cv2_stub.setNumThreads = lambda *args, **kwargs: None  # pragma: no cover - test stub
sys.modules.setdefault("cv2", cv2_stub)

core_stub = types.ModuleType("core")
core_stub.__path__ = []  # pragma: no cover - namespace stub
sys.modules.setdefault("core", core_stub)

vision_package = types.ModuleType("core.vision")
vision_package.__path__ = []  # pragma: no cover - namespace stub
sys.modules.setdefault("core.vision", vision_package)

voice_package = types.ModuleType("core.voice")
voice_package.__path__ = []  # pragma: no cover - namespace stub
sys.modules.setdefault("core.voice", voice_package)

voice_sfx_module = types.ModuleType("core.voice.sfx")
voice_sfx_module.play_sound = lambda *args, **kwargs: None
sys.modules.setdefault("core.voice.sfx", voice_sfx_module)

movement_control_module = types.ModuleType("core.MovementControl")


class _StubMovementControl:  # pragma: no cover - test stub
    head_limits = (-10.0, 10.0, 0.0)

    def __init__(self, *args, **kwargs) -> None:
        pass

    def start_loop(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def relax(self) -> None:
        pass

    def turn_left(self, *args, **kwargs) -> None:
        pass

    def turn_right(self, *args, **kwargs) -> None:
        pass

    def head_deg(self, *args, **kwargs) -> None:
        pass


movement_control_module.MovementControl = _StubMovementControl
sys.modules.setdefault("core.MovementControl", movement_control_module)

vision_manager_module = types.ModuleType("core.VisionManager")


class _StubVisionManager:  # pragma: no cover - test stub
    def __init__(self, *args, **kwargs) -> None:
        pass

    def start(self) -> None:
        pass

    def start_stream(self, *args, **kwargs) -> None:
        pass

    def stop(self) -> None:
        pass

    def select_pipeline(self, *args, **kwargs) -> None:
        pass

    def get_last_processed_encoded(self):
        return None

    def snapshot(self):
        return None


vision_manager_module.VisionManager = _StubVisionManager
sys.modules.setdefault("core.VisionManager", vision_manager_module)

profile_manager_module = types.ModuleType("core.vision.profile_manager")
profile_manager_module._profiles = {}
sys.modules.setdefault("core.vision.profile_manager", profile_manager_module)

vision_api_module = types.ModuleType("core.vision.api")
vision_api_module.register_pipeline = lambda *args, **kwargs: None
sys.modules.setdefault("core.vision.api", vision_api_module)

face_pipeline_module = types.ModuleType("core.vision.pipeline.face_pipeline")


class _StubFacePipeline:  # pragma: no cover - test stub
    def __init__(self, *args, **kwargs) -> None:
        pass


face_pipeline_module.FacePipeline = _StubFacePipeline
sys.modules.setdefault("core.vision.pipeline.face_pipeline", face_pipeline_module)

control_pid_module = types.ModuleType("control.pid")


class _StubPID:  # pragma: no cover - test stub
    def __init__(self, *args, **kwargs) -> None:
        pass

    def PID_compute(self, *args, **kwargs) -> float:
        return 0.0


control_pid_module.Incremental_PID = _StubPID
sys.modules.setdefault("control.pid", control_pid_module)

from app.controllers import social_fsm


class _DummyTracker:
    def __init__(self) -> None:
        self.deadband_x = 0.0
        self.lock_frames_needed = 0
        self.miss_release = 0
        self.recenter_after = 0

    def update(self, *_: object, **__: object) -> None:  # pragma: no cover - helper
        return


def _make_fsm(monkeypatch: pytest.MonkeyPatch, callbacks: dict | None = None) -> social_fsm.SocialFSM:
    tracker = _DummyTracker()
    monkeypatch.setattr(social_fsm, "FaceTracker", lambda *args, **kwargs: tracker)
    movement = SimpleNamespace(mc=object(), relax=Mock(), stop=Mock())
    vision = SimpleNamespace(vm=object())
    fsm = social_fsm.SocialFSM(vision, movement, callbacks=callbacks)
    monkeypatch.setattr(fsm, "_on_interact", Mock())
    return fsm


def test_interact_callback_invoked_once(monkeypatch: pytest.MonkeyPatch) -> None:
    on_interact = Mock()
    on_exit = Mock()
    fsm = _make_fsm(
        monkeypatch,
        callbacks={
            "on_interact": on_interact,
            "on_exit_interact": on_exit,
            "disable_default_interact": True,
        },
    )

    fsm._set_state("INTERACT")
    fsm._set_state("INTERACT")
    fsm._set_state("IDLE")

    assert on_interact.call_count == 1
    assert on_exit.call_count == 1
    assert fsm._on_interact.call_count == 0


def test_interact_callback_exception_logged(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    error = RuntimeError("boom")

    def failing_callback(_: social_fsm.SocialFSM) -> None:
        raise error

    fsm = _make_fsm(
        monkeypatch,
        callbacks={
            "on_interact": failing_callback,
            "disable_default_interact": True,
        },
    )

    with caplog.at_level(logging.ERROR, logger="social_fsm"):
        fsm._set_state("INTERACT")

    assert fsm.state == "INTERACT"
    assert fsm._on_interact.call_count == 0
    assert any(record.exc_info for record in caplog.records)
