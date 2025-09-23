import json
import sys
import types
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

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

from app.builder import build


def write_config(tmp_path: Path, data: dict) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(data))
    return config_path


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
    assert services.conversation_cfg == {
        "enable": False,
        "llama_binary": "",
        "model_path": "",
        "port": 9090,
        "threads": 2,
        "health_timeout": 5.0,
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
        "llm_base_url": "http://localhost",
        "llm_request_timeout": 30.0,
        "max_parallel_inference": 2,
    }
    assert services.conversation_disabled_reason is not None
    assert "llama_binary" in services.conversation_disabled_reason
    assert any("llama_binary" in record.message for record in caplog.records)


def test_conversation_client_uses_configured_url_and_timeout(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": False,
            "enable_movement": False,
            "conversation": {
                "enable": True,
                "llama_binary": "/bin/llama",
                "model_path": "/models/model.gguf",
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
    assert services.conversation is not None
    assert services.conversation.base_url == "http://configured:8080"
    assert services.conversation.request_timeout == 12.5


def test_conversation_client_falls_back_to_env_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLAMA_BASE", "http://env-base:9000")
    config_path = write_config(
        tmp_path,
        {
            "enable_vision": False,
            "enable_movement": False,
            "conversation": {
                "enable": True,
                "llama_binary": "/bin/llama",
                "model_path": "/models/model.gguf",
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
    assert services.conversation is not None
    assert services.conversation.base_url == "http://env-base:9000"
    assert services.conversation.request_timeout == 30.0
