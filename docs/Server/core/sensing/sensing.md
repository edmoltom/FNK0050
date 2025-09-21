# Sensores (`Server/core/sensing`)

## `IMU.py`

La clase `IMU` lee un MPU6050, aplica filtros de Kalman independientes para acelerómetro y giroscopio, y fusiona los datos mediante cuaterniones con control proporcional-integral, devolviendo `pitch`, `roll`, `yaw` y aceleraciones normalizadas en `update_imu`. Incluye un promedio inicial de 100 muestras para compensar offset y conserva un alias `imuUpdate` para compatibilidad con código legado.​:codex-file-citation[codex-file-citation]{line_range_start=6 line_range_end=92 path=Server/core/sensing/IMU.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/sensing/IMU.py#L6-L92"}​

## `odometry.py`

`Odometry` integra una odometría planar muy ligera: `tick_gait` suma desplazamiento en cada evento de zancada (según fase del CPG) y `zupt` permite anclar la posición cuando la pata está en apoyo y el giro es pequeño, usando un umbral configurable de velocidad angular.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=23 path=Server/core/sensing/odometry.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/sensing/odometry.py#L1-L23"}​

