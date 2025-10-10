import logging

from mind.persona import build_system
from mind.llm_client import DEFAULT_BASE_URL, LlamaClient
from mind.llm_memory import MemoryManager
from mind.proprioception.body_model import BodyModel

logger = logging.getLogger(__name__)


class MindContext:
    def __init__(self, config):
        self.persona = build_system()

        llm_cfg = {}
        if isinstance(config, dict):
            candidate = config.get("llm")
            if isinstance(candidate, dict):
                llm_cfg = candidate
            else:
                conversation_cfg = config.get("conversation")
                if isinstance(conversation_cfg, dict):
                    nested_candidate = conversation_cfg.get("llm")
                    if isinstance(nested_candidate, dict):
                        llm_cfg = nested_candidate

        self.llm = LlamaClient(
            base_url=llm_cfg.get("base_url", DEFAULT_BASE_URL),
            request_timeout=llm_cfg.get("timeout", 30.0),
            model=llm_cfg.get("model", "local-llm"),
        )
        self.memory = MemoryManager()
        self.body = BodyModel()
        logger.info("[COGNITIVE] Persona loaded successfully.")
        logger.info(
            "[MIND] LlamaClient initialized for %s (model=%s)",
            self.llm.base_url,
            getattr(self.llm, "model", "unknown"),
        )
        logger.info("[MIND] BodyModel initialized (proprioception active).")

    def summary(self):
        return {
            "persona": type(self.persona).__name__,
            "llm": type(self.llm).__name__,
            "memory": type(self.memory).__name__,
            "body": self.body.summary(),
        }
