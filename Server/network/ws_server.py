import asyncio
import websockets
import socket
import json

from core.Camera import Camera

camera = Camera()
camera.start_periodic_capture(interval=1.0)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

async def handler(websocket):

    print("[WS] New client connected")
    
    async for message in websocket:
        try:
            data = json.loads(message)
            cmd = data.get("cmd")
            if cmd == "ping":
                response = {
                    "status": "ok",
                    "type": "text",
                    "data": "pong"
                }
            elif cmd == "capture":
                img_str = camera.get_last_processed_encoded()
                response = {
                    "status": "ok",
                    "type": "image",
                    "data": img_str
                }
            elif cmd == "process":
                config = {k: v for k, v in data.items() if k in ["blur", "edges", "contours"]}
                camera.set_processing_config(config)
                response = {
                    "status": "ok",
                    "type": "text",
                    "data": "Processing config updated"
                }            
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

    print(f"WebSocket listening in ws://{get_local_ip()}:8765 ...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        try:
            await asyncio.Future()  # keep server running
        except asyncio.CancelledError:
            print("Server stopped with Ctrl+C.")

def start_ws_server():
    asyncio.run(start_ws_server_async())