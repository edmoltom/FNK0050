from __future__ import annotations

"""Entry point for starting server subsystems."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .app import create_app


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Server runner")
    parser.add_argument("-c", "--config", type=Path, help="JSON configuration file")
    parser.add_argument("--voice", action="store_true", help="Enable voice subsystem")
    parser.add_argument("--vision", action="store_true", help="Enable vision subsystem")
    args = parser.parse_args()

    cfg: Dict[str, Any] = {}
    if args.config:
        cfg.update(load_config(args.config))
    if args.voice:
        cfg["voice"] = True
    if args.vision:
        cfg["vision"] = True

    create_app(cfg)


if __name__ == "__main__":
    main()
