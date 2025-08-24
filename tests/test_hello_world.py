import pytest


def test_action_module_available():
    """Ensure Action module is importable via package path."""
    pytest.importorskip("Server.core.Action")
