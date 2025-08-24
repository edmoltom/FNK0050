import pytest

voice_module = pytest.importorskip("Server.core.Voice_interface")


def test_conversation_manager_exists():
    assert hasattr(voice_module, "ConversationManager")
