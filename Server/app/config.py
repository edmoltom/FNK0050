from __future__ import annotations

from dataclasses import dataclass, field
import os


@dataclass
class VisionConfig:
    """Configuration for the vision subsystem."""
    enable: bool = True
    profile: str = "object"  # e.g. "object" or "face"
    threshold: float = 0.5
    model_path: str = "models/default.pt"


@dataclass
class MovementConfig:
    """Configuration for the movement subsystem."""
    enable: bool = True


@dataclass
class AppConfig:
    """Top-level application configuration."""
    vision: VisionConfig = field(default_factory=VisionConfig)
    movement: MovementConfig = field(default_factory=MovementConfig)
    api_key: str = ""


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    vision = VisionConfig(
        enable=os.getenv("VISION_ENABLE", "1") == "1",
        profile=os.getenv("VISION_PROFILE", "object"),
        threshold=float(os.getenv("VISION_THRESHOLD", "0.5")),
        model_path=os.getenv("VISION_MODEL_PATH", "models/default.pt"),
    )
    movement = MovementConfig(
        enable=os.getenv("MOVEMENT_ENABLE", "1") == "1",
    )
    api_key = os.getenv("API_KEY", "")
    return AppConfig(vision=vision, movement=movement, api_key=api_key)
