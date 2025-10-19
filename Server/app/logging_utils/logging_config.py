import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

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
    echo_to_console = bool(root_cfg.get("echo_to_console", False))

    # File handler (always active)
    handlers = [
        RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    ]

    # Optional console handler (for debug runs)
    if echo_to_console:
        handlers.append(logging.StreamHandler(sys.stdout))

    # Configure root logger
    logging.basicConfig(level=root_level, format=fmt, handlers=handlers)
    root_logger = logging.getLogger()

    # Always ensure CRITICAL and exception messages go to console
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.CRITICAL)
    console_handler.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(console_handler)

    # --- Module-level configuration with prefix matching ---
    modules = config.get("modules", {})
    log_summary = []

    # Snapshot of all known loggers
    known = list(logging.root.manager.loggerDict.keys())

    def apply_to_logger(logger_name: str, level_upper: str):
        lg = logging.getLogger(logger_name)
        if level_upper == "NONE":
            lg.disabled = True
            lg.propagate = False
            return "DISABLED"
        try:
            lg.setLevel(getattr(logging, level_upper))
            return level_upper
        except AttributeError:
            lg.setLevel(logging.INFO)
            logging.warning(f"[LOGGING] Invalid level '{level_upper}' for module '{logger_name}' (default=INFO)")
            return f"INVALID({level_upper})->INFO"

    for prefix, level in modules.items():
        level_upper = str(level).upper().strip()
        # Apply to prefix and all its child loggers
        matched = [name for name in known if name == prefix or name.startswith(prefix + ".")]
        if prefix not in matched:
            matched.append(prefix)

        for name in matched:
            apply_to_logger(name, level_upper)

        log_summary.append(f"{prefix}: {'DISABLED' if level_upper == 'NONE' else level_upper}")

    # Startup summary (compact)
    logging.info(f"[LOGGING] Configuration loaded from {config_path}")
    if log_summary:
        logging.info("[LOGGING] Module log levels (prefix mode):")
        for entry in log_summary:
            logging.info(f"    - {entry}")
