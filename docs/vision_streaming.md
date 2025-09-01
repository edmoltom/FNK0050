# Vision Streaming

The server exposes a simple WebSocket API for pushing processed vision frames
from the robot to remote clients.  After connecting to the socket, clients send
commands encoded as JSON objects.

## Commands

- `stream_start` – begin the continuous stream of processed frames. The server
  responds with `{ "status": "ok", "type": "text", "data": "streaming started" }`
  and subsequently pushes frame messages.
- `stream_stop` – stop the stream. The server replies with
  `{ "status": "ok", "type": "text", "data": "streaming stopped" }` and ceases
  sending frames.

## Frame messages

Each frame is sent as a JSON object with the following shape:

```json
{ "type": "image", "data": "<base64 JPEG>" }
```

The `data` field contains a base64‑encoded JPEG produced by the vision
pipeline. Clients must decode this value before rendering.

## Example clients

### Python

```python
import asyncio
import base64
import cv2
import numpy as np
import websockets
import json

async def main():
    async with websockets.connect("ws://localhost:8765") as ws:
        await ws.send('{"cmd": "stream_start"}')
        while True:
            msg = await ws.recv()
            frame = json.loads(msg)
            if frame.get("type") != "image":
                print(frame)
                continue
            img = base64.b64decode(frame["data"])
            arr = np.frombuffer(img, dtype=np.uint8)
            cv2.imshow("Vision", cv2.imdecode(arr, cv2.IMREAD_COLOR))
            if cv2.waitKey(1) == 27:  # ESC to quit
                await ws.send('{"cmd": "stream_stop"}')
                break

asyncio.run(main())
```

### JavaScript

```html
<canvas id="viewer" width="640" height="480"></canvas>
<script>
const canvas = document.getElementById('viewer');
const ctx = canvas.getContext('2d');
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => ws.send(JSON.stringify({cmd: 'stream_start'}));
ws.onmessage = ev => {
  const msg = JSON.parse(ev.data);
  if (msg.type !== 'image') {
    console.log(msg);
    return;
  }
  const img = new Image();
  img.onload = () => ctx.drawImage(img, 0, 0);
  img.src = 'data:image/jpeg;base64,' + msg.data;
};
</script>
```

These snippets open the WebSocket, request streaming and render each frame. Send
`{"cmd": "stream_stop"}` to halt the feed and release resources.
