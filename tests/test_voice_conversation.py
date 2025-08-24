import sys
import types

# Provide stub for optional dependency
sys.modules.setdefault("requests", types.ModuleType("requests"))

from core.voice.speech_input import SpeechInput
from core.voice.speech_output import SpeechOutput, TTSInterface, LEDInterface
from core.voice.conversation import ConversationManager
from core.voice import VoiceInterface
from tests.mock_llm import MockClient


class FakeSTT(SpeechInput):
    def __init__(self, utterances):
        self._utter = iter(utterances)
        self.pause_calls = 0
        self.resume_calls = 0

    def start(self) -> None:
        pass

    def pause(self) -> None:
        self.pause_calls += 1

    def resume(self) -> None:
        self.resume_calls += 1

    def stop(self) -> None:
        pass

    def stream(self):
        for u in self._utter:
            yield u


class FakeLED(LEDInterface):
    def __init__(self):
        self.states = []

    def set_state(self, state: str) -> None:
        self.states.append(state)


class FakeTTS(TTSInterface):
    def __init__(self):
        self.spoken = []

    def say(self, text: str) -> None:
        self.spoken.append(text)


def test_wake_word_and_state_changes():
    llm = MockClient()
    conv = ConversationManager(llm, wake_words=["robot"])

    # No wake word -> no reply
    assert conv.process("hello") is None

    stt = FakeSTT(["hello robot"])
    leds = FakeLED()
    tts = FakeTTS()
    output = SpeechOutput(tts, leds)
    iface = VoiceInterface(stt, conv, output)

    iface.start()
    iface._thread.join(timeout=1)
    iface.stop()

    assert leds.states == ["wake", "listen", "speaking", "wake"]
    assert tts.spoken == ["ACK: hello robot"]
    assert stt.pause_calls == 1
    assert stt.resume_calls == 1
