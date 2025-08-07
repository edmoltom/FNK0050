from network.ws_client import WebSocketClient
import sys

"""
    Some examples:
        
    {"cmd": "set_mode", "mode": "blur"} -> python run.py set_mode mode=blur 
    {"cmd": "set_mode", "mode": "edges"}
    {"cmd": "set_mode", "mode": "original"}

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