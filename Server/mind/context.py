import logging

from mind.persona import build_system
from mind.llm_client import LlamaClient
from mind.llm_memory import MemoryManager

logger = logging.getLogger(__name__)


class MindContext:
    def __init__(self, config):
        self.persona = build_system()
        self.llm = LlamaClient(config)
        self.memory = MemoryManager()
        logger.info("[COGNITIVE] Persona loaded successfully.")

    def summary(self):
        return {
            "persona": type(self.persona).__name__,
            "llm": type(self.llm).__name__,
            "memory": type(self.memory).__name__,
        }
