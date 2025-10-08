import sys
import threading
import time
import types
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

core_stub = types.ModuleType("core")
core_stub.__path__ = [str(SERVER_ROOT / "core")]
sys.modules["core"] = core_stub

mind_stub = types.ModuleType("mind")
mind_stub.__path__ = [str(SERVER_ROOT / "mind")]
sys.modules["mind"] = mind_stub

led_stub = types.ModuleType("LedController")


class _StubLedController:
    async def stop_animation(self):  # pragma: no cover - defensive shim
        pass

    async def set_all(self, _color):  # pragma: no cover - defensive shim
        pass

    async def start_pulsed_wipe(self, _color, _wait, *_args):  # pragma: no cover
        pass

    async def close(self):  # pragma: no cover - defensive shim
        pass


led_stub.LedController = _StubLedController
sys.modules["LedController"] = led_stub
sys.modules["core.LedController"] = led_stub

sounddevice_stub = types.ModuleType("sounddevice")


class _StubStream:  # pragma: no cover - defensive shim
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


sounddevice_stub.RawInputStream = _StubStream
sys.modules["sounddevice"] = sounddevice_stub

vosk_stub = types.ModuleType("vosk")


class _StubModel:  # pragma: no cover - defensive shim
    def __init__(self, *args, **kwargs):
        pass


class _StubRecognizer:  # pragma: no cover - defensive shim
    def __init__(self, *args, **kwargs):
        pass

    def SetWords(self, *_args, **_kwargs):
        pass


vosk_stub.Model = _StubModel
vosk_stub.KaldiRecognizer = _StubRecognizer
sys.modules["vosk"] = vosk_stub

requests_stub = types.ModuleType("requests")


def _fail_post(*_args, **_kwargs):  # pragma: no cover - guardrail
    raise AssertionError("Unexpected HTTP call during tests")


requests_stub.post = _fail_post
sys.modules["requests"] = requests_stub

from mind.interface.voice_interface import ConversationManager


class FakeSTT:
    def __init__(self, utterances):
        self.utterances = list(utterances)
        self.pause_calls = 0
        self.resume_calls = 0
        self.stopped = False

    def stream(self):
        for item in self.utterances:
            yield item
        while True:
            yield None

    def pause(self):
        self.pause_calls += 1

    def resume(self):
        self.resume_calls += 1

    def stop(self):
        self.stopped = True


class FakeLLM:
    def __init__(self, failures, reply="respuesta"):
        self.failures = failures
        self.reply = reply
        self.calls = 0
        self.call_times = []
        self.call_event = threading.Event()

    def query(self, messages, max_reply_chars=220):
        self.calls += 1
        self.call_times.append(time.monotonic())
        self.call_event.set()
        if self.calls <= self.failures:
            raise TimeoutError("timeout")
        return self.reply


class FakeTTS:
    def __init__(self):
        self.phrases = []
        self.event = threading.Event()

    def speak(self, text):
        self.phrases.append(text)
        self.event.set()


class FakeLED:
    def __init__(self):
        self.states = []
        self.closed = False

    def set_state(self, state):
        self.states.append(state)

    def close(self):
        self.closed = True
def test_llm_backoff_retries_and_metrics():
    stt = FakeSTT(["humo", "hola"])
    llm = FakeLLM(2, reply="ok")
    tts = FakeTTS()
    led = FakeLED()
    stop_event = threading.Event()

    manager = ConversationManager(
        stt=stt,
        llm_client=llm,
        tts=tts,
        led_controller=led,
        stop_event=stop_event,
        wait_until_ready=lambda: None,
        stt_poll_interval=0.01,
        llm_retry_initial_delay=0.01,
        llm_retry_backoff=2.0,
        llm_retry_max_attempts=5,
        speak_cooldown=0.0,
    )

    thread = threading.Thread(target=manager.run, daemon=True)
    thread.start()

    assert tts.event.wait(3)
    stop_event.set()
    thread.join(3)

    assert llm.calls == 3
    assert manager.metrics.llm_retry_count == 2
    assert manager.metrics.llm_calls == 1
    assert stt.pause_calls >= 1
    assert stt.resume_calls >= 1

    diffs = [b - a for a, b in zip(llm.call_times, llm.call_times[1:])]
    assert diffs[0] >= 0.01
    assert diffs[1] >= 0.02


def test_backoff_respects_stop_event():
    stt = FakeSTT(["humo", "hola"])
    llm = FakeLLM(10)
    tts = FakeTTS()
    led = FakeLED()
    stop_event = threading.Event()

    manager = ConversationManager(
        stt=stt,
        llm_client=llm,
        tts=tts,
        led_controller=led,
        stop_event=stop_event,
        wait_until_ready=lambda: None,
        stt_poll_interval=0.01,
        llm_retry_initial_delay=0.1,
        llm_retry_backoff=2.0,
        llm_retry_max_attempts=10,
        speak_cooldown=0.0,
    )

    thread = threading.Thread(target=manager.run, daemon=True)
    thread.start()

    assert llm.call_event.wait(2)
    stop_event.set()
    thread.join(2)
    assert not thread.is_alive()
    assert stt.stopped

