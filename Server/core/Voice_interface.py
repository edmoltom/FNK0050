"""Legacy import wrapper for the new voice package."""

from .voice import ConversationManager, VoiceInterface, LLMClient, HTTPClient

__all__ = ["ConversationManager", "VoiceInterface", "LLMClient", "HTTPClient"]
