# Estado actual de la app web — Prestow

> Generado en la sesión del 26 de agosto de 2026.
> Este archivo documenta exactamente qué se construyó, cómo está organizado
> y qué falta. Leerlo antes de tocar cualquier archivo de `app/`.

---

## 1. Resumen de lo que se construyó

### Fase 0 (sesión anterior)

| Módulo | Archivo | Estado |
|---|---|---|
| API pura del modelo | `src/api.py` | ✅ Completo |
| Balance de peso | `src/balance_peso.py` | ✅ Completo |
| Test de estabilidad | `src/stability_test.py` | ✅ Completo, corrido con 5 semillas |
| Tests unitarios | `tests/test_balance_peso.py` | ✅ Pasan |
| Primer commit git | `9d54f38` | ✅ Hecho |

**Resultado del test de estabilidad (5 semillas, límite 180 s):**
Makespan idéntico en todas las corridas: **58.0963 h**. El solver es determinista
con la configuración actual (la semilla no se propaga a HiGHS por limitación del
binding PuLP/HiGHS — comportamiento conocido, no un bug).

### Fase 1 — Esqueleto navegable (sesión actual)

Estructura de archivos creada:

```
.streamlit/
  config.toml          ← tema: navy #0F3D5A, fondo blanco, gris F5F7FA
app/
  app.py               ← página Inicio (entry point de Streamlit)
  pages/
    1_Ejecutar.py      ← configura solver y ejecuta
    2_Resultados.py    ← KPIs + dashboard + tabla + descarga
  components/
    estilo.py          ← CSS global + paleta de colores exportada
    caso_demo.py       ← carga rutas del caso Kiwi Arrow en session_state
    formato.py         ← funciones de formateo + generación de Excel/CSV
    vista_buque.py     ← visualizaciones Plotly del plan de estiba
```

Commit: **f0c6cd5** — "Fase 1.5: interfaz Streamlit con dashboard visual del buque"

---

## 2. Qué hace cada página

### `app/app.py` — Inicio

- Hero con gradiente navy y ondas SVG inline (opacidad 0.05), sin datos
  específicos del Kiwi Arrow en el landing.
- Card "¿Qué genera el sistema?" con los 4 entregables (Excel, KPIs, vista visual, reporte).
- Botón "▶ Ejecutar caso demo" → llama a `cargar_caso_demo()` y navega a `1_Ejecutar.py`.
- Sidebar: "Prestow" + "Optimizador de plan de estiba" + "© 2026".
- `page_title="Inicio"` para que el menú lateral lo muestre correctamente.

### `app/pages/1_Ejecutar.py` — Ejecutar

- Verifica que `session_state["metadata"]` exista; si no, redirige al inicio.
- **Grilla de 6 cards** (3×2): buque, bodegas, destinos, unidades, toneladas, productos.
  Cada card con icono grande, valor bold y label pequeño, `border-left: 4px solid TEAL`.
- Expander de parámetros: selector de solver (HiGHS/CBC) + slider límite 30-300 s.
- Botón "🚀 Calcular plan de estiba" → llama a `resolver_prestow()` con spinner.
- Al terminar: guarda `resultado`, `resultado_excel` y `resultado_kpis_csv` en
  session_state; muestra makespan y ahorro; botón a Resultados.
- Errores: capturados con try/except, mensaje amigable al usuario, sin tracebacks.

### `app/pages/2_Resultados.py` — Resultados

**Secciones en orden:**

1. **3 métricas Streamlit**: makespan (delta: texto explícito "X h más rápido que el
   plan de referencia"), ahorro en horas y %, tiempo de cálculo.

2. **4 KPI cards**: desbalance (verde/ámbar/rojo según umbral), fragmentación,
   izadas totales, unidades embarcadas. Cards con `border-left` por categoría.

3. **⚓ Vista del buque** (sección nueva):
   - Timeline de cuadrillas (Plotly, barras horizontales).
   - Vista lateral del buque con selector de modo.
   - Detalle de capas por bodega (selectbox 1-8).
   - Expander "Fragmentación por destino" con heatmap.

4. **Tabla del plan** (`st.dataframe`), ordenada por bodega y plan.

5. **Descarga**: Excel (2 hojas: Plan + KPIs), CSV de KPIs, botón "Ejecutar de nuevo".

6. **Expander técnico**: estado del solver (texto legible, no "Estado PuLP: Optimal"),
   gap con nota si es None, verificaciones.

---

## 3. Componentes reutilizables

### `app/components/estilo.py`

Exporta **9 constantes de color** (top-level, importables directamente):
```python
AZUL_MARINO = "#0F3D5A"
TEAL        = "#0891B2"
DORADO      = "#C89B3C"
CORAL       = "#F97316"
VERDE       = "#10B981"
GRIS_FONDO  = "#F5F7FA"
GRIS_BORDE  = "#E2E8F0"
TEXTO_PRINCIPAL   = "#1E293B"
TEXTO_SECUNDARIO  = "#64748B"
```

Función `aplicar_estilo_global()` — inyecta CSS con Inter, cards con sombra,
variantes `.card-info / .card-datos / .card-accion / .card-resultado`,
tipografía bold con letter-spacing negativo.

### `app/components/caso_demo.py`

`cargar_caso_demo()` — puebla `session_state` con:
- `ruta_datos`: path a `data/datos_entrada_kiwi_arrow.xlsx`
- `ruta_capacidades`: path a `data/capacidades.csv`
- `metadata`: dict con buque, bodegas, unidades, toneladas, destinos, productos,
  `makespan_manual_h=60.61`
- Limpia `resultado`, `resultado_excel`, `resultado_kpis_csv` de corridas previas.

### `app/components/formato.py`

| Función | Qué hace |
|---|---|
| `formato_horas(h)` | `58.096 → "58 h 6 min"` |
| `formato_unidades(u)` | `29332 → "29.332"` (punto como separador de miles) |
| `formato_toneladas(t)` | `59197.0 → "59.197,0"` |
| `formato_diferencia(delta, unidad)` | `(texto, color_hex)` según signo |
| `generar_excel_bytes(resultado)` | `bytes` — 2 hojas: Plan de estiba + KPIs |
| `generar_kpis_csv(resultado)` | `str` CSV con indicadores |

### `app/components/vista_buque.py`

Módulo Plotly puro (sin Streamlit). Constantes de color definidas localmente
(duplica la paleta de estilo.py, no importa de ahí, para evitar dependencia
circular con `import streamlit`).

| Función | Descripción |
|---|---|
| `plot_timeline_cuadrillas(horas, makespan)` | Barras horizontales, coral = cuello de botella, línea punteada en makespan |
| `plot_vista_lateral(plan, modo)` | Silueta del buque. Modos: Destinos / Llenado / Cuadrillas / Izadas |
| `plot_capas_bodega(plan, bodega)` | 11 capas apiladas verticalmente, coloreadas por destino, divididas si mixtas |
| `plot_heatmap_destinos(plan)` | Heatmap bodega × destino, escala Blues, anotaciones numéricas |

**Mapeo cuadrilla → bodegas** (según CLAUDE.md):
- Cuadrilla 1: bodegas 7, 8
- Cuadrilla 2: bodegas 5, 6
- Cuadrilla 3: bodegas 3, 4
- Cuadrilla 4: bodegas 1, 2

**Colores de destino**:
- TAICHUNG → TEAL `#0891B2`
- QINGDAO → DORADO `#C89B3C`
- KUNSAN → AZUL_MARINO `#0F3D5A`
- ULSAN → CORAL `#F97316`

---

## 4. Decisiones de diseño tomadas en estas fases

- **Sin datos numéricos del caso base en el landing**: la página Inicio no menciona
  58,19 h ni el Kiwi Arrow. Son datos del caso demo, no de la propuesta de valor.
- **`page_title="Inicio"`** en `app.py` para que el menú lateral de Streamlit lo
  muestre con ese nombre (en vez de "app").
- **`_LAYOUT_BASE` sin `margin`**: las 4 funciones de Plotly declaran su propio
  `margin` para evitar el error "multiple values for keyword argument 'margin'".
- **Constantes de color en `vista_buque.py` son locales**: no se importan de
  `estilo.py` porque ese módulo importa `streamlit`, lo que causa errores cuando
  Plotly se usa fuera del contexto de Streamlit (tests, scripts).
- **Gap del solver**: se muestra "Gap no disponible (limitación conocida de HiGHS +
  Python)" cuando es None. No se inventa un valor.
- **Estado del solver**: se muestra "Solución encontrada dentro del tiempo asignado"
  en vez de "Estado PuLP: Optimal" que era engañoso.

---

## 5. Bugs corregidos en esta sesión

| Bug | Causa | Fix |
|---|---|---|
| `ImportError: cannot import name 'AZUL_MARINO'` | Bytecode `__pycache__` obsoleto de la versión anterior de `estilo.py` | Limpiar `__pycache__` + reiniciar Streamlit |
| `TypeError: multiple values for keyword argument 'margin'` en `update_layout()` | `_LAYOUT_BASE` tenía `margin` y cada función también pasaba `margin=` | Eliminar `margin` de `_LAYOUT_BASE` |
| `NameError: name 'TEXTO_PRINCIPAL' is not defined` en `vista_buque.py` | La constante existe en `estilo.py` pero no se copió a `vista_buque.py` | Agregar `TEXTO_PRINCIPAL` y `TEXTO_SECUNDARIO` al bloque de constantes de `vista_buque.py` |
| Delta de makespan confuso (`↓ -2.51`) | `st.metric(delta=número_negativo)` muestra flecha verde con signo negativo | Cambiar a `delta="2.51 h más rápido que el plan de referencia"` (texto explícito) |

---

## 6. Lo que falta construir (Fase 2 en adelante)

### Formularios editables (Fase 2)

- **Configuración del buque**: editar bodegas, cuadrillas, número de planes.
- **Productos**: agregar/quitar productos → re-correr `packer_2d.py` automáticamente.
- **Viaje**: editar unidades por (producto, destino).
- **Rotación**: reordenar puertos.

### Módulos `src/` pendientes

- `src/layout_capa.py` — posiciones (x, y, rotación) de cada unidad en la capa.
  Hoy el packer solo devuelve totales.
- `src/secuencia_izadas.py` — orden de carga dentro de cada capa (destino →
  producto → columnas), grupos de 16 unidades por izada.
- Estos dos módulos son prerrequisito para la "Planimetría visual tipo prestow"
  mencionada en CLAUDE.md sección 4.

### Pendientes menores

- **Warm start** desde el plan real (garantía de que nunca se supera 60,61 h).
- **275 unidades sin reconciliar** entre las dos vías de extracción del caso base.
- **La pasada 2 no resuelve en 180 s** — fragmentación queda sin optimizar del todo.
- **Pruebas automatizadas** de la app web (todo se verifica manualmente hoy).
- **Semilla de HiGHS no se propaga**: `options={"random_seed": seed}` se acepta
  pero no se reenvía al solver. Requiere actualizar PuLP o escribir un archivo `.opt`.

---

## 7. Cómo correr la app

```bash
# Activar entorno virtual (Windows)
.venv\Scripts\Activate.ps1

# Lanzar la app
streamlit run app/app.py

# URL local
http://localhost:8501
```

La app no necesita los formularios para funcionar — el caso demo usa los archivos
en `data/` directamente. El flujo completo es:
**Inicio → "▶ Ejecutar caso demo" → Ejecutar → "🚀 Calcular" (~6 min) → Resultados**

---

## 8. Fase 2 — formularios editables, planimetría, izadas y balance de peso

> Sesión del 21 de septiembre de 2026. Completa las secciones que faltaban de
> la tabla de la sección 4 de CLAUDE.md: Configuración del buque, Productos,
> Viaje, Rotación, Planimetría, Izadas y secuencia, y Balance de peso.

### Módulos nuevos en `src/`

| Módulo | Qué hace |
|---|---|
| `src/layout_capa.py` | Posición (x, y, rotación) de cada unidad dentro de una capa. `calcular_layout_capa()` llena grilla uniforme para capas de un solo producto/destino (80 de 85 capas del caso base); para capas mixtas reparte el piso en franjas verticales proporcionales al área de cada grupo (SUPUESTO declarado en el docstring: es una aproximación de visualización, no una cota de capacidad — la capacidad real la valida `capacidades.csv`). `obtener_huellas()` y `obtener_geometria_bodegas()` leen (largo, ancho) reales desde el Excel/carpeta de entrada, algo que `HUELLA`/`PISO` de `modelo_prestow.py` no exponen por separado (`HUELLA` solo guarda el área). |
| `src/secuencia_izadas.py` | Agrupa el layout de una capa en izadas de `UNIDADES_POR_IZADA=16`. Orden heurístico (no viene del modelo, documentado en el docstring): destino según rotación de descarga (se carga primero el que se descarga al final) → producto → barrido en serpentina por columna. |

Ambos con tests en `tests/test_layout_capa.py` y `tests/test_secuencia_izadas.py`
(11 casos, incluye que la capa mono-producto reproduce las 194 unidades
verificadas de N_ALDEA_EKP en bodega 1).

### Página nueva: `app/pages/0_Configuracion.py`

Formularios editables con `st.data_editor` en cuatro tabs: Buque, Productos,
Viaje, Rotación. Usa `app/components/config_editable.py` (funciones puras,
sin Streamlit):

- `leer_tablas_editables(ruta_datos)` — lee las 4 hojas del Excel a DataFrames.
- `validar_tablas(tablas)` — coherencia mínima (bodegas/productos/destinos sin
  duplicar, huellas y unidades positivas, que Viaje solo use productos/destinos
  declarados).
- `guardar_tablas_editables(tablas, carpeta)` — escribe 4 CSV en el formato que
  ya leen `packer_2d.leer_entrada` y `modelo_prestow.cargar_desde_csv`
  (`buque_editado.csv`, `productos_editado.csv`, `rotacion_editado.csv`,
  `viaje_editado.csv`). **Usa `df.to_dict("records")`, no `df.iterrows()`**:
  iterrows sube toda la fila al mismo dtype cuando hay columnas mixtas
  (`bodega` int junto a `largo_m` float), y escribía "8.0" en vez de "8" — se
  encontró y corrigió en esta sesión.
- `recalcular_capacidades(carpeta)` — corre `packer_2d` sobre la carpeta
  editada. Se llama automáticamente al guardar; agregar un producto nuevo
  dispara el recálculo sin que el usuario corra nada a mano (requisito de
  CLAUDE.md sección 4).
- `resumen_metadata(tablas)` — arma la metadata de la web. Marca
  `es_caso_base: False` y `makespan_manual_h: None`: un caso editado no tiene
  plan manual de referencia contra el cual comparar.

Al guardar: valida, escribe la carpeta (persistente en
`session_state["carpeta_config_editada"]`, se reusa entre guardados),
recalcula capacidades, actualiza `ruta_datos`/`ruta_capacidades`/`metadata`, y
limpia cualquier resultado/caché previo (`resultado`, `huellas_productos`,
`geometria_bodegas`, etc.) para que Resultados no mezcle datos de una
corrida anterior con la config nueva.

**Probado de punta a punta**: se agregó un producto ficticio vía las tablas
editables, se guardó, se verificó que `capacidades.csv` lo incluyera para las
8 bodegas, y se corrió `resolver_prestow()` sobre la carpeta editada — el
modelo ubicó correctamente las 100 unidades del producto nuevo.

### `1_Ejecutar.py` y `2_Resultados.py`: soporte para casos sin plan de referencia

Antes, `meta.get("makespan_manual_h", 60.61)` fallaba silenciosamente mal: si
la clave existe con valor `None` (caso editado), `.get(..., default)` devuelve
`None`, no el default, y `ahorro = None - resultado.makespan` revienta.
Corregido en ambas páginas: si no hay `makespan_manual_h`, se muestra el
makespan sin comparación ("Caso editado: sin plan de referencia para
comparar") en vez de crashear.

También se guarda `parametros_corrida` en `session_state` al ejecutar
(solver, límite de segundos, ruta de datos, fecha/hora) y se genera un tercer
CSV descargable con `generar_reporte_parametros()` (nuevo en
`components/formato.py`) — cierra el pendiente de CLAUDE.md sección 4,
"reporte de parámetros de la corrida" en Descarga.

### `2_Resultados.py`: dos secciones nuevas

**🗺️ Planimetría y secuencia de izadas** (entre "Vista del buque" y la tabla
del plan): selector de bodega + plan (capa) + "colorear por"
(Destino/Producto/Orden de izada — nombre del selectbox deliberadamente
distinto del "Colorear por" de la vista lateral de arriba, que ya existía;
tener dos widgets con la misma etiqueta rompía la navegación y los tests
headless no podían distinguirlos). Dibuja la capa real con
`plot_planimetria_capa()` (nuevo en `vista_buque.py`, usa el truco de un solo
trace de Plotly con muchos rectángulos separados por `None` — cientos de
polígonos sin crear un trace por unidad) y lista la secuencia de izadas en un
expander con `st.dataframe`.

**⚖️ Balance de peso (informativo)**: usa `balance_peso.calcular_balance()`
(ya existía, no estaba conectado a la web) con `plot_balance_peso()` (nuevo,
barras de peso + línea de densidad). Encabezado explícito de que no es
restricción del modelo (CLAUDE.md sección 6).

Ambas secciones están en `try/except` con mensaje de error legible: si
`layout_capa`/`secuencia_izadas`/`balance_peso` fallan por datos raros, la
página no se cae completa.

### Cómo se probó (sin navegador — ver nota abajo)

- `streamlit.testing.v1.AppTest` para correr las páginas sin servidor: carga
  `2_Resultados.py` con un `ResultadoCorrida` real (resuelto con límite bajo,
  15-60 s, solo para probar el wiring) y verifica `len(at.exception) == 0`.
  Se probaron también las interacciones (cambiar "Colorear planimetría por" a
  cada opción, cambiar de bodega) y `0_Configuracion.py` completo (cargar
  demo → editar → guardar).
- **No se pudo probar en navegador real**: la extensión Claude in Chrome no
  estaba conectada en esta sesión. `AppTest` cubre errores de ejecución
  (excepciones, imports rotos) pero no verifica layout visual ni CSS — antes
  de dar la Fase 2 por definitiva conviene una pasada visual en navegador.

### Pendiente detectado, no resuelto en esta sesión

- El plan manual de referencia (60,61 h) y todas sus comparaciones solo
  aplican al caso base Kiwi Arrow. Un caso editado no tiene esa referencia:
  quedó resuelto que las páginas no revienten (ver arriba), pero no hay forma
  de que el usuario sepa qué tan bueno es su resultado editado sin un plan
  manual propio. Fuera de alcance por ahora.
- `data/stability_report.csv` (5 semillas, `stability_test.py`) estaba
  generado pero no comiteado — confirma makespan idéntico (58,0963 h) y
  asignación por bodega idéntica en las 5 corridas. Esto cierra el pendiente
  #1 de CLAUDE.md sección 10 ("estabilidad de la asignación entre corridas"):
  el solver es determinista con la configuración actual. No se editó
  CLAUDE.md — esa es una decisión del equipo, no algo para cambiar sin aviso.

---

## 9. Correcciones de accesibilidad y UX (misma sesión, después de la Fase 2)

Reportadas por el usuario después de probar la Fase 2 en Opera:

- **Borrado de filas no funcionaba en Configuración.** `st.data_editor` con
  `num_rows="dynamic"` permite agregar (muy descubrible: fila en blanco al
  final) pero borrar requiere seleccionar la fila y una tecla, poco
  descubrible y con comportamiento inconsistente entre navegadores. Se
  reemplazó por botones explícitos "➕ Agregar" / selector + "🗑️ Eliminar
  fila" en las 4 tablas (`app/pages/0_Configuracion.py`), con
  `num_rows="fixed"` en la grilla (edición de celdas sí, agregar/quitar filas
  no). Requirió un patrón de versión de `key` (`editor_buque_{version}`) para
  forzar que la grilla se recargue desde `session_state` después de un
  cambio programático — sin eso, la grilla conserva su estado interno viejo
  aunque el `value=` que se le pasa haya cambiado.
- **Orden de bodegas invertido en Configuración** (aparecía 8,7,6...1 — así
  las lista el Excel del puerto). `leer_tablas_editables()` ahora ordena por
  bodega ascendente al leer (`app/components/config_editable.py`); no afecta
  al modelo, que ya ordena `BODEGAS` internamente.
- **Viaje y Rotación con listas desplegables** en vez de texto libre:
  `st.column_config.SelectboxColumn` para producto/destino en Viaje (usa las
  listas de Productos/Rotación ya editadas en la misma sesión) y para
  destino en Rotación (lista curada `PUERTOS_CELULOSA_REFERENCIA` en
  `config_editable.py` — puertos importantes que reciben celulosa, compilada
  por Claude, **no verificada por el puerto**, formato uppercase igual que
  los 4 existentes).
- **Límite de tiempo del solver**: slider de `1_Ejecutar.py` subido de
  máximo 300 s a 360 s por pasada (hasta 12 min totales entre pasadas 1 y 2).
- **Tooltip en "Origen del dato"** (columna de Productos): explica que
  documenta si la huella se midió en una plantilla real o es un supuesto.
- **Guía de navegación en Inicio** (`app/app.py`): tarjetas explicando qué
  hace cada página (Configuración, Ejecutar, Resultados) en lenguaje simple,
  con nota de dónde está el menú lateral.

Bug encontrado y corregido en el camino: un `.replace(",", ".")` aplicado
sobre un f-string con concatenación implícita de varios literales convertía
también las comas de puntuación de la oración en puntos (mensaje de éxito al
guardar en Configuración). Se corrigió usando `formato_unidades()` solo
sobre el número, no sobre todo el mensaje.

---

## 10. Pasada 3: balance de peso — investigación completa (misma sesión)

A pedido explícito del dueño del proyecto se reabrió la decisión cerrada de
CLAUDE.md sección 6 ("no agregar restricciones de peso"). Ver el detalle de
la decisión y el resultado final en CLAUDE.md sección 6. Acá queda el
registro completo de la investigación, para no repetir el camino si alguien
quiere subir `ETAPAS_BALANCE_PESO` en el futuro.

### Qué se construyó

- `src/modelo_prestow.py`: nuevo global `PESO[p]` (peso por unidad, ya se
  leía `peso_t` del Excel/CSV pero se descartaba), nueva pasada 3
  lexicográfica (`preparar_pasada3()`), nuevas variables `peso_max[k]` /
  `peso_min[k]` por etapa del viaje, nueva restricción (10). La restricción
  (9) de ruptura de simetría (ver su propio comentario "OJO": asume bodegas
  gemelas intercambiables) se retira específicamente antes de resolver la
  pasada 3, porque ahí es donde molesta — en las pasadas 1 y 2 sigue activa
  y ayuda mucho al solver.
- `src/api.py`: `ResultadoCorrida` gana el campo `excel_bytes` (el Excel
  oficial de `modelo_prestow.exportar_excel()`, generado con el lock tomado
  porque esa función lee globales del módulo). Nueva función
  `_resolver_con_warm_start()`: como PuLP no expone warm start para HiGHS en
  esta versión (3.3.2), reproduce a mano la secuencia interna de
  `pulp.HiGHS.actualSolve()` para poder inyectar la solución de la pasada 2
  como punto de partida de la pasada 3, usando `highspy.HighsSolution`
  directamente.
- `app/components/formato.py`: `generar_excel_bytes()` reescrito para partir
  del Excel oficial del modelo y agregarle hojas ("Izadas y secuencia" con
  TODAS las capas, "Balance de peso", "Parámetros de la corrida") — antes
  generaba su propio Excel simplificado de 2 hojas y había 2 CSV sueltos
  además. Ahora es un solo archivo de descarga.
- `app/components/vista_buque.py`: `plot_planimetria_capa()` rediseñado —
  bordes oscuros + hueco entre unidades (antes borde blanco fino, difícil de
  distinguir "paquetes" individuales), y recuadros punteados con el conteo
  de cada izada superpuestos (packs de 16, como pidió el usuario). Se sacó
  el modo de color "Orden de izada" (redundante con el nuevo overlay
  siempre visible).

### Cronología de la investigación (todo con el caso base Kiwi Arrow)

| # | Configuración | Resultado |
|---|---|---|
| 1 | 4 etapas, sin warm start, 90 s | Pasada 1 ni siquiera resuelve (la ruptura de simetría desactivada globalmente por error de diseño inicial frenaba TODO, no solo la pasada 3) |
| 2 | 4 etapas, sin warm start, 45 s — **con la simetría restaurada para pasadas 1-2** | Pasadas 1-2 OK; pasada 3 sin solución factible |
| 3 | 4 etapas, sin warm start, 180 s | Pasadas 1-2 OK (makespan 58,10 h); pasada 3 sin solución factible |
| 4 | 4 etapas, sin warm start, 900 s | Pasadas 1-2 OK (makespan 57,78 h, mejor); pasada 3 **sigue sin solución factible tras 45 min** — no era falta de tiempo |
| 5 | 1 etapa, sin warm start, 180 s | Pasada 3 sin solución factible (versión 4x más chica y tampoco alcanza) |
| 6 | 1 etapa, **con warm start**, 180 s | **Pasada 3 converge**: gap 16,1%, desbalance 4.930,82 t |
| 7 | 4 etapas, con warm start, 180 s | Pasada 3 encuentra factible (a diferencia de sin warm start) pero gap 77,4% |
| 8 | 4 etapas, con warm start, 600 s dedicados a la pasada 3 | **Primal bound idéntico** a la corrida de 180 s (30.031,34) — el solver exploró 5x más nodos sin mejorar nada: no es un problema de tiempo |
| 9 | 4 etapas, con warm start, tolerancia de pasada 2 aflojada 10x (2→20), 180 s | Mejora marginal (27.853,78 t, gap 75,6%) — la tolerancia no era el cuello de botella real |
| 10 | 1 etapa, con warm start, 180 s (repetición de la config final) | 9.152,62 t, gap 54,6% — **distinto** al de la fila 6 con la misma configuración: HiGHS no es determinista cuando no prueba optimalidad |

### Diagnóstico

1. **Sin warm start, la pasada 3 no encuentra ningún punto factible por su
   cuenta**, ni con mucho tiempo. PuLP no expone warm start para HiGHS en la
   versión instalada (`pulp.HiGHS.actualSolve()` reconstruye el modelo desde
   cero en cada `.solve()`), así que hubo que llamar a los métodos internos
   del solver a mano (`createAndConfigureSolver` → `buildSolverModel` →
   inyectar `highspy.HighsSolution` → `callSolver` → `findSolutionValues`).
   Con eso, la pasada 3 arranca desde la solución (ya factible) de la
   pasada 2 en vez de buscar una desde cero.
2. **Con warm start, la pasada 3 de 4 etapas SÍ encuentra factibilidad, pero
   se estanca**: ni 900 s de tiempo ni una tolerancia 10x más floja la
   sacan de un gap de 75-77%. La hipótesis más probable es que la relajación
   LP de "minimizar la suma de rangos máximo-menos-mínimo en 4 etapas, sin
   ruptura de simetría" es intrínsecamente débil para este solver —
   arreglarlo de verdad necesitaría desigualdades válidas más sofisticadas
   (trabajo de investigación en optimización, no un ajuste de parámetros).
3. **La versión de 1 sola etapa (carga inicial) sí converge razonablemente**
   (gap ~16-55% según la corrida — variable, ver más abajo), muy por encima
   de las 4 etapas. Es además la métrica que ya se había medido antes del
   proyecto (36,8% vs 18,9%), solo que ahora el modelo la optimiza en vez de
   solo medirla.
4. **El resultado exacto de la pasada 3 varía entre corridas** del mismo
   caso con los mismos parámetros (filas 6 y 10 de la tabla: 4.930,82 t vs
   9.152,62 t). A diferencia del resto del modelo (determinista, ver
   `data/stability_report.csv`), la pasada 3 nunca prueba optimalidad dentro
   del tiempo estándar, así que el punto exacto donde el solver se detiene
   depende del no-determinismo interno de HiGHS (orden de exploración,
   timing). El KPI `balance_peso_desbalance_ton` solo se informa cuando la
   pasada 3 realmente resolvió (`pasada3_exitosa=True` en `api.py`); si no,
   no se muestra un número — mostrar los valores sin optimizar de la pasada
   2 hubiera sido un número sin sentido (se detectó y corrigió esto en el
   camino: la primera versión mostraba 29.845,5 t, que no era un balance
   real).

### Configuración final

`USAR_BALANCE_PESO = True`, `ETAPAS_BALANCE_PESO = 1` (solo la carga
inicial), `TOLERANCIA_PASADA3 = 2.0` (valor original, la versión floja no
ayudó lo suficiente para justificar el riesgo de empeorar la fragmentación),
`limite_segundos_balance` por defecto igual a `limite_segundos` (no hace
falta más tiempo con 1 etapa). Antes de subir `ETAPAS_BALANCE_PESO`, resolver
el problema de fondo de la relajación débil — ya se probó que más tiempo y
más tolerancia no alcanzan por sí solos.

---

## 11. Izadas como bloques rectangulares + explicaciones (misma sesión, después de probar la hoja Planimetría)

El usuario probó la hoja "Planimetría" del Excel y notó que algunas izadas
quedaban con forma de L (parte de una columna de la grilla + parte de la
siguiente) — señaló correctamente que eso no tiene sentido físico: una grúa
no levanta 16 fardos desparramados en dos columnas distintas como si
estuvieran amarrados.

**Causa:** `secuencia_izadas.calcular_secuencia()` agrupaba las unidades
contando 16 en el orden de barrido (columna por columna). Correcto en
cantidad, no en forma.

**Fix:** `src/layout_capa.py` — `UnidadPosicion` gana `fila`/`columna`
(índice dentro de la grilla de su propio grupo producto+destino, poblado en
`_rellenar_zona`). `src/secuencia_izadas.py` — nuevo algoritmo
`_dimensiones_bloque()` elige el rectángulo más parecido a un cuadrado que
quepa en ≤16 unidades (para una grilla 10×20 da 4×4, no 1×16), y
`_bloques_del_grupo()` tila toda la grilla con ese tamaño, recorriendo los
bloques en serpentina. 4 tests nuevos verifican matemáticamente que cada
bloque sea un rectángulo real (sin huecos, sin superposición, cobertura
completa). Se aplica igual en el gráfico de la web y en la hoja Excel.

Además se agregaron explicaciones en lenguaje simple en cada sección de
`2_Resultados.py` y una nota (`_hoja_tabla(..., nota=...)`) en cada hoja
nueva del Excel, más una leyenda de colores por producto en "Planimetría".
De paso se corrigió una nota desactualizada en "Balance de peso" que todavía
decía "el modelo no restringe peso" — ya no es cierto desde la pasada 3
(sección 10 de este documento).

`plot_planimetria_capa()` en `vista_buque.py`: altura 460→760, y las
etiquetas de conteo por izada pasaron de texto chico a placas sólidas con
número grande (azul marino = 16 completas, coral = parcial) — mucho más
legibles a simple vista, que era el pedido original del usuario.

Commit: `8d245c6`.

---

## 12. Capacidad real por plan (misma sesión, pendiente #5 de CLAUDE.md)

A pedido explícito del dueño del proyecto, marcado como "el más importante"
de la lista de pendientes. Resumen ejecutivo en CLAUDE.md sección 6
("Capacidad real por plan") y sección 7 (supuesto #5). Acá el detalle.

### El bloqueo inicial y cómo se resolvió

Los datos reales viven en `PLANIMETRIAS_MN_KIWI_ARROW_2025.xls` (planilla
original del puerto, no versionada — `data/raw/` estaba vacía en esta
sesión). El usuario tenía su copia local en el Escritorio (sincronizado con
OneDrive: `OneDrive/Escritorio/capstone/`); se copió a `data/raw/` para que
el proceso sea reproducible dentro del repo.

### El hallazgo que cambió el diagnóstico

CLAUDE.md decía "para el Kiwi Arrow solo hay plantillas propias de los
planes 1 a 6" — eso salió de revisar solo la hoja LH-1 (bodega 1), que en
efecto solo tiene Kiwi Arrow hasta el plan 6 (el resto son plantillas del
Eagle Arrow, otro buque, mezcladas en el mismo archivo — mismo tipo de error
ya documentado en la sección 8 de CLAUDE.md sobre las hojas del Misago
Arrow). Al revisar las 8 hojas completas (LH-1 a LH-8) aparecieron **57
plantillas propias del Kiwi Arrow cubriendo planes 1 a 11** en las bodegas 2
a 8 — un hallazgo que contradice directamente lo que decía la documentación
existente.

### Análisis: aislar el efecto de la altura del efecto del producto

Cada plantilla trae (bodega, producto, rango de planes, unidades/plan). Como
cada producto tiene su propia huella, comparar unidades/plan entre
plantillas de DISTINTO producto mezcla dos efectos. Se agrupó por
(bodega, producto) y se comparó unidades/plan entre planes del MISMO
producto:

| Bodega | Patrón real |
|---|---|
| 1, 2 (BKP/CELCO), 5 (N_ALDEA_BKP), 7 (N_ALDEA_BKP) | Sin variación (0%) |
| 2 (EKP), 3, 6 | Variación leve (1-3%), ruido |
| **4, 5 (BKP), 7 (BKP/EKP), 8** | **Caída real de 3-13% en planes altos (8-10)** |
| 5 (ARAUCO_EKP) | Caso extremo: 385 en planes 1-7, 174 en el plan 10 (-55%) — no se pudo confirmar, excluido |

Tiene sentido físico: cerca de la cubierta (planes altos) suele haber vigas,
refuerzos, y la escotilla no siempre cubre todo el ancho de la bodega.

### Criterio de limpieza (ver docstring de `src/extraer_capacidades_reales.py`)

No se inventó ningún número. Se excluyeron:
1. **Productos ambiguos**: plantillas que mezclan 2 productos en una celda
   (ej. "ARAUCO BKP / EKP") — no se puede atribuir el número a uno solo.
2. **Conflictos**: 10 combinaciones (bodega, plan, producto) donde dos
   plantillas del mismo archivo dan valores distintos (ej. bodega 4, plan 9,
   ARAUCO_EKP: 362 en una, 341 en otra). Se descartan enteras.
3. **Un valor extremo sin confirmar**: bodega 5, plan 10, ARAUCO_EKP = 174.

Quedaron **72 combinaciones limpias** en
`data/capacidades_reales_por_plan.csv`.

### Cambios de código

- `src/extraer_capacidades_reales.py` — nuevo. Lee las 8 hojas del archivo
  raw, parsea los rangos de planes en español ("PRIMER A SEXTO PLAN" → 1-6),
  aplica el criterio de limpieza de arriba, y escribe el CSV. Reproducible:
  `python3 src/extraer_capacidades_reales.py`.
- `src/modelo_prestow.py` — nuevo global `CAPACIDAD_POR_PLAN[(bodega, plan,
  producto)]`, nueva función `cargar_capacidades_por_plan()`,
  `capacidad_unidades(h, p, t=None)` gana el parámetro `t` opcional (si se
  da y hay dato real para esa combinación exacta, pisa a `CAPACIDAD`). Se
  actualizaron los 5 sitios donde se llamaba `capacidad_unidades(h, p)`
  dentro de `construir_modelo()` (cota de `x`, `M` del enlace, restricción de
  capacidad de la capa, restricción de llenado mínimo) para pasar `t` — los
   5 ya estaban dentro de un loop `for t in PLANES`, cambio mecánico. También
  `verificar_capacidad()` (para que la verificación use la misma capacidad
  real que uso el solver, no la aproximación uniforme).
- `src/api.py` — `CAPACIDAD_POR_PLAN` agregado a `_NOMBRES_GLOBALES` (para
  que el lock guarde/restaure correctamente), `resolver_prestow()` carga
  `data/capacidades_reales_por_plan.csv` automáticamente. Es seguro para
  casos editados: si las claves (bodega, producto) no coinciden con las del
  Kiwi Arrow, el override simplemente no aplica, sin romper nada.

### Validación contra el caso base

Corrida completa (180 s/pasada, HiGHS): **makespan 59,67 h** (antes 58,19 h,
+1,48 h / +2,5%), desbalance 5,04%, fragmentación 12, **las 4 verificaciones
en 0 violaciones** (incluida "capacidad", la que más importaba verificar).
El cambio de makespan es real y esperado: el modelo anterior asumía más
capacidad de la que existe físicamente en los planes altos de las bodegas
4, 5, 7 y 8 — este número es más honesto, no peor. Documentado con el
cuidado que pide CLAUDE.md sección 12 ("no cambiar el makespan sin
advertirlo") en las secciones 3, 6 y 12 de ese archivo.

**Pendiente**: la validación histórica "el modelo reproduce las horas del
archivo del puerto con error de 0,01 h" se hizo ANTES de este cambio y no se
volvió a correr — no se sabe si sigue siendo tan precisa con la capacidad
real activa.

## 13. Pendiente #3 resuelto — las 275 unidades eran dos programas distintos

**Fecha:** 22 de septiembre de 2026. **Origen:** el archivo `PRESTOW N° 06`
de `data/raw/PRESTOW_N_10_KIWI_ARROW_FE_042025.xls` (no versionado, copiado
desde el Escritorio/OneDrive del usuario) mostraba en la fila 73 (columnas
33-35) los valores 29057 / 29332 / -275, es decir, el propio puerto ya
llevaba registrada la diferencia entre dos totales sin explicarla.

**Investigación:** cada bloque de bodega en esa hoja trae, además del total
`HOLD NRO. X` (fila 74, en unidades), dos filas más: `PROGRAMA G2OCEAN` y
`PROGRAMA LQN` (filas 75-76, en toneladas) — dos programas de estiba
paralelos para el mismo viaje. Se sumaron a mano todos los bloques
individuales de carga (destino + producto + valor UNITS + valor TONS,
repartidos por toda la hoja) en las tres bodegas que concentran toda la
brecha:

| Bodega | Suma bloques (unidades) | HOLD NRO. | Diferencia | Suma bloques (toneladas) | PROGRAMA LQN (toneladas) |
|---|---|---|---|---|---|
| 7 | 4013 | 3863 | +150 | 8120,181467378 | 8120,181467378 (exacto) |
| 5 | 3604 | 3672 | −68 | 7308,49 | 7308,46670458 (exacto al redondeo) |
| 3 | 3854 | 3661 | +193 | 7766,51 | 7766,508371228 (exacto al redondeo) |

+150 − 68 + 193 = 275, exacto. Las toneladas de la suma bloque-a-bloque
calzan con `PROGRAMA LQN`, no con `HOLD NRO.`, en las tres bodegas.

**Conclusión:** `DEMANDA` (29.332, lo que usa `modelo_prestow.py`) es la
suma de esos mismos bloques individuales en las 8 bodegas — corresponde a
`PROGRAMA LQN`, el programa propio de Lirquén. `29.057` es la suma de
`HOLD NRO.`, que coincide con LQN en 5 de las 8 bodegas pero no en 7, 5 y 3
(probablemente el conteo de G2Ocean, la naviera, aunque esto no se verificó
con el mismo nivel de detalle). No hubo error de extracción de nuestra
parte ni del puerto: son dos planes reales que no coinciden en 3 bodegas, y
el archivo del puerto ya lo sabía.

**No se modificó ningún código.** `DEMANDA` ya usaba 29.332, el valor
correcto (PROGRAMA LQN). Este hallazgo solo documenta por qué ese número es
el que hay que seguir citando — ver CLAUDE.md sección 9 y 10 (pendiente #3).

**No verificado:** las otras 5 bodegas (8, 6, 4, 2, 1) no se sumaron
bloque a bloque con este mismo detalle — se sabía de antes que su total
coincide entre `HOLD NRO.` y la suma de bloques, así que probablemente ahí
`PROGRAMA G2OCEAN` = `PROGRAMA LQN` (sin diferencia entre programas), pero
no se confirmó explícitamente. Tampoco se revisó si otras hojas del archivo
(otras rotaciones, u otros PRESTOW) tienen el mismo patrón de dos programas.

## 14. Warm start en la pasada 1 (nueva sesión, 22 de septiembre de 2026 por la tarde)

El usuario probó la app en su navegador (Opera, ver sección 9 — seguía sin
probarse en Chrome) y reportó el bug real que motivó esta sesión: con
límites de 30, 60 y 90 segundos por pasada, la página no devolvía nada —
error de "no se encontró solución factible" — y sin ningún feedback visible
mientras corría, dando la sensación de que se había colgado.

### Diagnóstico

Se reprodujo corriendo `api.resolver_prestow()` directamente con
`limite_segundos=30`: a los 30,01 s reportados por HiGHS, el log mostraba
`Primal bound inf` — CERO soluciones enteras encontradas, pese a que HiGHS
tenía todas sus heurísticas internas activas (feasibility pump, central
rounding, shifting, etc., ver la leyenda `Src:` del log). Se confirmó que
esto no era un problema de límite de tiempo mal aplicado (se descartó
revisando el log completo, incluida la sección `Solving report` con
`Timing`) sino que el modelo, para este caso, genuinamente necesita más de
120 s de búsqueda para encontrar la PRIMERA solución factible —
contiguidad + no-overstowage + llenado mínimo (restricción 5d) hacen que la
combinatoria sea dura para las heurísticas de HiGHS, incluso con un MILP de
tamaño moderado (2204 filas, 1707 columnas).

De paso se encontró un bug real y separado en el CLI: `modelo_prestow.
main()` llamaba `resolver(prob)` sin pasar `limite=` explícito, así que
usaba el DEFAULT del parámetro (`limite=LIMITE_SEGUNDOS`, evaluado UNA VEZ
cuando Python carga el módulo) en vez del valor reasignado por `--limite`
en tiempo de ejecución — con `--limite 30` el CLI igual resolvía con 120 s,
sin avisar (se vio con `Timing 120.01` en el log pese a pedir 30 s). No
afectaba a la web, que arma sus propios solvers en `api.py` pasando
`limite_segundos` explícito en cada llamada, pero se corrigió igual
(`src/modelo_prestow.py`, dos líneas).

### La solución: warm start heurístico para la pasada 1

**`src/solucion_inicial.py` (nuevo).** Construye una asignación x[h,t,p,d]
factible en milisegundos (no óptima, solo factible) para usar como punto de
partida (MIP start) del solver. Algoritmo:

1. Agrupa las combinaciones (producto, destino) por ROT descendente (tier
   por destino) y procesa tier por tier — eso solo ya garantiza
   no-overstowage (4) por construcción.
2. Dentro de un tier, reparte la demanda en RONDAS chicas (`_FRACCION_CHUNK
   = 0.15` de una capa por vuelta) en vez de agotar una combinación entera
   antes de pasar a la siguiente — necesario para que las capas queden
   MEZCLADAS entre productos del mismo destino. Se detectó en la práctica
   que sin esto, un producto de huella chica (capacidad_unidades grande,
   ej. ARAUCO_BKP) podía agotar la cota cruda de la restricción (5b)
   ("ocupacion_max", que usa área/huella-mínima-entre-TODOS-los-productos,
   más floja que la capacidad real por producto en general pero NO SIEMPRE:
   para varias combinaciones bodega/plan la capacidad real del packer la
   supera) sin llegar al 90% de llenado mínimo (5d) — mezclando con un
   producto de huella más grande (más fracción por unidad) se alcanza el
   90% dentro del mismo tope crudo.
3. Bodegas gemelas (restricción 9, ruptura de simetría): desempate por
   unidades acumuladas + orden fijo durante la construcción, más un reparo
   final (`_reparar_simetria`) que mueve unidades sueltas de una celda a
   otra ya existente (o a una capa nueva arriba, si no rompe el orden de
   rotación) cuando el desempate deja una diferencia de un par de unidades.

**Verificación exhaustiva antes de usar el resultado**: en vez de solo
correr `verificar_cobertura/capacidad/contiguidad/no_overstowage` (los 4
chequeos que ya existían), `construir_solucion_inicial()` fija los valores
construidos en las variables del `prob` REAL y evalúa TODAS sus
restricciones (`_verificar_contra_restricciones`, ~2200 en el caso base).
Hizo falta: se detectó en la práctica que el heurístico podía pasar los 4
chequeos existentes y aun así violar (5b) o (5d), que esos 4 no cubren. Si
CUALQUIER restricción falla, se devuelve `None` y quien llama resuelve sin
warm start — nunca se le inyecta a HiGHS algo sin validar.

**`api.py`**: usa `_resolver_con_warm_start` (el mismo mecanismo que ya
existía para la pasada 3, ver sección 10) para la pasada 1 — pero
**solo si `limite_segundos < UMBRAL_WARM_START_PASADA1` (180 s)**. La
pasada 2 SIEMPRE se warm-startea desde la solución de la pasada 1, sin
condición de umbral.

### Por qué el umbral de 180 s (hallazgo importante)

La primera versión aplicaba el warm start siempre, sin umbral. Verificando
contra el caso base a 180 s (la configuración "oficial" de CLAUDE.md), el
resultado fue **60,18 h** — peor que los 59,67 h documentados. Diagnóstico:
el log mostró `MIP start solution is feasible, objective value is
59.9716666667` seguido de `Gap 4.1%` al agotar los 180 s — el warm start
ANCLÓ la búsqueda cerca de su propio punto de partida (~60 h) y HiGHS no
logró escapar de esa región en el tiempo dado, mientras que buscando desde
CERO en el mismo tiempo sí llega a 59,67 h. Es un riesgo conocido de dar
warm start a un MILP: acelera encontrar *algo*, pero puede atrapar al
solver cerca de un óptimo local mediocre en vez de dejarlo explorar más
ampliamente.

Se agregó el umbral (`UMBRAL_WARM_START_PASADA1 = 180` en `api.py`) para
que la pasada 1 solo use warm start por debajo de 180 s — ahí SIEMPRE es
una mejora estricta (antes: sin solución; con warm start: un resultado
válido) — y a 180 s+ se resuelve exactamente como antes (desde cero), para
no tocar el número ya validado. Re-verificado tras el cambio: 180 s+ vuelve
a dar **59,6702 h**, prácticamente idéntico al histórico.

### Resultados de verificación (caso base, `api.resolver_prestow`)

| Límite/pasada | Warm start pasada 1 | Makespan | Verificaciones |
|---|---|---|---|
| 30 s | Sí | 59,97 h | 0 violaciones |
| 60 s | Sí | 60,21 h | 0 violaciones |
| 90 s | Sí | 60,18 h | 0 violaciones |
| 180 s | No (por umbral) | 59,67 h | 0 violaciones |

Antes del fix, 30/60/90 s fallaban con `ValueError: no se encontró ninguna
solución factible`. La pasada 2, de paso, se benefició del warm start desde
la pasada 1 (siempre activo, sin condición de umbral): en la corrida de
180 s llegó a gap 3,24%, mucho mejor que el estado previo sin warm start —
probablemente resuelve el pendiente #4 de CLAUDE.md ("la pasada 2 no
resuelve en 150-180 s"), aunque no se hizo una comparación A/B controlada
para confirmarlo con certeza.

### Feedback en vivo en la web

`app/pages/1_Ejecutar.py`: la corrida ahora se lanza en un hilo (`threading.
Thread`) aparte, y el hilo principal de Streamlit sondea su estado cada
segundo, actualizando un `st.empty()` con la etapa actual (que reporta
`resolver_prestow` vía un nuevo parámetro `progreso: Callable[[str], None]
| None`) y el tiempo transcurrido — antes era un spinner ciego durante los
minutos que puede tardar el solver, sin forma de saber si seguía calculando
o se había colgado. El hilo no llama ninguna API de Streamlit (solo muta un
dict plano), así que no dispara advertencias de "missing ScriptRunContext".

### Tests nuevos

`tests/test_solucion_inicial.py` (6 tests): que la asignación heurística
cubra toda la demanda, que NO viole ninguna restricción real del modelo
(evaluando `prob.constraints` directamente, no solo los 4 `verificar_*`) —
tanto con los datos harcodeados de `modelo_prestow.py` como cargados desde
el Excel del caso base vía `cargar_datos()` (la regresión real: el
heurístico pasaba con los datos harcodeados pero fallaba con los del Excel,
por una combinación distinta de productos/capacidades que exponía (5b) y
luego (5d) — no alcanzaba con probar un solo camino de datos), que
`construir_solucion_inicial()` devuelva un valor para cada variable del
problema, y que el `T_max` quede coherente con las izadas.

### Pendiente detectado, no resuelto en esta sesión

- El warm start de la pasada 1 solo vive en `api.py` (la web); el CLI
  (`modelo_prestow.py --limite N`) sigue sin él, así que con límites bajos
  desde la línea de comandos el problema original persiste ahí. Es
  consistente con que ya antes solo la web tenía warm start para la
  pasada 3 (ver comentario de `LIMITE_SEGUNDOS_BALANCE` en
  `modelo_prestow.py`).

## 15. QA de Resultados y Configuración + pendiente #1 resuelto (misma sesión, después del warm start)

Con el bug del warm start resuelto, el usuario pidió retomar la prueba
visual pendiente de la sesión anterior. Claude in Chrome seguía sin estar
conectado, así que se hizo con `streamlit.testing.v1.AppTest` (igual que en
Fase 2) en vez de un navegador real — cubre errores de ejecución y avisos
en pantalla, no layout ni CSS.

### Resultados (`2_Resultados.py`)

Página completa sin excepciones ni warnings ocultos. Se probaron las 32
combinaciones de los 5 selectbox de la página (Colorear por de la vista
lateral × 4, Ver detalle de bodega × 8, Bodega de Planimetría × 8, Plan de
Planimetría × 10, Colorear planimetría por × 2) — las 32, sin excepción. El
Excel de descarga se generó bien (158 KB, las 7 hojas esperadas: Plan de
estiba, Detalle, Indicadores, Izadas y secuencia, Planimetría, Balance de
peso, Parámetros de la corrida).

**Bug del script de prueba, no de la app** (documentado para no repetirlo):
`AppTest.from_file()` resuelve rutas relativas contra el archivo que hace la
llamada, no contra el directorio de trabajo — un script en un directorio
temporal necesita la ruta absoluta. Por separado, `Selectbox.select_index(i)`
en Streamlit 1.62 tiene un bug real con `format_func`: guarda el string ya
formateado como si fuera el valor crudo, y el próximo `.index` intenta
formatearlo de nuevo y no lo encuentra (`ValueError: list.index(x): x not in
list`). Para un selectbox con `format_func`, hay que pasarle a `.select()` el
valor CRUDO (el que aparece en `options=...` del código fuente), no el string
que devuelve `sb.options` (que ya viene formateado para mostrar).

**Hallazgo real, corregido** (commit `a004f6d`): el bloque que carga
`huellas_productos`/`geometria_bodegas` (usadas en Planimetría, Balance de
peso y la hoja Planimetría del Excel) atrapaba cualquier excepción en
silencio, sin ningún aviso — a diferencia de los otros `try/except` de la
página, que sí muestran `st.warning` con el detalle técnico. Se encontró
probando la página sin `ruta_datos` en `session_state`: esas tres secciones
simplemente desaparecían sin explicación. Se agregó el mismo patrón de aviso
que usa el resto de la página.

### Configuración (`0_Configuracion.py`)

Flujo completo sin excepciones: cargar caso demo → agregar bodega → agregar
producto → guardar (dispara `recalcular_capacidades`, el packer) → eliminar
una fila. `metadata` se actualiza correctamente en cada paso (bodegas,
productos, toneladas).

### Pendiente #1 de CLAUDE.md resuelto: estabilidad entre corridas

`python3 src/stability_test.py --limite 180 --n 5` (5 semillas) con la
configuración vigente (capacidad real por plan + warm start de las 3
pasadas) dio **makespan idéntico (59,6702 h) y unidades por bodega
idénticas en las 5 corridas**, desviación estándar 0,0000 en todo — ver
`data/stability_report.csv`. Revisando el log completo de las 5 corridas
(no solo lo que imprime el script), las TRES pasadas dieron exactamente el
mismo gap en las 5: pasada 1 3,29%, pasada 2 3,24%, **pasada 3 63,91%** —
esto último contradice el pendiente #7 de CLAUDE.md, que documentaba que la
pasada 3 variaba entre corridas (4.930 t vs 9.152 t de desbalance, medido
con una configuración anterior del modelo). Con la configuración de hoy no
se reprodujo esa variabilidad. No investigado a fondo por qué cambió (¿el
warm start? ¿la capacidad real por plan? ¿ambos?) — CLAUDE.md sección 10
ítem 7 queda con una nota de que el gap sigue siendo alto (no prueba
optimalidad) pero ya no varía, al menos en esta prueba.

De paso se aprovechó esta corrida para refrescar la tabla de CLAUDE.md
sección 3 ("Resultados verificados del caso base"), que seguía citando
58,19 h (de antes de la capacidad real por plan) y no se había vuelto a
correr. Con los números de hoy, la fragmentación del modelo (10) es
**mejor** que la del plan manual (14) — antes decía "peor (pasada 2 no
resuelve)", ya no es el caso.

## 16. Re-validación de la validación de horas por cuadrilla (misma sesión)

El usuario pidió revalidar específicamente "el modelo reproduce las horas
del archivo del puerto con error de 0,01 h" (CLAUDE.md sección 3, marcada
como pendiente desde la sesión de capacidad real por plan).

**Hallazgo clave: esta validación no depende del makespan del modelo ni de
ninguno de los cambios de hoy.** Compara dos cosas que NINGÚN cambio de
esta sesión (ni la anterior) toca:

1. Las horas reales por bodega del archivo del puerto — fila "HORAS
   TRABAJO x LH" de la hoja "PRESTOW N° 06" (`data/raw/
   PRESTOW_N_10_KIWI_ARROW_FE_042025.xls`, fila 77 en la lectura con
   `xlrd`): 26,55 / 30,07 / 31,42 / 27,07 / 28,50 / 28,76 / 32,09 / 28,52 h
   para bodegas 8 a 1. Dato histórico fijo del plan manual, no algo que el
   modelo produce.
2. `TIEMPO_CICLO_POR_BODEGA` — constante hardcodeada en `modelo_prestow.py`
   (7,14 / 7,19 / 7,11 / 7,19 / 7,15 / 7,16 / 7,16 / 13,91 min), sin tocar
   en ninguna de las dos sesiones recientes.

La validación es: recuperar las izadas reales por bodega
(`round(horas_declaradas × 60 / tiempo_ciclo_min)`) y sumar
`izadas × tiempo_ciclo` por cuadrilla (bodegas 8+7, 6+5, 4+3, 2+1), contra
las horas por cuadrilla que el propio archivo reporta (fila 78 de la misma
hoja: 56,62 / 58,49 / 57,26 / 60,61 h). Como ninguno de los dos insumos
cambió, el resultado no podía haber cambiado — se re-corrió igual para
confirmarlo con código, no de memoria: **error máximo 0,023 h**, coincide
con el 0,01-0,02 h documentado en `docs/01_Contexto_Informe_Academico.md`.

De paso quedó documentada la estructura completa de la hoja "PRESTOW N° 06"
para quien necesite volver a leerla (no había quedado registrada en ninguna
sesión anterior, solo se habían leído fragmentos puntuales para la
reconciliación de las 275 unidades):

- Filas 17-71: 11 bloques de 5 filas cada uno (destino, producto, etiqueta
  de aseguramiento, UNITS, TONS), uno por plan, de PLAN 11 (arriba, fila
  17) a PLAN 1 (fondo, fila 67) — el orden de filas es correcto, no
  invertido. Cada bodega ocupa un rango de columnas (aproximadamente 4
  columnas, arrancando en 1/5/9/13/17/21/25/29 para bodegas 8/7/6/5/4/3/2/1
  respectivamente, indicado en la fila 16 "HOLD NRO. X") que se ENSANCHA
  cuando un plan tiene más de un producto/destino en la misma capa (capa
  mixta) — no son rangos fijos, hay que ubicarlos por proximidad al header
  de cada bodega, no por un rango de columnas fijo.
- Fila 72: geometría de cada bodega (ej. "18,30 X 27,40 X 19,26").
- Fila 73: total de unidades por bodega ("HOLD NRO. X"), y en las columnas
  finales 29.057 / 29.332 / -275 (la brecha del pendiente #3, CLAUDE.md
  sección 10, ya resuelta).
- Filas 74-76: `PROGRAMA G2OCEAN`, `PROGRAMA LQN` y su diferencia, por
  bodega (ver pendiente #3 resuelto).
- Fila 77: horas de trabajo declaradas por bodega ("HORAS TRABAJO x LH").
- Fila 78: horas por CUADRILLA (suma de las 2 bodegas correspondientes),
  sin etiqueta de fila explícita — hay que ubicarla por posición de
  columna, alineada con el bloque "HOLD NRO." de la bodega de la izquierda
  de cada cuadrilla.

No se creó un script reproducible para esto (a diferencia de
`extraer_capacidades_reales.py`) porque es una validación estática de un
dato histórico fijo, no algo que haya que re-correr cuando cambie el
modelo — si vuelve a hacer falta, este párrafo tiene todo lo necesario para
rehacerla en minutos.
