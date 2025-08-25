import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from led.led import Led


class LedController:
    """Async wrapper around :class:`Led` providing non-blocking operations."""

    def __init__(self, loop=None, count=8, brightness=255, max_workers=1, use_queue=True):
        self.loop = loop or asyncio.get_event_loop_policy().get_event_loop()
        self.executor = (
            ThreadPoolExecutor(max_workers=max_workers) if max_workers else None
        )
        self.led = Led(count=count, brightness=brightness)
        self._queue = asyncio.Queue() if use_queue else None
        self._worker_task = None
        if self._queue:
            self._worker_task = self.loop.create_task(self._worker())
        self._anim_task = None
        self._anim_stop = None

    async def _run(self, func, *args, **kwargs):
        """Run blocking LED function in a thread."""
        bound = partial(func, *args, **kwargs)
        if self.executor:
            return await self.loop.run_in_executor(self.executor, bound)
        return await asyncio.to_thread(bound)

    async def _worker(self):
        """Consume queued LED commands sequentially."""
        while True:
            func, args, kwargs = await self._queue.get()
            if func is None:
                break
            try:
                await self._run(func, *args, **kwargs)
            finally:
                self._queue.task_done()

    async def _enqueue(self, func, *args, **kwargs):
        """Enqueue a LED operation or run immediately if no queue."""
        if self._queue:
            await self._queue.put((func, args, kwargs))
        else:
            self.loop.create_task(self._run(func, *args, **kwargs))

    async def _start_anim(self, coro):
        """Launch ``coro`` as animation, cancelling any previous one."""

        # Cancel previous animation if one is running
        await self.stop_animation()
        self._anim_stop = asyncio.Event()
        self._anim_task = self.loop.create_task(coro)

    # Public API --------------------------------------------------------------

    async def set_all(self, color):
        """Set all LEDs to ``color`` and update the strip."""
        await self._enqueue(self.led.set_all, color)
        await self._enqueue(self.led.show)

    async def off(self):
        """Turn off all LEDs."""
        await self._enqueue(self.led.off)

    async def color_wipe(self, color, wait_ms=10):
        """Fill the strip color-by-color with ``color``."""
        await self._enqueue(self.led.colorWipe, color, wait_ms)

    async def rainbow(self, wait_ms=10):
        """Display a moving rainbow animation."""
        await self._enqueue(self.led.rainbow, wait_ms)

    async def rainbow_cycle(self, wait_ms=10, cycles=1):
        """Show ``cycles`` of rainbow cycle animation."""
        await self._enqueue(self.led.rainbowCycle, wait_ms, cycles)

    async def stop_animation(self):
        """Request any running animation coroutine to finish."""
        if self._anim_task:
            if self._anim_stop:
                self._anim_stop.set()
            try:
                await self._anim_task
            except asyncio.CancelledError:
                pass
            self._anim_task = None
            self._anim_stop = None

    async def start_pulsed_wipe(self, color, wait_ms=10, pause_ms=120, off_ms=120):
        """Start a repeating wipe animation that pulses on and off."""

        async def _loop():
            # Loop until ``_anim_stop`` is set by :meth:`stop_animation`
            while not self._anim_stop.is_set():
                await self._run(self.led.off)
                await self._run(self.led.colorWipe, color, wait_ms)
                await asyncio.sleep(pause_ms / 1000)
                await self._run(self.led.off)
                await asyncio.sleep(off_ms / 1000)

        await self._start_anim(_loop())

    async def close(self):
        """Stop worker, turn off LEDs and release resources."""
        await self.stop_animation()
        await self.off()
        if self._queue:
            await self._queue.join()
            await self._queue.put((None, (), {}))
            if self._worker_task:
                await self._worker_task
        if self.executor:
            self.executor.shutdown(wait=False)
        self.led.close()
