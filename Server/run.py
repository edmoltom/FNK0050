from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

for relative_path in ("app", "core", "lib", "network", "test_codes"):
    folder_path = PROJECT_ROOT / relative_path
    if folder_path.exists():
        folder_path_str = str(folder_path)
        if folder_path_str not in sys.path:
            sys.path.insert(0, folder_path_str)

from app.application import main as app_main


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the server runtime")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Ruta al archivo JSON de configuración de la aplicación.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.config:
        app_main(config_path=args.config)
    else:
        app_main()


if __name__ == "__main__":
    main()
