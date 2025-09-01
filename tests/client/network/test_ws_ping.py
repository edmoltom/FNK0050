from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3] / "Client"
sys.path.insert(0, str(ROOT))

from network.ws_client import WebSocketClient


def main():
    print("Testing WebSocket connection...")
    client = WebSocketClient()
    response = client.send_command({"cmd": "ping"})

    if response:
        print(f"[Response OK] {response}")
    else:
        print("[Response Failed] No response or connection error.")


if __name__ == "__main__":
    main()

