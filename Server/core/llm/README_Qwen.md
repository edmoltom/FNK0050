# Qwen 2.5-0.5B Instruct --- Raspberry Pi 4 (8 GB) Setup Guide

This guide explains how to install and run a lightweight language model
(**Qwen 2.5-0.5B Instruct**, GGUF format, quantized Q3_K\_M) on a
Raspberry Pi 4 with 8 GB RAM.\
It is suitable for conversational agents (e.g. "chatty robot cat"
personality).

------------------------------------------------------------------------

## 1. Prepare the system

Update and install dependencies for compilation and networking:

``` bash
sudo apt update
sudo apt install -y git build-essential cmake libcurl4-openssl-dev python3-pip
```

------------------------------------------------------------------------

## 2. Clone and build llama.cpp (CMake build)

``` bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release -j4
```

The main binary will be created in:

    ~/llama.cpp/build/bin/llama-cli

------------------------------------------------------------------------

## 3. Download the Qwen 2.5-0.5B Instruct model (GGUF, Q3_K\_M)

Inside the `models` folder of llama.cpp:

``` bash
cd ~/llama.cpp/models
wget -O qwen2.5-0.5b-instruct-q3_k_m.gguf \  "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q3_k_m.gguf"
```

This quantization (`Q3_K_M`) is lightweight and fast, ideal for Pi 4
short replies.

------------------------------------------------------------------------

## 4. (Optional) Personality file

If you want to define a fixed personality, create:

``` bash
nano ~/llama.cpp/gato.txt
```

Example content:

    You are a talking cat named Mishi. Always reply in Spanish, in short sentences (max 1–2 lines), with a playful and slightly sarcastic tone. Do not give long explanations.

Save with `Ctrl+O`, exit with `Ctrl+X`.

------------------------------------------------------------------------

## 5. Run the model

From `~/llama.cpp/build`:

``` bash
./bin/llama-cli \  -m ../models/qwen2.5-0.5b-instruct-q3_k_m.gguf \  -t 2 -c 256 --temp 0.9 --repeat-penalty 1.05 \  -f ../gato.txt
```

If you don't use `gato.txt`, omit the `-f` argument and type the initial
prompt manually.

**Key parameters:** - `-t 2` → use 2 threads, leaving CPU resources for
other processes.\
- `-c 256` → short context for speed and reduced RAM use.\
- `--temp 0.9` → adds creativity.\
- `--repeat-penalty 1.05` → prevents annoying repetition.

------------------------------------------------------------------------

## 6. Interactive use

-   Type your message and press `Enter`.\
-   To interrupt a response: `Ctrl+C`.\
-   To exit: `Ctrl+D` or double `Ctrl+C`.

------------------------------------------------------------------------

## 7. Tips

-   If responses slow down after many turns, restart the process.\
-   Try smaller quantizations (`q2_k`) for more speed, or larger
    (`q4_k_m`) for higher quality.\
-   The `.gguf` model file can be copied to any other machine without
    recompilation.

------------------------------------------------------------------------

## 8. Troubleshooting

**Error:**
`The Makefile build is deprecated. Use the CMake build instead.`\
→ Solution: use the CMake method described in section 2.

**Error:** `Could NOT find CURL` during CMake.\
→ Solution: install the library:

``` bash
sudo apt install libcurl4-openssl-dev
```

**Error:** `externally-managed-environment` when installing Python
packages.\
→ Quick fix: append `--break-system-packages` to pip, e.g.:

``` bash
pip install -U huggingface_hub --break-system-packages
```

Or use a virtual environment:

``` bash
python3 -m venv ~/venvs/hf
source ~/venvs/hf/bin/activate
pip install -U huggingface_hub
```

**Error:** Model download returns 404 or empty file.\
→ Check the exact filename on Hugging Face, use direct URL as above.

**Error:** Responses are very slow.\
→ Reduce context (`-c 128`), use lighter quantization (`q2_k`), or lower
temperature.

------------------------------------------------------------------------

## 9. Credits

-   [llama.cpp](https://github.com/ggerganov/llama.cpp)\
-   [Qwen2.5-0.5B-Instruct-GGUF on Hugging
    Face](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)
