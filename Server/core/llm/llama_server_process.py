from __future__ import annotations

import atexit
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Mapping, Sequence


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
        ready_text: str | None = "HTTP server listening",
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
        self.logger = logger or logging.getLogger(__name__)
        self.log_prefix = log_prefix
        self.ready_text = ready_text

        self._process: subprocess.Popen[str] | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
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

        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=popen_env,
        )

        if not self._atexit_registered:
            atexit.register(self.terminate)
            self._atexit_registered = True

        self._stdout_thread = threading.Thread(
            target=self._stream_output,
            args=(self._process.stdout, logging.INFO, f"{self.log_prefix} stdout"),
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._stream_output,
            args=(self._process.stderr, logging.ERROR, f"{self.log_prefix} stderr"),
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def wait_ready(self, timeout: float | None = None) -> bool:
        process = self._ensure_process()

        if self.ready_text is None:
            return process.poll() is None

        waited = self._ready_event.wait(timeout)
        if waited:
            return True

        if process.poll() is not None:
            raise RuntimeError("Process exited before becoming ready")

        return False

    def terminate(self, timeout: float = 5.0) -> None:
        process = self._process
        if not process:
            return

        if process.poll() is None:
            self.logger.info("Terminating llama-server process")
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.logger.warning("Force killing llama-server process")
                process.kill()
                process.wait()

        if self._stdout_thread and self._stdout_thread.is_alive():
            self._stdout_thread.join(timeout=timeout)
        if self._stderr_thread and self._stderr_thread.is_alive():
            self._stderr_thread.join(timeout=timeout)

        self._process = None
        self._stdout_thread = None
        self._stderr_thread = None
        self._ready_event.clear()
        if self.ready_text is None:
            self._ready_event.set()

    def __enter__(self) -> "LlamaServerProcess":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple
        self.terminate()

    # Internal helpers ---------------------------------------------------
    def _ensure_process(self) -> subprocess.Popen[str]:
        if not self._process:
            raise RuntimeError("Process not started")
        return self._process

    def _stream_output(self, stream, level: int, prefix: str) -> None:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            text = line.rstrip()
            if text:
                self.logger.log(level, "%s | %s", prefix, text)
                if self.ready_text and self.ready_text in text:
                    self._ready_event.set()
        stream.close()


__all__ = ["LlamaServerProcess"]
