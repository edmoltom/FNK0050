@echo off
set MODEL_PATH=%~dp0models\qwen2.5-0.5b-instruct-q3_k_m.gguf
set SERVER_PATH=%~dp0llama.cpp\build\bin\Release\llama-server.exe
echo Starting llama-server with %MODEL_PATH%
"%SERVER_PATH%" --model "%MODEL_PATH%" --threads 4 --port 8080
pause