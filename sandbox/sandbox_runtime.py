"""SANDBOX RUNTIME
---------------
This environment is purely simulated.
It always uses mock sensors (IMU, Odometry) for proprioception.
Never intended for use with physical hardware.

Entry point for running the Lumo runtime in sandbox mode."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import logging
import sys
import threading
import time
import types
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "Server"

logger = logging.getLogger(__name__)

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

from interface.sensor_controller import SensorController
from interface.sensor_gateway import SensorGateway
from mind.proprioception.body_model import BodyModel


def _install_sandbox_stubs() -> None:
    """Inject lightweight stand-ins for heavy hardware modules."""

    core_module = sys.modules.get("core")
    if core_module is None:
        try:  # pragma: no cover - import side effects depend on environment
            import core as core_module  # type: ignore
        except Exception:
            core_module = types.ModuleType("core")
            sys.modules["core"] = core_module
        else:
            sys.modules.setdefault("core", core_module)

    interface_module = sys.modules.get("interface")
    if interface_module is None:
        interface_module = types.ModuleType("interface")
        sys.modules["interface"] = interface_module
    else:
        sys.modules.setdefault("interface", interface_module)

    core_path = SERVER_ROOT / "core"
    interface_path = SERVER_ROOT / "interface"
    llm_path = core_path / "llm"
    if core_path.exists():
        search_locations = list(getattr(core_module, "__path__", []))
        core_path_str = str(core_path)
        if core_path_str not in search_locations:
            search_locations.append(core_path_str)
        if search_locations:
            core_module.__path__ = search_locations  # type: ignore[attr-defined]
        if not getattr(core_module, "__package__", None):
            core_module.__package__ = "core"
        if not getattr(core_module, "__file__", None):
            init_file = core_path / "__init__.py"
            core_module.__file__ = str(init_file)
        spec = getattr(core_module, "__spec__", None)
        if not isinstance(spec, importlib.machinery.ModuleSpec) or not getattr(
            spec, "submodule_search_locations", None
        ):
            spec = importlib.machinery.ModuleSpec(
                "core", loader=None, is_package=True
            )
            spec.submodule_search_locations = search_locations or [core_path_str]
            core_module.__spec__ = spec  # type: ignore[attr-defined]
    if llm_path.exists():
        persona_spec = importlib.util.find_spec("mind.persona")
        if persona_spec is not None and persona_spec.origin:
            logging.getLogger("sandbox.cognitive").info(
                "[COGNITIVE] Real persona module linked successfully."
            )

    if interface_path.exists():
        interface_locations = list(getattr(interface_module, "__path__", []))
        interface_path_str = str(interface_path)
        if interface_path_str not in interface_locations:
            interface_locations.append(interface_path_str)
        if interface_locations:
            interface_module.__path__ = interface_locations  # type: ignore[attr-defined]
        if not getattr(interface_module, "__package__", None):
            interface_module.__package__ = "interface"
        if not getattr(interface_module, "__file__", None):
            init_file = interface_path / "__init__.py"
            interface_module.__file__ = str(init_file)

    if "cv2" not in sys.modules:
        cv2_module = types.ModuleType("cv2")

        def setNumThreads(threads: int) -> None:  # pragma: no cover - stub
            return None

        cv2_module.setNumThreads = setNumThreads
        sys.modules["cv2"] = cv2_module

    # Vision stubs ---------------------------------------------------------
    vm_module = sys.modules.get("interface.VisionManager")
    if vm_module is None:
        vm_module = types.ModuleType("interface.VisionManager")
        sys.modules["interface.VisionManager"] = vm_module

    if not hasattr(vm_module, "VisionManager"):

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

    sys.modules.setdefault("core.VisionManager", vm_module)
    interface_module.VisionManager = vm_module.VisionManager  # type: ignore[attr-defined]
    core_module.VisionManager = vm_module.VisionManager  # type: ignore[attr-defined]

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
    movement_module = sys.modules.get("interface.MovementControl")
    if movement_module is None:
        movement_module = types.ModuleType("interface.MovementControl")
        sys.modules["interface.MovementControl"] = movement_module

    if not hasattr(movement_module, "MovementControl"):

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

    sys.modules.setdefault("core.MovementControl", movement_module)
    interface_module.MovementControl = movement_module.MovementControl  # type: ignore[attr-defined]
    core_module.MovementControl = movement_module.MovementControl  # type: ignore[attr-defined]

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
from app.logging.logging_config import setup_logging  # type: ignore  # noqa: E402

from sandbox.mocks import (  # noqa: E402
    MockLedController,
    MockMovementService,
    MockVisionService,
    MockVoiceService,
)
from sandbox.mocks.mock_sensors import MockIMU, MockOdometry  # noqa: E402


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


class MockLLMClient:
    """Lightweight canned-response client used when no LLM is reachable."""

    def __init__(self, *, message: str = "Lumo is not thinking...") -> None:
        self._message = message
        self.base_url = "mock://llm"
        self._logger = logging.getLogger("sandbox.cognitive.mock_llm")

    def query(self, _messages, *, max_reply_chars: int = 220) -> str:
        self._logger.debug("MockLLMClient responding with canned message")
        return self._message[:max_reply_chars]


class _SimpleHttpLLMClient:
    """Minimal HTTP client compatible with the llama.cpp REST API."""

    def __init__(self, base_url: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._logger = logging.getLogger("sandbox.cognitive.http_llm")

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def query(self, messages, *, max_reply_chars: int = 220) -> str:
        payload = json.dumps({"model": "sandbox", "messages": list(messages)})
        request = urllib.request.Request(
            self.chat_url,
            data=payload.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
            self._logger.warning("HTTP error querying LLM: %s", exc)
            raise
        except urllib.error.URLError as exc:  # pragma: no cover - network dependent
            self._logger.warning("URL error querying LLM: %s", exc)
            raise

        choice = data.get("choices") or []
        if choice:
            message = choice[0].get("message") or {}
            content = str(message.get("content", "")).strip()
        else:
            content = str(data)

        if max_reply_chars > 0:
            content = content[:max_reply_chars]
        return content or "(no response)"


class _SandboxLlamaProcess:
    """Stub ``LlamaServerProcess`` compatible with :class:`ConversationService`."""

    def __init__(self, *, available: bool, base_url: Optional[str]) -> None:
        self.port = 0
        self._available = available
        self._base_url = (base_url or "").rstrip("/")
        self.logger = logging.getLogger("sandbox.cognitive.llama_process")

    def is_running(self) -> bool:
        return True

    def start(self) -> None:
        self.logger.debug("Sandbox llama process start() invoked")

    def wait_ready(self, timeout: Optional[float] = None) -> bool:
        self.logger.debug(
            "Sandbox llama process wait_ready(timeout=%s) -> True", timeout
        )
        return True

    def poll(self) -> Optional[int]:
        return None

    def poll_health(
        self,
        base_url: str,
        *,
        interval: float,
        max_retries: int,
        backoff: float,
        timeout: Optional[float],
    ) -> bool:
        if not self._available:
            self.logger.debug("Skipping health poll: LLM not available")
            return True

        url = f"{(base_url or self._base_url).rstrip('/')}/health"
        retries = max(0, int(max_retries)) + 1
        attempt = 0
        last_error: Optional[Exception] = None
        while attempt < retries:
            attempt += 1
            try:
                with urllib.request.urlopen(url, timeout=timeout or interval) as resp:
                    if 200 <= resp.status < 500:
                        self.logger.debug(
                            "Health check succeeded on attempt %s with status %s",
                            attempt,
                            resp.status,
                        )
                        return True
            except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
                self.logger.info("Health endpoint returned HTTP %s", exc.code)
                return True
            except urllib.error.URLError as exc:  # pragma: no cover - network dependent
                last_error = exc
                self.logger.debug("Health poll attempt %s failed: %s", attempt, exc)
            time.sleep(min(interval * (backoff ** attempt), 1.0))

        if last_error:
            self.logger.warning("Health checks failed: %s", last_error)
        return False

    def terminate(self) -> None:
        self.logger.debug("Sandbox llama process terminate() invoked")


class _SandboxConversationManager:
    """Conversation manager used by the sandbox cognitive service."""

    def __init__(
        self,
        *,
        stt: MockVoiceService,
        tts: MockVoiceService,
        led_controller: MockLedController,
        llm_client,
        stop_event: threading.Event,
        wait_until_ready: Callable[[], None],
        additional_stop_events: Optional[Iterable[threading.Event]] = None,
        logger: Optional[logging.Logger] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self._stt = stt
        self._tts = tts
        self._led = led_controller
        self._llm = llm_client
        self._stop_event = stop_event
        self._extra_stops = tuple(additional_stop_events or ())
        self._wait_until_ready = wait_until_ready
        self._logger = logger or logging.getLogger("sandbox.cognitive.manager")
        self._paused = False
        self._running = False
        self._system_prompt = system_prompt

    def run(self, stop_event: Optional[threading.Event] = None) -> None:
        stop = stop_event or self._stop_event
        self._logger.info("Sandbox conversation manager started")
        self._wait_until_ready()
        self._stt.start()
        self._running = True
        try:
            while not stop.is_set() and not self._stop_event.is_set():
                if any(ev.is_set() for ev in self._extra_stops):
                    self._logger.debug("Additional stop event triggered")
                    break

                if self._paused:
                    time.sleep(0.05)
                    continue

                utterance = self._stt.listen()
                if utterance is None:
                    continue
                utterance = utterance.strip()
                if not utterance:
                    continue

                self._led.set_color("thinking")
                self._logger.debug("User said: %s", utterance)

                system_prompt = (
                    self._system_prompt
                    or "You are Lumo, a friendly companion robot."
                )
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": utterance},
                ]

                try:
                    reply = self._llm.query(messages, max_reply_chars=220)
                except Exception as exc:  # pragma: no cover - network dependent
                    self._logger.warning("LLM query failed: %s", exc)
                    reply = "I am having trouble thinking right now."

                self._led.set_color("speaking")
                self._tts.speak(reply)
                self._led.set_color("idle")
        finally:
            self._running = False
            self._led.set_color("idle")
            self._logger.info("Sandbox conversation manager stopped")

    def pause_stt(self) -> None:
        self._logger.debug("pause_stt called")
        self._paused = True

    def drain_queues(self) -> None:
        self._logger.debug("drain_queues called (no-op)")

    def request_stop(self) -> None:
        self._logger.debug("request_stop called")
        self._stop_event.set()

    def stop(self) -> None:
        self._logger.debug("stop called")
        self._paused = True
        self._running = False


def _build_sandbox_manager_factory(
    system_prompt: Optional[str] = None,
) -> Tuple[
    Callable[..., _SandboxConversationManager],
    Dict[str, object],
    Callable[[threading.Event], None],
]:
    stop_ref: Dict[str, threading.Event] = {}

    def register(event: threading.Event) -> None:
        stop_ref["stop_event"] = event

    def factory(
        *,
        stt: MockVoiceService,
        tts: MockVoiceService,
        led_controller: MockLedController,
        llm_client,
        wait_until_ready: Callable[[], None],
        additional_stop_events: Optional[Iterable[threading.Event]] = None,
        logger: Optional[logging.Logger] = None,
        **_kwargs,
    ) -> _SandboxConversationManager:
        stop_event = stop_ref.get("stop_event")
        if stop_event is None:
            raise RuntimeError("Sandbox manager stop_event not registered")
        return _SandboxConversationManager(
            stt=stt,
            tts=tts,
            led_controller=led_controller,
            llm_client=llm_client,
            stop_event=stop_event,
            wait_until_ready=wait_until_ready,
            additional_stop_events=additional_stop_events,
            logger=logger,
            system_prompt=system_prompt,
        )

    manager_kwargs: Dict[str, object] = {
        "wait_until_ready": lambda: None,
        "logger": logging.getLogger("sandbox.cognitive.manager"),
    }
    return factory, manager_kwargs, register


def _load_sandbox_config(config_path: Path) -> Dict[str, object]:
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logging.getLogger("sandbox.cognitive").warning(
            "sandbox_config.json not found at %s", config_path
        )
    except json.JSONDecodeError as exc:
        logging.getLogger("sandbox.cognitive").warning(
            "Invalid sandbox_config.json (%s): %s", config_path, exc
        )
    return {}


class CognitiveConversationService:
    """Conversation service that optionally delegates to the real runtime."""

    def __init__(
        self,
        voice: MockVoiceService,
        led: MockLedController,
        *,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.logger = logging.getLogger("sandbox.cognitive.conversation")
        self.voice = voice
        self._led_controller = led
        self.state = "IDLE"
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._conversation = None
        self._stop_fallback = threading.Event()
        self._system_prompt = system_prompt

        config_path = Path(__file__).with_name("sandbox_config.json")
        self._config = _load_sandbox_config(config_path)
        self._llm_base_url = str(
            self._config.get("llm_server")
            or self._config.get("llm_base_url")
            or ""
        ).strip()

    # ------------------------------------------------------------------ helpers
    def _resolve_conversation_class(self):
        try:
            from app.services.conversation_service import ConversationService

            return ConversationService
        except Exception as exc:  # pragma: no cover - import defensive
            self.logger.warning(
                "Unable to import ConversationService: %s", exc
            )
            return None

    def _ping_llm(self, base_url: str, *, timeout: float = 1.5) -> bool:
        if not base_url:
            return False
        url_candidates = [
            f"{base_url.rstrip('/')}/health",
            base_url.rstrip("/") or base_url,
        ]
        for url in url_candidates:
            try:
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    if 200 <= resp.status < 500:
                        return True
            except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
                if 400 <= exc.code < 500:
                    return True
            except urllib.error.URLError:
                continue
        return False

    def _build_llm_client(self, base_url: str, available: bool):
        if not available:
            return MockLLMClient()

        try:
            from mind.llm_client import LlamaClient

            client = LlamaClient(base_url=base_url)
            self.logger.info("Using real LlamaClient for LLM interactions")
            return client
        except Exception as exc:  # pragma: no cover - import defensive
            self.logger.warning(
                "Falling back to simple HTTP client due to import error: %s", exc
            )
            return _SimpleHttpLLMClient(base_url)

    def _create_conversation(self, llm_client, available: bool):
        conversation_cls = self._resolve_conversation_class()
        if conversation_cls is None:
            return None

        process = _SandboxLlamaProcess(available=available, base_url=self._llm_base_url)
        manager_factory, manager_kwargs, register = _build_sandbox_manager_factory(
            self._system_prompt
        )

        conversation = conversation_cls(
            stt=self.voice,
            tts=self.voice,
            led_controller=self._led_controller,
            llm_client=llm_client,
            process=process,
            manager_factory=manager_factory,
            manager_kwargs=manager_kwargs,
            readiness_timeout=1.0,
            health_check_base_url=self._llm_base_url if available else None,
            health_check_interval=0.5,
            health_check_max_retries=1,
            health_check_backoff=1.2,
            health_check_timeout=1.0,
            led_cleanup=None,
            logger=logging.getLogger("sandbox.cognitive.real_service"),
        )

        register(conversation.stop_event)
        if self._system_prompt:
            logging.getLogger("sandbox.cognitive").info(
                "[COGNITIVE] Using real ConversationService with system prompt."
            )
        return conversation

    def _start_fallback_loop(self, llm_client) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_fallback.clear()
        thread = threading.Thread(
            target=self._loop,
            name="sandbox-conversation",
            daemon=True,
            args=(llm_client,),
        )
        self._thread = thread
        thread.start()

    def _loop(self, llm_client) -> None:
        while not self._stop_fallback.is_set():
            utterance = self.voice.listen()
            if utterance is None:
                continue
            utterance = utterance.strip()
            if not utterance:
                continue

            self.state = "THINK"
            self._led_controller.set_color("thinking")
            system_prompt = (
                self._system_prompt
                or "You are Lumo, a friendly companion robot."
            )
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": utterance},
            ]
            try:
                reply = llm_client.query(messages, max_reply_chars=220)
            except Exception as exc:  # pragma: no cover - network dependent
                self.logger.warning("Fallback LLM query failed: %s", exc)
                reply = "I am having trouble thinking right now."

            self.state = "SPEAK"
            self._led_controller.set_color("speaking")
            self.voice.speak(reply)
            self.state = "IDLE"
            self._led_controller.set_color("idle")

    # ------------------------------------------------------------------ API
    def start(self) -> None:
        if self._running:
            return

        self.voice.start()

        base_url = self._llm_base_url
        available = self._ping_llm(base_url) if base_url else False
        if available:
            self.logger.info("Connected to LLM server at %s", base_url)
        else:
            if base_url:
                self.logger.warning(
                    "LLM server %s not reachable, using mock responses", base_url
                )
            else:
                self.logger.info("No LLM server configured, using mock responses")

        llm_client = self._build_llm_client(base_url or "http://127.0.0.1:8080", available)

        conversation = self._create_conversation(llm_client, available)
        if conversation is not None:
            try:
                conversation.start()
                self._conversation = conversation
                self._running = True
                self.logger.info(
                    "Cognitive conversation service started using %s LLM",
                    "real" if available else "mock",
                )
                return
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.exception(
                    "Failed to start ConversationService, falling back to sandbox loop: %s",
                    exc,
                )
                self._conversation = None

        self.logger.info("Starting fallback sandbox conversation loop")
        self._running = True
        self._start_fallback_loop(llm_client)

    def stop(self, terminate_process: bool = False, shutdown_resources: bool = False) -> None:
        if not self._running:
            return

        if self._conversation is not None:
            self.logger.info("Stopping ConversationService")
            try:
                self._conversation.stop(
                    terminate_process=terminate_process,
                    shutdown_resources=shutdown_resources,
                )
            finally:
                self._conversation.join()
                self._conversation = None
        else:
            self.logger.info("Stopping sandbox fallback loop")
            self._stop_fallback.set()
            thread = self._thread
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
            self._thread = None

        self.voice.stop()
        self._led_controller.set_color("idle")
        self._running = False

    def join(self, timeout: Optional[float] = None) -> None:
        if self._conversation is not None:
            self._conversation.join(timeout)
        elif self._thread and self._thread.is_alive():
            self._thread.join(timeout)
            self._thread = None

    @property
    def stop_event(self):
        if self._conversation is not None:
            return self._conversation.stop_event
        return self._stop_fallback


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
    persona_logger = logging.getLogger("sandbox.cognitive")
    system_prompt: Optional[str] = None
    try:
        from mind.persona import build_system

        try:
            system_prompt = build_system()
        except Exception as exc:  # pragma: no cover - defensive
            persona_logger.warning(
                "[COGNITIVE] Failed to build persona: %s", exc
            )
        else:
            persona_logger.info("[COGNITIVE] Persona loaded successfully.")
    except Exception as exc:  # pragma: no cover - defensive
        persona_logger.warning(
            "[COGNITIVE] Unable to import persona module: %s", exc
        )

    conversation = CognitiveConversationService(
        voice,
        led,
        system_prompt=system_prompt,
    )
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

    gateway: Optional[SensorGateway] = None
    config = _load_sandbox_config(Path(__file__).with_name("sandbox_config.json"))

    # --- SANDBOX PROPRIOCEPTION (mock-only) ---
    if config.get("enable_proprioception", False):
        logger.info("[SANDBOX] Enabling proprioception simulation (mock-only)")

        body = BodyModel()

        controller = SensorController()
        controller.imu = MockIMU()
        controller.odom = MockOdometry()

        gateway = SensorGateway(
            controller=controller,
            body_model=body,
            poll_rate_hz=5.0,
        )
        gateway.start()
        logger.info("[SANDBOX] Proprioceptive sensors active (mock mode)")
    else:
        logger.info("[SANDBOX] Proprioception disabled")

    try:
        runtime.start()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.stop()
        try:
            if "gateway" in locals() and gateway:
                gateway.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
