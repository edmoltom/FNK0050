import logging
import os
from logging.handlers import RotatingFileHandler

# Place the log alongside the repository root
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "robot.log")


def setup_logging() -> None:
    """Configure root logging with a rotating file handler."""
    logger = logging.getLogger()

    root_level = os.getenv("ROOT_LOG_LEVEL", "DEBUG").upper()
    logger.setLevel(getattr(logging, root_level, logging.DEBUG))

    # Avoid adding multiple handlers if setup_logging is called more than once
    if any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        return

    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    conversation_level = os.getenv("CONVERSATION_LOG_LEVEL")
    if conversation_level:
        level_value = getattr(logging, conversation_level.upper(), None)
        if isinstance(level_value, int):
            conversation_logger = logging.getLogger("conversation")
            conversation_logger.setLevel(level_value)
