from __future__ import annotations
import os, sys, json, time
from typing import Any, Dict
from app.services.vision_service import VisionService
from network.ws_server import start_ws_server

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "app.json")

def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(config_path: str = CONFIG_PATH) -> None:
    cfg = _load_json(config_path)

    enable_vision = bool(cfg.get("enable_vision", True))
    enable_ws = bool(cfg.get("enable_ws", True))
    vision_cfg = cfg.get("vision", {}) or {}
    ws_cfg = cfg.get("ws", {}) or {}

    svc = VisionService()

    if enable_vision:
        interval = float(vision_cfg.get("interval_sec", 1.0))
        print(f"[App] Starting vision stream (interval={interval}s)")
        svc.start(interval_sec=interval)
    else:
        print("[App] Vision disabled in config.")

    if enable_ws:
        host = ws_cfg.get("host", "0.0.0.0")
        port = int(ws_cfg.get("port", 8765))
        print(f"[App] Starting WS server at {host}:{port}")
        start_ws_server(svc, host=host, port=port)
    else:
        print("[App] WS server disabled in config.")
        if enable_vision:
            try:
                while True:
                    time.sleep(1.0)
            except KeyboardInterrupt:
                pass

    if enable_vision:
        print("[App] Stopping vision…")
        svc.stop()
        print("[App] Vision stopped.")

if __name__ == "__main__":
    main()
