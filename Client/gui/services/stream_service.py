import asyncio

class StreamService:
    """High-level interface to fetch images from the server.

    The service delegates low-level communication to the provided
    ``client`` object which is expected to expose a ``send_command``
    coroutine or method.
    """

    def __init__(self, client):
        self.client = client

    def fetch_image(self):
        """Request a single image frame from the server.

        Returns the base64-encoded image data or ``None`` if the request
        fails.
        """
        send = getattr(self.client, "send_command", None)
        if send is None:
            return None

        if asyncio.iscoroutinefunction(send):
            response = asyncio.run(send({"cmd": "capture"}))
        else:
            response = send({"cmd": "capture"})

        if response and response.get("status") == "ok":
            return response.get("data")
        return None
