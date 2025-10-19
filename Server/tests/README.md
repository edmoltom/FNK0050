# Test and demo layout

This directory centralizes the automated tests and exploratory scripts for the
Lumo server stack. The subdirectories follow a simple convention:

- `unit/` – Focused pytest modules that exercise individual classes or
  functions with the help of stubs and fakes. They run quickly and do not rely
  on external services or hardware.
- `integration/` – Higher level pytest scenarios that stitch together multiple
  components (e.g. builders, runtimes, background processes). These tests may
  spin up subprocesses or threads but avoid direct hardware access by using
  mocks and fixtures.
- `demo/` – Stand‑alone scripts intended for manual exploration such as
  driving hardware with a gamepad or running the conversation loop. Each file
  can be executed directly, for example `python Server/tests/demo/demo_gamepad.py`.

To run the automated suite from the repository root:

```bash
pytest Server/tests/unit      # fast unit feedback
pytest Server/tests/integration
```

All subpackages include an `__init__.py` so imports resolve without modifying
`PYTHONPATH`, and `conftest.py` bootstraps the required search paths when the
suite is executed.
