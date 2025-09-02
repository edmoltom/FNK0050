from __future__ import annotations
import asyncio, json, socket, time
from typing import Callable, Optional
import websockets
from Server.App.services.vision_service import VisionService

async def _wait_for_frame(svc: VisionService, timeout=3.0, poll=0.05) -> Optional[str]:
    deadline = time.monotonic() + float(timeout)
    img = svc.last_b64()
    while img is None and time.monotonic() < deadline:
        await asyncio.sleep(poll)
        img = svc.last_b64()
    return img

def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def make_handler(svc: VisionService) -> Callable:
    async def handler(ws):
        print("[WS] client connected")
        async for message in ws:
            try:
                data = json.loads(message)
                cmd = data.get("cmd")

                if cmd == "ping":
                    resp = {"status": "ok", "type": "text", "data": "pong"}
                elif cmd == "start":
                    interval = float(data.get("interval", 1.0))
                    svc.start(interval_sec=interval)
                    resp = {"status": "ok", "type": "text", "data": f"capture started (interval={interval}s)"}
                elif cmd == "stop":
                    svc.stop()
                    resp = {"status": "ok", "type": "text", "data": "capture stopped"}
                elif cmd == "capture":
                    img = await _wait_for_frame(svc, float(data.get("timeout", 2.0)))
                    resp = {"status": "ok" if img else "wait",
                            "type": "image" if img else "text",
                            "data": img or "no frame yet"}
                elif cmd == "process":
                    svc.set_processing(data)
                    resp = {"status": "ok", "type": "text", "data": "processing updated"}
                else:
                    resp = {"status": "error", "type": "text", "data": f"unknown command: {cmd}"}

                await ws.send(json.dumps(resp))
            except Exception as e:
                await ws.send(json.dumps({"status": "error", "type": "text", "data": str(e)}))
    return handler

async def start_ws_server_async(svc: VisionService, host: str = "0.0.0.0", port: int = 8765) -> None:
    addr = _get_local_ip()
    print(f"WebSocket listening at ws://{addr}:{port} ...")
    async with websockets.serve(make_handler(svc), host, port):
        try:
            await asyncio.Future()
        finally:
            pass

def start_ws_server(svc: VisionService, host: str = "0.0.0.0", port: int = 8765) -> None:
    asyncio.run(start_ws_server_async(svc, host=host, port=port))
