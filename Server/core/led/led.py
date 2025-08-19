import time
from .spi_ledpixel import Freenove_SPI_LedPixel

class Led:
    """
    Minimal LED wrapper for Freenove Robot Dog (PCB v2, SPI backend).
    Keeps a tiny API: ledIndex(i,r,g,b), colorWipe([r,g,b], wait_ms), set_all([r,g,b]),
    off(), show(), close().
    """
    def __init__(self, count=8, brightness=255, sequence='GRB', bus=0, device=0):
        # PCB v2 uses SPI MOSI (GPIO10). No rpi_ws281x fallback here.
        self.strip = Freenove_SPI_LedPixel(
            count=count,
            bright=brightness,
            sequence=sequence,
            bus=bus,
            device=device
        )

    # --- Basic ops ------------------------------------------------------------
    def ledIndex(self, index, R, G, B):
        """Set one LED color (no auto-show)."""
        if hasattr(self.strip, "set_led_color"):
            self.strip.set_led_color(index, int(R), int(G), int(B))
        else:
            # Fallback naming, if library differs
            self.strip.setPixelColor(index, [int(R), int(G), int(B)])

    def set_all(self, color):
        """Set all LEDs to color [R,G,B] (no auto-show)."""
        R, G, B = map(int, color)
        if hasattr(self.strip, "set_all_led_color"):
            self.strip.set_all_led_color(R, G, B)
        else:
            for i in range(self.count()):
                self.ledIndex(i, R, G, B)

    def show(self):
        """Flush SPI buffer to LEDs."""
        if hasattr(self.strip, "led_show"):
            self.strip.led_show()
        else:
            self.strip.show()

    def off(self):
        """Turn all LEDs off and show."""
        self.set_all([0, 0, 0])
        self.show()

    def close(self):
        """Close SPI device."""
        if hasattr(self.strip, "led_close"):
            self.strip.led_close()

    def count(self):
        """Return LED count if available, else 8."""
        return getattr(self.strip, "led_count", 8)

    # --- Convenience patterns -------------------------------------------------
    def colorWipe(self, color, wait_ms=10):
        """Fill progressively with color [R,G,B]."""
        R, G, B = map(int, color)
        for i in range(self.count()):
            self.ledIndex(i, R, G, B)
            self.show()
            time.sleep(wait_ms / 1000.0)

    # (Optional) simple rainbow, lightweight
    def rainbow(self, wait_ms=10):
        for j in range(256):
            for i in range(self.count()):
                r, g, b = self._wheel((i + j) & 255)
                self.ledIndex(i, r, g, b)
            self.show()
            time.sleep(wait_ms / 1000.0)

    def rainbowCycle(self, wait_ms=10, cycles=1):
        n = self.count()
        for j in range(256 * cycles):
            for i in range(n):
                r, g, b = self._wheel((int(i * 256 / n) + j) & 255)
                self.ledIndex(i, r, g, b)
            self.show()
            time.sleep(wait_ms / 1000.0)

    # --- Utils ----------------------------------------------------------------
    @staticmethod
    def _wheel(pos):
        """Generate rainbow colors across 0-255."""
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)