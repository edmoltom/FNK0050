from __future__ import annotations

import inspect
import logging
import threading
from typing import Any, Callable, Dict, Optional

from core.llm.llama_server_process import LlamaServerProcess


ConversationManagerFactory = Callable[..., Any]


class ConversationService:
    """Administra el ciclo de vida de la conversación y del *llama-server*.

    La instancia recibe todas sus dependencias de manera explícita para
    facilitar las pruebas y el *wiring* desde el ``builder`` de la aplicación.
    El bucle de conversación se ejecuta en un hilo ``daemon`` y puede
    iniciarse/detenerse múltiples veces.
    """

    def __init__(
        self,
        *,
        stt: Any,
        tts: Any,
        led_controller: Any,
        llm_client: Any,
        process: LlamaServerProcess,
        manager_factory: ConversationManagerFactory,
        manager_kwargs: Optional[Dict[str, Any]] = None,
        readiness_timeout: float = 30.0,
        shutdown_timeout: float = 5.0,
        logger: Optional[logging.Logger] = None,
        thread_name: str = "conversation-loop",
    ) -> None:
        self._stt = stt
        self._tts = tts
        self._led_controller = led_controller
        self._llm_client = llm_client
        self._process = process
        self._manager_factory = manager_factory
        self._extra_manager_kwargs = dict(manager_kwargs or {})
        self._readiness_timeout = readiness_timeout
        self._shutdown_timeout = shutdown_timeout
        self._thread_name = thread_name
        self._logger = logger or logging.getLogger(__name__)

        self._thread: Optional[threading.Thread] = None
        self._manager: Any = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Inicia el servicio si no se encuentra en ejecución."""

        with self._lock:
            if self._thread and self._thread.is_alive():
                self._logger.debug("Conversation thread already running")
                return

            self._stop_event.clear()

            try:
                if not self._process.is_running():
                    self._process.start()
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.exception("Failed to start llama-server: %s", exc)
                return

            try:
                ready = self._process.wait_ready(timeout=self._readiness_timeout)
            except Exception as exc:
                self._logger.error("Llama server readiness failed: %s", exc)
                self._process.terminate()
                return

            if not ready:
                self._logger.error("Timeout waiting for llama server readiness")
                self._process.terminate()
                return

            manager_kwargs: Dict[str, Any] = {
                "stt": self._stt,
                "tts": self._tts,
                "led_controller": self._led_controller,
                "llm_client": self._llm_client,
            }
            manager_kwargs.update(self._extra_manager_kwargs)

            self._manager = self._manager_factory(**manager_kwargs)
            self._thread = threading.Thread(
                target=self._run_manager,
                name=self._thread_name,
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Detiene el servicio y asegura el cierre cooperativo."""

        thread: Optional[threading.Thread]
        with self._lock:
            thread = self._thread
            if not thread:
                self._process.terminate()
                return

            self._stop_event.set()
            self._invoke_manager_method("pause_stt")
            self._invoke_manager_method("drain_queues")
            self._invoke_manager_method("request_stop")
            self._invoke_manager_method("stop")

        joined = self.join()
        if not joined and thread and thread.is_alive():
            self._logger.warning(
                "Conversation thread did not terminate within %.2fs",
                self._shutdown_timeout,
            )

        self._process.terminate()

    def join(self, timeout: Optional[float] = None) -> bool:
        """Bloquea hasta que el hilo de conversación termine."""

        timeout = self._shutdown_timeout if timeout is None else timeout
        thread: Optional[threading.Thread]
        with self._lock:
            thread = self._thread

        if not thread:
            return True

        thread.join(timeout)
        alive = thread.is_alive()
        if not alive:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
                    self._manager = None
        return not alive

    # ------------------------------------------------------------------
    def _run_manager(self) -> None:
        manager = self._manager
        if not manager:
            return

        run = getattr(manager, "run", None)
        if not callable(run):
            self._logger.error("ConversationManager missing run() method")
            return

        try:
            if self._accepts_stop_event(run):
                run(stop_event=self._stop_event)
            else:
                run()
        except Exception:  # pragma: no cover - defensive
            self._logger.exception("ConversationManager.run raised an exception")
        finally:
            self._stop_event.set()

    def _accepts_stop_event(self, func: Callable[..., Any]) -> bool:
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):  # pragma: no cover - best effort
            return False

        for param in signature.parameters.values():
            if param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
                if param.name == "stop_event":
                    return True
            elif param.kind is param.VAR_KEYWORD:
                return True
        return False

    def _invoke_manager_method(self, name: str) -> None:
        manager = self._manager
        if not manager:
            return

        method = getattr(manager, name, None)
        if callable(method):
            try:
                method()
            except Exception:  # pragma: no cover - defensive
                self._logger.exception(
                    "ConversationManager.%s raised an exception", name
                )


__all__ = ["ConversationService"]

