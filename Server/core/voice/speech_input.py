from __future__ import annotations

"""Speech input utilities for STT integration.

This module provides a base :class:`SpeechInput` interface that can be
implemented by real or fake speech-to-text backends.  A default
``SubprocessSpeechInput`` implementation is included which reads
utterances from the existing ``stt.py`` script.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Optional
import subprocess
import sys
import threading
import queue
import time


class SpeechInput(ABC):
    """Abstract interface for speech-to-text providers."""

    @abstractmethod
    def start(self) -> None:
        """Start the STT engine."""

    @abstractmethod
    def pause(self) -> None:
        """Temporarily stop producing new utterances."""

    @abstractmethod
    def resume(self) -> None:
        """Resume after a :meth:`pause`."""

    @abstractmethod
    def stop(self) -> None:
        """Completely stop the STT engine."""

    @abstractmethod
    def stream(self) -> Iterator[Optional[str]]:
        """Yield transcribed utterances.

        ``None`` may be yielded when no new utterance is available.
        Implementations should terminate the iterator once the STT
        engine finishes.
        """


class SubprocessSpeechInput(SpeechInput):
    """STT implementation that reads from the ``stt.py`` script."""

    def __init__(self, stt_script: Path) -> None:
        self._script = stt_script
        self._proc: Optional[subprocess.Popen[str]] = None
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._paused = False
        self._reader: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            [sys.executable, "-u", str(self._script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _reader() -> None:
            assert self._proc and self._proc.stdout
            for line in iter(self._proc.stdout.readline, ""):
                if line.startswith("> "):
                    self._queue.put(line[2:].strip())
            self._queue.put(None)  # sentinel indicates EOF

        self._reader = threading.Thread(target=_reader, daemon=True)
        self._reader.start()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None

    def stream(self) -> Iterator[Optional[str]]:
        while True:
            if self._paused:
                # Drain queue quickly while paused
                drained = False
                try:
                    while True:
                        item = self._queue.get_nowait()
                        if item is None:
                            return
                        drained = True
                except queue.Empty:
                    pass
                time.sleep(0.01 if drained else 0.02)
                yield None
                continue

            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                yield None
                continue
            if item is None:
                return
            yield item
