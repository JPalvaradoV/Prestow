# Proyecto Prestow Lirquén — Contexto operacional

Este archivo se carga automáticamente en cada sesión de Claude Code en este repositorio. Contiene el estado real del proyecto y las reglas que debes seguir al escribir código.

**No debates decisiones cerradas ni cambies el motor sin aviso.** Los documentos completos viven en `docs/`.

---

## 1. Estado del proyecto en una línea

El modelo de optimización está **implementado, corrido con datos reales y validado**. Ahora se construye la **página web** que envuelve al modelo.

## 2. Lo que ya existe y funciona

- **`src/modelo_prestow.py`** — modelo MILP completo (PuLP + HiGHS), tres pasadas lexicográficas (makespan → izadas+fragmentación → balance de peso, ver sección 6), exporta `plan_estiba.xlsx` con formato tipo prestow del puerto.
- **`src/packer_2d.py`** — cálculo de capacidad por geometría con tres patrones (uniforme, dos bloques, cuatro bloques). Corre una vez, produce `data/capacidades.csv`.
- **`data/datos_entrada_kiwi_arrow.xlsx`** — caso base editable, cinco hojas: Instrucciones, Viaje, Rotación, Buque, Productos.
- **`data/capacidades.csv`** — 40 combinaciones (8 bodegas × 5 productos), generadas por el packer.
- **`data/plan_estiba.xlsx`** — salida de ejemplo, tres hojas: Plan visual, Detalle, Indicadores. Es un ensayo, no la salida final.

## 3. Resultados verificados del caso base

Con datos reales, HiGHS, 180 s por pasada, rotación con Ulsan como último destino:

| Indicador | Plan manual | Modelo | Diferencia |
|---|---|---|---|
| Makespan | 60,61 h | **58,19 h** | −4,0% |
| Desbalance entre cuadrillas | 6,9% | **0,2%** | mucho mejor |
| Fragmentación | 14 bodegas | 22 | peor (pasada 2 no resuelve) |
| Overstowage | 0 | 0 | igual |

**La validación más fuerte:** el modelo reproduce las horas del archivo del puerto con **error de 0,01 h** en las cuatro cuadrillas. Reproduce lo que hace el planificador real casi exactamente.

⚠️ Un resultado anterior de **57,59 h** circuló en documentos previos — correspondía a la rotación con Kunsan/Ulsan empatados, que ya no es la configuración vigente. **No citarlo.**

## 4. Lo que se está construyendo ahora — la página web

**Objetivo:** interfaz Streamlit que envuelve el modelo. Convive con `plan_estiba.xlsx` como opción de descarga; no lo reemplaza.

**Estructura decidida:**

| Sección | Qué contiene |
|---|---|
| Inicio | Explicación del sistema, propuesta de valor, botón "correr caso demo" |
| Configuración del buque | Bodegas (tamaños, cuadrillas, número de planes) — editable |
| Productos | Tipos de unidad con huella y peso — **con opción de agregar nuevos, que dispara re-cálculo automático del packer** |
| Viaje | Carga a embarcar (producto, destino, unidades) |
| Rotación | Puertos de destino y orden de descarga |
| Ejecutar | Botón de correr modelo con parámetros (solver, tiempo límite, tolerancia) |
| Resultados: Planimetría | Vista visual por bodega y plan, tipo prestow |
| Resultados: KPIs | Los 5 KPIs con comparación al plan manual |
| Resultados: Izadas y secuencia | Número de izadas por capa + orden de carga dentro de cada capa |
| Resultados: Balance de peso | Peso y densidad por bodega, **informativo (no es restricción del modelo)** |
| Descarga | Enlaces al `plan_estiba.xlsx`, KPIs en CSV, y reporte de parámetros de la corrida |

**Stack:** Streamlit para la interfaz. Todo lo que hoy corre por CLI se expone como funciones puras desde `src/`.

**Despliegue previsto:** Streamlit Community Cloud (gratuito, con la app durmiendo tras 12 h de inactividad).

## 5. Módulos nuevos que hay que construir

- **`src/api.py`** — funciones puras que envuelven el modelo actual: `resolver_prestow(config, viaje, opciones) → resultado`. Sin variables globales. Es lo que la web va a llamar.
- **`src/layout_capa.py`** — modifica el packer para exponer posiciones (x, y, rotación) de cada unidad dentro de la capa. Hoy el packer solo devuelve totales.
- **`src/secuencia_izadas.py`** — dado un layout, agrupa las unidades en izadas de 16 y decide el orden de carga (destino → producto → columnas).
- **`src/balance_peso.py`** — peso y densidad por bodega. Solo informativo, no restringe.
- **`src/stability_test.py`** — corre el modelo con 5 semillas y produce un CSV de variabilidad por bodega. Bloquea la publicación de análisis por bodega en la web hasta que se corra.

## 6. Decisiones cerradas — asumir, no debatir

- **Método**: MILP exacto con límite de tiempo, tres pasadas lexicográficas (makespan → izadas+fragmentación → balance de peso). No metaheurística.
- **Solver**: HiGHS en producción (libre, sin licencia), CBC como respaldo. **CPLEX/Gurobi no se pueden desplegar en hosting público.**
- **Librería**: PuLP.
- **Packer**: módulo separado, precalculado, tres patrones. No es fórmula cerrada.
- **Restricción 4 (no-overstowage)**: solo entre planes adyacentes — demostrado equivalente, verificado con 211.000 configuraciones.
- **La bandera `SEPARAR_ROTACION_EMPATADA` fue eliminada**. No reintroducirla sin releer por qué se descartó.
- **Merma de capacidad = 0**, avalado por el profesor como supuesto declarado.
- **Balance de peso: decisión reabierta el 21 de septiembre de 2026, a pedido explícito del dueño del proyecto.** Antes decía "no agregar restricciones de peso ni distribución al modelo" — la razón seguía siendo válida (dispersión relativa 36,8% del modelo vs 18,9% del plan manual, sin evidencia de problema operativo), pero el dueño del proyecto pidió agregarla igual: la web genera un plan desde cero para alguien sin plan de referencia, y prefiere pagar makespan por un buque mejor balanceado. Implementado como **pasada 3 lexicográfica** (después de izadas+fragmentación) en `modelo_prestow.py`, activa por defecto (`USAR_BALANCE_PESO = True`). Balancea la carga inicial (zarpe) entre bodegas — **no** el trim puerto a puerto: se investigó balancear las 4 etapas del viaje completo y el solver nunca converge bien (se estanca en 75-77% de gap pase lo que se pruebe: sin warm start no encuentra factibilidad, con warm start encuentra pero no mejora ni con 900 s ni con tolerancia más floja). El detalle completo de la investigación está en `docs/05_Estado_app_web.md`. **No subir `ETAPAS_BALANCE_PESO` por encima de 1 sin resolver antes el problema de fondo** (relajación LP débil de la pasada 3, no un tema de tiempo ni de parámetros).

## 7. Los 9 supuestos, con su estado actual

| # | Supuesto | Estado |
|---|---|---|
| 1 | El Puerto fija el tonelaje por bodega | Sin confirmar |
| 2 | Rendimientos t/h del archivo (140 bod 1, 270 el resto) | Sin confirmar |
| 3 | Pares de cuadrillas son fijos: (8+7), (6+5), (4+3), (2+1) | Sin confirmar |
| 4 | Huellas de los productos | **Resuelto** — verificadas en 58 plantillas |
| 5 | Acortamiento de bodega en planes altos | **Descartado** — era del Eagle Arrow |
| 6 | Tiempo por izada | **Corregido** — varía por bodega (13,91 min bod 1 vs 7,15 el resto) |
| 7 | Sin bloqueo entre destinos dentro de una capa | Declarado |
| 8 | Sin merma por separadores, maniobra ni medidas no netas | Avalado por el profesor |
| 9 | Orden entre Kunsan y Ulsan | **CERRADO** — confirmado: Ulsan es el último (orden 4) |

## 8. Errores documentados que no hay que repetir

| Error | Cómo se detectó |
|---|---|
| Leer solo la hoja LH-1 de planimetrías | El archivo tiene 58 plantillas del Kiwi Arrow en LH-1 a LH-8 |
| Trabajar sobre hojas ocultas del Misago Arrow | 4 hojas ocultas de 2017, mismo formato — se construyeron análisis sobre el buque equivocado |
| Contigüidad sobre `y` (activable sin carga) | El solver dejaba carga flotando; se agregó `w` con implicación en ambos sentidos |
| Tiempo de izada constante | Subestimaba la bodega 1, que determina el makespan |
| Pesos en vez de lexicográfico | Con tres términos el tercero se volvía indistinguible; la fragmentación empeoraba al agregarlo |
| Confiar en el estado de PuLP | Reporta "Optimal" en corridas que no alcanzaron el óptimo; se lee el gap del log directo |
| Cambiar configuración sin regenerar artefactos | Se midió sobre un `plan_estiba.xlsx` desactualizado; todo el análisis salió invertido |

## 9. Cifras del caso base — cualquier test debe reproducirlas

| Métrica | Valor |
|---|---|
| Buque | Kiwi Arrow (G2 Ocean) |
| Unidades totales | **29.332** (extracción actual; hay 275 sin reconciliar respecto de 29.057 citado por otra vía) |
| Toneladas totales | 59.197 |
| Bodegas cargadas | 8 de 8 |
| Peso por unidad | 2,02 t (constante) |
| Marco de grúa | hasta 16 unidades por izada |
| Rendimientos | 140 t/h bodega 1 · 270 t/h bodegas 2-8 |
| Tiempo de ciclo | 7,11-7,19 min bodegas 2-8 · **13,91 min bodega 1** |
| Capas con carga | 85, de las cuales 5 mixtas |
| Casos de overstowage | **0** |
| Destinos y rotación | TAICHUNG (1) → QINGDAO (2) → KUNSAN (3) → ULSAN (4) |

**Unidades por bodega (plan manual)**: 8→3555, 7→3863, 6→4227, 5→3672, 4→3823, 3→3661, 2→4294, 1→1962.

**Geometría**: bodegas 2-8 miden 18,30 × 27,40 m (idénticas). Bodega 1 mide 16,80 × 14,80 m. Altura total 19,26 m, hasta 11 planes por bodega.

**Huellas verificadas**:
- N_ALDEA_EKP: 0,84 × 1,47 m
- N_ALDEA_BKP: 0,84 × 1,36 m (nota: en el archivo aparece como "ALDEA BKP", asumido mismo producto)
- ARAUCO_EKP: 0,89 × 1,41 m
- ARAUCO_BKP: 0,84 × 1,36 m
- CELCO_UKP: 0,84 × 1,43 m (⚠️ en algunas celdas aparece como "CELCO" a secas — fusionados manualmente)

## 10. Pendientes conocidos — advertir si aparecen

En orden de prioridad:

1. **Estabilidad de la asignación entre corridas.** No se sabe cuánto varía. Mientras no se corran las 5 semillas, **cualquier análisis sobre "en qué bodega quedó qué"** puede ser ruido. La web no debería mostrar detalle por bodega con confianza hasta cerrar esto.
2. **Warm start desde el plan real** — daría garantía de que el resultado nunca es peor que 60,61 h.
3. **275 unidades sin reconciliar** entre las dos vías de extracción.
4. **La pasada 2 no resuelve en 150-180 s** — por eso la fragmentación quedó sin optimizar.
5. **El packer no distingue altura** — asume los 11 planes iguales.
6. **Pruebas automatizadas** — todo se verifica a mano.
7. **La pasada 3 (balance de peso) no converge de forma estable entre corridas.** A diferencia del resto del modelo (determinista, ver `data/stability_report.csv`), la pasada 3 nunca prueba optimalidad dentro del tiempo estándar (gap ~16-55% visto en pruebas, varía de corrida en corrida por el no-determinismo de HiGHS). El resultado siempre es un balance real y válido, pero no comparable número a número entre dos corridas del mismo caso. No confundir esto con el ítem 1 (que es sobre el resto del modelo, ya determinista).

## 11. Convenciones de código

- **Python 3.11+**, type hints en firmas públicas.
- **Docstrings y comentarios en español** — el equipo y los revisores son hispanohablantes.
- **Nombres de variables siguiendo el modelo matemático**: `bodega`, `plan`, `producto`, `destino`, `unidades`. Sin abreviar salvo cuando el modelo lo usa (h, t, p, d, g).
- **pytest** para tests. Cada módulo del núcleo tiene su `test_*.py` en `tests/`.
- **black + ruff** para format y lint. Configurados en `pyproject.toml`.
- **Sin efectos secundarios ocultos en `src/`**: los módulos nuevos son funciones puras que reciben y devuelven datos. El código existente (`modelo_prestow.py`, `packer_2d.py`) usa globales — no romper esa interfaz hasta que exista `api.py` que la envuelva.
- **Streamlit vive en `app/`**, no en `src/`. La web es un cliente del núcleo, no parte de él.
- **Sin llamadas a red**. Todo local.

## 12. Qué NO hacer

- **No modificar `modelo_prestow.py` ni `packer_2d.py`** sin explicar por qué en un commit separado y correr las verificaciones sobre el caso base. El código actual ya está validado.
- **Balance de peso: ver sección 6 — decisión reabierta.** Ahora SÍ hay una restricción de peso en el modelo (pasada 3, solo la carga inicial). El panel "Balance de peso" de la web sigue mostrando el estado real logrado, informativo.
- **No inventar cifras** para completar ejemplos o tests. Si falta un dato, marca el test como pendiente.
- **No usar solvers con licencia** (CPLEX, Gurobi, Mosek). Solo HiGHS o CBC.
- **No introducir dependencias nuevas** sin agregarlas a `requirements.txt` y explicarlo en el commit.
- **No cambiar el makespan del caso base sin advertirlo.** Cualquier cambio que altere 58,19 h debe justificarse.
- **No usar `assert` para validación en producción**. `assert` solo en tests.
- **No usar la palabra "óptimo"** en la interfaz sin gap cero verificado. El resultado actual tiene gap de 0,195%.

## 13. Cómo se corre hoy (línea de comandos)

```bash
# Una vez, genera capacidades.csv
python3 src/packer_2d.py --datos data/datos_entrada_kiwi_arrow.xlsx

# Cada corrida
python3 src/modelo_prestow.py --datos data/datos_entrada_kiwi_arrow.xlsx --limite 180

# O cargando el caso base cableado
python3 src/modelo_prestow.py --caso-base
```

La web va a envolver esto, no reemplazarlo.

## 14. Documentos de referencia

- `docs/00_LEEME_PRIMERO_contexto.md` — contexto general del proyecto
- `docs/Resumen_Trabajo_Realizado.md` — resumen del análisis y decisiones
- `docs/03_Instrucciones_afinar_modelo.md` — cambios recientes al modelo y pendientes técnicos
- `docs/Restricciones_Modelo_Prestow_Lirquen.pdf` — formulación matemática completa
- `docs/Guia_de_tareas_Prestow_Lirquen.pdf` — las 120 tareas del proyecto
- `docs/04_Prompt_Informe_Tecnico.md` y `docs/01_Contexto_Informe_Academico.md` — bases de los informes finales
- **`docs/05_Estado_app_web.md`** — **estado actual de la app Streamlit** (leer antes de tocar `app/`): qué se construyó en Fases 1 y 1.5, decisiones de diseño, bugs resueltos y lo que falta
