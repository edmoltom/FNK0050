# TTS (Kawai profile, single preset with metallic distortion)
# ----------------------------------------------------------
# Generates "kawaii/robotic" voice using Piper TTS + SoX, prioritizing treble and low latency.
# Adds modulation/effects for a more METALLIC timbre (without rubberband).
#
# Requirements:
#   - piper-tts       (pip install --user piper-tts)
#   - sox             (apt install sox)
#   - aplay           (apt install alsa-utils)
#   - A Piper model (.onnx) + .onnx.json (e.g., es-hikari-medium.onnx)
#
# Usage:
#   ./tts.py --text "Hello, human."
#   ./tts.py --text "Tachikoma mode." --save output.wav
#
# Main parameters are defined in SOX_CHAIN below.
#
import argparse, shutil, subprocess, sys, tempfile
from pathlib import Path

# ----------------------
# SINGLE PROFILE (editable)
# ----------------------
# SoX effect chain applied to Piper’s raw WAV.
# Purpose of each stage:
# 1)  pitch 410        → +4 semitones approx. Keeps kawaii tone without going too chipmunk.
# 2)  tempo 1.00       → Neutral speed (adjust if you want livelier/faster).
# 3)  highpass/lowpass → 250–6000 Hz: trims extremes, softer “helmet” sound.
# 4)  equalizer 2.6 kHz +6 dB → Adds presence/brightness to consonants.
# 5)  compand          → Strong speech compression (flatter, more “mechanical” voice).
# 6)  tremolo 35 Hz 75%→ Fast AM modulation (metallic AM/ring-mod flavor).
# 7)  phaser           → Light spectral feedback (subtle metallic resonance).
# 8)  overdrive        → Gentle distortion (extra harmonics, “electric” feel).
# 9)  treble           → Boosts high frequencies for sharper timbre.
# 10) gain -n          → Normalizes to avoid clipping.
# 11) rate 16000       → Downsample for robotic tone and lower CPU use.
#
# Adjust intensity:
#   - More metallic: increase tremolo (e.g., 45 80), phaser, or overdrive.
#   - Less metallic: reduce tremolo or disable phaser.
#   - More kawaii: raise pitch to 500 and add treble +8..+12.
SOX_CHAIN = [
    "pitch","390",
    "tempo","0.96",
    "highpass","250","lowpass","6000",
    "equalizer","2600","1.0q","+6",
    "compand","0.05,0.15","-60,-60,-35,-12,0,-8","-5","-8","0.03",
    "tremolo","35","75",
    "phaser","0.8","0.74","3","0.4","2","-t",
    "overdrive","6","30",
    "treble","8","10",
    "gain","-n"
]
TARGET_RATE = 16000  # Hz

# Default model candidates (adjust to your preferred voice)
HOME = Path.home()
CANDIDATES = [
    HOME / "piper" / "es-hikari-medium.onnx",
]

def which(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)

def pick_model(user_model: str|None) -> Path|None:
    if user_model:
        p = Path(user_model)
        return p if p.exists() else None
    for c in CANDIDATES:
        if c.exists():
            return c
    return None

def synth_piper(text: str, model: Path, wav_out: Path, config: Path|None, speaker: int|None) -> None:
    """Invoke Piper TTS via Python module to synthesize speech."""
    cmd = [sys.executable, "-m", "piper", "-m", str(model), "-f", str(wav_out)]
    if config:
        cmd += ["-c", str(config)]
    if speaker is not None:
        cmd += ["--speaker", str(speaker)]
    p = run(cmd, input=text.encode("utf-8"))
    if p.returncode != 0:
        sys.stderr.write(p.stderr.decode(errors="ignore"))
        sys.exit(p.returncode)

def sox_fx(wav_in: Path, wav_out: Path, effects: list, rate: int|None) -> None:
    """Apply SoX effect chain to Piper output."""
    if not which("sox"):
        print("[WARN] Missing 'sox'; playing raw output.")
        wav_out.write_bytes(wav_in.read_bytes())
        return
    cmd = ["sox", str(wav_in), str(wav_out)] + effects
    if rate:
        cmd += ["rate", str(rate)]
    p = run(cmd)
    if p.returncode != 0:
        sys.stderr.write(p.stderr.decode(errors="ignore"))
        sys.exit(p.returncode)

def play(wav_path: Path) -> None:
    """Play the WAV using available player (aplay/paplay/play)."""
    for player in ("aplay","paplay","play"):
        if which(player):
            subprocess.run([player, str(wav_path)])
            return
    print(f"[INFO] WAV ready at {wav_path}")

def main():
    ap = argparse.ArgumentParser(description="TTS (single kawaii-robotic metallic profile).")
    ap.add_argument("--text", default=None, help="Text to speak. If omitted, reads from stdin.")
    ap.add_argument("--model", default=None, help="Path to .onnx model (default: auto-discover in ~/piper).")
    ap.add_argument("--config", default=None, help="Path to .onnx.json config (optional).")
    ap.add_argument("--speaker", type=int, default=None, help="Voice ID if the model has multiple speakers.")
    ap.add_argument("--save", default=None, help="Save final WAV to file.")
    args = ap.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        sys.exit("[ERROR] No text provided.")

    model = pick_model(args.model)
    if not model or not model.exists():
        sys.exit(f"[ERROR] No .onnx model found. Place one in ~/piper or use --model.")

    config = Path(args.config) if args.config else None
    if not config:
        maybe = model.with_suffix(model.suffix + ".json")
        if maybe.exists():
            config = maybe

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dry = td / "dry.wav"
        out = td / "out.wav"
        synth_piper(text, model, dry, config, args.speaker)

        sox_fx(dry, out, SOX_CHAIN, rate=TARGET_RATE)

        final_wav = out
        if args.save:
            dest = Path(args.save).expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(final_wav.read_bytes())
            play(dest)
        else:
            play(final_wav)

if __name__ == "__main__":
    main()