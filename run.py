"""Server entry point."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SERVER_DIR = ROOT / "Server"
CORE_DIR = SERVER_DIR / "core"
for path in (str(SERVER_DIR), str(CORE_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from Server.app.application import Application


def main() -> None:
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
