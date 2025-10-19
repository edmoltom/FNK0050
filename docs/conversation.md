# Conversation quickstart

This guide summarises the steps required to exercise the conversation pipeline before deploying it
on the physical robot.

## Requirements

- **Audio in/out**: a microphone recognised by ALSA/PulseAudio and speakers or headphones.
- **LLM model**: a llama.cpp-compatible `GGUF` file accessible from the server.
- **Binary**: the `llama-server` binary compiled for your platform (AVX/NEON/CUDA as appropriate).

## Configuration

`Server/app/app.json` contains a `conversation` section. The most relevant fields are:

```json
{
  "conversation": {
    "enable": true,
    "llama_binary": "/path/to/llama-server",
    "model_path": "/path/to/model.gguf",
    "port": 9090,
    "threads": 4,
    "health_timeout": 30.0,
    "health_check_interval": 0.5,
    "health_check_max_retries": 3,
    "health_check_backoff": 2.0,
    "llm_base_url": "http://127.0.0.1:9090",
    "max_parallel_inference": 1
  }
}
```

- Set `enable` to `false` to skip the whole stack (useful in CI or when the model is unavailable).
- Adjust `threads` and `max_parallel_inference` according to the host CPU.
- When the runtime cannot find the binary or the model path it disables conversation automatically
  and stores the reason in `AppServices.conversation_disabled_reason`.

## Running the stack

1. Launch the server with logging enabled:
   ```bash
   python Server/run.py --config Server/app/app.json
   ```
2. Speak one of the wake words (default: “humo”). LEDs should switch to the *listen* state.
3. Ask a short question. The runtime pauses Speech-to-Text while the LLM is generating a reply,
   plays the answer through Text-to-Speech, and then resumes listening.

## Troubleshooting

- **Binary fails to start** – ensure it has execute permissions and that all shared libraries are
  present (`ldd llama-server`).
- **Health checks timing out** – increase `health_timeout` or decrease `health_check_interval` and
  `health_check_backoff`.
- **No audio output** – double-check ALSA/PulseAudio devices and that no other process is locking the
  audio sink.
- **Want to avoid heavy dependencies in tests** – either disable conversation in the config or rely
  on `pytest Server/tests/test_app_runtime_conversation_integration.py`, which uses mocks for STT,
  TTS, and the llama process.
