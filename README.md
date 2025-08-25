# FNK0050

FNK0050 is a modular robotics platform split into a `Server` that controls hardware and AI capabilities and a `Client` that provides a GUI and network interface. The project also contains various tools for vision tuning and movement analysis.

## Running tests

The test suite is powered by [pytest](https://pytest.org). Install the optional dependencies such as `pytest`, `numpy`, `websockets`, and `PyQt6` to enable more tests. Hardware‑specific modules (gamepads, cameras, microphones, etc.) are imported with `pytest.importorskip` and will be skipped if the dependencies are missing.

Run the full suite:

```bash
pytest
```

Run only client tests:

```bash
pytest tests/client
```

Run a single test module:

```bash
pytest tests/test_ws_client_async.py
```

Some client network tests honour the `SERVER_URI` environment variable to pick the WebSocket endpoint:

```bash
SERVER_URI=ws://localhost:8765 pytest tests/client/test_ws_command.py
```

See [tests/README.md](tests/README.md) for more detailed guidance on running and targeting tests.
