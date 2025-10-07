# Audición (`Server/core/hearing`)

## `stt.py`

`SpeechToText` encapsula el reconocimiento continuo con Vosk: abre un flujo `sounddevice.RawInputStream`, pasa los bloques al recognizer y, tras filtrar por confianza media (≥0.60) y longitud, emite frases normalizadas mediante `normalize_punct`. Expone métodos `pause`/`resume` para suspender temporalmente la emisión y conserva la interfaz CLI original (imprime cada frase con prefijo `>`).​:codex-file-citation[codex-file-citation]{line_range_start=29 line_range_end=123 path=Server/core/hearing/stt.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/hearing/stt.py#L29-L123"}​

## `text_norm.py`

`normalize_punct` limpia signos redundantes y añade signos de interrogación de apertura cuando detecta preguntas en español, asegurando además que todas las frases terminen en `.?!`.​:codex-file-citation[codex-file-citation]{line_range_start=6 line_range_end=23 path=Server/core/hearing/text_norm.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/hearing/text_norm.py#L6-L23"}​

