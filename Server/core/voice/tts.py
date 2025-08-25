"""Text-to-speech helper using Piper and SoX.

This module provides a small wrapper around the original stand-alone script in
``core/llm/tts.py``.  The functionality is now encapsulated in the
``TextToSpeech`` class so it can be imported and reused from other modules
without spawning a new process.  The command line interface is preserved for
compatibility.

The synthesis profile and effect chain remain identical to the original
implementation; only the structure has changed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Effect chain (single profile)
# ---------------------------------------------------------------------------
# The comments below are kept verbatim from the original script.  They describe
# the intention of each SoX stage and allow easy tweaking by the user.
SOX_CHAIN: List[str] = [
    "pitch", "390",
    "tempo", "0.96",
    "highpass", "250", "lowpass", "6000",
    "equalizer", "2600", "1.0q", "+6",
    "compand", "0.05,0.15", "-60,-60,-35,-12,0,-8", "-5", "-8", "0.03",
    "tremolo", "35", "75",
    "phaser", "0.8", "0.74", "3", "0.4", "2", "-t",
    "overdrive", "6", "30",
    "treble", "8", "10",
    "gain", "-n",
]

TARGET_RATE = 16000  # Hz


# Default model candidates (adjust to your preferred voice)
HOME = Path.home()
CANDIDATES = [
    HOME / "piper" / "es-hikari-medium.onnx",
]


class TextToSpeech:
    """Simple Piper + SoX TTS engine."""

    def __init__(
        self,
        model: Optional[str | Path] = None,
        config: Optional[str | Path] = None,
        speaker: Optional[int] = None,
        effects: Optional[List[str]] = None,
        rate: int = TARGET_RATE,
    ) -> None:
        self.model = self._pick_model(model)
        self.config = Path(config) if config else self._auto_config(self.model)
        self.speaker = speaker
        self.effects = effects or SOX_CHAIN
        self.rate = rate

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _which(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    @staticmethod
    def _run(cmd, **kw):
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)

    def _pick_model(self, user_model: Optional[str | Path]) -> Optional[Path]:
        if user_model:
            p = Path(user_model)
            return p if p.exists() else None
        for c in CANDIDATES:
            if c.exists():
                return c
        return None

    def _auto_config(self, model: Optional[Path]) -> Optional[Path]:
        if not model:
            return None
        maybe = model.with_suffix(model.suffix + ".json")
        return maybe if maybe.exists() else None

    # --------------------------------------------------------------- pipelines
    def _synth_piper(self, text: str, wav_out: Path) -> None:
        cmd = [sys.executable, "-m", "piper", "-m", str(self.model), "-f", str(wav_out)]
        if self.config:
            cmd += ["-c", str(self.config)]
        if self.speaker is not None:
            cmd += ["--speaker", str(self.speaker)]
        p = self._run(cmd, input=text.encode("utf-8"))
        if p.returncode != 0:
            sys.stderr.write(p.stderr.decode(errors="ignore"))
            raise RuntimeError("Piper synthesis failed")

    def _sox_fx(self, wav_in: Path, wav_out: Path) -> None:
        if not self._which("sox"):
            print("[WARN] Missing 'sox'; playing raw output.")
            wav_out.write_bytes(wav_in.read_bytes())
            return
        cmd = ["sox", str(wav_in), str(wav_out)] + self.effects
        if self.rate:
            cmd += ["rate", str(self.rate)]
        p = self._run(cmd)
        if p.returncode != 0:
            sys.stderr.write(p.stderr.decode(errors="ignore"))
            raise RuntimeError("SoX processing failed")

    def _play(self, wav_path: Path) -> None:
        for player in ("aplay", "paplay", "play"):
            if self._which(player):
                subprocess.run([player, str(wav_path)])
                return
        print(f"[INFO] WAV ready at {wav_path}")

    # ----------------------------------------------------------------- public
    def speak(self, text: str, save: Optional[str | Path] = None) -> None:
        """Synthesize *text* and play it.  Optionally save the result."""
        if not text.strip():
            raise ValueError("[ERROR] No text provided.")

        if not self.model or not self.model.exists():
            raise FileNotFoundError(
                "[ERROR] No .onnx model found. Place one in ~/piper or use --model."
            )

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            dry = td_path / "dry.wav"
            out = td_path / "out.wav"
            self._synth_piper(text, dry)
            self._sox_fx(dry, out)

            final_wav = out
            if save:
                dest = Path(save).expanduser()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(final_wav.read_bytes())
                self._play(dest)
            else:
                self._play(final_wav)


# ---------------------------------------------------------------------------
# CLI entry point (unchanged behaviour)
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover - thin wrapper
    ap = argparse.ArgumentParser(
        description="TTS (single kawaii-robotic metallic profile)."
    )
    ap.add_argument(
        "--text", default=None, help="Text to speak. If omitted, reads from stdin."
    )
    ap.add_argument(
        "--model",
        default=None,
        help="Path to .onnx model (default: auto-discover in ~/piper).",
    )
    ap.add_argument(
        "--config", default=None, help="Path to .onnx.json config (optional)."
    )
    ap.add_argument(
        "--speaker", type=int, default=None, help="Voice ID if the model has multiple speakers."
    )
    ap.add_argument("--save", default=None, help="Save final WAV to file.")
    args = ap.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()

    tts = TextToSpeech(model=args.model, config=args.config, speaker=args.speaker)
    tts.speak(text, save=args.save)


if __name__ == "__main__":
    main()

