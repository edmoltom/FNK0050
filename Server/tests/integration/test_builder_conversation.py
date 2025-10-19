import json
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest

cv2_stub = types.ModuleType("cv2")
cv2_stub.COLOR_RGB2BGR = 4
cv2_stub.COLOR_BGR2RGB = 2


def _noop(*_args, **_kwargs):
    return None


cv2_stub.setNumThreads = _noop
cv2_stub.cvtColor = _noop
cv2_stub.VideoCapture = object
sys.modules.setdefault("cv2", cv2_stub)

numpy_stub = types.ModuleType("numpy")
numpy_stub.ndarray = object
numpy_stub.float32 = float
numpy_stub.uint8 = int
sys.modules.setdefault("numpy", numpy_stub)
numpy_typing_stub = types.ModuleType("numpy.typing")
numpy_typing_stub.NDArray = object
sys.modules.setdefault("numpy.typing", numpy_typing_stub)

from Server.app.services.conversation_service import ConversationService

from Server.app.builder import build


def write_config(tmp_path: Path, data: dict) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(data))
    return config_path


def install_conversation_stubs(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    created: Dict[str, Any] = {}

    class DummyLLMClient:
        def __init__(
            self, *, base_url: str | None = None, request_timeout: float | None = None
        ) -> None:
            env_base = os.getenv("LLAMA_BASE", "http://127.0.0.1:8080")
            chosen = base_url or env_base
            self.base_url = str(chosen).rstrip("/")
            self.request_timeout = 30.0 if request_timeout is None else request_timeout

    def fake_llm_client(cfg: Dict[str, Any]) -> DummyLLMClient:
        client = DummyLLMClient(
            base_url=cfg.get("llm_base_url") or None,
            request_timeout=cfg.get("llm_request_timeout"),
        )
        created["llm_client"] = client
        created["llm_cfg"] = cfg
        return client

    class DummyProcess:
        def __init__(self, cfg: Dict[str, Any]) -> None:
            self.cfg = dict(cfg)

    def fake_process(cfg: Dict[str, Any]) -> DummyProcess:
        process = DummyProcess(cfg)
        created["process"] = process
        return process

    class DummySTT:
        pass

    def fake_stt(_cfg: Dict[str, Any]) -> DummySTT:
        stt = DummySTT()
        created["stt"] = stt
        return stt

    class DummyTTS:
        pass

    def fake_tts(_cfg: Dict[str, Any]) -> DummyTTS:
        tts = DummyTTS()
        created["tts"] = tts
        return tts

    class DummyLED:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    def fake_led(_cfg: Dict[str, Any]):
        led = DummyLED()
        created["led"] = led

        def _cleanup() -> None:
            created["led_cleanup_called"] = True
            led.close()

        return led, _cleanup

    def fake_manager_factory():
        holder: Dict[str, Any] = {}

        def register(event: Any) -> None:
            holder["stop_event"] = event
            created["registered_stop_event"] = event

        def factory(**kwargs: Any) -> Any:
            created["manager_factory_kwargs"] = kwargs
            manager = types.SimpleNamespace(**kwargs)
            manager.stop_event = holder.get("stop_event")
            manager.run = lambda: None
            manager.pause_stt = lambda: None
            manager.drain_queues = lambda: None
            manager.request_stop = lambda: None
            manager.stop = lambda: None
            return manager

        manager_kwargs = {"wait_until_ready": lambda: None}
        return factory, manager_kwargs, register

    monkeypatch.setattr("app.builder._build_conversation_llm_client", fake_llm_client)
    monkeypatch.setattr("app.builder._build_conversation_process", fake_process)
    monkeypatch.setattr("app.builder._build_conversation_stt_service", fake_stt)
    monkeypatch.setattr("app.builder._build_conversation_tts", fake_tts)
    monkeypatch.setattr("app.builder._build_conversation_led_handler", fake_led)
    monkeypatch.setattr("app.builder._build_conversation_manager_factory", fake_manager_factory)

    return created


def test_conversation_defaults_when_missing_section(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": False,
            "enable_movement": False,
        },
    )

    services = build(str(config_path))

    assert services.enable_conversation is False
    assert services.conversation_disabled_reason is None
    assert services.conversation is None
    assert services.conversation_cfg == {
        "enable": False,
        "llama_binary": "",
        "model_path": "",
        "port": 9090,
        "threads": 2,
        "health_timeout": 5.0,
        "health_check_interval": 0.5,
        "health_check_max_retries": 3,
        "health_check_backoff": 2.0,
        "llm_base_url": "",
        "llm_request_timeout": 30.0,
        "max_parallel_inference": 1,
    }


def test_conversation_disabled_when_required_paths_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": False,
            "enable_movement": False,
            "conversation": {
                "enable": True,
                "llama_binary": "",
                "model_path": "/models/model.gguf",
                "port": "8088",
                "threads": "4",
                "health_timeout": "6.5",
                "llm_base_url": "http://localhost",
                "max_parallel_inference": "2",
            }
        },
    )

    services = build(str(config_path))

    assert services.enable_conversation is False
    assert services.conversation_cfg == {
        "enable": False,
        "llama_binary": "",
        "model_path": "/models/model.gguf",
        "port": 8088,
        "threads": 4,
        "health_timeout": 6.5,
        "health_check_interval": 0.5,
        "health_check_max_retries": 3,
        "health_check_backoff": 2.0,
        "llm_base_url": "http://localhost",
        "llm_request_timeout": 30.0,
        "max_parallel_inference": 2,
    }
    assert services.conversation_disabled_reason is not None
    assert "llama_binary" in services.conversation_disabled_reason
    assert "paths not found" in services.conversation_disabled_reason
    assert any("llama_binary" in record.message for record in caplog.records)
    assert services.conversation is None


def test_conversation_client_uses_configured_url_and_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stubs = install_conversation_stubs(monkeypatch)
    llama_path = tmp_path / "llama"
    model_path = tmp_path / "model.gguf"
    llama_path.write_text("")
    model_path.write_text("")
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": False,
            "enable_movement": False,
            "conversation": {
                "enable": True,
                "llama_binary": str(llama_path),
                "model_path": str(model_path),
                "port": 8088,
                "threads": 4,
                "health_timeout": 6.5,
                "llm_base_url": "http://configured:8080",
                "llm_request_timeout": 12.5,
                "max_parallel_inference": 2,
            },
        },
    )

    services = build(str(config_path))

    assert services.enable_conversation is True
    assert isinstance(services.conversation, ConversationService)
    assert stubs["llm_client"].base_url == "http://configured:8080"
    assert stubs["llm_client"].request_timeout == 12.5
    assert stubs["registered_stop_event"] is services.conversation.stop_event
    assert services.conversation._extra_manager_kwargs["close_led_on_cleanup"] is False


def test_conversation_client_falls_back_to_env_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stubs = install_conversation_stubs(monkeypatch)
    monkeypatch.setenv("LLAMA_BASE", "http://env-base:9000")
    llama_path = tmp_path / "llama"
    model_path = tmp_path / "model.gguf"
    llama_path.write_text("")
    model_path.write_text("")
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": False,
            "enable_movement": False,
            "conversation": {
                "enable": True,
                "llama_binary": str(llama_path),
                "model_path": str(model_path),
                "port": 8088,
                "threads": 4,
                "health_timeout": 6.5,
                "llm_base_url": "",
                "max_parallel_inference": 2,
            },
        },
    )

    services = build(str(config_path))

    assert services.enable_conversation is True
    assert isinstance(services.conversation, ConversationService)
    assert stubs["llm_client"].base_url == "http://env-base:9000"
    assert stubs["llm_client"].request_timeout == 30.0
    assert stubs["registered_stop_event"] is services.conversation.stop_event
    assert services.conversation._extra_manager_kwargs["close_led_on_cleanup"] is False


def test_social_fsm_registers_conversation_callbacks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stubs = install_conversation_stubs(monkeypatch)

    class DummyVision:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

        def register_face_pipeline(self, _profile: str) -> None:
            return None

    class DummyMovement:
        def __init__(self) -> None:
            self.started = True

    class DummyFSM:
        def __init__(self, _vision, _movement, _cfg, callbacks=None) -> None:
            self.callbacks = dict(callbacks or {})

    vision_module = types.ModuleType("app.services.vision_service")
    vision_module.VisionService = DummyVision
    monkeypatch.setitem(sys.modules, "app.services.vision_service", vision_module)

    movement_module = types.ModuleType("app.services.movement_service")
    movement_module.MovementService = DummyMovement
    monkeypatch.setitem(sys.modules, "app.services.movement_service", movement_module)

    social_module = types.ModuleType("mind.behavior.social_fsm")
    social_module.SocialFSM = DummyFSM
    monkeypatch.setitem(sys.modules, "mind.behavior.social_fsm", social_module)

    llama_path = tmp_path / "llama"
    model_path = tmp_path / "model.gguf"
    llama_path.write_text("")
    model_path.write_text("")
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": True,
            "enable_movement": True,
            "conversation": {
                "enable": True,
                "llama_binary": str(llama_path),
                "model_path": str(model_path),
                "port": 8088,
                "threads": 4,
                "health_timeout": 6.5,
            },
        },
    )

    services = build(str(config_path))

    assert isinstance(services.conversation, ConversationService)
    assert isinstance(services.fsm, DummyFSM)
    assert "on_interact" in services.fsm.callbacks
    assert "on_exit_interact" in services.fsm.callbacks

    start_mock = mock.Mock()
    stop_mock = mock.Mock()
    monkeypatch.setattr(services.conversation, "start", start_mock)
    monkeypatch.setattr(services.conversation, "stop", stop_mock)

    services.fsm.callbacks["on_interact"](services.fsm)
    start_mock.assert_called_once_with()
    services.fsm.callbacks["on_exit_interact"](services.fsm)
    stop_mock.assert_called_once_with()

    assert stubs["registered_stop_event"] is services.conversation.stop_event
