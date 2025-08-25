# Tests

This directory hosts the test suite for FNK0050.

## Prerequisites

* Python 3.10+
* [pytest](https://pytest.org)
* Optional libraries to enable additional tests: `numpy`, `websockets`, `PyQt6`, and hardware interfaces such as `Gamepad` or camera drivers. Tests use `pytest.importorskip` so missing optional dependencies simply cause the related tests to be skipped.
* The LLM subsystem can be mocked using [`tests/mock_llm.py`](mock_llm.py).

## Running the tests

Run the entire suite from the project root:

```bash
pytest
```

Only run client tests:

```bash
pytest tests/client
```

Run a specific server test module:

```bash
pytest tests/test_vision_system.py
```

## Targeting subsystems

* **Client network and GUI** – `pytest tests/client`
* **WebSocket client** – `pytest tests/test_ws_client_async.py`
* **Server core (vision, voice, etc.)** – run individual files under `tests/`

Use `-k` to filter further, e.g. `pytest -k vision`.

## Environment variables

Some client networking tests honour the `SERVER_URI` variable to select the WebSocket endpoint:

```bash
SERVER_URI=ws://localhost:8765 pytest tests/client/test_ws_command.py
```

## Hardware mocks

Hardware-dependent modules (gamepads, sensors, LEDs, microphones) are imported using `pytest.importorskip`. Without the actual hardware or libraries the tests will be skipped. Provide mocks or install the required libraries if you need those tests to run.
