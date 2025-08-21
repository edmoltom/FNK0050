import sys
import time
import subprocess
import threading
import queue
import asyncio, threading
from LedController import LedController
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "llm"))
from llm_client import query_llm

BASE = Path(__file__).resolve().parent
WAKE_WORDS = ["humo", "lo humo", "alumno", "lune"]
MAX_REPLY_CHARS = 220
THINK_TIMEOUT_SEC = 30
SPEAK_COOLDOWN_SEC = 1.5
ATTENTION_TTL_SEC = 15.0        # wake-up window (seconds)
ATTN_BONUS_AFTER_SPEAK = 5.0    # extra after speaking to chain turns

STT_PATH = BASE / "llm" / "stt.py"
TTS_PATH = BASE / "llm" / "tts.py"

STT_PAUSED = False
STT_PROC = None


_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()
_ctrl = LedController(brightness=10, loop=_loop)


async def _led_state(state: str):
    if state == "wake":
        await _ctrl.stop_animation()
        await _ctrl.set_all([0, 128, 0])    
    elif state == "listen":
        await _ctrl.stop_animation()
        await _ctrl.start_pulsed_wipe([0, 255, 0], 20)            
    elif state == "processing":
        await _ctrl.stop_animation()
        await _ctrl.set_all([0, 0, 0])
        await _ctrl.start_pulsed_wipe([0, 0, 128], 20)
    elif state == "speaking":
        await _ctrl.stop_animation()
        await _ctrl.set_all([0, 0, 255])
    else:
        await _ctrl.stop_animation()
        await _ctrl.set_all([0, 0, 0])

def _submit(coro):
    try:
        asyncio.run_coroutine_threadsafe(coro, _loop)
    except RuntimeError:
        pass  # loop cerrado al apagar

def leds_set(state: str) -> None:
    print(f"[LEDS] {state}")  # TODO: integrate real LEDs
    _submit(_led_state(state))


def stt_pause() -> None:
    global STT_PAUSED
    STT_PAUSED = True


def stt_resume() -> None:
    global STT_PAUSED
    STT_PAUSED = False


def stt_stop() -> None:
    if STT_PROC and STT_PROC.poll() is None:
        STT_PROC.terminate()


def stt_stream():
    """Yield utterances from the STT subprocess (drains queue when paused)."""
    global STT_PROC
    proc = subprocess.Popen(
        [sys.executable, "-u", str(STT_PATH)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    STT_PROC = proc
    q = queue.Queue()

    def reader():
        for line in iter(proc.stdout.readline, ""):
            if line.startswith("> "):
                q.put(line[2:].strip())
        # EOF: mark with sentinel
        q.put(None)

    threading.Thread(target=reader, daemon=True).start()

    while True:
        if STT_PAUSED:
            # Drain fast while paused
            drained = False
            try:
                while True:
                    item = q.get_nowait()
                    if item is None:
                        return  # STT ended
                    drained = True
            except queue.Empty:
                pass
            time.sleep(0.01 if drained else 0.02)
            yield None
            continue

        try:
            item = q.get(timeout=0.1)
            if item is None:
                return  # STT ended
            yield item
        except queue.Empty:
            yield None

def llm_ask(text: str) -> str:
    """Query the shared LLM client and return a brief Spanish reply."""
    return query_llm(text, max_reply_chars=MAX_REPLY_CHARS)

def tts_say(text: str) -> int:
    p = subprocess.run([sys.executable, str(TTS_PATH), "--text", text], check=False)
    return p.returncode


def contains_wake_word(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in WAKE_WORDS)

class ConversationManager:
    def __init__(self) -> None:
        self.state = "NONE"
        self.stt_iter = stt_stream()
        self.pending = ""
        self.reply = None
        self.last_speak_end = time.monotonic()
        self.attentive_until = 0.0      # active attention window
        self.set_state("WAKE")

    def set_state(self, new_state: str) -> None:
        if self.state != new_state:
            print(f"[STATE] -> {new_state}")
            if new_state == "WAKE":
                leds_set("wake")
            elif new_state == "ATTENTIVE_LISTEN":
                leds_set("listen")
            elif new_state == "THINK":
                leds_set("processing")
            elif new_state == "SPEAK":
                leds_set("speaking")
            self.state = new_state

    def run(self) -> None:
        try:
            while True:
                try:
                    utter = next(self.stt_iter)
                except StopIteration:
                    stt_resume()
                    self.stt_iter = stt_stream()
                    time.sleep(0.02)
                    continue

                now = time.monotonic()

                if self.state == "WAKE":
                    if utter:
                        print(f"[HEARD] {utter}")
                        if contains_wake_word(utter):
                            print("[WAKE] wakeword detected → attentive mode")
                            self.attentive_until = now + ATTENTION_TTL_SEC
                            self.set_state("ATTENTIVE_LISTEN")

                elif self.state == "ATTENTIVE_LISTEN":
                    # expire window if no interaction
                    if now > self.attentive_until:
                        print("[ATTN] attention expired → WAKE")
                        self.set_state("WAKE")
                    elif utter:
                        print(f"[CMD] {utter}")
                        self.pending = utter
                        self.attentive_until = (
                            now + ATTENTION_TTL_SEC
                        )  # renew attention
                        stt_pause()
                        self.set_state("THINK")

                elif self.state == "THINK":
                    try:
                        self.reply = llm_ask(self.pending)
                        self.set_state("SPEAK")
                    except Exception as e:
                        print(f"[THINK ERROR] {e}")
                        stt_resume()
                        self.set_state("WAKE")

                elif self.state == "SPEAK":
                    if self.reply is not None:
                        print(f"[SAY] {self.reply}")
                        tts_say(self.reply)
                        self.reply = None
                        self.last_speak_end = time.monotonic()
                        self.attentive_until = (
                            self.last_speak_end
                            + ATTENTION_TTL_SEC
                            + ATTN_BONUS_AFTER_SPEAK
                        )

                    if time.monotonic() - self.last_speak_end >= SPEAK_COOLDOWN_SEC:
                        stt_resume()
                        self.set_state("ATTENTIVE_LISTEN")

                time.sleep(0.02)

        except KeyboardInterrupt:
            pass
        finally:
            stt_stop()
            try:
                _submit(_ctrl.close())
            finally:
                _loop.call_soon_threadsafe(_loop.stop)

if __name__ == "__main__":
    ConversationManager().run()
