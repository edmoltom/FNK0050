# Server

The server package implements the hardware and AI back‑end for FNK0050. It covers vision, movement, voice interaction and LLM integration, and communicates with clients via WebSockets.

## Running tests

Install `pytest` and any optional dependencies for the subsystems you want to exercise: `numpy` for vision, hardware drivers such as `Gamepad` or LED controllers, etc. Tests use `pytest.importorskip` so missing dependencies result in skipped tests rather than failures.

Example server tests:

```bash
pytest tests/test_vision_system.py
pytest tests/test_led.py
```

Target a specific subsystem:

```bash
pytest tests/test_voice_interface.py
```

The LLM component can be replaced by the in‑memory mock found in [`tests/mock_llm.py`](../tests/mock_llm.py).
