from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Server"))
sys.path.insert(0, str(ROOT))

from network.ws_server import start_ws_server


def main():
    print("Starting WebSocket server...")
    start_ws_server()


if __name__ == "__main__":
    main()

