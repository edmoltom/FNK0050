from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3] / "Client"
sys.path.insert(0, str(ROOT))

from network.ws_client import WebSocketClient

"""
    Some examples:

    {"cmd": "procces", "blur": "true/false", "edges": "true/false", "contours": "true/false"   }
    e.g. \\ python run.py process blur=true edges=true contours=true

"""

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_command_sender.py <cmd> [<key=value> ...]")
        return

    cmd = sys.argv[1]
    args = dict(arg.split("=", 1) for arg in sys.argv[2:] if "=" in arg)
    command_data = {"cmd": cmd, **args}

    client = WebSocketClient()
    response = client.send_command(command_data)
    print(f"[Response] {response}")


if __name__ == "__main__":
    main()

