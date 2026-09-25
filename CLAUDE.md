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

**Actualizado el 25 de septiembre de 2026**, con la pasada 3 por búsqueda de vecindarios (ver sección 6). El makespan no cambió (59,67 h, el mismo del test de estabilidad de 5 corridas del 22-sep, `data/stability_report.csv`); cambiaron el desbalance entre cuadrillas y la fragmentación, porque la pasada 3 ahora sí reordena la carga. Dos corridas de 180 s dieron exactamente los mismos números.

Con datos reales, HiGHS, 180 s por pasada, rotación con Ulsan como último destino:

| Indicador | Plan manual | Modelo | Diferencia |
|---|---|---|---|
| Makespan | 60,61 h | **59,67 h** | −1,6% |
| Desbalance entre cuadrillas | 6,9% | **5,8%** | mejor |
| Fragmentación | 14 bodegas | **11** | mejor |
| Izadas | sin dato | **1836** | — |
| Desbalance de peso entre bodegas (máx − mín, al zarpar) | — | **3.604 t** (gap 9,19%) | — |
| Overstowage | 0 | 0 | igual |

**No volver a citar 58,19 h como el resultado vigente del modelo** — era el número con capacidad geométrica uniforme (antes de la sección 6, "Capacidad real por plan"), que en varias bodegas (4, 5, 7, 8) resultó ser más capacidad de la que existe físicamente en los planes altos. Tampoco citar 57,59 h (circuló en documentos previos, correspondía a la rotación con Kunsan/Ulsan empatados, ya no vigente).

**Re-verificado el 22 de septiembre de 2026: la validación de las horas por cuadrilla sigue siendo válida, sin cambios.** Esta validación NO depende del makespan del modelo ni de sus cambios recientes (capacidad por plan, warm start) — compara las horas reales por bodega del archivo del puerto (fila "HORAS TRABAJO x LH" de la hoja PRESTOW N° 06, dato histórico fijo) contra `izadas × TIEMPO_CICLO_POR_BODEGA` (constante hardcodeada en `modelo_prestow.py`, tampoco tocada hoy) — ninguno de los dos insumos cambió, así que el resultado no podía haber cambiado. Recuperando las izadas reales por bodega (`round(horas_declaradas × 60 / tiempo_ciclo_min)`, ver `data/raw/PRESTOW_N_10_KIWI_ARROW_FE_042025.xls`, hoja "PRESTOW N° 06", filas 73-78) y sumando por cuadrilla: error máximo **0,023 h**, coincide con el 0,01-0,02 h documentado históricamente. La confusión anterior fue no distinguir esta validación (usa datos fijos del plan manual, independiente del makespan del modelo) de la tabla de arriba (que sí depende de qué produce el optimizador).

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
| Resultados: KPIs | Los KPIs con comparación contra el **plan de referencia que ingresa el usuario** en Configuración (nombre del buque + makespan, desbalance, fragmentación, izadas; opcionales). El caso demo trae precargado el plan manual del Kiwi Arrow. Ver `docs/05` sección 18 |
| Resultados: Izadas y secuencia | Número de izadas por capa + orden de carga dentro de cada capa |
| Resultados: Balance de peso | Peso y densidad por bodega, **informativo (no es restricción del modelo)** |
| Descarga | Enlaces al `plan_estiba.xlsx`, KPIs en CSV, y reporte de parámetros de la corrida |

**Stack:** Streamlit para la interfaz. Todo lo que hoy corre por CLI se expone como funciones puras desde `src/`.

**Despliegue:** Streamlit Community Cloud (gratuito, con la app durmiendo tras 12 h de inactividad). **Desplegada el 24 de septiembre de 2026 en https://prestow.streamlit.app**, desde `master` (cada push a `master` redespliega). **Validada en Cloud el mismo día**: el caso demo a 180 s reprodujo el caso base exacto (59,67 h, 1844 izadas, 9,4% de desbalance). Ojo: el límite es de reloj, así que en una máquina más lenta el resultado podría diferir mientras el gap no sea cero.

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
- **Capacidad real por plan: implementado el 22 de septiembre de 2026, a pedido explícito del dueño del proyecto** (pendiente #5 de la sección 10, "el packer no distingue altura"). Se revisaron las 8 hojas completas de `PLANIMETRIAS_MN_KIWI_ARROW_2025.xls` (antes solo se había revisado LH-1) y aparecieron 57 plantillas propias del Kiwi Arrow cubriendo planes 1-11 en bodegas 2-8 — mucho más de lo que se creía. Comparando la misma combinación bodega+producto entre planes: la mayoría de las bodegas no varían (0-3%, ruido), pero las **bodegas 4, 5, 7 y 8 muestran una caída real de 3-13% en los planes altos (8-10)**. Nuevo global `CAPACIDAD_POR_PLAN[(bodega, plan, producto)]` en `modelo_prestow.py`, pisa a `CAPACIDAD` (el valor uniforme del packer) donde hay dato real verificado — 72 combinaciones limpias tras excluir productos ambiguos, 10 conflictos entre plantillas del mismo archivo, y 1 valor extremo sin confirmar (bodega 5, plan 10, ARAUCO_EKP = 174, -55%). Extracción reproducible en `src/extraer_capacidades_reales.py` (lee `data/raw/PLANIMETRIAS_MN_KIWI_ARROW_2025.xls`, no versionado). **Esto cambió el makespan del caso base de 58,19 h a ≈59,67 h — ver sección 3, es un cambio real y esperado, no un bug.**
- **Pasada 3 por búsqueda de vecindarios: implementado el 25 de septiembre de 2026, a pedido explícito del dueño del proyecto** (pendiente #7 de la sección 10). Con el problema completo, HiGHS nunca mejoraba el punto de partida de la pasada 3: devolvía la solución de la pasada 2 sin cambios, y encima con `peso_min = 0`, así que el "desbalance" informado era el peso de la bodega más cargada. Ahora `resolver_pasada3_por_vecindarios` (en `modelo_prestow.py`, usada por la web y el CLI) hace tres cosas: ajusta `peso_max`/`peso_min` al peso real; corre 10 s de HiGHS sobre el problema completo, solo para obtener la cota dual y poder informar el gap; y recorre los pares de bodegas (libera dos, fija las otras seis) hasta que ningún par mejore. Cada solución aceptada se verifica contra todas las restricciones. El makespan queda acotado al de la pasada 2: la pasada 3 nunca lo empeora (sin esa cota, a 30 s subía de 59,97 a 60,21 h). Caso base a 180 s: desbalance de peso 6.294 → 3.604 t, gap 63,91% → 9,19%, desbalance entre cuadrillas 9,4% → 5,8%, makespan sin cambio. Detalle en `docs/05_Estado_app_web.md`, sección 20.
- **Warm start en la pasada 1, solo por debajo de 180 s: implementado el 22 de septiembre de 2026**, a raíz de que el usuario reportó que la web se quedaba sin devolver nada con límites de 30-90 s por pasada. Se verificó que el problema era real: sin punto de partida, HiGHS puede tardar más de 120 s solo en encontrar la PRIMERA solución entera factible de este modelo (a 30 s, a los 30 s el primal bound seguía en `inf`, cero soluciones encontradas pese a tener todas sus heurísticas internas activas). Nuevo módulo `src/solucion_inicial.py`: arma una asignación heurística factible en milisegundos (agrupa por destino según ROT, reparte en rondas chicas para mezclar productos dentro de una capa cuando hace falta, con reparo de la restricción de simetría al final) y la verifica contra **todas** las restricciones reales del modelo (no un subconjunto) antes de usarla — si no pasa, se resuelve sin warm start, igual que antes; nunca se le inyecta al solver algo sin validar. `api.py` la usa para la pasada 1 **solo si `limite_segundos < UMBRAL_WARM_START_PASADA1` (180 s)** — medido que un warm start heurístico por encima de ese umbral ANCLA la búsqueda cerca de su propio punto de partida: a 180 s con warm start el resultado fue 60,18 h (gap 4,1% sin bajar más), peor que los 59,67 h que el solver ya lograba buscando desde cero en el mismo tiempo. Por debajo del umbral el warm start es estrictamente una mejora (antes: sin solución; ahora: 59,97-60,21 h en pruebas a 30/60/90 s). La pasada 2 SIEMPRE usa warm start desde la solución de la pasada 1 (sin condición de umbral) — es continuar la propia búsqueda del solver bajo la nueva cota de makespan, no un heurístico externo, así que no tiene el mismo riesgo de anclaje; de paso probablemente resuelve el pendiente #4 de la sección 10 ("la pasada 2 no resuelve en 150-180 s"), aunque no se hizo una comparación A/B rigurosa. **Verificado que a 180 s+ el makespan del caso base sigue dando 59,67 h, igual al vigente — no cambió nada para la configuración ya validada.** La web (`app/pages/1_Ejecutar.py`) ahora corre el solver en un hilo aparte y muestra la etapa actual + tiempo transcurrido cada segundo, en vez de un spinner ciego. De paso se corrigió un bug real en el CLI (`modelo_prestow.py`): `resolver(prob)` en `main()` no pasaba `limite=LIMITE_SEGUNDOS` explícito, así que usaba el default del parámetro (evaluado una sola vez al cargar el módulo) en vez del valor de `--limite` — con `--limite 30` igual resolvía con 120 s, sin avisar. No afectaba a la web (que no pasa por ese código), pero se corrigió igual. Detalle completo en `docs/05_Estado_app_web.md`.

## 7. Los 9 supuestos, con su estado actual

| # | Supuesto | Estado |
|---|---|---|
| 1 | El Puerto fija el tonelaje por bodega | Sin confirmar |
| 2 | Rendimientos t/h del archivo (140 bod 1, 270 el resto) | Sin confirmar |
| 3 | Pares de cuadrillas son fijos: (8+7), (6+5), (4+3), (2+1) | Sin confirmar |
| 4 | Huellas de los productos | **Resuelto** — verificadas en 58 plantillas |
| 5 | Acortamiento de bodega en planes altos | **Parcialmente confirmado (22-sep-2026)** — se había descartado por revisar solo la hoja LH-1 (bodega 1), donde en efecto los planes altos son del Eagle Arrow. Al revisar las 8 hojas completas, las bodegas 4, 5, 7 y 8 SÍ muestran una caída real de capacidad de 3-13% en planes altos (8-10) con datos propios del Kiwi Arrow. Ver "Capacidad real por plan" en sección 6. |
| 6 | Tiempo por izada | **Corregido** — varía por bodega (13,91 min bod 1 vs 7,15 el resto) |
| 7 | Sin bloqueo entre destinos dentro de una capa | Declarado |
| 8 | Sin merma por separadores, maniobra ni medidas no netas | Avalado por el profesor |
| 9 | Orden entre Kunsan y Ulsan | **CERRADO** — confirmado: Ulsan es el último (orden 4) |

## 8. Errores documentados que no hay que repetir

| Error | Cómo se detectó |
|---|---|
| Leer solo la hoja LH-1 de planimetrías | El archivo tiene 58 plantillas del Kiwi Arrow en LH-1 a LH-8. Este mismo error se repitió una segunda vez (22-sep-2026): de la revisión parcial de LH-1 se generalizó "solo hay plantillas propias del Kiwi Arrow hasta el plan 6" a TODAS las bodegas, cuando en realidad bodegas 2-8 sí tienen plantillas propias hasta el plan 11. Verificar siempre las 8 hojas antes de asumir qué datos faltan. |
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
| Unidades totales | **29.332** — confirmado como **PROGRAMA LQN** (ver pendiente #3, resuelto en sección 10) |
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

1. ~~Estabilidad de la asignación entre corridas~~ — **Resuelto el 22 de septiembre de 2026, re-verificado con la configuración vigente** (capacidad real por plan + warm start de las pasadas 1-3, ver sección 6). `python3 src/stability_test.py --limite 180 --n 5` (5 semillas: 42, 1337, 0, 271828, 314159) dio **makespan idéntico (59,6702 h, desv. std 0,0000) y unidades por bodega idénticas en las 5 corridas**, sin excepción — ver `data/stability_report.csv`. Además, revisando el log completo, las TRES pasadas dieron el mismo gap en las 5 corridas (pasada 1: 3,29%; pasada 2: 3,24%; pasada 3: 63,91%), incluida la pasada 3, que el pendiente #7 documentaba como variable entre corridas — esa variabilidad se midió con una configuración anterior (antes de la capacidad real por plan) y hoy no se reprodujo. El modelo es determinista con la configuración actual: el análisis "en qué bodega quedó qué" ya se puede mostrar con confianza en la web.
2. ~~Warm start desde el plan real~~ — **Implementado el 22 de septiembre de 2026, aunque no exactamente como se planteaba.** No es warm start desde el plan real del puerto (no se construyó ese parseo), sino desde una asignación heurística propia (`src/solucion_inicial.py`), y solo por debajo de 180 s por pasada — ver sección 6. No da la garantía original de "nunca peor que 60,61 h" (a 30-90 s se vio 59,97-60,21 h, todos mejores que 60,61 h en las pruebas hechas, pero no hay garantía matemática), pero sí resuelve el problema real que motivaba el pendiente: la web ya no se queda sin devolver nada con límites bajos.
3. ~~275 unidades sin reconciliar~~ — **Resuelto el 22 de septiembre de 2026.** La hoja "PRESTOW N° 06" de `data/raw/PRESTOW_N_10_KIWI_ARROW_FE_042025.xls` trae, por bodega, dos programas paralelos: `PROGRAMA G2OCEAN` y `PROGRAMA LQN` (filas 75-76 de cada bloque de bodega), además de un total `HOLD NRO. X` en unidades (fila 74). Sumando a mano los bloques individuales de carga (destino+producto+UNITS+TONS) en las tres bodegas responsables de toda la brecha (7: +150, 5: −68, 3: +193, suman exactamente 275), el total y las toneladas calzan **exactas, al centavo**, con `PROGRAMA LQN` — no con `HOLD NRO.`. `DEMANDA` (29.332) es la suma de esos mismos bloques en las 8 bodegas, o sea corresponde a PROGRAMA LQN — el programa propio de Lirquén, consistente con que el modelo ya se calibra contra el archivo del puerto. 29.057 es la suma de `HOLD NRO.`, que coincide con LQN en 5 de 8 bodegas pero no en esas 3. El propio archivo del puerto ya traía la brecha marcada (fila 73, columnas 33-35: 29057/29332/-275) sin resolverla — no era un error de nuestra extracción. No se tocó `modelo_prestow.py`: `DEMANDA` ya usaba el valor correcto.
4. ~~La pasada 2 no resuelve en 150-180 s~~ — **Cerrado el 24 de septiembre de 2026** con la comparación A/B controlada que faltaba (misma solución de pasada 1, dos pasadas 2 de 180 s): con warm start objetivo 1944 (gap 3,24%), sin warm start 1959 (gap 4,03%), makespan 59,67 h en ambas. Con la configuración vigente la pasada 2 SÍ resuelve sin warm start (primera solución a los ~20 s); el warm start se mantiene porque mejora el objetivo. Detalle en `docs/05_Estado_app_web.md`, sección 17.
5. ~~El packer no distingue altura~~ — **Resuelto el 22 de septiembre de 2026** para las combinaciones con dato real verificado (72 de las posibles, ver "Capacidad real por plan" en sección 6). El packer sigue sin distinguir altura por sí mismo (sigue siendo geométrico uniforme); lo que cambió es que `modelo_prestow.py` ahora pisa ese cálculo con datos reales del puerto donde existen.
6. **Pruebas automatizadas** — parcial: `tests/` cubre layout, secuencia de izadas, balance de peso, capacidad por plan, solución inicial, el packer (`test_packer_2d.py`) y la capa de resolución (`test_resolucion.py`), estos dos últimos del 24-sep-2026. Sin tests: `api.resolver_prestow` de punta a punta (tarda minutos) y la app Streamlit (QA manual con AppTest, ver `docs/05` sección 15).
7. ~~La pasada 3 (balance de peso) no optimizaba nada~~ — **Resuelto el 25 de septiembre de 2026**: ahora se resuelve por búsqueda de vecindarios (ver sección 6). En el caso base, desbalance de peso de 6.294 a 3.604 t, gap de 63,91% a 9,19%. Queda abierto: probar si con vecindarios se puede volver a subir `ETAPAS_BALANCE_PESO` (balance puerto a puerto); la sección 10 de `docs/05` lo había descartado atribuyéndolo a una relajación débil, pero es más probable que también ahí fuera la búsqueda.

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
- **No cambiar el makespan del caso base sin advertirlo.** Cualquier cambio que altere el makespan vigente debe justificarse. **El valor vigente ya NO es 58,19 h — es ≈59,67 h desde el 22 de septiembre de 2026** (capacidad real por plan, ver sección 6). El cambio está justificado y documentado; lo que no se debe hacer es introducir OTRO cambio sin la misma documentación.
- **No usar `assert` para validación en producción**. `assert` solo en tests.
- **No usar la palabra "óptimo"** en la interfaz sin gap cero verificado. El caso base a 180 s termina con gap 3,29% (pasada 1), 3,24% (pasada 2) y 9,19% (pasada 3). Desde el 24-sep-2026 el gap se lee del objeto HiGHS (antes el log no se capturaba y el gap quedaba en None) — ver `docs/05` sección 17.

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
- **`docs/reportes_sesion/2026-09-25_explicacion_completa_para_informes.md`** — **explicación completa del sistema como base para los informes Técnico y Académico**, con las cifras vigentes y el registro de cifras obsoletas de los documentos anteriores (leer antes de redactar cualquier informe)
- `src/generador_instancias.py` + `src/analisis_informes.py` — instancias de prueba y análisis de sensibilidad (rendimientos t/h, tamaño) para los informes; datos en `data/instancias/`, resultados en `data/resultados_analisis/resultados.csv`, tablas en la sección 18 del documento anterior. Hallazgo: a 180 s o más la pasada 1 no usa punto de partida y 3 de 8 instancias no encontraron solución; a 170 s resolvieron las 12
- `docs/Resumen_Trabajo_Realizado.md` — resumen del análisis y decisiones (⚠️ cifras de resultados desactualizadas, ver el documento anterior, sección 15)
- `docs/03_Instrucciones_afinar_modelo.md` — cambios recientes al modelo y pendientes técnicos
- `docs/Restricciones_Modelo_Prestow_Lirquen.pdf` — formulación matemática completa
- `docs/Guia_de_tareas_Prestow_Lirquen.pdf` — las 120 tareas del proyecto
- `docs/04_Prompt_Informe_Tecnico.md` y `docs/01_Contexto_Informe_Academico.md` — bases de los informes finales
- **`docs/05_Estado_app_web.md`** — **estado actual de la app Streamlit** (leer antes de tocar `app/`): qué se construyó en Fases 1 y 1.5, decisiones de diseño, bugs resueltos y lo que falta
