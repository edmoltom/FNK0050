"""Streaming speech-to-text using Vosk.

Encapsulates Vosk streaming recognition into a reusable class and preserves the
original command line behaviour (printing recognised phrases prefixed with
"> ").
"""

from __future__ import annotations

import json
import queue
import sys
from pathlib import Path
from typing import Generator, Optional

import sounddevice as sd
from vosk import Model, KaldiRecognizer

from .text_norm import normalize_punct

# Default configuration (same as the original script)
DEFAULT_MODEL_DIR = Path("/home/user/vosk/vosk-model-small-es-0.42")
DEFAULT_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_DEVICE: Optional[int] = None
DEFAULT_BLOCK_SIZE = 8000


class SpeechToText:
    """Simple Vosk-based streaming STT engine."""

    def __init__(
        self,
        model_dir: str | Path = DEFAULT_MODEL_DIR,
        sample_rate: int = DEFAULT_RATE,
        device: Optional[int] = DEFAULT_DEVICE,
        channels: int = DEFAULT_CHANNELS,
        block_size: int = DEFAULT_BLOCK_SIZE,
    ) -> None:
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"[ERROR] Vosk model not found: {self.model_dir}")

        self.sample_rate = sample_rate
        self.device = device
        self.channels = channels
        self.block_size = block_size
        self._paused = False

        self.model = Model(str(self.model_dir))
        self.rec = KaldiRecognizer(self.model, self.sample_rate)
        self.rec.SetWords(True)

    # ------------------------------------------------------------------ control
    def pause(self) -> None:
        """Pause the emission of recognised phrases."""
        self._paused = True

    def resume(self) -> None:
        """Resume yielding recognised phrases."""
        self._paused = False

    # --------------------------------------------------------------- processing
    def _stream(self) -> Generator[str, None, None]:
        """Internal generator producing validated phrases from the microphone."""
        q: queue.Queue[bytes] = queue.Queue()

        def cb(indata, frames, time, status):
            if status:
                print(f"[WARN] {status}", file=sys.stderr)
            q.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            device=self.device,
            dtype="int16",
            channels=self.channels,
            callback=cb,
        ):
            try:
                while True:
                    data = q.get()
                    if self.rec.AcceptWaveform(data):
                        res = json.loads(self.rec.Result())
                        txt = (res.get("text") or "").strip()

                        words = res.get("result") or []
                        if words:
                            avg_conf = sum(w.get("conf", 0.0) for w in words) / max(
                                1, len(words)
                            )
                        else:
                            avg_conf = 0.0

                        if txt and avg_conf >= 0.60 and len(txt) >= 8:
                            yield normalize_punct(txt)
            except KeyboardInterrupt:
                final = json.loads(self.rec.FinalResult()).get("text", "").strip()
                if final:
                    yield normalize_punct(final)

    # ------------------------------------------------------------------- public
    def listen(self) -> Generator[str, None, None]:
        """Yield phrases recognised from the audio stream."""
        for phrase in self._stream():
            if self._paused:
                continue  # drain while paused
            yield phrase


# ---------------------------------------------------------------------------
# CLI entry point (unchanged behaviour)
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover - thin wrapper
    stt = SpeechToText()
    for text in stt.listen():
        print(f"> {text}")


if __name__ == "__main__":
    main()

