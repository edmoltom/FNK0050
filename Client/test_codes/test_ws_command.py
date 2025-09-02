from network.ws_client import WebSocketClient
import sys

"""Send arbitrary commands to the WebSocket server.

Examples:
    {"cmd": "ping"}
    {"cmd": "start", "interval": "1.0"}
    {"cmd": "stop"}
    {"cmd": "capture", "timeout": "2.0"}

Usage:
    python test_ws_command.py <cmd> [<key=value> ...]
    valid commands: ``ping``, ``start``, ``stop``, ``capture``
"""
def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python test_ws_command.py <cmd> [<key=value> ...]\n"
            "Valid commands: ping, start, stop, capture"
        )
        return

    cmd = sys.argv[1]
    args = dict(arg.split("=", 1) for arg in sys.argv[2:] if "=" in arg)
    command_data = {"cmd": cmd, **args}

    client = WebSocketClient()
    response = client.send_command(command_data)
    print(f"[Response] {response}")

if __name__ == "__main__":
    main()