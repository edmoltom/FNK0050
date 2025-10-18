from __future__ import annotations

import logging
import os

from app.builder import build
from app.logging_utils.logging_config import setup_logging
from app.runtime import AppRuntime


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "app.json")


def main(config_path: str = CONFIG_PATH) -> None:
    setup_logging()
    services = build(config_path=config_path)
    runtime = AppRuntime(services)
    app_logger = logging.getLogger("app.application")

    try:
        runtime.start()
    except KeyboardInterrupt:
        app_logger.info("[APP] Ctrl-C received, shutting down...")
    finally:
        try:
            runtime.stop()
        except Exception as exc:  # pragma: no cover - defensive
            app_logger.exception("[APP] Error during shutdown: %s", exc)


if __name__ == "__main__":
    main()
    