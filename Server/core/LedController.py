import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from led.led import Led


class LedController:
    """Async wrapper around :class:`Led` providing non-blocking operations."""

    def __init__(self, count=8, brightness=255, max_workers=1, use_queue=True):
        self.loop = asyncio.get_running_loop()
        self.executor = (
            ThreadPoolExecutor(max_workers=max_workers) if max_workers else None
        )
        self.led = Led(count=count, brightness=brightness)
        self._queue = asyncio.Queue() if use_queue else None
        self._worker_task = None
        if self._queue:
            self._worker_task = self.loop.create_task(self._worker())

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

    # Public API --------------------------------------------------------------

    async def set_all(self, color):
        await self._enqueue(self.led.set_all, color)
        await self._enqueue(self.led.show)

    async def off(self):
        await self._enqueue(self.led.off)

    async def color_wipe(self, color, wait_ms=10):
        await self._enqueue(self.led.colorWipe, color, wait_ms)

    async def rainbow(self, wait_ms=10):
        await self._enqueue(self.led.rainbow, wait_ms)

    async def rainbow_cycle(self, wait_ms=10, cycles=1):
        await self._enqueue(self.led.rainbowCycle, wait_ms, cycles)

    async def close(self):
        """Stop worker, turn off LEDs and release resources."""
        await self.off()
        if self._queue:
            await self._queue.join()
            await self._queue.put((None, (), {}))
            if self._worker_task:
                await self._worker_task
        if self.executor:
            self.executor.shutdown(wait=False)
        self.led.close()
