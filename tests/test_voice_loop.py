from pathlib import Path


def test_voice_loop_scripts_exist():
    root = Path("Server/core/llm")
    assert (root / "llm_to_tts.py").is_file()
    assert (root / "stt.py").is_file()
