"""Entry point for running the Lumo runtime in sandbox mode."""
from __future__ import annotations

import logging
import sys
import threading
import time
import types
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "Server"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

for relative in ("app", "core", "lib", "network"):
    folder = SERVER_ROOT / relative
    if folder.exists():
        folder_str = str(folder)
        if folder_str not in sys.path:
            sys.path.insert(0, folder_str)


def _install_sandbox_stubs() -> None:
    """Inject lightweight stand-ins for heavy hardware modules."""

    core_module = sys.modules.get("core")
    if core_module is None:
        core_module = types.ModuleType("core")
        sys.modules["core"] = core_module

    if "cv2" not in sys.modules:
        cv2_module = types.ModuleType("cv2")

        def setNumThreads(threads: int) -> None:  # pragma: no cover - stub
            return None

        cv2_module.setNumThreads = setNumThreads
        sys.modules["cv2"] = cv2_module

    # Vision stubs ---------------------------------------------------------
    if "core.VisionManager" not in sys.modules:
        vm_module = types.ModuleType("core.VisionManager")

        class _VisionManager:
            def __init__(self, *args, **kwargs) -> None:
                self._running = False

            def start(self) -> None:  # pragma: no cover - stub
                self._running = True

            def start_stream(
                self, interval_sec: float = 1.0, on_frame: Optional[callable] = None
            ) -> None:  # pragma: no cover - stub
                self._running = True

            def stop(self) -> None:  # pragma: no cover - stub
                self._running = False

            def get_last_processed_encoded(self):  # pragma: no cover - stub
                return None

            def snapshot(self):  # pragma: no cover - stub
                return None

        vm_module.VisionManager = _VisionManager
        sys.modules["core.VisionManager"] = vm_module
        core_module.VisionManager = _VisionManager  # type: ignore[attr-defined]

    if "core.vision.profile_manager" not in sys.modules:
        pm_module = types.ModuleType("core.vision.profile_manager")
        pm_module._profiles = {}
        sys.modules["core.vision.profile_manager"] = pm_module
    else:
        pm_module = sys.modules["core.vision.profile_manager"]

    if "core.vision.api" not in sys.modules:
        api_module = types.ModuleType("core.vision.api")

        def register_pipeline(name: str, pipeline: object) -> None:  # pragma: no cover - stub
            return None

        api_module.register_pipeline = register_pipeline
        sys.modules["core.vision.api"] = api_module
    else:
        api_module = sys.modules["core.vision.api"]

    if "core.vision.pipeline.face_pipeline" not in sys.modules:
        pipeline_module = types.ModuleType("core.vision.pipeline.face_pipeline")

        class FacePipeline:  # pragma: no cover - stub
            def __init__(self, cfg: Optional[dict] = None) -> None:
                self.cfg = dict(cfg or {})

        pipeline_module.FacePipeline = FacePipeline
        sys.modules["core.vision.pipeline.face_pipeline"] = pipeline_module

    if "core.vision" not in sys.modules:
        vision_pkg = types.ModuleType("core.vision")
        sys.modules["core.vision"] = vision_pkg
    else:
        vision_pkg = sys.modules["core.vision"]

    vision_pkg.profile_manager = pm_module  # type: ignore[attr-defined]
    vision_pkg.api = api_module  # type: ignore[attr-defined]

    pipeline_pkg = sys.modules.get("core.vision.pipeline")
    if pipeline_pkg is None:
        pipeline_pkg = types.ModuleType("core.vision.pipeline")
        sys.modules["core.vision.pipeline"] = pipeline_pkg
    pipeline_pkg.face_pipeline = sys.modules["core.vision.pipeline.face_pipeline"]
    vision_pkg.pipeline = pipeline_pkg  # type: ignore[attr-defined]
    core_module.vision = vision_pkg  # type: ignore[attr-defined]

    # Movement stubs -------------------------------------------------------
    if "core.MovementControl" not in sys.modules:
        movement_module = types.ModuleType("core.MovementControl")

        class MovementControl:  # pragma: no cover - stub
            def start_loop(self) -> None:
                return None

            def stop(self) -> None:
                return None

            def relax(self) -> None:
                return None

            def turn_left(self, duration_ms: int, speed: float) -> None:
                return None

            def turn_right(self, duration_ms: int, speed: float) -> None:
                return None

        movement_module.MovementControl = MovementControl
        sys.modules["core.MovementControl"] = movement_module

    # Audio stubs ----------------------------------------------------------
    if "core.voice.sfx" not in sys.modules:
        voice_pkg = sys.modules.get("core.voice")
        if voice_pkg is None:
            voice_pkg = types.ModuleType("core.voice")
            sys.modules["core.voice"] = voice_pkg
        sfx_module = types.ModuleType("core.voice.sfx")

        def play_sound(path: object) -> None:  # pragma: no cover - stub
            logging.getLogger("mock.voice").debug("[MOCK] play_sound(%s)", path)

        sfx_module.play_sound = play_sound
        sys.modules["core.voice.sfx"] = sfx_module
        voice_pkg.sfx = sfx_module  # type: ignore[attr-defined]
        core_module.voice = voice_pkg  # type: ignore[attr-defined]


_install_sandbox_stubs()

from app.application import AppRuntime  # type: ignore  # noqa: E402
from app.builder import AppServices  # type: ignore  # noqa: E402
from app.logging_config import setup_logging  # type: ignore  # noqa: E402

from sandbox.mocks import (  # noqa: E402
    MockLedController,
    MockMovementService,
    MockVisionService,
    MockVoiceService,
)


class MockTracker:
    """Minimal tracker compatible with :class:`BehaviorManager` expectations."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mock.tracker")
        self.enabled = True

    def set_enabled(
        self,
        enabled: bool | None = None,
        *,
        enable_x: bool | None = None,
        enable_y: bool | None = None,
    ) -> None:
        if enabled is None and enable_x is None and enable_y is None:
            return
        if enabled is None:
            enabled = bool(enable_x if enable_x is not None else True)
        self.enabled = bool(enabled)
        self.logger.debug("[MOCK] Tracker enabled=%s", self.enabled)


class MockSocialFSM:
    """Lightweight stand-in for the social finite state machine."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mock.social_fsm")
        self.state = "IDLE"
        self.paused = False
        self.social_muted = False
        self.tracker = MockTracker()

    def pause(self) -> None:
        self.paused = True
        self.logger.info("[FSM] paused")

    def resume(self) -> None:
        self.paused = False
        self.logger.info("[FSM] resumed")

    def mute_social(self, enabled: bool) -> None:
        self.social_muted = enabled
        if enabled:
            self.logger.info("[FSM] social reactions muted")
        else:
            self.logger.info("[FSM] social reactions unmuted")

    def on_frame(self, detection: Optional[dict], dt: float) -> None:
        if self.paused:
            return
        target_visible = bool(detection and detection.get("face_detected"))
        if target_visible:
            self._set_state("INTERACT")
        else:
            self._set_state("SEARCH")

    def _set_state(self, new_state: str) -> None:
        if new_state == self.state:
            return
        self.logger.info("[FSM] %s -> %s", self.state, new_state)
        self.state = new_state


class SandboxConversationService:
    """Small conversation loop that echoes user input through the voice mock."""

    def __init__(self, voice: MockVoiceService, led: MockLedController) -> None:
        self.logger = logging.getLogger("mock.conversation")
        self.voice = voice
        self._led_controller = led
        self.state = "IDLE"
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.voice.start()
        thread = threading.Thread(target=self._loop, name="mock-conversation", daemon=True)
        self._thread = thread
        thread.start()
        self.logger.info("Mock conversation service started")

    def _loop(self) -> None:
        while self._running:
            utterance = self.voice.listen()
            if utterance is None:
                continue
            if not utterance:
                continue
            self.state = "THINK"
            self._led_controller.set_color("thinking")
            self.logger.debug("Processing utterance: %s", utterance)
            time.sleep(0.2)
            response = f"I heard: {utterance}"
            self.state = "SPEAK"
            self._led_controller.set_color("speaking")
            self.voice.speak(response)
            self.state = "IDLE"
            self._led_controller.set_color("idle")

    def stop(self, terminate_process: bool = False, shutdown_resources: bool = False) -> None:
        if not self._running:
            return
        self.logger.info("Mock conversation service stopping")
        self._running = False
        self.voice.stop()

    def join(self, timeout: Optional[float] = None) -> None:
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            self._thread = None

    # Compatibility hook ----------------------------------------------------
    @property
    def stop_event(self):  # pragma: no cover - compatibility stub
        return None


def build_services() -> tuple[AppServices, MockVisionService, MockMovementService, MockVoiceService, MockLedController]:
    """Create mock-backed :class:`AppServices` for the sandbox runtime."""

    config = {"mode": "sandbox"}

    services = AppServices(cfg=config)
    services.enable_vision = True
    services.enable_movement = True
    services.enable_ws = False
    services.enable_conversation = True
    services.interval_sec = 1.0
    services.conversation_cfg = {"enable": True}

    vision = MockVisionService()
    movement = MockMovementService()
    voice = MockVoiceService()
    led = MockLedController()
    conversation = SandboxConversationService(voice, led)
    social_fsm = MockSocialFSM()

    services.vision = vision
    services.movement = movement
    services.conversation = conversation
    services.fsm = social_fsm

    return services, vision, movement, voice, led


def main() -> None:
    setup_logging()

    services, vision, movement, voice, led = build_services()
    runtime = AppRuntime(services)

    runtime.vision = vision
    runtime.movement = movement
    runtime.voice = voice
    runtime.led = led
    runtime.conversation = services.conversation
    runtime.social_fsm = services.fsm

    try:
        runtime.start()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
