from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, Optional

from LedController import LedController
from core.hearing.stt import SpeechToText
from core.llm.llm_client import LlamaClient, build_default_client
from core.llm.llm_memory import ConversationMemory
from core.llm.persona import build_system
from core.voice.tts import TextToSpeech

logger = logging.getLogger(__name__)


mem = ConversationMemory(last_n=3)


WAKE_WORDS = ["humo", "lo humo", "alumno", "lune", "lomo"]
MAX_REPLY_CHARS = 220
THINK_TIMEOUT_SEC = 30
SPEAK_COOLDOWN_SEC = 1.5
ATTENTION_TTL_SEC = 15.0        # wake-up window (seconds)
ATTN_BONUS_AFTER_SPEAK = 5.0    # extra after speaking to chain turns


LED_STATE_MAP = {
    "WAKE": "wake",
    "ATTENTIVE_LISTEN": "listen",
    "THINK": "processing",
    "SPEAK": "speaking",
}


class StopRequested(Exception):
    """Raised internally when a shutdown signal is received."""


@dataclass
class ConversationMetrics:
    """Simple container to track timing metrics exposed through logging."""

    llm_retry_count: int = 0
    llm_calls: int = 0
    llm_total_latency: float = 0.0
    listen_started_at: Optional[float] = None
    total_listen_time: float = 0.0

    def start_listen(self, now: float) -> None:
        if self.listen_started_at is None:
            self.listen_started_at = now
            logger.info("listen window started at %.3fs", now)

    def stop_listen(self, now: float) -> None:
        if self.listen_started_at is None:
            return
        elapsed = max(0.0, now - self.listen_started_at)
        self.total_listen_time += elapsed
        logger.info(
            "listen window duration %.3fs (cumulative %.3fs)",
            elapsed,
            self.total_listen_time,
        )
        self.listen_started_at = None

    def record_llm(self, latency: float, retries: int) -> None:
        self.llm_calls += 1
        self.llm_retry_count += retries
        self.llm_total_latency += latency
        avg = self.llm_total_latency / self.llm_calls if self.llm_calls else 0.0
        logger.info(
            "LLM call latency %.3fs, retries %d (total retries %d, avg latency %.3fs)",
            latency,
            retries,
            self.llm_retry_count,
            avg,
        )


class STTService:
    """Adapter around :class:`SpeechToText` providing a reusable generator."""

    def __init__(self, engine: SpeechToText, *, queue_poll: float = 0.1) -> None:
        self._engine = engine
        self._queue_poll = queue_poll

    def stream(self) -> Iterator[Optional[str]]:
        q: queue.Queue[Optional[str]] = queue.Queue()

        def reader() -> None:
            try:
                for phrase in self._engine.listen():
                    q.put(phrase)
            finally:
                q.put(None)

        threading.Thread(target=reader, daemon=True).start()

        while True:
            try:
                item = q.get(timeout=self._queue_poll)
            except queue.Empty:
                yield None
                continue

            if item is None:
                return
            yield item

    def pause(self) -> None:
        self._engine.pause()

    def resume(self) -> None:
        self._engine.resume()

    def stop(self) -> None:
        self._engine.pause()


class LedStateHandler:
    """Thread-safe helper to drive :class:`LedController` animations."""

    def __init__(
        self,
        controller: LedController,
        loop: asyncio.AbstractEventLoop,
        *,
        loop_thread: Optional[threading.Thread] = None,
    ) -> None:
        self._controller = controller
        self._loop = loop
        self._loop_thread = loop_thread

    def _submit(self, coro: asyncio.coroutines.Coroutine[Any, Any, Any]) -> None:
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError:
            logger.debug("LED loop no longer running")

    async def _apply_state(self, state: str) -> None:
        if state == "wake":
            await self._controller.stop_animation()
            await self._controller.set_all([0, 128, 0])
        elif state == "listen":
            await self._controller.stop_animation()
            await self._controller.start_pulsed_wipe([0, 255, 0], 20)
        elif state == "processing":
            await self._controller.stop_animation()
            await self._controller.set_all([0, 0, 0])
            await self._controller.start_pulsed_wipe([0, 0, 128], 20)
        elif state == "speaking":
            await self._controller.stop_animation()
            await self._controller.set_all([0, 0, 255])
        else:
            await self._controller.stop_animation()
            await self._controller.set_all([0, 0, 0])

    def set_state(self, state: str) -> None:
        logger.debug("LED state -> %s", state)
        self._submit(self._apply_state(state))

    def close(self) -> None:
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._controller.close(), self._loop
            )
            fut.result(timeout=2)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Error closing LED controller: %s", exc)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=1)


def contains_wake_word(text: str) -> bool:
    lowered = text.lower()
    return any(w in lowered for w in WAKE_WORDS)


def llm_ask(text: str, client: LlamaClient) -> str:
    """Query the provided LLM client and return a brief Spanish reply."""

    system = build_system()
    msgs = mem.build_messages(system, text)
    reply = client.query(msgs, max_reply_chars=MAX_REPLY_CHARS)
    mem.add_turn(text, reply)
    return reply


def tts_say(text: str, tts: TextToSpeech) -> int:
    try:
        tts.speak(text)
        return 0
    except Exception as exc:  # pragma: no cover - hardware dependent
        logger.error("TTS failed: %s", exc)
        return 1


class ConversationManager:
    def __init__(
        self,
        *,
        stt: STTService,
        llm_client: LlamaClient,
        tts: TextToSpeech,
        led_controller: Any,
        stop_event: threading.Event,
        wait_until_ready: Callable[[], None],
        additional_stop_events: Optional[Iterable[threading.Event]] = None,
        llm_retry_max_attempts: int = 3,
        llm_retry_initial_delay: float = 0.5,
        llm_retry_backoff: float = 2.0,
        llm_retry_max_delay: Optional[float] = None,
        stt_poll_interval: float = 0.02,
        speak_cooldown: float = SPEAK_COOLDOWN_SEC,
    ) -> None:
        self.state = "NONE"
        self._stt = stt
        self._stt_iter = stt.stream()
        self.pending = ""
        self.reply: Optional[str] = None
        self.last_speak_end = time.monotonic()
        self.attentive_until = 0.0
        self.metrics = ConversationMetrics()

        self._llm_client = llm_client
        self._tts = tts
        self._led = led_controller
        self._stop_event = stop_event
        self._extra_stop_events = tuple(additional_stop_events or ())
        self._wait_until_ready = wait_until_ready

        self._llm_retry_max_attempts = max(1, llm_retry_max_attempts)
        self._llm_retry_initial_delay = max(0.0, llm_retry_initial_delay)
        self._llm_retry_backoff = max(1.0, llm_retry_backoff)
        self._llm_retry_max_delay = (
            max(0.0, llm_retry_max_delay) if llm_retry_max_delay else None
        )
        self._poll_interval = max(0.0, stt_poll_interval)
        self._poll_resolution = min(0.1, self._poll_interval or 0.02)
        self._speak_cooldown = speak_cooldown

        self.set_state("WAKE")

    # ------------------------------------------------------------------ helpers
    def _should_stop(self) -> bool:
        if self._stop_event.is_set():
            return True
        for ev in self._extra_stop_events:
            if ev.is_set():
                self._stop_event.set()
                return True
        return False

    def _wait_with_stop(self, timeout: float) -> None:
        if timeout <= 0:
            if self._should_stop():
                raise StopRequested
            return

        deadline = time.monotonic() + timeout
        while True:
            if self._should_stop():
                raise StopRequested

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return

            slice_timeout = min(remaining, self._poll_resolution)
            if self._stop_event.wait(slice_timeout):
                raise StopRequested

    def _ensure_ready(self) -> None:
        result: queue.Queue[Optional[BaseException]] = queue.Queue(maxsize=1)

        def runner() -> None:
            try:
                self._wait_until_ready()
                result.put(None)
            except BaseException as exc:  # pragma: no cover - defensive
                result.put(exc)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

        while True:
            try:
                exc = result.get(timeout=0.1)
            except queue.Empty:
                if self._should_stop():
                    raise StopRequested
                continue

            if exc is None:
                return
            raise exc

    def _poll_stt(self) -> Optional[str]:
        try:
            return next(self._stt_iter)
        except StopIteration:
            logger.debug("STT stream exhausted, recreating")
            self._stt.resume()
            self._stt_iter = self._stt.stream()
            return None

    def _set_led_state(self, state: str) -> None:
        mapped = LED_STATE_MAP.get(state, "off")
        if hasattr(self._led, "set_state"):
            try:
                self._led.set_state(mapped)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("LED set_state failed: %s", exc)

    def set_state(self, new_state: str) -> None:
        if self.state == new_state:
            return
        logger.info("state transition %s -> %s", self.state, new_state)
        self.state = new_state
        self._set_led_state(new_state)

    def _query_llm(self, text: str) -> str:
        delay = self._llm_retry_initial_delay
        attempt = 0
        retries_for_call = 0

        while attempt < self._llm_retry_max_attempts:
            attempt += 1
            start = time.perf_counter()
            try:
                reply = llm_ask(text, self._llm_client)
            except Exception as exc:
                logger.warning(
                    "LLM error attempt %d/%d: %s",
                    attempt,
                    self._llm_retry_max_attempts,
                    exc,
                )

                if attempt >= self._llm_retry_max_attempts:
                    logger.error("LLM failed after %d attempts", attempt)
                    raise

                retries_for_call += 1

                wait_time = delay
                if self._llm_retry_max_delay is not None:
                    wait_time = min(wait_time, self._llm_retry_max_delay)

                self._wait_with_stop(wait_time)
                delay *= self._llm_retry_backoff
                continue

            latency = time.perf_counter() - start
            self.metrics.record_llm(latency, retries_for_call)
            return reply

        raise RuntimeError("LLM retry configuration invalid")

    def _cleanup(self) -> None:
        now = time.monotonic()
        self.metrics.stop_listen(now)
        try:
            self._stt.stop()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Error stopping STT: %s", exc)

        if hasattr(self._led, "set_state"):
            try:
                self._led.set_state("off")
            except Exception:  # pragma: no cover - defensive
                pass

        if hasattr(self._led, "close"):
            try:
                self._led.close()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Error closing LED handler: %s", exc)

    # --------------------------------------------------------------------- main
    def run(self) -> None:
        logger.info("Conversation manager starting")
        try:
            self._ensure_ready()

            while True:
                if self._should_stop():
                    raise StopRequested

                utter = self._poll_stt()
                now = time.monotonic()

                if self.state == "WAKE":
                    if utter:
                        logger.info("heard: %s", utter)
                        if contains_wake_word(utter):
                            logger.info("wake word detected → attentive mode")
                            self.attentive_until = now + ATTENTION_TTL_SEC
                            self.metrics.start_listen(now)
                            self.set_state("ATTENTIVE_LISTEN")

                elif self.state == "ATTENTIVE_LISTEN":
                    if now > self.attentive_until:
                        logger.info("attention expired → WAKE")
                        self.metrics.stop_listen(now)
                        self.set_state("WAKE")
                    elif utter:
                        logger.info("command: %s", utter)
                        self.pending = utter
                        self.attentive_until = now + ATTENTION_TTL_SEC
                        self.metrics.stop_listen(now)
                        self._stt.pause()
                        self.set_state("THINK")

                elif self.state == "THINK":
                    try:
                        self.reply = self._query_llm(self.pending)
                        self.set_state("SPEAK")
                    except StopRequested:
                        raise
                    except Exception as exc:
                        logger.error("LLM processing failed: %s", exc)
                        self._stt.resume()
                        self.set_state("WAKE")

                elif self.state == "SPEAK":
                    if self.reply is not None:
                        logger.info("reply: %s", self.reply)
                        tts_say(self.reply, self._tts)
                        self.reply = None
                        self.last_speak_end = time.monotonic()
                        self.attentive_until = (
                            self.last_speak_end
                            + ATTENTION_TTL_SEC
                            + ATTN_BONUS_AFTER_SPEAK
                        )

                    if time.monotonic() - self.last_speak_end >= self._speak_cooldown:
                        self._stt.resume()
                        now = time.monotonic()
                        self.metrics.start_listen(now)
                        self.set_state("ATTENTIVE_LISTEN")

                self._wait_with_stop(self._poll_interval)

        except StopRequested:
            logger.info("Stop requested, shutting down conversation manager")
        except Exception:
            logger.exception("Conversation manager crashed")
            raise
        finally:
            self._cleanup()


def build_default_conversation_manager(
    *,
    stop_event: Optional[threading.Event] = None,
    additional_stop_events: Optional[Iterable[threading.Event]] = None,
) -> ConversationManager:
    """Helper to build a :class:`ConversationManager` with default engines."""

    stop = stop_event or threading.Event()

    stt_engine = SpeechToText()
    stt_service = STTService(stt_engine)
    tts_engine = TextToSpeech()
    llm_client = build_default_client()

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    led_ctrl = LedController(brightness=10, loop=loop)
    led_handler = LedStateHandler(led_ctrl, loop, loop_thread=loop_thread)

    return ConversationManager(
        stt=stt_service,
        llm_client=llm_client,
        tts=tts_engine,
        led_controller=led_handler,
        stop_event=stop,
        additional_stop_events=additional_stop_events,
        wait_until_ready=lambda: None,
    )


if __name__ == "__main__":  # pragma: no cover - manual execution only
    logging.basicConfig(level=logging.INFO)
    manager = build_default_conversation_manager()
    manager.run()
