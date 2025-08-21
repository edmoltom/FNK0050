# stt.py — Vosk small ES streaming test (USB mic → text)
# ---------------------------------------------------------------------------
# Converts live microphone audio into Spanish text using Vosk (small model).
# Prints full sentences as lines prefixed with "> ".
#
# Notes
#  - Requires PortAudio and sounddevice: `sudo apt install python3-pyaudio portaudio19-dev`
#    then `pip install --break-system-packages sounddevice vosk`
#  - MODEL_DIR points to your installed Vosk model directory.
#  - Use `python3 -c "import sounddevice as sd; print(sd.query_devices())"`
#    to discover device indices if you need to select a specific input.

import json, queue, sys, signal
from pathlib import Path
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# Absolute model path on your Pi. Adjust if you move the model.
# Example structure: /home/user/vosk/vosk-model-small-es-0.42
MODEL_DIR = Path("/home/user/vosk/vosk-model-small-es-0.42")
SAMPLE_RATE = 16000
CHANNELS = 1

# Optional: set a specific input device index (None = default).
# Example tip: print(sd.query_devices()) to find the right index.
INPUT_DEVICE = None

def main():
    if not MODEL_DIR.exists():
        sys.exit(f"[ERROR] Vosk model not found: {MODEL_DIR}")

    model = Model(str(MODEL_DIR))
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    rec.SetWords(True)

    q = queue.Queue()

    def cb(indata, frames, time, status):
        """SoundDevice callback: push raw bytes into the queue."""
        if status:
            print(f"[WARN] {status}", file=sys.stderr)
        q.put(bytes(indata))

    print("[INFO] Starting microphone stream… Ctrl+C to stop.")
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                           device=INPUT_DEVICE, dtype="int16",
                           channels=CHANNELS, callback=cb):
        try:
            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    txt = (res.get("text") or "").strip()

                    # confidence-based gating
                    words = res.get("result") or []
                    if words:
                        avg_conf = sum(w.get("conf", 0.0) for w in words) / max(1, len(words))
                    else:
                        avg_conf = 0.0

                    # confianza >= 0.60 y al menos 8 caracteres
                    if txt and avg_conf >= 0.60 and len(txt) >= 8:
                        print(f"> {txt}")

                else:
                    # If you need partial hypotheses in real time:
                    # partial = json.loads(rec.PartialResult()).get("partial", "")
                    # print(f"~ {partial}")
                    pass
        except KeyboardInterrupt:
            print("\n[INFO] Stopped by user (Ctrl+C).")
            final = json.loads(rec.FinalResult()).get("text", "").strip()
            if final:
                print(f"> {final}")

if __name__ == "__main__":
    main()