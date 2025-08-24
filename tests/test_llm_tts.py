from pathlib import Path


def test_llm_to_tts_script_exists():
    path = Path("Server/core/llm/llm_to_tts.py")
    assert path.is_file()
