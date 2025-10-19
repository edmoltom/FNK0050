from __future__ import annotations

import atexit
import inspect
import logging
import threading
import time
import weakref
from typing import Any, Callable, Dict, NamedTuple, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from mind.llm.process import LlamaServerProcess


ConversationManagerFactory = Callable[..., Any]


class _ReadinessResult(NamedTuple):
    event_ready: bool
    health_ready: bool
    elapsed: float
    base_url: str


class ConversationService:
    """Manage the conversation and *llama-server* lifecycle.

    The instance receives its dependencies explicitly to simplify testing and
    the wiring performed by the application ``builder``. The conversation loop
    runs on a ``daemon`` thread and can be started or stopped multiple times.
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
        self._last_start_ts: float | None = None
        self._last_stop_ts: float | None = None
        self._min_on_time = float(getattr(self, "_min_on_time", 3.0))
        self._min_off_time = float(getattr(self, "_min_off_time", 2.0))

        self._register_atexit_hook()

    @property
    def stop_event(self) -> threading.Event:
        """Expose the internal stop event so dependencies can be wired."""

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
    def _prepare_process(self) -> bool:
        try:
            if not self._process.is_running():
                self._logger.info("Starting llama-server process")
                self._process.start()
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.exception("Failed to start llama-server: %s", exc)
            return False
        return True

    def _wait_for_readiness(self) -> Optional[_ReadinessResult]:
        wait_start = time.monotonic()
        readiness_deadline = wait_start + self._readiness_timeout
        timeout_partial = min(5.0, self._readiness_timeout)
        event_stop = threading.Event()
        event_state: Dict[str, Any] = {"ready": False, "error": None}

        def _wait_ready_event() -> None:
            deadline = readiness_deadline
            remaining = self._readiness_timeout
            try:
                while remaining > 0 and not event_stop.is_set():
                    wait_for = min(timeout_partial, remaining)
                    if wait_for <= 0:
                        break
                    if self._process.wait_ready(timeout=wait_for):
                        event_state["ready"] = True
                        break
                    if event_stop.is_set():
                        break
                    remaining = deadline - time.monotonic()
            except Exception as exc:  # pragma: no cover - defensive
                event_state["error"] = exc

        event_thread = threading.Thread(
            target=_wait_ready_event,
            name="llama-ready-wait",
            daemon=True,
        )
        event_thread.start()

        base_url = self._resolve_health_base_url()
        health_url = f"{base_url.rstrip('/')}/health"
        health_method = "GET"
        max_attempts = max(0, self._health_check_max_retries) + 1
        attempts = 0
        next_attempt = wait_start
        sleep_for = self._health_check_interval
        backoff = self._health_check_backoff
        health_ready = False
        process_died = False

        try:
            while True:
                now = time.monotonic()
                if now >= readiness_deadline:
                    break

                if event_state["error"] is not None:
                    break

                if event_state["ready"] or health_ready:
                    break

                if self._process.poll() is not None:
                    process_died = True
                    break

                if attempts >= max_attempts:
                    sleep_window = min(0.1, max(0.0, readiness_deadline - now))
                    if sleep_window > 0:
                        time.sleep(sleep_window)
                    continue

                if now < next_attempt:
                    sleep_window = min(next_attempt - now, readiness_deadline - now, 0.1)
                    if sleep_window > 0:
                        time.sleep(sleep_window)
                    continue

                attempts += 1

                warmup_retry = False
                try:
                    req = urllib_request.Request(health_url, method=health_method)
                    remaining = max(0.0, readiness_deadline - now)
                    timeout = max(0.1, min(self._health_check_timeout, remaining))
                    with urllib_request.urlopen(req, timeout=timeout) as response:
                        status = getattr(response, "status", 200)
                        if 200 <= status < 300:
                            self._logger.info(
                                "Health check succeeded on attempt %d", attempts
                            )
                            health_ready = True
                            break
                        if status == 503:
                            self._logger.info(
                                "Health check: model warming up (503)"
                            )
                            warmup_retry = True
                        else:
                            self._logger.warning(
                                "Health check HTTP %s %s returned status %s",
                                health_method,
                                health_url,
                                status,
                            )
                except urllib_error.URLError as exc:  # pragma: no cover - network failures
                    self._logger.warning("Health check request failed: %s", exc)

                if health_ready:
                    break

                if warmup_retry:
                    sleep_window = min(
                        self._health_check_interval,
                        max(0.0, readiness_deadline - time.monotonic()),
                    )
                    if sleep_window > 0:
                        time.sleep(sleep_window)
                    next_attempt = time.monotonic()
                    continue

                if attempts >= max_attempts:
                    continue

                sleep_window = min(sleep_for, max(0.0, readiness_deadline - now))
                if sleep_window > 0:
                    self._logger.info(
                        "Health check backoff sleeping %.2fs before retry %d",
                        sleep_window,
                        attempts + 1,
                    )
                next_attempt = now + sleep_window
                sleep_for *= backoff
        finally:
            event_stop.set()
            event_thread.join()

        if event_state["error"] is not None:
            self._logger.error("Llama server readiness failed: %s", event_state["error"])
            return None

        if process_died:
            self._logger.error("Llama server exited before readiness confirmation")
            return None

        event_ready = bool(event_state.get("ready"))

        if not event_ready and not health_ready:
            self._logger.error("Timeout waiting for llama server readiness")
            return None

        elapsed = time.monotonic() - wait_start
        self._logger.info(
            "Llama server ready (event=%s, health=%s) in %.2fs",
            event_ready,
            health_ready,
            elapsed,
        )

        return _ReadinessResult(
            event_ready=event_ready,
            health_ready=health_ready,
            elapsed=elapsed,
            base_url=base_url,
        )

    def _verify_process_health(self, readiness: _ReadinessResult) -> bool:
        if readiness.health_ready:
            return True
        try:
            healthy = self._process.poll_health(
                readiness.base_url,
                interval=self._health_check_interval,
                max_retries=self._health_check_max_retries,
                backoff=self._health_check_backoff,
                timeout=self._health_check_timeout,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error("Health check invocation failed: %s", exc)
            return False

        if not healthy:
            self._logger.error("Llama server health check did not succeed")
            return False

        return True

    # ------------------------------------------------------------------
    def _since(self, ts: float | None) -> float:
        import time

        return float("inf") if ts is None else (time.monotonic() - ts)

    def _can_start(self) -> bool:
        return self._since(self._last_stop_ts) >= self._min_off_time

    def _can_stop(self) -> bool:
        return self._since(self._last_start_ts) >= self._min_on_time

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the service if it is not already running."""

        with self._lock:
            if self._thread and self._thread.is_alive():
                self._logger.info("Conversation thread already running")
                return

            if not self._can_start():
                self._logger.info(
                    "Start suppressed by cooldown (off-time %.2fs not reached)",
                    self._min_off_time,
                )
                return

            self._stop_event.clear()

            self._logger.info("Bootstrapping conversation service")

            if not self._prepare_process():
                return

            readiness = self._wait_for_readiness()
            if readiness is None:
                self._process.terminate()
                return

            if not self._verify_process_health(readiness):
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
            self._last_start_ts = time.monotonic()

    def stop(
        self,
        *,
        terminate_process: bool = False,
        shutdown_resources: Optional[bool] = None,
    ) -> None:
        """Stop the service and ensure a cooperative shutdown."""

        thread: Optional[threading.Thread]
        with self._lock:
            thread = self._thread
            if not thread:
                self._logger.info("Stop requested with no active conversation thread")
                if terminate_process is True:
                    self._logger.info("Terminating Llama process by explicit request")
                    self._process.terminate()
                    if shutdown_resources or shutdown_resources is None:
                        self._shutdown_led()
                else:
                    self._logger.debug("Preserving Llama process (FSM or transient stop)")
                return

            if not self._can_stop():
                self._logger.info(
                    "Stop suppressed by cooldown (on-time %.2fs not reached)",
                    self._min_on_time,
                )
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

        # --- Controlled process termination policy ---
        # The Llama process should only be terminated on explicit shutdown requests
        # from the main runtime (AppRuntime / SandboxRuntime). FSM-triggered stops
        # must *not* kill the process; they only pause conversation activity.

        if terminate_process is True:
            self._logger.info("Terminating Llama process by explicit request")
            self._process.terminate()
        else:
            self._logger.debug("Preserving Llama process (FSM or transient stop)")

        # Only shut down LED resources when performing a full termination
        if terminate_process and (shutdown_resources or shutdown_resources is None):
            self._shutdown_led()

        self._last_stop_ts = time.monotonic()
        self._logger.info("Conversation service shutdown sequence finished")

    def join(self, timeout: Optional[float] = None) -> bool:
        """Block until the conversation thread finishes."""

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
        self._logger.info("ConversationManager created, entering run()")
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
        """Stop the service and wait for shutdown to complete."""

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

