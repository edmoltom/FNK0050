import asyncio
import socket
import json
import websockets

from app.application import Application
from app.controllers.robot_controller import RobotController

# Wire application services with the controller
_app = Application()
_controller = RobotController(_app.movement_service, _app.vision_service)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

async def handler(websocket):
    print("[WS] New client connected")
    async for message in websocket:
        try:
            data = json.loads(message)
            response = await _controller.handle(data)
            await websocket.send(json.dumps(response))

        except Exception as e:
            await websocket.send(json.dumps({"status": "error", "type": "text", "data": str(e)}))


async def start_ws_server_async():
    addr = get_local_ip()
    print(f"WebSocket listening in ws://{addr}:8765 ...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        try:
            await asyncio.Future()  # keep server running
        except asyncio.CancelledError:
            print("Server stopped with Ctrl+C.")
        finally:
            # parada limpia de los servicios
            _app.vision_service.stop()
            _app.movement_service.stop()


def start_ws_server():
    asyncio.run(start_ws_server_async())

