import time

from Server.core.voice import (
    SpeechInput,
    SpeechOutput,
    ConversationManager,
    VoiceInterface,
    TTSInterface,
    LLMClient,
)
from tests.mock_llm import MockClient


class DummySTT(SpeechInput):
    def __init__(self, utterances):
        self._utter = iter(utterances)

    def start(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def resume(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def stream(self):
        for u in self._utter:
            yield u
        while True:
            yield None


class DummyTTS(TTSInterface):
    def __init__(self):
        self.spoken = []

    def say(self, text: str) -> None:
        self.spoken.append(text)


def test_voice_interface_flow():
    stt = DummySTT(["wake hello"])
    llm = MockClient()
    conv = ConversationManager(llm, wake_words=["wake"])
    tts = DummyTTS()
    output = SpeechOutput(tts)
    iface = VoiceInterface(stt, conv, output)
    iface.start()
    time.sleep(0.05)
    iface.stop()
    assert tts.spoken == ["ACK: wake hello"]
