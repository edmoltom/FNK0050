from __future__ import annotations
import os, sys, json, time, logging
from typing import Any, Dict
from app.services.vision_service import VisionService
from app.services.movement_service import MovementService
from app.controllers.social_fsm import SocialFSM
from network.ws_server import start_ws_server
from app.logging_config import setup_logging

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "app.json")

def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(config_path: str = CONFIG_PATH) -> None:
    setup_logging()
    vision_logger = logging.getLogger("vision")
    movement_logger = logging.getLogger("movement")
    fsm_logger = logging.getLogger("social_fsm")
    ft_logger = logging.getLogger("face_tracker")

    cfg = _load_json(config_path)
    latest_face_detection: Dict[str, Any] = {}

    def _store_latest_detection(result: Dict[str, Any] | None) -> None:
        latest_face_detection.clear()
        if result:
            latest_face_detection.update(result)

    enable_vision = bool(cfg.get("enable_vision", True))
    enable_ws = bool(cfg.get("enable_ws", True))
    enable_movement = bool(cfg.get("enable_movement", True))
    vision_cfg = cfg.get("vision", {}) or {}
    ws_cfg = cfg.get("ws", {}) or {}

    mode = vision_cfg.get("mode", "object")
    camera_fps = float(vision_cfg.get("camera_fps", 15.0))
    face_cfg = vision_cfg.get("face", {}) or {}
    svc = VisionService(mode=mode, camera_fps=camera_fps, face_cfg=face_cfg)

    fsm: SocialFSM | None = None
    if enable_movement:
        mc = MovementService()
        mc.start()
        mc.relax()
        fsm = SocialFSM(svc, mc, cfg)
    else:
        print("[App] Movement disabled in config.")

    prev_time = time.monotonic()

    if enable_vision:
        interval = float(vision_cfg.get("interval_sec", 1.0))
        print(f"[App] Starting vision stream (interval={interval}s)")

        def _handle_frame(result: Dict[str, Any] | None) -> None:
            nonlocal prev_time
            now = time.monotonic()
            dt = now - prev_time
            prev_time = now
            if fsm:
                fsm.on_frame(result, dt)
            _store_latest_detection(result)

        svc.start(interval_sec=interval, frame_handler=_handle_frame)
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
