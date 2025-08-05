
import asyncio
import websockets
import json
import base64

async def main():
    uri = "ws://192.168.1.135:8765"
    async with websockets.connect(uri) as websocket:
        request = {
            "cmd": "capture",
            "args": {}
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        response_data = json.loads(response)

        if response_data["status"] == "ok" and response_data["type"] == "image":
            img_data = base64.b64decode(response_data["data"])
            with open("output.jpg", "wb") as f:
                f.write(img_data)
            print("Imagen recibida y guardada como output.jpg")
        else:
            print("Respuesta del servidor:", response_data)

asyncio.run(main())
