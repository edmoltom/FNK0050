"""Process manager for llama.cpp servers (mind.llm.process)."""

from __future__ import annotations

import atexit
import logging
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Mapping, Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request

logger = logging.getLogger(__name__)
logger.info("[LLM] Module loaded: mind.llm.process")

class LlamaServerProcess:
    """Manage the lifecycle of a ``llama-server`` process."""

    def __init__(
        self,
        llama_binary: str | os.PathLike[str] | Path,
        model_path: str | os.PathLike[str] | Path,
        *,
        port: int = 8080,
        threads: int | None = None,
        parallel: int | None = None,
        context: int | None = None,
        batch: int | None = None,
        mlock: bool = False,
        embeddings: bool = False,
        extra_args: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
        logger: logging.Logger | None = None,
        ready_text: str | None = "listening",
        log_prefix: str = "llama-server",
    ) -> None:
        self.binary_path = self._validate_path(llama_binary, "llama_binary")
        self.model_path = self._validate_path(model_path, "model_path")

        self.port = port
        self.threads = threads
        self.parallel = parallel
        self.context = context
        self.batch = batch
        self.mlock = mlock
        self.embeddings = embeddings
        self.extra_args = list(extra_args or [])
        self.env = dict(env or {})
        self.logger = logger or logging.getLogger("conversation.llama")
        self.log_prefix = log_prefix
        self.ready_text = ready_text

        self._process: subprocess.Popen[str] | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._uses_process_group = False
        self._ready_event = threading.Event()
        if ready_text is None:
            self._ready_event.set()

        self._atexit_registered = False

    @staticmethod
    def _validate_path(path: str | os.PathLike[str] | Path, name: str) -> Path:
        candidate = Path(path)
        if not candidate.exists():
            raise FileNotFoundError(f"{name} not found: {candidate}")
        return candidate

    # Public API ---------------------------------------------------------
    def build_command(self) -> list[str]:
        cmd: list[str] = [str(self.binary_path), "-m", str(self.model_path)]

        cmd.extend(["--port", str(self.port)])
        if self.threads is not None:
            cmd.extend(["-t", str(self.threads)])
        if self.parallel is not None:
            cmd.extend(["--parallel", str(self.parallel)])
        if self.context is not None:
            cmd.extend(["-c", str(self.context)])
        if self.batch is not None:
            cmd.extend(["-b", str(self.batch)])
        if self.mlock:
            cmd.append("--mlock")
        if self.embeddings:
            cmd.append("--embeddings")

        cmd.extend(self.extra_args)
        return cmd

    def start(self) -> None:
        if self._process and self._process.poll() is None:
            raise RuntimeError("Process already running")

        self._ready_event.clear()
        if self.ready_text is None:
            self._ready_event.set()

        command = self.build_command()
        self.logger.info("Starting llama-server: %s", " ".join(command))

        popen_env = os.environ.copy()
        popen_env.update(self.env)

        popen_kwargs: dict[str, object] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "env": popen_env,
        }

        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            popen_kwargs["creationflags"] = creationflags
            self._uses_process_group = creationflags != 0
        else:
            popen_kwargs["start_new_session"] = True
            self._uses_process_group = True

        self._process = subprocess.Popen(command, **popen_kwargs)

        if not self._atexit_registered:
            atexit.register(self.terminate)
            self._atexit_registered = True

        self._stdout_thread = threading.Thread(
            target=self._stream_output,
            args=(self._process.stdout, logging.INFO, f"{self.log_prefix} output"),
            daemon=True,
        )
        self._stderr_thread = None
        self._stdout_thread.start()

    def wait_ready(self, timeout: float | None = None) -> bool:
        process = self._ensure_process()

        if self.ready_text is None:
            ready = process.poll() is None
            if ready:
                self.logger.info("llama-server ready (no readiness text configured)")
            return ready

        start_wait = time.monotonic()
        waited = self._ready_event.wait(timeout)
        if waited:
            elapsed = time.monotonic() - start_wait
            self.logger.info("llama-server signaled readiness after %.2fs", elapsed)
            return True

        if process.poll() is not None:
            self.logger.error("llama-server exited before readiness was signaled")
            raise RuntimeError("Process exited before becoming ready")

        return False

    def stop(self, graceful_timeout: float = 5.0, force_timeout: float = 5.0) -> None:
        process = self._process
        if not process:
            return

        try:
            if process.poll() is None:
                self.logger.info("[LLM] Stopping llama-server (graceful)...")
                if os.name == "nt":
                    sent_break = False
                    if self._uses_process_group and hasattr(signal, "CTRL_BREAK_EVENT"):
                        try:
                            os.kill(process.pid, signal.CTRL_BREAK_EVENT)  # type: ignore[arg-type]
                            sent_break = True
                        except Exception:
                            self.logger.debug(
                                "Failed to send CTRL_BREAK_EVENT to llama-server",
                                exc_info=True,
                            )
                    if not sent_break:
                        process.terminate()
                else:
                    try:
                        os.killpg(process.pid, signal.SIGINT)
                    except ProcessLookupError:
                        pass
                    except Exception:
                        self.logger.debug(
                            "Failed to send SIGINT to llama-server group", exc_info=True
                        )
                        process.terminate()

                deadline = time.time() + max(graceful_timeout, 0.0)
                while process.poll() is None and time.time() < deadline:
                    time.sleep(0.1)

                if process.poll() is None:
                    self.logger.warning("[LLM] Graceful stop timed out, sending TERM...")
                    if os.name == "nt":
                        process.terminate()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        except Exception:
                            self.logger.debug(
                                "Failed to send SIGTERM to llama-server group",
                                exc_info=True,
                            )
                            process.terminate()

                    deadline = time.time() + max(force_timeout, 0.0)
                    while process.poll() is None and time.time() < deadline:
                        time.sleep(0.1)

                if process.poll() is None:
                    self.logger.error("[LLM] Forcing kill of llama-server...")
                    if os.name == "nt":
                        process.kill()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        except Exception:
                            self.logger.debug(
                                "Failed to send SIGKILL to llama-server group",
                                exc_info=True,
                            )
                            process.kill()
                    process.wait()
        finally:
            if process.poll() is not None:
                try:
                    process.wait(timeout=0.1)
                except Exception:
                    pass

            join_timeout = max(graceful_timeout + force_timeout, 1.0)
            if self._stdout_thread and self._stdout_thread.is_alive():
                self._stdout_thread.join(timeout=join_timeout)
            if self._stderr_thread and self._stderr_thread.is_alive():
                self._stderr_thread.join(timeout=join_timeout)

            self._process = None
            self._stdout_thread = None
            self._stderr_thread = None
            self._ready_event.clear()
            if self.ready_text is None:
                self._ready_event.set()

            self.logger.info("[LLM] llama-server stopped.")

    def terminate(self, timeout: float = 5.0) -> None:
        self.stop(graceful_timeout=timeout)

    def __enter__(self) -> "LlamaServerProcess":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple
        self.stop()

    # Internal helpers ---------------------------------------------------
    def _ensure_process(self) -> subprocess.Popen[str]:
        if not self._process:
            raise RuntimeError("Process not started")
        return self._process

    def _stream_output(self, stream, level: int, prefix: str) -> None:
        if stream is None:
            return
        ready_markers = (
            "http server is listening",
            "server is listening",
            "listening on",
            "starting http server",
            "starting the main loop",
            "all slots are idle",
        )

        for line in iter(stream.readline, ""):
            text = line.rstrip()
            if text:
                self.logger.log(level, "%s | %s", prefix, text)
                line_lower = text.strip().lower()
                ready = False
                if self.ready_text and self.ready_text.lower() in line_lower:
                    ready = True
                elif any(marker in line_lower for marker in ready_markers):
                    ready = True

                if ready and not self._ready_event.is_set():
                    self._ready_event.set()
                    self.logger.debug(
                        "Readiness marker detected in output: %s", text.strip()
                    )
        stream.close()

    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        process = self._process
        return bool(process) and process.poll() is None

    def poll(self) -> int | None:
        process = self._process
        return process.poll() if process else None

    def poll_health(
        self,
        base_url: str,
        *,
        endpoint: str = "/health",
        method: str = "GET",
        timeout: float = 5.0,
        interval: float = 0.5,
        max_retries: int = 3,
        backoff: float = 2.0,
    ) -> bool:
        """Ping the llama-server HTTP endpoint until it becomes healthy."""

        if not base_url:
            raise ValueError("base_url must be provided for health polling")

        interval = max(0.05, interval)
        backoff = max(1.0, backoff)
        attempt_deadline = time.monotonic() + max(0.0, timeout)
        attempts = max_retries + 1

        url = f"{base_url.rstrip('/')}{endpoint}"
        sleep_for = interval

        for attempt in range(attempts):
            if self.poll() is not None:
                self.logger.error("llama-server process died during health polling")
                return False

            try:
                req = urllib_request.Request(url, method=method.upper())
                with urllib_request.urlopen(req, timeout=min(timeout, max(interval, 0.1))) as response:
                    status = getattr(response, "status", 200)
                    if 200 <= status < 300:
                        self.logger.info(
                            "Health check succeeded on attempt %d", attempt + 1
                        )
                        return True
                    self.logger.warning(
                        "Health check HTTP %s %s returned status %s",
                        method,
                        url,
                        status,
                    )
            except urllib_error.URLError as exc:  # pragma: no cover - network failures
                self.logger.warning("Health check request failed: %s", exc)

            if attempt == attempts - 1:
                break

            now = time.monotonic()
            if now >= attempt_deadline:
                break

            remaining = attempt_deadline - now
            sleep_time = min(sleep_for, max(0.0, remaining))
            if sleep_time > 0:
                self.logger.info(
                    "Health check backoff sleeping %.2fs before retry %d",
                    sleep_time,
                    attempt + 2,
                )
                time.sleep(sleep_time)
            sleep_for *= backoff

        self.logger.error("Health check failed after %d attempts", attempts)
        return False


__all__ = ["LlamaServerProcess"]
