
import asyncio
import websockets
import json
import base64
from io import BytesIO
from PIL import Image

from core.Camera import Camera

camera = Camera()
camera.start_periodic_capture(interval=1.0)

async def handler(websocket):

    print("[WS] New client connected")
    
    async for message in websocket:
        try:
            data = json.loads(message)
            cmd = data.get("cmd")
            if cmd == "capture":
                img_str = camera.get_last_processed_encoded()
                response = {
                    "status": "ok",
                    "type": "image",
                    "data": img_str
                }
            elif cmd == "set_mode":
                mode = data.get("mode")
                if mode:
                    camera.set_mode(mode)
                    response = {"status": "ok", "type": "text", "data": f"Mode set to {mode}"}
                else:
                    response = {"status": "error", "type": "text", "data": "No mode provided"}            
            else:
                response = {
                    "status": "error",
                    "type": "text",
                    "data": f"Unknown command: {cmd}"
                }
                
            await websocket.send(json.dumps(response))
        except Exception as e:
            await websocket.send(json.dumps({
                "status": "error",
                "type": "text",
                "data": str(e)
            }))

async def start_ws_server_async():

    print("WebSocket listening in ws://0.0.0.0:8765 ...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        try:
            await asyncio.Future()  # keep server running
        except asyncio.CancelledError:
            print("Server stopped with Ctrl+C.")

def start_ws_server():
    asyncio.run(start_ws_server_async())