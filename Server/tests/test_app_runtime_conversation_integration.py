from __future__ import annotations

import importlib
import sys
import threading
import time
import types
from pathlib import Path
from typing import Dict, Iterable, Optional

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

cv2_stub = types.ModuleType("cv2")
numpy_stub = types.ModuleType("numpy")
numpy_typing_stub = types.ModuleType("numpy.typing")
led_controller_stub = types.ModuleType("LedController")
sounddevice_stub = types.ModuleType("sounddevice")
vosk_stub = types.ModuleType("vosk")

core_stub = types.ModuleType("core")
core_stub.__path__ = [str(SERVER_ROOT / "core")]
sys.modules["core"] = core_stub

mind_stub = types.ModuleType("mind")
mind_stub.__path__ = [str(SERVER_ROOT / "mind")]
sys.modules["mind"] = mind_stub
importlib.import_module("mind.llama_server_process")

interface_stub = types.ModuleType("interface")
interface_stub.__path__ = [str(SERVER_ROOT / "interface")]
sys.modules["interface"] = interface_stub

requests_stub = types.ModuleType("requests")


class _StubRequestsResponse:
    def __init__(self) -> None:
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": ""}}]}


def _requests_post(*_args, **_kwargs):
    raise RuntimeError("requests.post should not be called in tests")

requests_stub.post = _requests_post
requests_stub.Response = _StubRequestsResponse
sys.modules.setdefault("requests", requests_stub)

def teardown_module() -> None:
    sys.modules.pop("mind.llama_server_process", None)
    sys.modules.pop("interface.VoiceInterface", None)
    sys.modules.pop("mind", None)
    sys.modules.pop("interface", None)
    sys.modules.pop("core", None)

def _no_op(*_args, **_kwargs) -> None:
    return None


cv2_stub.setNumThreads = _no_op  # type: ignore[attr-defined]
sys.modules.setdefault("cv2", cv2_stub)
sys.modules.setdefault("numpy", numpy_stub)
sys.modules.setdefault("numpy.typing", numpy_typing_stub)
sys.modules.setdefault("LedController", led_controller_stub)
sys.modules.setdefault("interface.LedController", led_controller_stub)
sys.modules.setdefault("sounddevice", sounddevice_stub)
sys.modules.setdefault("vosk", vosk_stub)

numpy_stub.ndarray = type("ndarray", (), {})  # type: ignore[attr-defined]
numpy_typing_stub.NDArray = object  # type: ignore[attr-defined]


class _StubLedController:  # pragma: no cover - minimal shim
    async def close(self) -> None:
        return None

    async def stop_animation(self) -> None:
        return None

    async def set_all(self, *_args, **_kwargs) -> None:
        return None

    async def start_pulsed_wipe(self, *_args, **_kwargs) -> None:
        return None


led_controller_stub.LedController = _StubLedController


class _StubRawInputStream:
    def __init__(self, *args, **_kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _StubModel:
    def __init__(self, _path: str) -> None:
        pass


class _StubKaldiRecognizer:
    def __init__(self, _model: _StubModel, _sample_rate: int) -> None:
        self._result = "{}"

    def SetWords(self, _flag: bool) -> None:
        return None

    def AcceptWaveform(self, _data: bytes) -> bool:
        return False

    def Result(self) -> str:
        return self._result

    def FinalResult(self) -> str:
        return self._result


sounddevice_stub.RawInputStream = _StubRawInputStream
vosk_stub.Model = _StubModel
vosk_stub.KaldiRecognizer = _StubKaldiRecognizer

from app.builder import AppServices
from app.runtime import AppRuntime
from app.services.conversation_service import ConversationService




class StubSTTService:
    def __init__(self, phrases: Iterable[Optional[str]]) -> None:
        self._phrases = list(phrases)
        self._index = 0
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._stop_event = threading.Event()
        self.pause_calls = 0
        self.resume_calls = 0
        self.stop_calls = 0

    def stream(self):
        while not self._stop_event.is_set():
            if not self._resume_event.wait(timeout=0.01):
                yield None
                continue

            if self._index < len(self._phrases):
                phrase = self._phrases[self._index]
                self._index += 1
                yield phrase
                continue

            yield None

    def pause(self) -> None:
        self.pause_calls += 1
        self._resume_event.clear()

    def resume(self) -> None:
        self.resume_calls += 1
        self._resume_event.set()

    def stop(self) -> None:
        self.stop_calls += 1
        self._stop_event.set()
        self._resume_event.set()


class StubTTSEngine:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.event = threading.Event()

    def speak(self, text: str) -> None:
        self.spoken.append(text)
        self.event.set()


class StubLLMClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.queries: list[tuple[list[dict[str, str]], int]] = []

    def query(self, messages, *, max_reply_chars: int):
        self.queries.append((messages, max_reply_chars))
        return self.reply


class StubLlamaProcess:
    def __init__(self) -> None:
        self.started = False
        self.start_count = 0
        self.terminate_count = 0

    def start(self) -> None:
        self.started = True
        self.start_count += 1

    def terminate(self) -> None:
        self.started = False
        self.terminate_count += 1

    def is_running(self) -> bool:
        return self.started

    def wait_ready(self, timeout: float) -> bool:
        return True

    def poll_health(
        self,
        _base_url: str,
        *,
        endpoint: str = "/health",
        method: str = "GET",
        timeout: float = 5.0,
        interval: float = 0.5,
        max_retries: int = 3,
        backoff: float = 2.0,
    ) -> bool:
        return True


class StubLedHandler:
    def __init__(self) -> None:
        self.states: list[str] = []
        self.closed = False

    def set_state(self, state: str) -> None:
        self.states.append(state)

    def close(self) -> None:
        self.closed = True


class StubVision:
    def __init__(self) -> None:
        self.frame_handler = None
        self.started = False

    def set_frame_callback(self, callback) -> None:
        self.frame_handler = callback

    def start(self, *, interval_sec: float, frame_handler=None) -> None:
        self.started = True
        self.frame_handler = frame_handler

    def stop(self) -> None:
        self.started = False


def _build_runtime_with_conversation() -> tuple[
    AppRuntime,
    ConversationService,
    StubTTSEngine,
    StubLLMClient,
    StubLlamaProcess,
    StubLedHandler,
    StubSTTService,
]:
    stt = StubSTTService(["hola humo", "enciende las luces"])
    tts = StubTTSEngine()
    llm_client = StubLLMClient("claro, encendiendo las luces")
    llama_process = StubLlamaProcess()
    led_handler = StubLedHandler()

    from interface.VoiceInterface import ConversationManager as _ConversationManager

    stop_event_ref: Dict[str, threading.Event] = {}

    def manager_factory(
        *,
        stt: StubSTTService,
        tts: StubTTSEngine,
        led_controller: StubLedHandler,
        llm_client: StubLLMClient,
        wait_until_ready,
        additional_stop_events=None,
        close_led_on_cleanup: bool = False,
    ) -> _ConversationManager:
        stop_event = stop_event_ref.get("stop_event")
        if stop_event is None:
            raise RuntimeError("Stop event not registered")
        return _ConversationManager(
            stt=stt,
            tts=tts,
            led_controller=led_controller,
            llm_client=llm_client,
            stop_event=stop_event,
            wait_until_ready=wait_until_ready,
            additional_stop_events=additional_stop_events,
            stt_poll_interval=0.01,
            speak_cooldown=0.05,
            close_led_on_cleanup=close_led_on_cleanup,
        )

    conversation_service = ConversationService(
        stt=stt,
        tts=tts,
        led_controller=led_handler,
        llm_client=llm_client,
        process=llama_process,
        manager_factory=manager_factory,
        manager_kwargs={"wait_until_ready": lambda: None},
        readiness_timeout=0.1,
        shutdown_timeout=0.2,
        health_check_interval=0.01,
        health_check_max_retries=0,
        health_check_timeout=0.1,
        led_cleanup=led_handler.close,
    )
    stop_event_ref["stop_event"] = conversation_service.stop_event

    services = AppServices()
    services.enable_conversation = True
    services.conversation = conversation_service
    services.enable_vision = True
    services.enable_movement = False
    services.vision = StubVision()
    services.enable_ws = False

    runtime = AppRuntime(services)
    return runtime, conversation_service, tts, llm_client, llama_process, led_handler, stt


def test_conversation_cycle_and_clean_shutdown() -> None:
    runtime, conversation_service, tts, llm_client, llama_process, led_handler, stt = _build_runtime_with_conversation()

    thread = threading.Thread(target=runtime.start, daemon=True)
    thread.start()

    assert tts.event.wait(timeout=5.0), "TTS output was not produced"

    time.sleep(0.1)
    runtime.stop()
    thread.join(timeout=2.0)
    assert not thread.is_alive(), "Runtime thread did not terminate"

    assert conversation_service.join(timeout=1.0)
    assert llama_process.start_count == 1
    assert llama_process.terminate_count >= 1

    assert tts.spoken == ["claro, encendiendo las luces"]
    assert llm_client.queries, "LLM client was not queried"

    last_messages, max_chars = llm_client.queries[-1]
    assert max_chars == 220
    assert any(msg.get("content") == "enciende las luces" for msg in last_messages)

    assert stt.pause_calls >= 1
    assert stt.resume_calls >= 1
    assert stt.stop_calls >= 1
    assert "speaking" in led_handler.states
    assert led_handler.states[-1] == "off"
    assert led_handler.closed
