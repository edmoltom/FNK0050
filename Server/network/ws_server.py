import asyncio
import socket
import json
import time
import websockets

from core.Camera import Camera
from core.vision import api as vision_api

camera = Camera()
camera.start_periodic_capture(interval=1.0)  # sigue autoarrancando; si prefieres lazy, quita esta línea


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def wait_for_frame(timeout=3.0, poll=0.05):
    """Wait until timeout for the camera to have a processed frame."""
    deadline = time.monotonic() + float(timeout)
    img_str = camera.get_last_processed_encoded()
    while img_str is None and time.monotonic() < deadline:
        await asyncio.sleep(poll)
        img_str = camera.get_last_processed_encoded()
    return img_str


async def handler(websocket):
    print("[WS] New client connected")
    async for message in websocket:
        try:
            data = json.loads(message)
            cmd = data.get("cmd")
            if cmd == "ping":
                response = {"status": "ok", "type": "text", "data": "pong"}

            elif cmd == "start":
                interval = float(data.get("interval", 1.0))
                camera.start_periodic_capture(interval=interval)
                response = {"status": "ok", "type": "text", "data": f"capture started @ {interval}s"}

            elif cmd == "stop":
                camera.stop_periodic_capture()
                response = {"status": "ok", "type": "text", "data": "capture stopped"}

            elif cmd == "capture":
                # intenta devolver frame; si aún no hay, espera un poco
                img_str = await wait_for_frame(timeout=float(data.get("timeout", 2.0)))
                if img_str is None:
                    response = {"status": "wait", "type": "text", "data": "no frame yet"}
                else:
                    response = {"status": "ok", "type": "image", "data": img_str}

            elif cmd == "process":
                # filtra solo claves conocidas; pasa al pipeline vía set_processing_config
                allowed = {"blur", "edges", "contours", "ref_size"}
                config = {k: v for k, v in data.items() if k in allowed}
                camera.set_processing_config(config)
                response = {"status": "ok", "type": "text", "data": "processing config updated"}

            elif cmd == "load_profile":
                which = data.get("which", "big")
                path = data.get("path")
                vision_api.load_profile(which, path)
                response = {"status": "ok", "type": "text", "data": f"profile {which} loaded"}

            elif cmd == "dynamic":
                which = data.get("which", "big")
                params = data.get("params", {})
                vision_api.update_dynamic(which, params)
                response = {"status": "ok", "type": "text", "data": "dynamic params updated"}

            else:
                response = {"status": "error", "type": "text", "data": f"unknown command: {cmd}"}

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
            # parada limpia de la cámara
            camera.stop_periodic_capture()


def start_ws_server():
    asyncio.run(start_ws_server_async())

