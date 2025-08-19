# Piper TTS --- Low-Latency Robotic Presets (Linux/Raspberry Pi)

Quick guide to install and run **Piper TTS** with low-latency
"robotic/kawaii" style presets.

------------------------------------------------------------------------

## 1. Dependencies

``` bash
sudo apt update
sudo apt install -y python3 python3-pip sox alsa-utils
```

-   **sox**: audio effects (pitch, EQ, filters).\
-   **aplay** (alsa-utils): playback of `.wav` files.

------------------------------------------------------------------------

## 2. Install Piper TTS

``` bash
pip install --user piper-tts
```

If you encounter **PEP 668** restrictions on Raspberry Pi/Debian,
either:\
- Append `--break-system-packages` (not recommended long-term), or\
- Create a Python virtual environment with `python3 -m venv venv`.

------------------------------------------------------------------------

## 3. Download the Spanish Voice Model

In this repository we include the file:

    es-hikari-medium.onnx.zip

Unzip it in your Piper working directory. It will provide a good balance
between quality and latency.

------------------------------------------------------------------------

## 4. Basic Test

``` bash
echo "Hola, humano." | python3 -m piper -m es-hikari-medium.onnx -f out.wav
aplay out.wav
```

------------------------------------------------------------------------

## 5. Custom Script with Presets

Place `mishi_tts_fixed.py` in your Piper folder, make it executable:

``` bash
chmod +x mishi_tts_fixed.py
./mishi_tts_fixed.py --text "Tachikoma mode activated." --preset tachikoma_sharp
```

### Available Presets (low latency, no rubberband):

-   **ultra** → very fast, "walkie-talkie style".\
-   **tachikoma** → high-pitch with mild "helmet" filter (16 kHz).\
-   **tachikoma_plus** → sharper, 12 kHz band.\
-   **tachikoma_sharp** → extremely sharp/bright, wide band (16 kHz).

------------------------------------------------------------------------

## 6. Save to File

``` bash
./mishi_tts_fixed.py --text "Hello, world." --preset tachikoma_sharp --save output.wav
```

------------------------------------------------------------------------

## 7. Quick Tuning Tips

-   Higher pitch → use `tachikoma_sharp` preset or adjust
    `pitch`/`treble` in the script.\
-   More "helmet" effect → increase `highpass` (300--600 Hz), lower
    `lowpass` (2.8--3.6 kHz).\
-   Lower latency → choose `x_low` models, resample to 12--16 kHz, avoid
    rubberband.\
-   If distortion occurs → reduce `overdrive`/`treble` and lower system
    volume.

------------------------------------------------------------------------

✅ With this setup you can replicate installation and usage on any
Linux/Raspberry Pi machine.
