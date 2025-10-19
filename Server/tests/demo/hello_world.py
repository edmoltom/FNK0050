from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = PROJECT_ROOT / "Server"

for path in (PROJECT_ROOT, SERVER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from Server.interface.MovementControl import MovementControl


def main() -> None:
    """Simple hello world demonstrating MovementControl."""
    print("Hello!! (●'◡'●)")
    controller = MovementControl()
    controller.walk(1.0, 0.0, 0.0)

    for _ in range(20):
        controller.tick(0.1)
        time.sleep(0.1)

    controller.stop()


if __name__ == "__main__":
    main()
