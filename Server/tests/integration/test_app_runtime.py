from __future__ import annotations
from __future__ import annotations

import sys
import threading
import types

cv2_stub = types.ModuleType("cv2")
numpy_stub = types.ModuleType("numpy")


def _no_op(*_args, **_kwargs) -> None:
    return None


cv2_stub.setNumThreads = _no_op  # type: ignore[attr-defined]
sys.modules.setdefault("cv2", cv2_stub)
sys.modules.setdefault("numpy", numpy_stub)

numpy_stub.ndarray = type("ndarray", (), {})  # type: ignore[attr-defined]

vision_service_stub = types.ModuleType("app.services.vision_service")


class _StubVisionService:  # pragma: no cover - minimal shim
    pass


vision_service_stub.VisionService = _StubVisionService
sys.modules.setdefault("app.services.vision_service", vision_service_stub)

from Server.app.builder import AppServices
from Server.app.runtime import AppRuntime


class _Recorder:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.lock = threading.Lock()

    def add(self, name: str) -> None:
        with self.lock:
            self.events.append(name)

    def index(self, name: str) -> int:
        with self.lock:
            return self.events.index(name)

    def count(self, name: str) -> int:
        with self.lock:
            return self.events.count(name)


class MockMovement:
    def __init__(self, recorder: _Recorder) -> None:
        self.recorder = recorder

    def start(self) -> None:
        self.recorder.add("movement.start")

    def relax(self) -> None:
        self.recorder.add("movement.relax")

    def stop(self) -> None:
        self.recorder.add("movement.stop")


class MockVision:
    def __init__(self, recorder: _Recorder) -> None:
        self.recorder = recorder

    def set_frame_callback(self, _cb) -> None:
        self.recorder.add("vision.set_frame_callback")

    def start(self, *, interval_sec: float, frame_handler=None) -> None:
        self.recorder.add("vision.start")

    def stop(self) -> None:
        self.recorder.add("vision.stop")


class MockProcess:
    def __init__(self, recorder: _Recorder) -> None:
        self.recorder = recorder

    def terminate(self) -> None:
        self.recorder.add("llm.terminate")


class MockConversation:
    def __init__(self, recorder: _Recorder) -> None:
        self.recorder = recorder
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.process = MockProcess(recorder)

    def start(self) -> None:
        self.recorder.add("conversation.start")
        self.started.set()

    def stop(self, **kwargs: object) -> None:
        self.recorder.add("conversation.stop")
        if kwargs.get("terminate_process"):
            self.process.terminate()
        self.stopped.set()

    def join(self, timeout: float | None = None) -> bool:
        self.recorder.add("conversation.join")
        return True


def _make_runtime(enable_ws: bool = False) -> tuple[AppRuntime, _Recorder, MockConversation]:
    recorder = _Recorder()
    services = AppServices()
    services.enable_vision = True
    services.enable_movement = True
    services.enable_ws = enable_ws
    services.enable_conversation = True
    services.interval_sec = 0.1
    services.vision = MockVision(recorder)
    services.movement = MockMovement(recorder)
    conversation = MockConversation(recorder)
    services.conversation = conversation
    runtime = AppRuntime(services)
    return runtime, recorder, conversation


def _run_runtime(runtime: AppRuntime) -> threading.Thread:
    thread = threading.Thread(target=runtime.start, daemon=True)
    thread.start()
    return thread


def test_runtime_starts_conversation_after_vision_and_movement() -> None:
    runtime, recorder, conversation = _make_runtime()
    thread = _run_runtime(runtime)

    assert conversation.started.wait(timeout=1.0)

    runtime.stop()
    thread.join(timeout=1.0)

    assert recorder.index("movement.start") < recorder.index("conversation.start")
    assert recorder.index("vision.start") < recorder.index("conversation.start")


def test_runtime_stop_is_idempotent_and_orders_shutdown() -> None:
    runtime, recorder, conversation = _make_runtime()
    thread = _run_runtime(runtime)

    assert conversation.started.wait(timeout=1.0)

    runtime.stop()
    runtime.stop()
    thread.join(timeout=1.0)

    stop_index = recorder.index("conversation.stop")
    join_index = recorder.index("conversation.join")
    terminate_index = recorder.index("llm.terminate")

    assert stop_index < terminate_index
    assert terminate_index <= join_index
    assert recorder.count("conversation.stop") == 1
    assert recorder.count("llm.terminate") == 1
    assert recorder.count("vision.stop") == 1
    assert recorder.count("movement.stop") == 1
