from __future__ import annotations

"""Voice interface package assembling speech I/O and conversation."""

from typing import Optional
import threading
import time

from .speech_input import SpeechInput, SubprocessSpeechInput
from .speech_output import (
    SpeechOutput,
    TTSInterface,
    SubprocessTTS,
    LEDInterface,
    NullLED,
)
from .conversation import ConversationManager
from core.llm.base import LLMClient
from core.llm.http_client import HTTPClient


class VoiceInterface:
    """High level orchestrator for the voice assistant."""

    def __init__(
        self,
        speech_input: SpeechInput,
        conversation: ConversationManager,
        speech_output: SpeechOutput,
    ) -> None:
        self.speech_input = speech_input
        self.conversation = conversation
        self.speech_output = speech_output
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.speech_output.set_state("wake")
        self.speech_input.start()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        for utter in self.speech_input.stream():
            if not self._running:
                break
            if utter:
                self.speech_output.set_state("listen")
                reply = self.conversation.process(utter)
                if reply:
                    self.speech_output.set_state("speaking")
                    self.speech_input.pause()
                    self.speech_output.speak(reply)
                    self.speech_input.resume()
                    self.speech_output.set_state("wake")
            time.sleep(0.01)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self.speech_input.stop()
        self.speech_output.close()
        if self._thread:
            self._thread.join(timeout=1)


__all__ = [
    "SpeechInput",
    "SubprocessSpeechInput",
    "SpeechOutput",
    "TTSInterface",
    "SubprocessTTS",
    "LEDInterface",
    "NullLED",
    "ConversationManager",
    "LLMClient",
    "HTTPClient",
    "VoiceInterface",
]
