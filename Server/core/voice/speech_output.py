from __future__ import annotations

"""Speech output helpers for text-to-speech and LED feedback."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import subprocess
import sys


class TTSInterface(ABC):
    """Abstract text-to-speech engine."""

    @abstractmethod
    def say(self, text: str) -> None:
        """Speak ``text`` synchronously."""


class LEDInterface(ABC):
    """Simple interface for LED feedback controllers."""

    @abstractmethod
    def set_state(self, state: str) -> None:
        """Update LEDs to reflect ``state``."""

    def close(self) -> None:  # pragma: no cover - optional
        """Clean up resources."""
        pass


class NullLED(LEDInterface):
    """Fallback LED controller that performs no action."""

    def set_state(self, state: str) -> None:  # pragma: no cover - trivial
        pass


class SubprocessTTS(TTSInterface):
    """TTS implementation invoking the existing ``tts.py`` script."""

    def __init__(self, tts_script: Path) -> None:
        self._script = tts_script

    def say(self, text: str) -> None:
        subprocess.run([sys.executable, str(self._script), "--text", text], check=False)


class SpeechOutput:
    """High level speech output handler combining TTS and LEDs."""

    def __init__(self, tts: TTSInterface, leds: Optional[LEDInterface] = None) -> None:
        self.tts = tts
        self.leds = leds or NullLED()

    def set_state(self, state: str) -> None:
        self.leds.set_state(state)

    def speak(self, text: str) -> None:
        self.tts.say(text)

    def close(self) -> None:
        self.leds.close()
