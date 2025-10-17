import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Default path for configuration file
CONFIG_PATH = Path(__file__).resolve().parent / "logging_config.json"

def setup_logging(config_path: Path = CONFIG_PATH):
    """Initialize logging from JSON configuration file."""

    if not config_path.exists():
        raise FileNotFoundError(f"Logging configuration not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # --- Root configuration ---
    root_cfg = config.get("root", {})
    root_level = getattr(logging, root_cfg.get("level", "INFO").upper(), logging.INFO)
    log_file = Path(root_cfg.get("file", "robot.log"))
    fmt = root_cfg.get("format", "%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    max_bytes = root_cfg.get("max_bytes", 1048576)
    backup_count = root_cfg.get("backup_count", 3)

    # Configure root logger
    logging.basicConfig(
        level=root_level,
        format=fmt,
        handlers=[
            RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    # --- Module-level configuration ---
    modules = config.get("modules", {})
    for name, level in modules.items():
        try:
            logging.getLogger(name).setLevel(getattr(logging, level.upper()))
        except AttributeError:
            logging.warning(f"[LOGGING] Invalid level '{level}' for module '{name}'")

    # --- Silenced modules ---
    for module in config.get("silenced", []):
        logging.getLogger(module).disabled = True
        logging.info(f"[LOGGING] Disabled logger: {module}")

    logging.info(f"[LOGGING] Configuration loaded from {config_path}")
