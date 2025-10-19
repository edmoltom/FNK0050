"""Mock voice interface using console input/output."""
from __future__ import annotations

import logging
from typing import Optional


class MockVoiceService:
    """Simulate STT/TTS interactions through the terminal."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mock.voice")
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.logger.debug("[MOCK] Voice interface started")

    def listen(self) -> Optional[str]:
        if not self._running:
            self.logger.debug("[MOCK] Voice interface not running; listen() ignored")
            return None
        try:
            text = input("[YOU]: ")
        except EOFError:
            self.logger.debug("[MOCK] Voice input stream closed")
            return None
        text = text.strip()
        self.logger.debug("[MOCK] Heard: %s", text)
        return text

    def speak(self, text: str) -> None:
        self.logger.debug("[MOCK] Speaking: %s", text)
        print("[LUMO]:", text)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self.logger.debug("[MOCK] Voice interface stopped")
