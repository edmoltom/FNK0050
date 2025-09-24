from __future__ import annotations

import atexit
import inspect
import logging
import threading
import time
import weakref
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
        health_check_base_url: Optional[str] = None,
        health_check_interval: float = 0.5,
        health_check_max_retries: int = 3,
        health_check_backoff: float = 2.0,
        health_check_timeout: Optional[float] = None,
        led_cleanup: Optional[Callable[[], None]] = None,
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
        self._health_base_url = (health_check_base_url or "").strip() or None
        self._health_check_interval = max(0.05, float(health_check_interval))
        self._health_check_max_retries = max(0, int(health_check_max_retries))
        self._health_check_backoff = max(1.0, float(health_check_backoff))
        self._health_check_timeout = (
            readiness_timeout if health_check_timeout is None else float(health_check_timeout)
        )
        self._thread_name = thread_name
        self._logger = logger or logging.getLogger("conversation.service")

        self._thread: Optional[threading.Thread] = None
        self._manager: Any = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._led_cleanup = led_cleanup
        self._led_shutdown = False
        self._atexit_callback: Optional[Callable[[], None]] = None

        self._register_atexit_hook()

    @property
    def stop_event(self) -> threading.Event:
        """Expose the internal stop event for dependency wiring."""

        return self._stop_event

    # ------------------------------------------------------------------
    def _resolve_health_base_url(self) -> str:
        if self._health_base_url:
            return self._health_base_url
        port = getattr(self._process, "port", None)
        if port:
            return f"http://127.0.0.1:{int(port)}"
        return "http://127.0.0.1:8080"

    def _shutdown_led(self) -> None:
        if self._led_shutdown:
            return
        cleanup = self._led_cleanup
        if cleanup is None:
            self._led_shutdown = True
            return
        try:
            cleanup()
        except Exception:  # pragma: no cover - defensive
            self._logger.debug("Error shutting down LED resources", exc_info=True)
        finally:
            self._led_shutdown = True

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Inicia el servicio si no se encuentra en ejecución."""

        with self._lock:
            if self._thread and self._thread.is_alive():
                self._logger.info("Conversation thread already running")
                return

            self._stop_event.clear()

            self._logger.info("Bootstrapping conversation service")

            try:
                if not self._process.is_running():
                    self._logger.info("Starting llama-server process")
                    self._process.start()
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.exception("Failed to start llama-server: %s", exc)
                return

            try:
                wait_start = time.monotonic()
                ready = self._process.wait_ready(timeout=self._readiness_timeout)
            except Exception as exc:
                self._logger.error("Llama server readiness failed: %s", exc)
                self._process.terminate()
                return

            if not ready:
                self._logger.error("Timeout waiting for llama server readiness")
                self._process.terminate()
                return

            elapsed = time.monotonic() - wait_start
            self._logger.info("Llama server ready after %.2fs", elapsed)

            try:
                healthy = self._process.poll_health(
                    self._resolve_health_base_url(),
                    interval=self._health_check_interval,
                    max_retries=self._health_check_max_retries,
                    backoff=self._health_check_backoff,
                    timeout=self._health_check_timeout,
                )
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.error("Health check invocation failed: %s", exc)
                self._process.terminate()
                return

            if not healthy:
                self._logger.error("Llama server health check did not succeed")
                self._process.terminate()
                return

            query_callable = getattr(self._llm_client, "query", None)
            if callable(query_callable):
                try:
                    self._logger.info("Performing non-blocking LLM smoke ping")
                    query_callable(
                        [
                            {"role": "system", "content": "ping check"},
                            {"role": "user", "content": "ping"},
                        ],
                        max_reply_chars=8,
                    )
                except Exception as exc:  # pragma: no cover - network dependent
                    self._logger.warning("LLM smoke check failed: %s", exc)

            manager_kwargs: Dict[str, Any] = {
                "stt": self._stt,
                "tts": self._tts,
                "led_controller": self._led_controller,
                "llm_client": self._llm_client,
            }
            manager_kwargs.update(self._extra_manager_kwargs)
            manager_kwargs.setdefault("close_led_on_cleanup", False)

            process_info = {
                "llama_binary": str(getattr(self._process, "binary_path", "")),
                "model_path": str(getattr(self._process, "model_path", "")),
                "port": getattr(self._process, "port", None),
                "llm_base_url": getattr(self._llm_client, "base_url", None),
            }
            self._logger.info("Creating ConversationManager with cfg=%s", process_info)

            self._manager = self._manager_factory(**manager_kwargs)
            self._logger.info("ConversationManager created, starting thread...")

            def _thread_target() -> None:
                try:
                    self._run_manager()
                except BaseException:  # pragma: no cover - defensive
                    self._logger.exception("Conversation loop crashed")
                    raise

            self._thread = threading.Thread(
                target=_thread_target,
                name=self._thread_name,
                daemon=True,
            )
            self._thread.start()
            self._logger.info("Conversation loop thread started")

    def stop(
        self,
        *,
        terminate_process: bool = False,
        shutdown_resources: Optional[bool] = None,
    ) -> None:
        """Detiene el servicio y asegura el cierre cooperativo."""

        thread: Optional[threading.Thread]
        with self._lock:
            thread = self._thread
            if not thread:
                self._logger.info("Stop requested with no active conversation thread")
                if terminate_process:
                    self._process.terminate()
                    if shutdown_resources or (shutdown_resources is None and terminate_process):
                        self._shutdown_led()
                return

            self._logger.info("Stopping conversation service")
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

        if terminate_process:
            self._process.terminate()

        if shutdown_resources or (shutdown_resources is None and terminate_process):
            self._shutdown_led()

        self._logger.info("Conversation service shutdown sequence finished")

    def join(self, timeout: Optional[float] = None) -> bool:
        """Bloquea hasta que el hilo de conversación termine."""

        timeout = self._shutdown_timeout if timeout is None else timeout
        thread: Optional[threading.Thread]
        with self._lock:
            thread = self._thread

        if not thread:
            self._logger.debug("Join requested but no conversation thread active")
            return True

        thread.join(timeout)
        alive = thread.is_alive()
        if not alive:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
                    self._manager = None
            self._logger.info("Conversation thread %s finished", thread.name)
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

        self._logger.info("Conversation loop started")
        try:
            if self._accepts_stop_event(run):
                run(stop_event=self._stop_event)
            else:
                run()
        except KeyboardInterrupt:
            self._logger.info("Conversation loop interrupted by KeyboardInterrupt")
        except BaseException:  # pragma: no cover - defensive
            self._logger.exception("ConversationManager.run raised an exception")
        finally:
            self._stop_event.set()
            self._logger.info("Conversation loop terminated")

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

    def close(self) -> None:
        """Detiene y espera el cierre del servicio."""

        self._logger.info("Closing conversation service")
        self.stop(terminate_process=True, shutdown_resources=True)
        self.join()
        self._unregister_atexit_hook()

    def __enter__(self) -> "ConversationService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    def _register_atexit_hook(self) -> None:
        if self._atexit_callback is not None:
            return

        self_ref = weakref.ref(self)

        def _cleanup() -> None:
            instance = self_ref()
            if not instance:
                return
            instance._logger.info("atexit cleanup: shutting down conversation service")
            instance.close()

        atexit.register(_cleanup)
        self._atexit_callback = _cleanup

    def _unregister_atexit_hook(self) -> None:
        if self._atexit_callback is None:
            return

        try:
            atexit.unregister(self._atexit_callback)
        except AttributeError:  # pragma: no cover - Python <3.11 compat
            pass
        finally:
            self._atexit_callback = None


__all__ = ["ConversationService"]

