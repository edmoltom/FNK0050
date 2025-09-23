from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Iterable, Sequence

from core.llm.llama_server_process import LlamaServerProcess
from core.llm.llm_client import LlamaClient


_NotReadyCallback = Callable[[], None]
_ExitCallback = Callable[[int | None], None]


class ConversationService:
    """Coordinate the llama-server process and readiness lifecycle."""

    def __init__(
        self,
        *,
        process: LlamaServerProcess,
        client: LlamaClient,
        llm_base_url: str | None = None,
        health_timeout: float = 5.0,
        health_check_interval: float = 0.5,
        health_check_max_retries: int = 3,
        health_check_backoff: float = 2.0,
        auto_restart: bool = False,
        watchdog_interval: float | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._process = process
        self._client = client
        self._llm_base_url = llm_base_url or client.base_url
        self._health_timeout = health_timeout
        self._health_check_interval = max(0.05, health_check_interval)
        self._health_check_max_retries = max(0, health_check_max_retries)
        self._health_check_backoff = max(1.0, health_check_backoff)
        self._auto_restart = auto_restart
        self._watchdog_interval = watchdog_interval or self._health_check_interval
        self._logger = logger or logging.getLogger(__name__)

        self._ready_event = threading.Event()
        self._stop_event = threading.Event()

        self._not_ready_callbacks: list[_NotReadyCallback] = []
        self._exit_callbacks: list[_ExitCallback] = []

        self._watchdog_thread: threading.Thread | None = None
        self._health_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    @property
    def llm_client(self) -> LlamaClient:
        return self._client

    def __getattr__(self, name: str):  # pragma: no cover - delegation helper
        return getattr(self._client, name)

    def add_not_ready_callback(self, callback: _NotReadyCallback) -> None:
        self._not_ready_callbacks.append(callback)

    def add_exit_callback(self, callback: _ExitCallback) -> None:
        self._exit_callbacks.append(callback)

    def start(self) -> None:
        if self._process.is_running():
            return

        self._logger.info("Starting conversation llama-server process")
        self._stop_event.clear()
        self._ready_event.clear()

        self._process.start()
        self._start_health_monitor()
        self._ensure_watchdog()

    def stop(self) -> None:
        self._logger.info("Stopping conversation llama-server process")
        self._stop_event.set()
        self._ready_event.clear()
        self._process.terminate()
        self._join_thread(self._watchdog_thread)
        self._watchdog_thread = None
        self._join_thread(self._health_thread)
        self._health_thread = None

    def wait_for_ready(self, timeout: float | None = None) -> bool:
        return self._ready_event.wait(timeout)

    def restart(self) -> None:
        self.stop()
        self.start()

    # ------------------------------------------------------------------
    def query(self, messages: Sequence[dict], **kwargs):
        self.wait_for_ready(timeout=self._health_timeout)
        return self._client.query(messages, **kwargs)

    # Internal helpers --------------------------------------------------
    def _ensure_watchdog(self) -> None:
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return

        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def _start_health_monitor(self) -> None:
        if self._health_thread and self._health_thread.is_alive():
            return

        self._health_thread = threading.Thread(target=self._monitor_readiness, daemon=True)
        self._health_thread.start()

    def _monitor_readiness(self) -> None:
        while not self._stop_event.is_set():
            if not self._process.is_running():
                self._ready_event.clear()
                return

            try:
                ready = self._process.wait_ready(timeout=min(self._health_check_interval, 0.5))
            except RuntimeError:
                self._ready_event.clear()
                return

            if not ready:
                continue

            if not self._llm_base_url:
                self._logger.debug("LLM base URL missing; assuming ready after process signal")
                self._ready_event.set()
                return

            healthy = self._process.poll_health(
                self._llm_base_url,
                timeout=self._health_timeout,
                interval=self._health_check_interval,
                max_retries=self._health_check_max_retries,
                backoff=self._health_check_backoff,
            )
            if healthy:
                self._ready_event.set()
                return

            self._ready_event.clear()
            self._fire_callbacks(self._not_ready_callbacks)

        self._ready_event.clear()

    def _watchdog_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._process.is_running():
                retcode = self._process.poll()
                self._ready_event.clear()
                self._fire_callbacks(self._exit_callbacks, retcode)

                if self._auto_restart and not self._stop_event.is_set():
                    self._logger.warning("llama-server exited; attempting restart")
                    try:
                        self._process.start()
                    except Exception:
                        self._logger.exception("Failed to restart llama-server process")
                        return
                    self._start_health_monitor()
                    continue
                return

            time.sleep(self._watchdog_interval)

    def _fire_callbacks(self, callbacks: Iterable[Callable], *args) -> None:
        for callback in list(callbacks):
            try:
                callback(*args)
            except Exception:  # pragma: no cover - defensive
                self._logger.exception("ConversationService callback failed")

    @staticmethod
    def _join_thread(thread: threading.Thread | None) -> None:
        if thread and thread.is_alive():
            thread.join(timeout=1.0)


__all__ = ["ConversationService"]
