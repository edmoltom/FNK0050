import os
import sys
import time
import subprocess
import threading
import queue
import requests
from pathlib import Path

BASE = Path(__file__).resolve().parent
LLAMA_BASE = os.getenv("LLAMA_BASE", "http://127.0.0.1:8080")
WAKE_WORDS = ["humo", "lo humo", "alumno", "lune"]
#WAKE_WORDS = []
MAX_REPLY_CHARS = 220
THINK_TIMEOUT_SEC = 30
SPEAK_COOLDOWN_SEC = 1.5
ATTENTION_TTL_SEC = 15.0        # wake-up window (seconds)
ATTN_BONUS_AFTER_SPEAK = 5.0    # extra after speaking to chain turns

STT_PATH = BASE / "llm" / "stt.py"
TTS_PATH = BASE / "llm" / "tts.py"

STT_PAUSED = False
STT_PROC = None


def leds_set(state: str) -> None:
    print(f"[LEDS] {state}")  # TODO: integrate real LEDs


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

LLM_ENDPOINT = None

def llm_ask(text: str) -> str:
    """Query the LLM server and return the reply (v1 compat → fallback)."""
    global LLM_ENDPOINT
    payload = {
        "model": "local-llm",
        "messages": [
            {"role": "system", "content": "Responde en español, breve."},
            {"role": "user", "content": text},
        ]
    }
    # Try OpenAI-compatible endpoint
    try:
        if LLM_ENDPOINT in (None, "/v1/chat/completions"):
            url = f"{LLAMA_BASE}/v1/chat/completions"
            print(f"[LLM →] POST {url}")
            r = requests.post(url, json=payload, timeout=THINK_TIMEOUT_SEC)
            r.raise_for_status()
            data = r.json()
            if LLM_ENDPOINT is None:
                LLM_ENDPOINT = "/v1/chat/completions"
                print("[LLM] using /v1/chat/completions")
            reply = data["choices"][0]["message"]["content"]
            return reply[:MAX_REPLY_CHARS]
    except Exception as e:
        print(f"[LLM v1 ERROR] {e} -> fallback /completion")
        LLM_ENDPOINT = "/completion"

    try:
        url = f"{LLAMA_BASE}/completion"
        fb = {"prompt": text, "n_predict": 200, "temperature": 1.2,
            "top_p": 0.95, "top_k": 80, "repeat_penalty": 1.07,
            "mirostat": 2, "mirostat_tau": 8.0, "mirostat_eta": 0.1}
        print(f"[LLM →] POST {url}")
        r = requests.post(url, json=fb, timeout=THINK_TIMEOUT_SEC)
        r.raise_for_status()
        data = r.json()
        if LLM_ENDPOINT != "/completion":
            LLM_ENDPOINT = "/completion"
            print("[LLM] using /completion")
        reply = data.get("completion") or data.get("content") or ""
        return reply[:MAX_REPLY_CHARS]
    except Exception as e:
        print(f"[LLM legacy ERROR] {e}")
        raise

def tts_say(text: str) -> int:
    p = subprocess.run([sys.executable, str(TTS_PATH), "--text", text], check=False)
    return p.returncode


def contains_wake_word(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in WAKE_WORDS)

#def contains_wake_word(text: str) -> bool:
#    return True

class ConversationManager:
    def __init__(self) -> None:
        self.state = "WAKE"
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
            elif new_state == "LISTEN":
                leds_set("idle")
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
                        self.attentive_until = now + ATTENTION_TTL_SEC   # RENEW ATTENTION
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
                        self.attentive_until = self.last_speak_end + ATTENTION_TTL_SEC + ATTN_BONUS_AFTER_SPEAK

                    if time.monotonic() - self.last_speak_end >= SPEAK_COOLDOWN_SEC:
                        stt_resume()
                        self.set_state("ATTENTIVE_LISTEN")

                time.sleep(0.02)

        except KeyboardInterrupt:
            pass
        finally:
            stt_stop()


if __name__ == "__main__":
    ConversationManager().run()