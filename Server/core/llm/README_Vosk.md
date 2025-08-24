# Speech-to-Text with Vosk

This guide explains how to set up **Vosk** on a Raspberry Pi to convert microphone input into text in real time. It uses the lightweight **Spanish small model** (~50 MB) to ensure good performance on constrained hardware.

---

## Installation

1. Update packages and install dependencies:

```bash
sudo apt update
sudo apt install -y python3-pip python3-pyaudio portaudio19-dev
```

2. Install Python packages:

```bash
pip install --break-system-packages vosk sounddevice
```

3. Download the Vosk small Spanish model:

```bash
mkdir -p ~/vosk && cd ~/vosk
wget -O vosk-model-small-es-0.42.zip   https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip
```

The model will be located in:
```
/home/user/vosk/vosk-model-small-es-0.42
```

---

## Test Script

Save the following script as `stt_vosk_test.py`:

```python
#!/usr/bin/env python3
import json, queue, sys
from pathlib import Path
import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_DIR = Path("/home/user/vosk/vosk-model-small-es-0.42")
SAMPLE_RATE = 16000
CHANNELS = 1
INPUT_DEVICE = None  # Use default mic, change index if needed

def main():
    if not MODEL_DIR.exists():
        sys.exit(f"[ERROR] Vosk model not found: {MODEL_DIR}")

    model = Model(str(MODEL_DIR))
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    rec.SetWords(True)

    q = queue.Queue()

    def cb(indata, frames, time, status):
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
                    if txt:
                        print(f"> {txt}")
        except KeyboardInterrupt:
            print("\n[INFO] Stopped by user.")
            final = json.loads(rec.FinalResult()).get("text", "").strip()
            if final:
                print(f"> {final}")

if __name__ == "__main__":
    main()
```

Make it executable:

```bash
chmod +x stt_vosk_test.py
```

Run it:

```bash
python3 stt_vosk_test.py
```

Speak into your USB microphone. Detected text will be printed in the terminal.

---

## Notes

- Run `python3 -c "import sounddevice as sd; print(sd.query_devices())"` to check microphone indexes if needed.
- The small Spanish model (`~50 MB`) is optimized for speed. For higher accuracy, larger models (up to 1.8 GB) are available, but may run slower on a Raspberry Pi.
- This STT module will later be integrated into the robot’s pipeline:  
  **Voice input → LLM → Text-to-Speech output**.
