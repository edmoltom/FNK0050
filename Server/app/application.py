from __future__ import annotations

import os

from app.builder import build
from app.logging_utils.logging_config import setup_logging
from app.runtime import AppRuntime


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "app.json")


def main(config_path: str = CONFIG_PATH) -> None:
    setup_logging()
    services = build(config_path=config_path)
    runtime = AppRuntime(services)
    runtime.start()


if __name__ == "__main__":
    main()
    