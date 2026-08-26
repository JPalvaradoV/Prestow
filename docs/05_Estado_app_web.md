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
