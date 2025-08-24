"""Run client subsystems based on command line options or a config file."""

import argparse
import json
import app


def load_config(path: str) -> dict:
    """Load JSON configuration from *path* if provided."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description="Client runner")
    parser.add_argument("--gui", action="store_true", help="start graphical interface")
    parser.add_argument("--network", action="store_true", help="start network client only")
    parser.add_argument("--config", help="path to JSON configuration file")
    args = parser.parse_args()

    config = {}
    if args.config:
        config = load_config(args.config)

    gui_enabled = args.gui or config.get("gui", False)
    network_enabled = args.network or config.get("network", False)

    if gui_enabled and network_enabled:
        app.start_all()
    elif gui_enabled:
        app.start_gui()
    elif network_enabled:
        app.start_network()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
