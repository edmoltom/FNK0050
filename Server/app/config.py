from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass
class VisionConfig:
    """Configuration for the vision subsystem."""
    enable: bool = True
    stream_interval: float = 0.2
    profile: str = "object"  # e.g. "object" or "face"
    threshold: float = 0.5
    model_path: str = "models/default.pt"


@dataclass
class MovementConfig:
    """Configuration for the movement subsystem."""
    enable: bool = True


@dataclass
class LoggingConfig:
    """Global logging configuration."""

    enable: bool = True
    level: str = "INFO"
    vision: bool = True
    movement: bool = False


@dataclass
class AppConfig:
    """Top-level application configuration."""
    vision: VisionConfig = field(default_factory=VisionConfig)
    movement: MovementConfig = field(default_factory=MovementConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api_key: str = ""


def load_config() -> AppConfig:
    """Load configuration from ``config.toml`` with sensible defaults."""

    cfg_path = Path(__file__).with_name("config.toml")
    data = {}
    if cfg_path.exists():
        with cfg_path.open("rb") as fh:
            data = tomllib.load(fh)

    vision_defaults = VisionConfig()
    vision_data = data.get("vision", {})
    vision = VisionConfig(
        enable=vision_data.get("enable", vision_defaults.enable),
        stream_interval=vision_data.get(
            "stream_interval", vision_defaults.stream_interval
        ),
        profile=vision_data.get("profile", vision_defaults.profile),
        threshold=vision_data.get("threshold", vision_defaults.threshold),
        model_path=vision_data.get("model_path", vision_defaults.model_path),
    )

    movement_defaults = MovementConfig()
    movement_data = data.get("movement", {})
    movement = MovementConfig(
        enable=movement_data.get("enable", movement_defaults.enable),
    )

    logging_defaults = LoggingConfig()
    logging_data = data.get("logging", {})
    logging_cfg = LoggingConfig(
        enable=logging_data.get("enable", logging_defaults.enable),
        level=logging_data.get("level", logging_defaults.level),
        vision=vision_data.get("log", logging_defaults.vision),
        movement=movement_data.get("log", logging_defaults.movement),
    )

    api_key = data.get("api_key", "")

    return AppConfig(
        vision=vision,
        movement=movement,
        logging=logging_cfg,
        api_key=api_key,
    )
