"""Server entry point."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

from app.application import Application


def main() -> None:
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
