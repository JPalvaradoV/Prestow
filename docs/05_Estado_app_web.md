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
