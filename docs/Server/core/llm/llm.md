# LLM (`Server/core/llm`)

## Persona y memoria

- `persona.py` define los parámetros de sampling (temperatura, top-p/k, máximo de tokens) y construye el prompt de sistema con la personalidad “Lumo”, estado del robot y fragmentos prohibidos. La función `postprocess` filtra frases vetadas y recorta al número máximo de caracteres.​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=92 path=Server/core/llm/persona.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/llm/persona.py#L5-L92"}​
- `llm_memory.py` mantiene el historial corto de conversación (`ConversationMemory`), conservando los últimos N turnos y ensamblando la lista de mensajes (`system` + historial + entrada de usuario).​:codex-file-citation[codex-file-citation]{line_range_start=3 line_range_end=23 path=Server/core/llm/llm_memory.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/llm/llm_memory.py#L3-L23"}​

## Cliente y utilidades

- `llm_client.py` envía peticiones a `LLAMA_BASE` (`/v1/chat/completions`), fija parámetros de sampling y penalización de repetición y procesa la respuesta con `postprocess`.​:codex-file-citation[codex-file-citation]{line_range_start=6 line_range_end=22 path=Server/core/llm/llm_client.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/llm/llm_client.py#L6-L22"}​
- `llm_to_tts.py` reutiliza el motor de TTS para convertir un prompt único en audio tras consultar el LLM; está pensado como script directo y demuestra el flujo `build_system → query_llm → TextToSpeech`. (El CLI requiere completar el parser para definir `args.prompt`.)​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=41 path=Server/core/llm/llm_to_tts.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/llm/llm_to_tts.py#L1-L41"}​
- `start_llama_server.py` lanza `llama-server` (modelo Qwen 0.5B quantizado) con parámetros seguros para Raspberry Pi y valida la existencia del ejecutable/modelo antes de iniciar.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=37 path=Server/core/llm/start_llama_server.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/llm/start_llama_server.py#L1-L37"}​

