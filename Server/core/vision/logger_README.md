# Vision logging

This directory contains `viz_logger.py`, a helper that records detector
artefacts and per-frame metrics to CSV.

## Enabling the logger
`VisionLogger` is disabled by default. To turn it on set environment variables
before launching your application:

```bash
VISION_LOG=1 python run.py
```

Optional variables:

* `VISION_LOG_STRIDE` – log every Nth frame (default: 5).
* `VISION_LOG_DIR` – output directory (default: `runs/vision/<timestamp>`).

Example:

```bash
VISION_LOG=1 VISION_LOG_STRIDE=10 VISION_LOG_DIR=/tmp/vision_logs python run.py
```

The helper `create_logger_from_env()` in `viz_logger.py` reads these variables
and returns a configured logger or `None` when logging is disabled.

## Notes for developers
`VisionLogger` lazily imports the vision API to avoid circular dependencies.
`VisionInterface` accepts an existing logger and delegates all logging work to
it via the API's `create_logger_from_env()` helper.
