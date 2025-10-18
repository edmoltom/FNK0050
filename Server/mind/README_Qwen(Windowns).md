# Guía de instalación y uso de Qwen 2.5-0.5B Instruct (Windows)

Esta guía explica cómo instalar, descargar y ejecutar el modelo **Qwen 2.5-0.5B Instruct (GGUF)** en Windows utilizando `llama.cpp`.  
El objetivo es poder usarlo como modelo de lenguaje local dentro de **Lumo** o su **modo sandbox**.

---

## 🧩 Requisitos

1. **Windows 10 o 11 (64 bits)**
2. **Python 3.11 o superior** (opcional, si usas el sandbox)
3. **Compilador C++** compatible (VS Build Tools o MSYS2)
4. **Herramienta `git`** instalada
5. **Espacio libre**: al menos 2 GB

---

## ⚙️ Paso 1. Descargar y compilar `llama.cpp`

Abre una terminal (PowerShell o cmd) y ejecuta:

```cmd
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
```

Compila el binario:

```cmd
cmake -B build -DLLAMA_CURL=OFF
cmake --build build --config Release
```

El ejecutable llama-server.exe quedará disponible en:

..\llama.cpp\build\bin\Release\

## 🧠 Paso 2. Descargar el modelo Qwen 2.5-0.5B Instruct

Crea una carpeta dentro de tu proyecto (por ejemplo):

D:\Software development\Other\FNK0050\models\


Descarga el modelo en formato GGUF:

cd D:\Software development\Other\FNK0050\models
curl -L -o qwen2.5-0.5b-instruct-q3_k_m.gguf ^
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q3_k_m.gguf


(Alternativamente puedes descargarlo manualmente desde Hugging Face
 y colocarlo en esa carpeta.)

## 🚀 Paso 3. Ejecutar el servidor LLM

Lanza el servidor con el modelo:

```cmd
llama-server.exe ^
  --model D:\Software development\Other\FNK0050\models\qwen2.5-0.5b-instruct-q3_k_m.gguf ^
  --threads 4 ^
  --port 8080
```

Si todo va bien, verás una salida similar a:

main: server is listening on http://127.0.0.1:8080 - starting the main loop

## 🧩 Paso 4. Integrar con Lumo o el Sandbox

En el archivo sandbox/sandbox_config.json, asegúrate de incluir:

{
  "mode": "sandbox",
  "llm_server": "http://127.0.0.1:8080",
  "mock_behavior": "face_follow_loop"
}

## 🧩 Paso 5. Verificación rápida (opcional)

Puedes probar la conexión manualmente desde PowerShell:

```
curl -X POST http://127.0.0.1:8080/completion -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"Hola, ¿quién eres?\", \"n_predict\": 64}"
```

Deberías recibir una respuesta JSON con el texto generado.

## ⚙️ Paso 6. (Opcional) Simplificar la ejecución

Crea un script start_llm_server.bat en la raíz del proyecto:

```
@echo off
set MODEL_PATH=%~dp0models\qwen2.5-0.5b-instruct-q3_k_m.gguf
set SERVER_PATH=%~dp0llama.cpp\build\bin\Release\llama-server.exe
echo Starting llama-server with %MODEL_PATH%
"%SERVER_PATH%" --model "%MODEL_PATH%" --threads 4 --port 8080
pause
```