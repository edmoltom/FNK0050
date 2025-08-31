# Vision Profiles – Reference Guide

Este directorio contiene los perfiles JSON que configuran el **detector por contornos**.  
Los perfiles definen resolución de trabajo, parámetros de Canny, ajustes de rescate,  
umbral de color y pesos de scoring para elegir la mejor detección.

Actualmente se incluyen:

- **profile_big.json** → resolución alta (mayor precisión, más carga de CPU).  
- **profile_small.json** → resolución reducida (más rápido, menos preciso).  

## Parámetros principales

### Sección `proc`
- **proc_w / proc_h**: resolución interna del pipeline.  
  *Mayor resolución = más detalle pero más coste.*  
- **blur_k**: tamaño del kernel Gaussiano para suavizar.  
  *Suaviza ruido antes de Canny.*

### Sección `canny`
- **t1_init / t2_ratio**: umbrales iniciales de Canny.  
  *El algoritmo autoajusta dentro de los rangos `life_min` y `life_max`.*  
- **life_min / life_max**: rango aceptable de densidad de bordes.  
- **rescue_life_min**: umbral para activar el rescate adaptativo.  
- **kp**: ganancia de corrección. Cuánto se ajusta T1 en cada iteración.  
- **max_iter**: iteraciones máximas de ajuste.

### Sección `color_gate`
- **enable**: activa el filtro por color.  
- **mode**: `"lab_bg"` (LAB con diferencia a fondo) o `"hsv"`.  
- **combine**: `"OR"` o `"AND"`, cómo se combina máscara de color y bordes.  
- **lab.ab_thresh**: diferencia mínima en canal AB.  
- **hsv.lo / hsv.hi**: rangos HSV para la máscara de color.  
- **min_cover_pct / max_cover_pct**: cobertura mínima/máxima de color para aceptar un objeto.

### Sección `morph`
- **close_min / close_max**: tamaño de kernel de “closing”.  
- **dil_min / dil_max**: tamaño de dilatación.  
- **steps**: número de pasos intermedios para probar morfologías.

### Sección `premorph`
- **bottom_margin_pct**: porcentaje inferior de la imagen que se descarta antes de morfología.  
- **min_blob_px**: blobs más pequeños que esto se eliminan.  
- **fill_from_edges**: si `true`, rellena huecos conectados a bordes.

### Sección `geom`
- **ar_min / ar_max**: relación de aspecto mínima/máxima de los candidatos.  
- **bbox_min / bbox_max**: proporción mínima/máxima de bounding box respecto al frame.  
- **bbox_hard_cap**: límite duro de bbox en altura.  
- **fill_min / fill_max**: rango aceptable de “relleno” del contorno.  
- **min_area_frac**: área mínima de contorno aceptada.

### Sección `weights`
Estos pesos combinan características geométricas en un *score* final.  
- **area**: favorece áreas grandes.  
- **fill**: premia formas sólidas.  
- **solidity**: premia contornos compactos.  
- **circular**: favorece formas circulares.  
- **rect**: favorece rectangularidad.  
- **ar**: penaliza relaciones de aspecto alejadas del 1.  
- **center_bias**: penaliza distancia al centro de la imagen.  
- **dist**: peso de la penalización por distancia.

## Cómo actúa el *score*

El detector evalúa cada contorno candidato con la fórmula:

score = W_AREAarea + W_FILLfill + W_SOLIsolidity + W_CIRCcircularity + W_RECTrectangularity + W_ARaspect_ratio − (dist_from_center * W_CENTER_BIAS * W_DIST)


El contorno con mayor *score* dentro de los filtros pasa a ser el objeto detectado.

## Objetivo de cada perfil

- **profile_big.json**  
  Resolución de trabajo mayor (`proc_w` alto).  
  Pensado para objetos pequeños en imagen completa o cuando la precisión en bordes es crítica.  
  Más consumo de CPU, pero estabilidad superior en detección.

- **profile_small.json**  
  Resolución de trabajo reducida (`proc_w` bajo).  
  Diseñado para pruebas rápidas, entornos con poca CPU (Raspberry Pi en tiempo real).  
  Puede perder detalle fino, pero mantiene detecciones estables a bajo coste.

## Consejos de ajuste

- Empieza probando con `weights.center_bias` si quieres que el robot atienda más o menos al centro.  
- Ajusta `geom.bbox_min / bbox_max` según el tamaño esperado de objetos.  
- Si no detecta nada: baja `canny.life_min` o activa `color_gate.enable`.  
- Si detecta demasiado ruido: sube `canny.life_min` y `premorph.min_blob_px`.  
- Para favorecer un tipo de forma, toca los pesos (`circular`, `rect`, `ar`).  

---
