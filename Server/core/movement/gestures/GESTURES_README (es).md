# Gestos por JSON (plantilla rápida)

**Dónde colocar los JSON**
- Coloca cada gesto en una carpeta `gestures/` junto a `controller.py`.
- El archivo debe llamarse `<nombre>.json`. Por ejemplo, `greet.json` se reproduce con `GestureCmd("greet")` o `GreetCmd`.

**Estructura del archivo**
```json
{
  "name": "my_gesture",
  "loop": false,
  "frames": [
    { "t": 0, "legs": [[x,y,z],[x,y,z],[x,y,z],[x,y,z]] },
    { "t": 500, "legs": [[...],[...],[...],[...]], "overrides": { "11": 120 } }
  ]
}
```
- `t`: tiempo **absoluto** en milisegundos desde el inicio del gesto.
- `legs`: **lista de 4** posiciones `[x,y,z]` (mm) en **coordenadas absolutas de pie**.
  - Convención típica: **X** hacia delante (+), **Y** arriba (+), **Z** a la izquierda (+).
  - Usa tu neutral actual como referencia (puedes leerlo de `controller.point`).
- `overrides` (opcional): diccionario `canal_servo → grados`. Se aplica en ese frame (p.ej. muñeca/pata).

**Interpolación y mezcla**
- El reproductor interpola **linealmente** entre frames a `tick_hz`.
- Si tu primer frame empieza con `t > 0`, el controlador **inyecta la pose actual** a `t=0` para evitar saltos.
- `loop: true` hace que el gesto se repita (si tu versión de `gestures.py` expone esa bandera).

**Cómo reproducir**
- Crea `gestures/<nombre>.json` y desde tu app lanza `GestureCmd("<nombre>")` (o el atajo que tengas).
- El gait se pausa mientras dure el gesto; al terminar, todo vuelve a estado normal.

**Consejos**
- Mantén `t` **estrictamente creciente** y en milisegundos.
- Limita XYZ a rangos seguros para tu cinemática; valida en frío antes de energizar.
- Para “waving” fino, añade varios frames con `overrides` separados por 10–20 ms.

¡Listo! Duplica la plantilla, ajusta `legs/overrides` y tendrás animaciones nuevas sin tocar Python.
