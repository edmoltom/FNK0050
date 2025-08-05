
import asyncio
import websockets
import json
import base64
from io import BytesIO
from PIL import Image

async def handler(websocket):
    async for message in websocket:
        try:
            data = json.loads(message)
            cmd = data.get("cmd")
            if cmd == "capture":
                # Imagen de prueba en blanco de 100x100 píxeles
                img = Image.new('RGB', (100, 100), color = (255, 255, 255))
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                response = {
                    "status": "ok",
                    "type": "image",
                    "data": img_str
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
    print("Servidor WebSocket escuchando en ws://0.0.0.0:8765 ...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # mantener el servidor corriendo

def start_ws_server():
    asyncio.run(start_ws_server_async())