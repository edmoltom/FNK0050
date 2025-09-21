# Voz (`Server/core/voice`)

## `tts.py`

`TextToSpeech` envuelve Piper y SoX en una clase reutilizable: auto-detecta modelos en `~/piper`, permite elegir configuración JSON y speaker, aplica una cadena de efectos (pitch, compand, phaser, etc.) y ejecuta el reproductor disponible (`aplay`/`paplay`/`play`). El método `speak` sintetiza en un directorio temporal y opcionalmente guarda el WAV final; el módulo conserva una CLI compatible con el script original.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=185 path=Server/core/voice/tts.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/voice/tts.py#L1-L185"}​

## `sfx.py`

Proporciona `play_sound`, que detecta el primer reproductor disponible y reproduce WAVs; si no encuentra ninguno, informa la ruta para reproducción manual.​:codex-file-citation[codex-file-citation]{line_range_start=10 line_range_end=29 path=Server/core/voice/sfx.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/voice/sfx.py#L10-L29"}​

## Integración superior

`VoiceInterface` combina `SpeechToText`, `TextToSpeech`, `LedController` y memoria de conversación para gestionar estados `WAKE → ATTENTIVE_LISTEN → THINK → SPEAK`, pausando el STT durante la generación de respuestas y controlando LEDs según el estado.​:codex-file-citation[codex-file-citation]{line_range_start=7 line_range_end=232 path=Server/core/VoiceInterface.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/VoiceInterface.py#L7-L232"}​

