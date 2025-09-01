import asyncio
import socket
import json
import websockets

from app.application import Application
from app.controllers.robot_controller import RobotController

# Wire application services with the controller
_app = Application()
_controller = RobotController(_app.movement_service, _app.vision_service)

# Track websockets currently receiving vision frames
_streaming_clients: set[websockets.WebSocketServerProtocol] = set()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def _vision_stream(websocket: websockets.WebSocketServerProtocol) -> None:
    """Continuously push vision frames to a websocket client."""
    interval = getattr(getattr(_app.config, "vision", _app.config), "stream_interval", 0.0)
    try:
        stream = (
            _controller._vision.stream(interval_sec=interval)
            if _controller._vision
            else iter(())
        )
        while websocket in _streaming_clients:
            frame = next(stream, None)
            if frame:
                await websocket.send(json.dumps({"type": "image", "data": frame}))
    except websockets.ConnectionClosed:
        pass
    finally:
        _streaming_clients.discard(websocket)


async def handler(websocket):
    print("[WS] New client connected")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                cmd = data.get("cmd")

                if cmd == "stream_start":
                    if websocket not in _streaming_clients:
                        _streaming_clients.add(websocket)
                        asyncio.create_task(_vision_stream(websocket))
                    response = await _controller.handle(data)

                elif cmd == "stream_stop":
                    _streaming_clients.discard(websocket)
                    response = await _controller.handle(data)

                else:
                    response = await _controller.handle(data)

                await websocket.send(json.dumps(response))

            except Exception as e:
                await websocket.send(json.dumps({"status": "error", "type": "text", "data": str(e)}))
    finally:
        _streaming_clients.discard(websocket)


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

