import asyncio
import websockets
import json
import sys

async def send_command(uri, command_data):
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(command_data))
            response = await websocket.recv()
            print(f"[Response] {response}")
    except Exception as e:
        print(f"[Error] {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_command_sender.py <cmd> [<key=value> ...]")
        return

    cmd = sys.argv[1]
    args = dict(arg.split("=", 1) for arg in sys.argv[2:] if "=" in arg)

    command_data = {"cmd": cmd, **args}
    uri = "ws://192.168.1.135:8765"

    asyncio.run(send_command(uri, command_data))

if __name__ == "__main__":
    main()
