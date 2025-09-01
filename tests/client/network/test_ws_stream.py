"""Simple script for testing the WebSocket image stream.

Run this file directly to connect to the server, receive base64 encoded
frames, decode them and display the resulting images using OpenCV.
The stream continues until the user presses the ESC key or closes the
window.
"""

import base64
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "Client"
sys.path.insert(0, str(ROOT))


def main() -> None:
    """Connect to the server and display the streamed frames."""

    from network.ws_client import WebSocketClient
    import cv2  # Imported here to avoid dependency during test collection
    import numpy as np

    client = WebSocketClient()

    def on_frame(base64_frame: str) -> None:
        img_bytes = base64.b64decode(base64_frame)
        img_array = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame is not None:
            cv2.imshow("WebSocket Stream", frame)

    client.start_stream(on_frame)

    try:
        while True:
            # Exit if ESC pressed or the window has been closed.
            if cv2.waitKey(1) & 0xFF == 27:
                break
            if cv2.getWindowProperty("WebSocket Stream", cv2.WND_PROP_VISIBLE) < 1:
                break
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        client.stop_stream()
        client.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

