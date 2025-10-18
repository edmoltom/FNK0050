# Guía de humo para habilitar la conversación

Esta guía resume los pasos mínimos para comprobar el pipeline de conversación de `AppRuntime` antes de desplegar en un entorno con hardware real.

## Requisitos de hardware

* **Audio de entrada:** un micrófono USB o la tarjeta de sonido integrada con soporte ALSA/PulseAudio.
* **Audio de salida:** altavoces o auriculares conectados al sistema operativo.
* **Modelo LLM:** un modelo `GGUF` compatible con llama.cpp ubicado en el disco del servidor.
* **CPU/GPU:** el binario de `llama-server` incluido en tu build de llama.cpp debe compilarse para la arquitectura disponible (AVX/AVX2 en CPU x86_64 o CUDA si se desea offload a GPU).

## Configuración de la aplicación

El archivo por defecto `Server/app/app.json` incluye la sección `conversation`. Para habilitar la conversación:

```json
{
  "conversation": {
    "enable": true,
    "llama_binary": "/ruta/a/llama-server",
    "model_path": "/ruta/al/modelo.gguf",
    "port": 9090,
    "threads": 4
  }
}
```

* Ajusta `threads` y `max_parallel_inference` según los cores disponibles.
* Establece `enable` en `false` para desactivar la conversación de forma inmediata (útil en CI/staging).
* Se puede pasar un archivo alternativo usando `python Server/run.py --config path/al/config.json`.

## Lanzar `llama-server`

1. Verifica que el binario indicado tenga permisos de ejecución y que el modelo exista.
2. El `ConversationService` arranca automáticamente el proceso cuando `AppRuntime` lo solicita, pero para pruebas manuales puedes ejecutarlo directamente:

   ```bash
   ./llama-server -m /ruta/al/modelo.gguf --port 9090 --threads 4
   ```

3. Comprueba que el puerto esté libre y accesible (por defecto `9090`).

## Ejecución de humo

1. Ajusta la configuración como se describe arriba.
2. Lanza la aplicación con logging de información:

   ```bash
   python Server/run.py --config Server/app/app.json
   ```

3. Habla la palabra de activación (por defecto “humo”) y emite un comando corto. El robot debería:
   * Detectar la palabra clave y cambiar el estado de los LEDs a *listen*.
   * Consultar el LLM y reproducir una respuesta por TTS.

## Pruebas automatizadas con dependencias mockeadas

Para validar el pipeline en CI sin hardware:

```bash
pytest Server/tests/test_app_runtime_conversation_integration.py
```

La prueba usa stubs para STT, TTS y el proceso LLM, y verifica que se complete un ciclo de conversación y un apagado limpio. En pipelines donde no se desea arrancar la conversación basta con usar una configuración con `"enable": false`.

## Solución de problemas

* **El binario no arranca:** verifica permisos (`chmod +x`) y dependencias dinámicas del binario llama.cpp.
* **Timeout de readiness:** ajusta `health_timeout`, `health_check_interval` y `health_check_max_retries` en la configuración.
* **Audio sin salida:** valida que ALSA/PulseAudio reconozca el dispositivo y que ningún otro proceso esté bloqueando el acceso.
* **Fallo en CI:** usa el archivo de configuración por defecto o uno específico con `"enable": false` para omitir la conversación cuando no se dispone de audio.
