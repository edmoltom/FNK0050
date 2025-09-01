"""Run the full voice interface pipeline (STT -> LLM -> TTS)."""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


class _SpiDev:
    def __init__(self):
        self.mode = 0

    def open(self, bus, device):
        pass

    def close(self):
        pass


spidev_stub = types.SimpleNamespace(SpiDev=_SpiDev)
class _NPArray(list):
    def ravel(self):
        return self

numpy_stub = types.SimpleNamespace(
    array=lambda x: _NPArray(x),
    zeros=lambda n, dtype=None: [0] * n,
    uint8=int,
)
sounddevice_stub = types.SimpleNamespace(
    RawInputStream=lambda *a, **k: types.SimpleNamespace(
        __enter__=lambda self: self,
        __exit__=lambda self, exc_type, exc, tb: None,
    )
)
vosk_stub = types.SimpleNamespace(
    Model=lambda *a, **k: object(),
    KaldiRecognizer=lambda *a, **k: types.SimpleNamespace(
        SetWords=lambda flag: None,
        AcceptWaveform=lambda data: True,
        Result=lambda: '{"text": ""}',
        FinalResult=lambda: '{"text": ""}',
    ),
)

sys.modules.setdefault("spidev", spidev_stub)
sys.modules.setdefault("numpy", numpy_stub)
sys.modules.setdefault("sounddevice", sounddevice_stub)
sys.modules.setdefault("vosk", vosk_stub)
_resp = types.SimpleNamespace(
    raise_for_status=lambda: None,
    json=lambda: {"choices": [{"message": {"content": ""}}]},
)
requests_stub = types.SimpleNamespace(post=lambda *a, **k: _resp)
sys.modules.setdefault("requests", requests_stub)
class _STT:
    def pause(self):
        pass

    def resume(self):
        pass

    def listen(self):
        if False:
            yield ""
        return iter(())

sys.modules.setdefault("Server.core.hearing.stt", types.SimpleNamespace(SpeechToText=_STT))
class _LedController:
    def __init__(self, *a, **k):
        pass

    async def set_all(self, color):
        pass

    async def close(self):
        pass

    async def color_wipe(self, *a, **k):
        pass

    async def rainbow(self, *a, **k):
        pass

sys.modules.setdefault("Server.core.LedController", types.SimpleNamespace(LedController=_LedController))

from Server.core.VoiceInterface import ConversationManager


def main(prompt: str = None) -> None:
    """Entry point for run.py"""
    print("[INFO] Starting ConversationManager… (Ctrl+C to stop)")
    ConversationManager().run()


if __name__ == "__main__":
    main()

