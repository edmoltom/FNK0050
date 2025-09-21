# LEDs (`Server/core/led`)

## `LedController.py`

Controlador asíncrono que envuelve `led.Led`: encola operaciones en una `asyncio.Queue`, ejecuta funciones bloqueantes en un `ThreadPoolExecutor` (opcional) y ofrece utilidades para animaciones (`start_pulsed_wipe`, `rainbow`, etc.), detención segura y liberación de recursos (`close`).​:codex-file-citation[codex-file-citation]{line_range_start=8 line_range_end=107 path=Server/core/LedController.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/LedController.py#L8-L107"}​

## `led/led.py`

Capa delgada sobre `Freenove_SPI_LedPixel` para la placa SPI del robot: implementa operaciones básicas (`set_all`, `show`, `off`) y patrones sencillos (`colorWipe`, `rainbow`, `rainbowCycle`) además de un helper `_wheel` para generar colores.​:codex-file-citation[codex-file-citation]{line_range_start=4 line_range_end=96 path=Server/core/led/led.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/led/led.py#L4-L96"}​

## `led/spi_ledpixel.py`

Driver específico para tiras WS2812 sobre SPI: inicializa el bus con `spidev`, gestiona el formato de color (RGB/GRB), ajusta brillo y convierte los datos RGB a la señal SPI requerida (`write_ws2812_numpy8`/`numpy4`). También expone utilidades de depuración (información de GPIO, verificación de estado).​:codex-file-citation[codex-file-citation]{line_range_start=6 line_range_end=182 path=Server/core/led/spi_ledpixel.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/led/spi_ledpixel.py#L6-L182"}​

