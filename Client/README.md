# Client

The client package contains the GUI and networking front‑end for FNK0050. It connects to the server over WebSockets and offers a PyQt6‑based user interface.

## Running tests

Install `pytest` and optional dependencies such as `websockets` and `PyQt6`. The test suite provides an in‑process WebSocket server so no external hardware is required.

Run all client tests:

```bash
pytest tests/client
```

Run a single test module:

```bash
pytest tests/client/test_ws_ping.py
```

Client networking tests can read the target endpoint from the `SERVER_URI` environment variable:

```bash
SERVER_URI=ws://localhost:8765 pytest tests/client/test_ws_command.py
```
