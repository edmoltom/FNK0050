from __future__ import annotations

"""Application helpers to start and configure server subsystems."""

from pathlib import Path
from typing import Any, Dict, Optional

from .core.voice import (
    ConversationManager,
    HTTPClient,
    SpeechOutput,
    SubprocessSpeechInput,
    SubprocessTTS,
    VoiceInterface,
)
from .core.vision.system import VisionSystem

BASE_DIR = Path(__file__).resolve().parent


def start_voice(config: Optional[Dict[str, Any]] = None) -> VoiceInterface:
    """Initialise and start the voice interface.

    Parameters
    ----------
    config:
        Optional configuration dictionary. Supported keys:
        ``stt_script`` and ``tts_script`` for custom executable paths and
        ``wake_words`` for the conversation manager.
    """

    cfg = config or {}
    stt_script = Path(cfg.get("stt_script", BASE_DIR / "core" / "llm" / "stt.py"))
    tts_script = Path(cfg.get("tts_script", BASE_DIR / "core" / "llm" / "tts.py"))
    wake_words = cfg.get("wake_words", ["robot"])

    llm = HTTPClient()
    conv = ConversationManager(llm, wake_words=wake_words)
    stt = SubprocessSpeechInput(stt_script)
    tts = SubprocessTTS(tts_script)
    output = SpeechOutput(tts)
    iface = VoiceInterface(stt, conv, output)
    iface.start()
    return iface


def start_vision(config: Optional[Dict[str, Any]] = None) -> VisionSystem:
    """Create the vision system with ``config``."""
    return VisionSystem(config=config)


def create_app(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create and start requested subsystems based on ``config``.

    The configuration can enable subsystems via boolean flags:
    ``voice`` and ``vision``.  Sub-dictionaries ``voice_config`` and
    ``vision_config`` allow subsystem specific options.
    """
    cfg = config or {}
    systems: Dict[str, Any] = {}

    if cfg.get("voice"):
        systems["voice"] = start_voice(cfg.get("voice_config"))
    if cfg.get("vision"):
        systems["vision"] = start_vision(cfg.get("vision_config"))
    return systems
