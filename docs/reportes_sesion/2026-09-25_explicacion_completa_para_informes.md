# Explicación completa del sistema — base para los informes Técnico y Académico

**Fecha:** 25 de septiembre de 2026 · **Estado del código:** commit `188815c` (`origin/master`) · **App desplegada:** https://prestow.streamlit.app

Este documento reúne en un solo lugar qué hace el programa, cómo está construido, qué resultados da hoy y cómo se llegó a él. Está pensado como **insumo para redactar los dos informes**:

- **Informe Técnico:** describe la solución para quien la usa y la mantiene (planificador portuario). Sección 13.
- **Informe Académico:** reflexiona sobre el proceso de desarrollo: decisiones, alternativas, errores y aprendizajes (lector: el profesor). Sección 14.

> **Tareas pendientes del equipo:** hay 5 cosas que ningún asistente puede hacer y que el equipo debe desarrollar antes de cerrar los informes (referencias APA, capturas, bitácora, autoevaluaciones y enunciado oficial). Están en la **sección 16**, con cómo hacerlas y cuándo quedan terminadas.

Las secciones 1 a 12 son el contenido común: se escriben una vez y cada informe toma lo que necesita, con su tono. La sección 18 trae los análisis hechos específicamente para los informes (instancias de prueba, sensibilidad a rendimientos y a tamaño).

> **Antes de copiar cifras de otros documentos:** varios documentos anteriores (`00_LEEME_PRIMERO_contexto.md`, `01_Contexto_Informe_Academico.md`, `04_Prompt_Informe_Tecnico.md`, `Resumen_Trabajo_Realizado.md`) tienen cifras que ya no están vigentes (57,59 h, 58,19 h, desbalance 0,1-0,2%, fragmentación 21-22, "275 unidades sin reconciliar", "gap 0,195%"). La **sección 15** lista cada cifra obsoleta con su reemplazo. **Ante cualquier duda, manda este documento y `CLAUDE.md` sección 3.**

---

## 0. Instrucciones para el asistente que redacte los informes

**Contexto.** La aplicación está terminada: el profesor la dio por lista. Tu trabajo es **redactar los informes**, no proponer mejoras al software. Lo que la app no hace se declara como alcance o limitación (secciones 8 y 11), no como tarea pendiente.

**Archivos que deberías tener adjuntos** (si falta alguno, pídelo antes de escribir la sección que lo necesita):

| Archivo | Para qué |
|---|---|
| Este documento | Fuente principal de contenido y cifras |
| `docs/Guia_Informe_Tecnico_Prestow_Lirquen.pdf` | Qué pide cada subtarea del Informe Técnico, criterio de terminado y errores de redacción a evitar |
| `docs/Guia_de_tareas_Prestow_Lirquen.pdf` | Qué pide cada subtarea de ambos informes (tareas T, A, M, W) |
| `docs/Restricciones_Modelo_Prestow_Lirquen.pdf` | Formulación matemática formal para el anexo (completarla con la sección 5 de este documento) |
| `data/resultados_analisis/resultados.csv` | Resultados de cada instancia de prueba (sección 18), por si se necesita una columna que no está en las tablas |
| `planificacion/Bitacora_Semanal_Prestow_Lirquen.xlsx` | Única fuente de la sección "Proceso de desarrollo" del Académico |
| Enunciado oficial del curso (lo tiene el equipo) | Rúbrica y puntajes definitivos |

**Reglas de redacción:**

1. **Cifras:** usar solo las de este documento (secciones 1, 10 y 18). Si otro documento dice otra cosa, manda este (ver la sección 15). La cifra del resumen ejecutivo, la de la comparación con el plan manual y la de la captura del manual deben ser la misma: **59,67 h contra 60,61 h**.
2. **No inventar.** Si falta un dato, escribir `[PENDIENTE: qué falta]` en vez de estimarlo. Nunca generar referencias bibliográficas: las citas APA las verifica el equipo en la fuente original.
3. **No decir "óptimo" ni "solución óptima"**: ninguna pasada probó optimalidad. Decir "la mejor solución encontrada dentro del límite de tiempo" o "a lo más a X% del óptimo" (gap).
4. **No presentar la mejora de makespan (−1,6%) como el resultado principal.** El valor es "minutos en lugar de días" con calidad equivalente o mejor (sección 1). Con otra instancia la diferencia podría ser negativa.
5. **No mezclar el objetivo del modelo** (minimizar el makespan) **con los beneficios del sistema** (velocidad, repetibilidad, escalabilidad).
6. **Supuestos en tres partes:** qué se asume, por qué y qué pasaría si fuera falso (sección 4).
7. **Informe Técnico:** para el planificador portuario; prosa en el cuerpo y modelo formal en anexo. Extensión máxima: Resumen ejecutivo 1 página, Problema y contexto 2, Objetivos 1, Modelo y método 4, Arquitectura 1, Datos de entrada 2, Instrucciones de uso 5, Validación y testeo 3.
8. **Informe Académico:** para el profesor; reflexión sobre el proceso: decisiones con sus alternativas, errores y aprendizajes (sección 14). Declarar el uso de IA generativa (sección 14).
9. **Lo que solo aporta el equipo** (sección 16, tareas T1 a T5): no lo redactes tú. Donde haga falta, deja el marcador `[PENDIENTE EQUIPO: T#]` (por ejemplo `[PENDIENTE EQUIPO: T2 — captura de la página Resultados]`), para que el equipo encuentre todo lo que falta buscando ese texto.

---

## Índice

1. El sistema en una página
2. El problema operativo
3. Los datos: fuentes, extracción y hallazgos
4. Los supuestos
5. El modelo matemático
6. El método de solución
7. Arquitectura del software
8. La aplicación web
9. Validación
10. Resultados vigentes
11. Limitaciones
12. Cronología del trabajo
13. Guía para el Informe Técnico (sección por sección)
14. Guía para el Informe Académico (sección por sección)
15. Registro de cifras obsoletas
16. Tareas del equipo (lo que falta y solo el equipo puede hacer)
17. Glosario
18. Análisis para los informes: instancias de prueba, rendimientos y tamaño

---

## 1. El sistema en una página

**Qué es.** Una herramienta que genera el *prestow* (plan de estiba) de celulosa unitizada para un buque *open hatch* en Puerto Lirquén. Decide cuántas unidades de cada producto y destino van a cada bodega y a cada capa ("plan"), de modo que el buque termine de cargarse lo antes posible.

**Para quién.** El planificador del puerto. Hoy arma el plan a mano, copiando el archivo del viaje anterior.

**Qué optimiza.** El *makespan*: las horas de la cuadrilla más cargada. El buque zarpa cuando termina la última de las cuatro cuadrillas, así que lo que importa es el máximo, no la suma. En segundo y tercer lugar, sin empeorar lo anterior: menos izadas de grúa, menos fragmentación de cada destino entre bodegas y mejor balance de peso entre bodegas al zarpar.

**Qué garantiza siempre** (restricciones duras): se embarca exactamente lo pedido; ninguna capa excede lo que cabe; la carga que se descarga primero queda arriba (cero *overstowage*); no hay capas flotando; una capa se llena al menos al 90% antes de abrir la siguiente.

**Cómo se usa.** Por una página web: se carga el caso demo o se edita el buque, los productos, el viaje y la rotación; se indica el nombre del buque y los KPIs del plan de referencia; se ejecuta (≈7 minutos con la configuración recomendada: 180 s en cada una de las dos primeras pasadas y ~40 s en la tercera); y se revisan los resultados (vista del buque, planimetría por capa, secuencia de izadas, balance de peso, comparación con el plan de referencia) y se descarga un Excel con todo.

**Resultado principal (caso base Kiwi Arrow, 180 s por pasada):**

| Indicador | Plan manual del puerto | Modelo | Lectura |
|---|---|---|---|
| Makespan | 60,61 h | **59,67 h** | −0,94 h (−1,6%) |
| Desbalance entre cuadrillas | 6,9% | **5,8%** | mejor |
| Fragmentación (bodegas × destino) | 14 | **11** | mejor |
| Overstowage | 0 | **0** | igual |
| Tiempo de planificación | días (manual) | **minutos** | la ganancia principal |

**Propuesta de valor** (citarla igual en ambos informes): el plan manual ya es bueno (cero overstowage, 6,9% de desbalance). El sistema no compite contra un proceso deficiente: **reproduce esa calidad, o la mejora levemente, en minutos en lugar de días, para cualquier configuración de carga, sin depender de la experiencia de una persona ni de copiar el archivo del viaje anterior.** Los beneficios son velocidad, repetibilidad y escalabilidad. La mejora de makespan (−1,6%) es un beneficio secundario y no debe presentarse como la conclusión principal.

---

## 2. El problema operativo

**El buque.** Kiwi Arrow (G2 Ocean). Ocho bodegas en fila. Cada una es una caja de 19,26 m de alto sin cubiertas intermedias, donde la carga se apila en hasta **11 capas horizontales ("planes")**; el plan 1 es el fondo. Las bodegas 2 a 8 miden 18,30 × 27,40 m y son idénticas. La **bodega 1 es más chica: 16,80 × 14,80 m**.

**Las cuadrillas.** Cuatro equipos trabajan en paralelo, cada uno sobre un **par fijo de bodegas contiguas**: (8+7), (6+5), (4+3), (2+1). Cada cuadrilla atiende sus dos bodegas una tras otra. El buque zarpa cuando termina la última cuadrilla.

**Las izadas.** La grúa mueve hasta **16 unidades por izada**. El tiempo por ciclo es de **7,11-7,19 min en las bodegas 2-8 y 13,91 min en la bodega 1**, casi el doble. Este dato resultó decisivo: la bodega 1 (junto con la 2) define la cuadrilla crítica.

**El overstowage.** La carga que se descarga primero debe quedar arriba. Si carga del último puerto queda debajo de la del primero, en el primer puerto hay que sacarla, dejarla en el muelle y volver a cargarla (*rehandle*): tiempo y dinero perdidos.

**La rotación del caso base.** Taichung (1) → Qingdao (2) → Kunsan (3) → Ulsan (4). Ulsan como último destino está confirmado.

**La carga del caso base.** 29.332 unidades, 59.197 t, 2,02 t por unidad, 5 productos (N_ALDEA_EKP, N_ALDEA_BKP, ARAUCO_EKP, ARAUCO_BKP, CELCO_UKP), 4 destinos, 13 combinaciones producto-destino.

**El plan manual (referencia).** Sale de la hoja "PRESTOW N° 06" del archivo del puerto: 85 capas con carga (5 mixtas), 0 overstowage, horas por cuadrilla 56,62 / 58,49 / 57,26 / **60,61 h** (la cuadrilla 4, bodegas 2+1, define el makespan) y desbalance de 6,9%. Unidades por bodega: 8→3.555, 7→3.863, 6→4.227, 5→3.672, 4→3.823, 3→3.661, 2→4.294, 1→1.962.

---

## 3. Los datos: fuentes, extracción y hallazgos

### Fuentes

| Archivo | Qué contiene | Versionado |
|---|---|---|
| `data/raw/PRESTOW_N_10_KIWI_ARROW_FE_042025.xls` | Plan real del puerto (hoja "PRESTOW N° 06"): carga por bodega y plan, horas por bodega y cuadrilla | No (datos del puerto) |
| `data/raw/PLANIMETRIAS_MN_KIWI_ARROW_2025.xls` | Plantillas de planimetría LH-1 a LH-8: cuántas unidades caben por bodega, plan y producto | No |
| `data/datos_entrada_kiwi_arrow.xlsx` | Entrada editable del modelo: hojas Instrucciones, Viaje, Rotación, Buque, Productos | Sí |
| `data/capacidades.csv` | Salida del packer: 40 combinaciones (8 bodegas × 5 productos) | Sí |
| `data/capacidades_reales_por_plan.csv` | 72 capacidades reales por (bodega, plan, producto) extraídas de las plantillas | Sí |

### Hallazgos en los datos (material para "Tratamiento de datos")

1. **Hojas ocultas de otro buque.** El archivo del prestow tiene 6 hojas, solo 2 visibles; 4 son del Misago Arrow (2017) con el mismo formato. Se trabajó un tiempo sobre la hoja equivocada. Esto es evidencia de que **el archivo no se rehace por buque: crece por acumulación**, y es un argumento a favor de la herramienta.
2. **Planimetrías repartidas en 8 hojas.** Al revisar solo LH-1 se concluyó que tres productos no tenían plantilla propia. En realidad hay 57-58 plantillas del Kiwi Arrow en LH-1 a LH-8. **El error se cometió dos veces** (la segunda al generalizar "solo hay plantillas hasta el plan 6" desde LH-1 a todas las bodegas).
3. **Huellas mal supuestas.** Cuatro capas del plan real ponían 408 unidades donde el cálculo permitía 403. La cota absoluta por área con la huella supuesta ya daba 406, así que ningún patrón podía explicarlo: el error estaba en la huella. Las reales son ARAUCO_BKP 0,84 × 1,36 (no 1,47) y CELCO_UKP 0,84 × 1,43. Con las huellas correctas, el plan real satisface las cuatro verificaciones del modelo.
4. **Inconsistencias del archivo.** Sobrantes negativos de hasta 20 m (físicamente imposibles); bloques de igual dimensión con distinta cantidad declarada; el mismo producto como "CELCO UKP" y "CELCO" (fusionados como decisión declarada).
5. **Las 275 unidades (resuelto).** La extracción suma 29.332 unidades y circulaba otra cifra de 29.057. La hoja trae dos programas paralelos por bodega: `PROGRAMA G2OCEAN` y `PROGRAMA LQN`. La extracción calza exacto, en unidades y toneladas, con **PROGRAMA LQN** (el programa propio de Lirquén); 29.057 es la suma de `HOLD NRO.`, que difiere en las bodegas 3 (+193), 5 (−68) y 7 (+150). El propio archivo del puerto ya marcaba la brecha (fila 73) sin resolverla.
6. **La capacidad cambia con la altura (parcialmente confirmado).** Comparando la misma bodega y producto entre planes, las bodegas 4, 5, 7 y 8 muestran una caída real de 3-13% en los planes altos (8-10). Se extrajeron 72 capacidades limpias (`src/extraer_capacidades_reales.py`), descartando 10 conflictos entre plantillas, productos ambiguos y un valor extremo sin confirmar (bodega 5, plan 10, ARAUCO_EKP = 174). Sin inventar números: donde el dato es dudoso se usa el cálculo geométrico.

### Parámetros derivados

- **Tiempo de ciclo por bodega:** derivado de las horas declaradas del archivo (7,11-7,19 min en las bodegas 2-8; 13,91 min en la bodega 1).
- **Rendimientos del archivo:** 140 t/h en la bodega 1 y 270 t/h en el resto (supuesto 2, sin confirmar).
- **Huellas verificadas (m):** N_ALDEA_EKP 0,84 × 1,47 · N_ALDEA_BKP 0,84 × 1,36 · ARAUCO_EKP 0,89 × 1,41 · ARAUCO_BKP 0,84 × 1,36 · CELCO_UKP 0,84 × 1,43.

---

## 4. Los supuestos

Redactarlos en los informes con tres partes: **qué se asume, por qué, y qué pasaría si fuera falso.**

| # | Supuesto | Estado | Si fuera falso |
|---|---|---|---|
| 1 | El puerto fija el tonelaje por bodega | Sin confirmar | Si lo fijara el armador, habría que agregar una restricción de tonelaje por bodega y retirar la ruptura de simetría |
| 2 | Rendimientos t/h del archivo (140 / 270) | Sin confirmar | Cambian los tiempos de ciclo y, con ellos, qué cuadrilla es crítica |
| 3 | Pares de cuadrillas fijos: (8+7), (6+5), (4+3), (2+1) | Sin confirmar | Si pudieran reagruparse, el makespan podría bajar más; el modelo necesitaría decidir los pares |
| 4 | Huellas de los productos | **Resuelto**: verificadas en las plantillas | — |
| 5 | Acortamiento de la bodega en planes altos | **Parcialmente confirmado**: caída de 3-13% en las bodegas 4, 5, 7 y 8; modelado con capacidad real por plan | Donde no hay dato, el modelo podría sobrestimar la capacidad de los planes altos |
| 6 | Tiempo por izada | **Corregido**: varía por bodega | — |
| 7 | Sin bloqueo entre destinos dentro de una misma capa | Declarado | Si hubiera bloqueo, las capas mixtas necesitarían un orden interno; hoy son 5 de 85 |
| 8 | Sin merma por separadores, maniobra ni medidas no netas | Avalado por el profesor | La capacidad real sería algo menor que la geométrica |
| 9 | Orden entre Kunsan y Ulsan | **Cerrado**: Ulsan es el último | — |

Distinguir en la redacción **restricción** (algo que el modelo garantiza siempre) de **supuesto** (algo que el modelo trata como cierto pero podría no serlo).

---

## 5. El modelo matemático

### En prosa (para el cuerpo del Informe Técnico)

> «El sistema decide qué carga va en cada bodega y en qué capa, de modo que las cuatro cuadrillas terminen lo más pronto posible, porque el buque no puede zarpar hasta que la última termine. Al mismo tiempo respeta que la carga que se descarga primero quede siempre arriba, que cada capa no exceda lo que cabe en el piso y que se embarque exactamente lo comprometido.»

### Tamaño real

Las 29.332 unidades **no son variables**: el modelo decide cantidades por (bodega, plan, producto, destino). Queda en **1.707 variables** (1.704 enteras, de ellas 472 binarias) y **2.204 restricciones**. Las unidades individuales solo aparecen dentro de la capa, en el packer y en la planimetría.

### Conjuntos

- *H*: bodegas (1-8); *T*: planes (1-11, 1 = fondo); *P*: productos; *D*: destinos; *K* ⊆ *P* × *D*: combinaciones con demanda; *G*: cuadrillas, cada una con su par de bodegas.

### Parámetros

- *Q*(p,d): unidades a embarcar; *C*(h,t,p): unidades de p que caben en una capa de la bodega h en el plan t (packer, reemplazado por el dato real del puerto cuando existe).
- *rot*(d): orden de descarga; *tc*(h): horas por izada de la bodega h; *U* = 16 unidades por izada; φ = 0,90 (llenado mínimo); *peso*(p) = 2,02 t.

### Variables

- *x*(h,t,p,d) ∈ ℤ⁺: unidades de p con destino d en el plan t de la bodega h.
- *y*(h,t,d) ∈ {0,1}: el destino d ocupa el plan t de la bodega h.
- *w*(h,t) ∈ {0,1}: el plan t de la bodega h tiene carga (distinta de *y*, ver el error de contigüidad en la sección 14).
- *z*(h,t) ∈ ℤ⁺: izadas del plan t de la bodega h.
- *v*(h,d) ∈ {0,1}: el destino d usa la bodega h (fragmentación).
- *T_max* ≥ 0: makespan. *peso_max*, *peso_min* ≥ 0: bodega más y menos cargada al zarpar.

### Restricciones (10 familias, en `construir_modelo()`)

| # | Nombre | Forma | Por qué |
|---|---|---|---|
| 1 | Cobertura | Σ_{h,t} x(h,t,p,d) = Q(p,d) | Se embarca exactamente lo comprometido |
| 2 | Capacidad | Σ_{p,d} x(h,t,p,d) / C(h,t,p) ≤ 1 | Cada producto ocupa una fracción de la capa; la suma no pasa de 1 |
| 3 | Enlace x-y | x ≤ M · y, con M = min(C, Q) | Si hay carga de un destino, su binaria se activa; M ajustado para una relajación más fuerte |
| 4 | No-overstowage | y(h,t,d) + y(h,t+1,d') ≤ 1 si rot(d') > rot(d) | Un destino que se descarga después no puede quedar encima de uno que se descarga antes. Solo entre planes adyacentes: equivalente a imponerla entre todos los pares gracias a la contigüidad (demostrado por inducción y verificado en 211.000 configuraciones), y reduce el modelo de 3.828 a 2.108 restricciones |
| 5a-c | Ocupación y contigüidad | Σx ≥ w; Σx ≤ Ā · w; w(h,t+1) ≤ w(h,t) | Sin capas flotando; escrita sobre *w*, no sobre *y* |
| 5d | Llenado mínimo | Σ x/C ≥ φ · w(h,t+1) | Una capa debe estar al 90% antes de abrir la siguiente (la última queda exenta) |
| 6 | Izadas | U · z(h,t) ≥ Σ_{p,d} x(h,t,p,d) | Cada izada mueve hasta 16 unidades |
| 7 | Makespan | T_max ≥ Σ_{h∈g} Σ_t tc(h) · z(h,t), para cada cuadrilla g | El buque zarpa cuando termina la cuadrilla más cargada |
| 8 | Fragmentación | Σ_t y(h,t,d) ≤ \|T\| · v(h,d) | Cuenta en cuántas bodegas queda cada destino |
| 9 | Ruptura de simetría | Σ x(h1) ≥ Σ x(h2) para bodegas gemelas de una misma cuadrilla | Evita explorar soluciones permutadas; solo en las pasadas 1 y 2 |
| 10 | Balance de peso | peso_max ≥ peso(h) ≥ peso_min para toda bodega h (carga al zarpar) | Solo en la pasada 3 |

La formulación completa con justificaciones está en `docs/Restricciones_Modelo_Prestow_Lirquen.pdf`. **Ese PDF es anterior** a las restricciones 9 y 10 y a la capacidad real por plan: para el anexo, completarlo con esta tabla.

### Objetivo: tres pasadas lexicográficas

1. **Pasada 1:** minimizar *T_max*.
2. **Pasada 2:** acotar *T_max* ≤ T₁ + 2 izadas (tolerancia absoluta) y minimizar izadas + 10 × fragmentación.
3. **Pasada 3:** acotar el objetivo de la pasada 2 (+2) y el makespan de la pasada 2, retirar la ruptura de simetría y minimizar peso_max − peso_min (balance de peso al zarpar).

**Por qué lexicográfico y no pesos:** se probó con pesos y el tercer término quedaba numéricamente indistinguible (la fragmentación empeoraba al agregarlo). La tolerancia es absoluta (en izadas) porque una relativa dejaba menos margen justamente cuando la pasada 1 era mejor.

---

## 6. El método de solución

### Elección del método

- **Alternativas consideradas:** exacto puro, metaheurística, e híbrido (exacto en la asignación + heurístico en el empaquetamiento). La propuesta inicial de híbrido fue una opinión externa con confianza media; el grupo la evaluó y eligió **MILP exacto con límite de tiempo**, que dio mejores resultados medidos y es más simple de mantener.
- **Solver:** HiGHS (libre, sin licencia, desplegable en la nube) con CBC de respaldo. CPLEX y Gurobi no se pueden desplegar en un hosting público. Medición histórica (versión anterior del modelo, 150 s): CBC 57,12 h contra HiGHS 56,88 h, y CBC necesitó 600 s para alcanzar lo que HiGHS logró en 150. **Es de una versión anterior del modelo: citarla como medición histórica o repetirla.**
- **Librería:** PuLP 3.3.2.

### El packer 2D (capacidad por capa)

Módulo separado (`packer_2d.py`) porque la geometría no cambia entre viajes: se precalcula una vez. Prueba tres patrones de empaquetamiento (uniforme, dos bloques y cuatro bloques) y se queda con el mejor. En las bodegas grandes gana el de cuatro bloques y en la bodega 1 el uniforme, así que los tres hacen falta. Produce `capacidades.csv`. El modelo pisa ese valor con la capacidad real del puerto donde existe (72 combinaciones).

### Punto de partida (warm start) de la pasada 1

Sin punto de partida, HiGHS puede tardar más de 120 s solo en encontrar la primera solución factible (por la combinatoria de contigüidad + no-overstowage + llenado mínimo). Con límites bajos, la web no devolvía nada. `solucion_inicial.py` arma en milisegundos una asignación factible (llenado por niveles, en orden de rotación) y **la verifica contra todas las restricciones reales** antes de usarla. Se aplica **solo por debajo de 180 s**: se midió que por encima ancla la búsqueda (a 180 s con warm start: 60,18 h, contra 59,67 h sin él).

### Pasadas 2 y 3 con punto de partida

La pasada 2 arranca desde la solución de la pasada 1. Comparación A/B controlada: objetivo 1944 con warm start contra 1959 sin él.

**La pasada 3 se resuelve por búsqueda de vecindarios** (25-sep-2026). Con el problema completo, HiGHS nunca mejoraba el punto de partida. La búsqueda:

1. Ajusta *peso_max*/*peso_min* al peso real de la solución de la pasada 2.
2. Corre 10 s de HiGHS sobre el problema completo, solo para obtener la cota dual (y así informar un gap honesto).
3. Recorre los 28 pares de bodegas: libera las dos, fija las otras seis y resuelve el subproblema (segundos). Acepta el cambio si baja el desbalance y la solución pasa la verificación contra todas las restricciones. Repite hasta que ninguna ronda mejora.

El makespan queda acotado al de la pasada 2: el balance nunca empeora el tiempo de carga. En el caso base baja el desbalance de peso de 6.294 a 3.604 t en ~40 s.

### Cómo se mide la calidad de la solución

Se informa el **gap** de cada pasada: qué tan lejos puede estar la solución del mejor valor posible, según la cota que el solver alcanzó a probar. Se lee directo del solver (`getInfo().mip_gap`). **No confiar en el estado que devuelve PuLP**: dice "Optimal" en corridas que no probaron optimalidad. La palabra "óptimo" solo se usa con gap cero.

---

## 7. Arquitectura del software

### Módulos (`src/`, el núcleo)

| Módulo | Qué hace |
|---|---|
| `modelo_prestow.py` | Lectura de datos, construcción del MILP, las tres pasadas, verificaciones, exportación del Excel tipo prestow. También es el CLI |
| `packer_2d.py` | Capacidad por geometría (tres patrones); genera `capacidades.csv` |
| `extraer_capacidades_reales.py` | Extrae las capacidades reales por plan desde las planimetrías del puerto |
| `solucion_inicial.py` | Heurístico de punto de partida para la pasada 1, verificado contra todas las restricciones |
| `api.py` | `resolver_prestow()`: función que llama la web. Aísla los globales del modelo entre corridas, informa el progreso, arma el resultado (plan, KPIs, gaps por pasada, verificaciones, Excel) |
| `layout_capa.py` | Posición (x, y) de cada grupo de unidades dentro de una capa, para la planimetría visual |
| `secuencia_izadas.py` | Agrupa las unidades en izadas de 16 como bloques rectangulares y decide el orden de carga |
| `balance_peso.py` | Peso y densidad por bodega (informativo) |
| `stability_test.py` | Corre el modelo con 5 semillas y mide la variabilidad |

### Aplicación web (`app/`, cliente del núcleo)

`app.py` (Inicio) y las páginas `0_Configuracion.py`, `1_Ejecutar.py` y `2_Resultados.py`. Componentes en `app/components/`: formularios editables, gráficos del buque (Plotly), formato y Excel, comparación con la referencia (`referencia.py`), caso demo y recarga del núcleo tras un despliegue (`nucleo.py`).

### Flujo de datos

```
datos_entrada.xlsx ──► packer_2d ──► capacidades.csv ─┐
planimetrías puerto ─► extraer_capacidades_reales ────┤  (capacidad real por plan)
                                                      ▼
Configuración (web) ─► api.resolver_prestow ─► modelo_prestow
                           │   pasada 1 (makespan; warm start si < 180 s)
                           │   pasada 2 (izadas + fragmentación; warm start)
                           │   pasada 3 (balance de peso; vecindarios)
                           ▼
                   ResultadoCorrida ─► Resultados (web): KPIs, vista del buque,
                                       planimetría (layout_capa), izadas
                                       (secuencia_izadas), balance (balance_peso),
                                       comparación con referencia, Excel
```

Diagrama conceptual del **método** (distinto del de módulos, para el Informe Técnico, subtarea 9): entrada → packer (capacidad por geometría) → asignador MILP (bodega y plan, tres pasadas) → verificación (no-overstowage, cobertura, contigüidad, capacidad) → makespan y KPIs → plan final.

### Tecnologías y versiones (las del entorno verificado)

Python 3.14 (el proyecto exige ≥ 3.11) · PuLP 3.3.2 (acotado a < 4, porque PuLP 4.0 cambia `prob.constraints`) · highspy 1.15.1 · Streamlit 1.62.0 · pandas 3.0.5 · numpy 2.5.2 · openpyxl 3.1.5 · xlrd 2.0.2 · Plotly 6.9.0 · matplotlib 3.11.1. Dependencias de ejecución en `requirements.txt`; las de desarrollo (pytest, black, ruff, mypy) en `requirements-dev.txt`.

### Despliegue

Streamlit Community Cloud, gratuito, desde la rama `master`: **https://prestow.streamlit.app**. Cada push redespliega. La app se duerme tras 12 h sin uso. Cada sesión guarda sus datos editados en un directorio temporal propio, y las corridas del solver se encolan (una a la vez por proceso). Detalle técnico: Cloud no recarga `src/` tras un push, así que cada página verifica si el núcleo cambió y lo recarga (`nucleo.py`).

### Cómo se corre sin la web (CLI)

```bash
python src/packer_2d.py --datos data/datos_entrada_kiwi_arrow.xlsx      # una vez
python src/modelo_prestow.py --datos data/datos_entrada_kiwi_arrow.xlsx --limite 180
streamlit run app/app.py                                                  # la web, local
python -m pytest                                                          # 47 tests
```

El CLI y la web dan exactamente los mismos resultados (verificado el 24 y 25 de septiembre).

---

## 8. La aplicación web

### Páginas y flujo del usuario

| Página | Qué hace el usuario | Qué ve |
|---|---|---|
| **Inicio** | Lee cómo funciona; carga el caso demo o va a configurar | Explicación en 4 pasos, botón "correr caso demo" |
| **Configuración** | Escribe el **nombre del buque** y los **KPIs del plan de referencia** (makespan, desbalance, fragmentación, izadas; opcionales). Edita en tablas: Buque (bodegas, medidas, cuadrillas), Productos (huella, peso; agregar un producto recalcula el packer automáticamente), Viaje (unidades por producto y destino), Rotación (orden de descarga) | Validación de coherencia al guardar |
| **Ejecutar** | Elige el solver (HiGHS recomendado) y el límite por pasada (30-360 s; viene en 180; 180 s para el caso demo (Kiwi Arrow); **menos de 180 s, por ejemplo 170 s, para cualquier otro caso** (sección 18.1)); presiona "Calcular" | Resumen del caso y de la referencia; avance en vivo (pasada actual, tiempo, desbalance de peso bajando) |
| **Resultados** | Revisa y descarga | Indicadores clave con comparación contra la referencia; tabla de comparación KPI por KPI; vista lateral del buque, capas por bodega, mapa destino × bodega, horas por cuadrilla; planimetría de cualquier capa con sus izadas numeradas y la secuencia de carga; balance de peso y densidad por bodega; plan completo; detalles técnicos (estado, gap por pasada, verificaciones) |

### Salida descargable

**Un solo Excel** (`prestow_reporte_completo.xlsx`) con 8 hojas:

| Hoja | Qué permite decidir |
|---|---|
| Plan de estiba | La asignación visual tipo prestow, para comunicarla a las cuadrillas |
| Detalle | Fila por fila (bodega, plan, producto, destino, unidades), para revisar o importar |
| Indicadores | Los KPIs de la corrida |
| Izadas y secuencia | Cuántas izadas y en qué orden, capa por capa |
| Planimetría | Posición de las unidades por capa |
| Balance de peso | Toneladas y densidad por bodega |
| Parámetros de la corrida | Solver, límite, fecha, buque, estado, gap por pasada: para reproducir el resultado |
| Comparación con referencia | Modelo contra plan de referencia, KPI por KPI (si se ingresó referencia) |

### Datos de entrada (para el manual: tabla de campos)

Los datos se ingresan **editando tablas en la página Configuración**, partiendo del caso demo. La web no tiene carga de archivos: el Excel `datos_entrada_kiwi_arrow.xlsx` (hojas Instrucciones, Viaje, Rotación, Buque, Productos) es el formato de la línea de comandos y el que se adjunta como archivo de muestra. Hay dos naturalezas de datos: **configuración del buque** (Buque, Productos; cambia solo si cambia el buque) y **datos del viaje** (Viaje, Rotación; cambian en cada corrida).

| Tabla | Campo | Tipo / unidad | Regla que valida la web al guardar |
|---|---|---|---|
| Buque | bodega | entero | Obligatorio, sin repetidos |
| Buque | largo_m, ancho_m | decimal, m | Mayor que 0 |
| Buque | planes | entero | Mayor que 0 (todas las bodegas usan el mayor) |
| Buque | cuadrilla | entero | Qué cuadrilla atiende la bodega |
| Productos | producto | texto | Obligatorio, sin repetidos |
| Productos | huella_largo_m, huella_ancho_m | decimal, m | Mayor que 0 (cambiarlas recalcula la capacidad automáticamente) |
| Productos | peso_t | decimal, t | Peso por unidad |
| Viaje | producto, destino | texto | Deben existir en Productos y Rotación (se eligen de una lista) |
| Viaje | unidades | entero | No negativo |
| Rotación | destino | texto | Sin repetidos |
| Rotación | orden_descarga | entero | 1 = se descarga primero; sin repetidos |

Además, antes de resolver, el modelo rechaza con un mensaje claro una carga que no cabe en el buque (ver la instancia P7 de la sección 18). Parámetros de ejecución: solver (HiGHS recomendado; CBC de respaldo) y límite de tiempo por pasada (30-360 s; viene en 180 s; 180 s para el caso demo (Kiwi Arrow); **menos de 180 s, por ejemplo 170 s, para cualquier otro caso** (sección 18.1)). Con límites bajos el plan es válido, pero la fragmentación empeora mucho (sección 10).

**Cómo declararlo en los informes** (la app se da por terminada):

- Entrada: "los datos se editan en pantalla a partir del caso demo". La carga de un archivo propio queda como trabajo futuro.
- Salida: un único Excel con 8 hojas (no hay descargas separadas en CSV).
- Uso: 180 s por pasada para el caso demo; menos de 180 s (por ejemplo 170 s) para cualquier otro caso, porque desde 180 s el sistema puede terminar sin solución (sección 18.1). Con límites muy bajos (30 s) el plan es válido pero la fragmentación empeora mucho (sección 10). La web no advierte ninguna de las dos cosas: decirlo en el manual.

---

## 9. Validación

| Prueba | Qué comprueba | Resultado |
|---|---|---|
| **Plan real del puerto contra el modelo** | Que el modelo represente la operación real | El plan manual satisface las 4 verificaciones del modelo |
| **Horas por cuadrilla** | Que el cálculo de tiempos reproduzca la realidad | Con el tiempo de ciclo por bodega se reproducen las horas del archivo del puerto con **error máximo de 0,023 h** (re-verificado el 22-sep). No depende del optimizador: compara datos fijos del plan manual |
| **4 verificaciones automáticas** sobre cada plan generado | No-overstowage, cobertura exacta, contigüidad, capacidad | Todas OK en el caso base (180 s y 30 s) |
| **Verificación contra todas las restricciones** | Que los puntos de partida y las soluciones de la búsqueda por vecindarios sean factibles | 0 violaciones |
| **Estabilidad (5 semillas, 180 s)** | Que el resultado no sea ruido | Makespan y unidades por bodega idénticos en las 5 (medido el 22-sep, antes de la búsqueda por vecindarios; dos corridas posteriores de 180 s dieron también resultados idénticos) |
| **52 tests automáticos** (`pytest`, ~2 s) | Packer, capacidad por plan, solución inicial, layout, secuencia de izadas, balance de peso, lectura del gap, comparación con referencia, recarga del núcleo, generador de instancias | 52/52 |
| **QA de la web** (Streamlit AppTest) | Configuración → Ejecutar → Resultados → Excel, sin excepciones | Sin excepciones; 32 combinaciones de selectores probadas |
| **Prueba en la nube** | Que la app desplegada reproduzca el caso base | El dueño del proyecto obtuvo 59 h 40 min (= 59,67 h), 1844 izadas y 9,4% de desbalance antes de la búsqueda por vecindarios. **Falta repetirla con la versión actual a 180 s** (esperado: 59,67 h, 5,8%, fragmentación 11) |

**Instancias de prueba, sensibilidad a rendimientos y a tamaño:** ver la sección 18 (generadas con `src/generador_instancias.py`, corridas con `src/analisis_informes.py`).

---

## 10. Resultados vigentes

Caso base Kiwi Arrow, HiGHS, 180 s por pasada, capacidad real por plan, pasada 3 por vecindarios. Dos corridas idénticas (25-sep-2026).

### Comparación con el plan manual

| Indicador | Plan manual | Modelo |
|---|---|---|
| Makespan | 60,61 h | **59,67 h** (−0,94 h, −1,6%) |
| Horas por cuadrilla (1 / 2 / 3 / 4) | 56,62 / 58,49 / 57,26 / 60,61 | 56,24 / 59,34 / 59,62 / 59,66 |
| Desbalance entre cuadrillas | 6,9% | **5,8%** |
| Fragmentación | 14 | **11** (Taichung 2, Qingdao 6, Kunsan 2, Ulsan 1) |
| Izadas totales | sin dato documentado | 1.836 |
| Overstowage | 0 | 0 |
| Desbalance de peso al zarpar (máx − mín) | no medido | 3.604 t |

Nota de precisión: el makespan informado (59,67 h) es la cota que viene de la pasada 2 (59,6702 h). Tras la pasada 3, la cuadrilla más cargada queda en 59,66 h.

**Unidades por bodega (modelo):** 1→2.256, 2→3.616, 3→3.952, 4→4.040, 5→3.905, 6→4.040, 7→3.759, 8→3.764. **De dónde sale la mejora:** el modelo carga la bodega 1 (grúa lenta) sin pasarse en la cuadrilla 4 y reparte el resto de modo que ninguna cuadrilla supere 59,67 h. El plan manual tenía la cuadrilla 4 en 60,61 h.

### Calidad de la solución por pasada

| Pasada | Objetivo | Gap al terminar |
|---|---|---|
| 1 · Makespan | 59,43 h (cota inferior 57,48 h) | 3,29% |
| 2 · Izadas + fragmentación | 1944 → 1946 en la pasada 3 (dentro del margen de +2) | 3,24% |
| 3 · Balance de peso | 6.294 → 3.604 t (cota 3.272 t) | 9,19% |

**Ninguna pasada prueba optimalidad.** Frase para el informe: "la solución reportada es la mejor encontrada en 180 s por pasada; en makespan está a lo más a 3,29% del óptimo". Con las instancias de la sección 18 se acota mejor: el óptimo del caso base está entre 57,49 y 58,24 h.

### Por qué el makespan cambió entre versiones (para el Informe Académico)

57,59 h (rotación con Kunsan y Ulsan empatados) → 58,19 h (Ulsan confirmado como último) → **59,67 h** (capacidad real por plan: en las bodegas 4, 5, 7 y 8 los planes altos tienen menos capacidad de la que suponía la geometría). **No son retrocesos**: cada cambio hace el modelo más fiel a la operación real. Las cifras anteriores eran optimistas.

### Sensibilidad al límite de tiempo (una corrida por valor)

| Límite por pasada | Makespan | Fragmentación | Desbalance cuadrillas | Desbalance de peso |
|---|---|---|---|---|
| 30 s | 59,97 h | 31 | 1,4% | 3.519 t |
| 180 s | 59,67 h | 11 | 5,8% | 3.604 t |

Con poco tiempo, la pasada 2 (gap 14% a 30 s) no alcanza a agrupar la carga por destino. A 170 s (con punto de partida) el caso base da 60,18 h, fragmentación 11 y desbalance 6,6%. **Para el caso base, 180 s; para instancias nuevas, menos de 180 s (por ejemplo 170 s)**, porque a 180 s o más el sistema puede no encontrar solución (sección 18.1).

### Análisis de sensibilidad Kunsan/Ulsan (histórico)

Se midió cuando el orden estaba en duda: empatados 57,59 h, Kunsan antes 57,86 h, Ulsan antes 58,82 h. El peor caso costaba 1,23 h (2,1%). **Se hizo con la configuración anterior del modelo y el orden ya está confirmado.** Sirve para el Informe Académico como ejemplo de cómo se trató un supuesto (medirlo en vez de dejarlo como incertidumbre), no como resultado vigente.

---

## 11. Limitaciones

1. **Sin optimalidad probada** en ninguna pasada (gaps de 3,29%, 3,24% y 9,19%). El óptimo del caso base está entre 57,49 y 58,24 h (sección 18.5).
   - **A 180 s o más por pasada el sistema puede terminar sin solución** en instancias distintas del caso base (3 de 8, sección 18.1), y el mensaje de error recomienda subir el límite cuando lo que sirve es bajarlo de 180 s.
2. **Dependencia del límite de tiempo:** el límite es de reloj, así que en una máquina más lenta el resultado puede diferir mientras el gap no sea cero. Con límites bajos la fragmentación empeora mucho.
3. **Supuestos 1-3 sin confirmar** con el puerto (tonelaje por bodega, rendimientos, pares de cuadrillas). El de rendimientos es el que más pesa: ±10% de rendimiento mueve el makespan ∓10% (sección 18.3).
4. **Capas mixtas aproximadas:** la capacidad de una capa con varios productos se aproxima por suma de fracciones (5 de 85 capas en el caso base), y la planimetría de esas capas es una aproximación visual.
5. **Capacidad por altura parcial:** solo 72 combinaciones con dato real; el resto usa la geometría uniforme.
6. **El balance de peso es solo al zarpar**, no puerto a puerto. Se descartó con la pasada 3 antigua; con la búsqueda por vecindarios podría funcionar, pero no se ha probado.
7. **Fuera de alcance declarado:** no decide la rotación (la recibe); no considera estabilidad transversal, trim ni esfuerzos del casco (verificar con el loading computer); no planifica varios buques a la vez; no tiene control de acceso de usuarios.
8. **La web no permite subir un archivo de datos**: se edita en pantalla a partir del caso demo.
9. **Instancias sintéticas, no reales:** fuera del Kiwi Arrow, el sistema se probó con variantes generadas por perturbación del caso base (sección 18). Sin contacto con la contraparte no hay otros prestows reales con los que compararse.

---

## 12. Cronología del trabajo

| Fecha | Hito |
|---|---|
| Antes del 25-ago | Análisis del archivo del puerto, formulación, packer, modelo MILP, validación contra el plan real (fuera del historial de git; documentado en `Resumen_Trabajo_Realizado.md`) |
| 25-ago | Fase 0: modelo validado + `api.py` para la web |
| 25-26 ago | Fase 1.5: interfaz Streamlit con vista del buque |
| 21-sep | Fase 2: formularios editables, planimetría, izadas, balance de peso (pasada 3, reabierta a pedido del dueño del proyecto) |
| 22-sep | Correcciones de UX; capacidad real por plan (makespan 58,19 → 59,67 h); reconciliación de las 275 unidades; warm start de la pasada 1; QA de la web; estabilidad re-verificada; validación de horas re-verificada |
| 24-sep | Gap real de HiGHS (antes nunca se leía); CLI alineado con la web; A/B de la pasada 2; tests; despliegue en Streamlit Cloud; plan de referencia ingresado por el usuario; arreglo de la recarga en Cloud |
| 25-sep | Pendiente #7: la pasada 3 no optimizaba; búsqueda por vecindarios (desbalance de peso −43%, desbalance entre cuadrillas 9,4% → 5,8%) |

Detalle diario en `docs/reportes_sesion/` y técnico en `docs/05_Estado_app_web.md` (secciones 1-20).

---

## 13. Guía para el Informe Técnico (sección por sección)

**Lector:** el planificador portuario y quien mantenga el sistema. Modelo formal en anexo, prosa en el cuerpo. El manual pesa 20/100; modelo y método, 35/100.

| Sección (subtareas) | Material de este documento | Estado |
|---|---|---|
| 1 · Resumen ejecutivo (1) | Sección 1: problema, tipo de solución, beneficios, resultado 59,67 contra 60,61 h, propuesta de valor | **Se puede escribir.** La cifra debe coincidir con la subtarea 22 y con la captura del manual |
| 2 · Problema y alcance (2-5) | Secciones 2, 4 y 11 (qué NO hace). Stakeholders: planificador (velocidad), armador (horas de buque), puerto (gana si llena el sitio liberado), cuadrillas (redistribución), puertos de destino (fragmentación) | **Se puede escribir** |
| 4 · Modelo y método (6-10) | Sección 5 (prosa, tabla de restricciones), sección 6 (método), diagrama del método en la sección 7. Pseudocódigo: pasadas, warm start y búsqueda por vecindarios | **Se puede escribir, salvo la 8** (citas APA verificadas) |
| 5 · Arquitectura (11) | Sección 7: módulos, flujo, versiones, despliegue | **Se puede escribir** |
| 6 · Datos de entrada (12-14) | Sección 3 (fuentes) y tabla de campos de la sección 8. Archivo de muestra: `datos_entrada_kiwi_arrow.xlsx` | **Se puede escribir.** El flujo real es editar en pantalla (sección 8) |
| 7 · Manual de usuario (15-20) | Sección 8. **15 (acceso) y 17 (ejemplo paso a paso) ya no están bloqueadas**: la app está desplegada, hay que tomar las capturas. 16: parámetros (solver; límite 30-360 s: 180 s para el caso demo, 170 s para otros casos) con las tablas de sensibilidad de las secciones 10 y 18. 19: limitaciones y tamaño máximo recomendado (sección 18). 18: las 8 hojas del Excel. 20: uso interno, sin autenticación, no cargar datos sensibles | **Casi todo se puede escribir**; faltan las capturas |
| 8 · Validación y testeo (21-23) | 21: tabla de instancias de la sección 18 (ID, pregunta, tamaño, resultado, no-overstowage). 22: sección 10. 23: sección 9 | **Se puede escribir** |
| 9 · Anexos (24-26) | Código comentado; glosario (sección 17); modelo formal (PDF + sección 5); 26: instancias de `data/instancias/` con sus resultados (sección 18) | **Se puede escribir** |
| 10 · Cierre (27-28) | Límites de extensión por sección; revisión cruzada | Al final |

Frases que sí se sostienen:

- «El sistema reproduce la calidad del plan manual —cero overstowage, balance equivalente o mejor— en minutos en lugar de días.»
- «En el caso base, el sistema encontró un plan con makespan de 59,67 h, frente a 60,61 h del plan manual, con menor desbalance entre cuadrillas (5,8% frente a 6,9%) y menor fragmentación (11 frente a 14).»

---

## 14. Guía para el Informe Académico (sección por sección)

**Lector:** el profesor evaluando el proceso. Reflexión sobre decisiones, alternativas, errores y aprendizajes. Método de solución pesa 30; resultados, 20.

| Sección (subtareas) | Material |
|---|---|
| 1 · Introducción (1-2) | Problema (archivo que crece por acumulación, hojas del Misago Arrow); particularidad del grupo (packer 2D propio, capacidad real por plan); objetivo; propuesta de valor |
| 2 · Proceso de desarrollo (3-4) | Cronología (sección 12), bitácora (`planificacion/Bitacora_Semanal_Prestow_Lirquen.xlsx`), carta Gantt. Decisiones con su porqué (tabla de abajo) |
| 3 · Contexto y planteamiento (5-7) | Sección 2; KPIs con fórmula; los 9 supuestos en tres partes (sección 4) |
| 4 · Tratamiento de datos (8-12) | Sección 3 completa: hallazgos y cómo se resolvió cada uno. 11: diseño de las instancias (sección 18: método de perturbación, una pregunta por instancia). 12: anexar `src/generador_instancias.py` (y los prompts de IA, ver abajo) |
| 5 · Modelamiento (13-16) | Sección 5. Reflexión sobre lo omitido: estabilidad transversal, reagrupación de cuadrillas, separadores y maniobra, bloqueo dentro de capas mixtas |
| 6 · Método de solución (17-22) | Sección 6 y las tablas de decisiones y errores de abajo. Es la sección de mayor peso: aquí va la historia del warm start, la pasada 2 y la pasada 3 |
| 7 · Validación (23-24) | Sección 9. Validación más fuerte: reproducción de las horas del puerto (0,023 h) |
| 8 · Resultados (25-26) | Sección 10 (incluida la evolución 57,59 → 58,19 → 59,67 h) y sección 18: sensibilidad a rendimientos t/h (el análisis que la guía llama obligatorio) y al tamaño |
| 9 · Limitaciones (27) | Sección 11 |
| 10 · Conclusiones (28) | Individuales; usar la propuesta de valor como vara común |
| 11 · Cierre (29) | APA 7 verificadas; revisión cruzada |

### Decisiones clave y su porqué

| Decisión | Alternativas | Por qué se eligió |
|---|---|---|
| MILP exacto con límite de tiempo | Metaheurística, híbrido | Mejor resultado medido, más simple de mantener; la opinión inicial a favor del híbrido se evaluó y se descartó |
| HiGHS | CBC, CPLEX, Gurobi | Libre y desplegable; más rápido que CBC en este modelo |
| Lexicográfico en pasadas | Suma ponderada | Con pesos, el tercer término se volvía indistinguible |
| Tolerancia absoluta (en izadas) | Relativa | La relativa dejaba menos margen justo cuando la pasada 1 era mejor |
| Packer separado y precalculado | Capacidad tabulada fija | La geometría no cambia entre viajes; da una palanca real (los patrones de 4 bloques) |
| Capacidad real por plan donde hay dato | Solo geometría | Las plantillas mostraron caídas reales de 3-13%; sin inventar donde el dato es dudoso |
| Balance de peso como pasada 3 (reabierto) | No restringir peso | Pedido del dueño del proyecto: la web genera planes para quien no tiene referencia |
| Warm start solo < 180 s | Siempre, nunca | Medido en el caso base: por debajo evita "sin solución"; por encima ancla la búsqueda y empeora. Las instancias de prueba mostraron después que, sin él, 3 de 8 casos no encuentran solución a 180 s (ver errores) |
| Pasada 3 por vecindarios | HiGHS sobre el problema completo | El problema completo nunca mejoraba el punto de partida; los vecindarios bajan el desbalance de peso 43% |
| Streamlit + Streamlit Cloud | Otras interfaces | Gratuito, Python puro, despliegue desde GitHub |

### Errores encontrados y lo que enseñaron

| Error | Cómo se detectó | Corrección | Aprendizaje |
|---|---|---|---|
| Leer solo la hoja LH-1 (dos veces) | Capas del plan real que no cabían; luego datos "faltantes" que sí existían | Revisar las 8 hojas | Verificar la fuente completa antes de declarar que falta un dato |
| Trabajar en hojas ocultas de otro buque | Inconsistencias con el caso | Identificar el buque de cada hoja | Los archivos operativos acumulan casos viejos |
| Contigüidad escrita sobre *y* | Carga flotando en la solución | Variable *w* con implicación en ambos sentidos | Una restricción puede cumplirse formalmente y violarse en la realidad |
| Tiempo de ciclo constante | Subestimaba la bodega crítica | Tiempo por bodega | El parámetro "promedio" escondía justo lo que define el makespan |
| Pesos en vez de lexicográfico | La fragmentación empeoraba al agregarla | Pasadas | — |
| Restricción mal formulada (880 restricciones) | Modelo irresoluble | Reformulada sobre *v* (8 restricciones) | — |
| Confiar en el estado de PuLP | "Optimal" con valores distintos según el tiempo | Leer el gap | — |
| **El gap de HiGHS nunca se leía** | El gap salía siempre vacío; la UI decía "limitación conocida" | Leer estado y gap del objeto del solver, no del log (HiGHS escribe desde C) | Una "limitación conocida" puede ser un bug no investigado |
| Cambiar configuración sin regenerar artefactos | Análisis sobre un Excel viejo, con conclusiones invertidas | Regenerar siempre | — |
| Warm start que ancla | A 180 s daba 60,18 contra 59,67 h | Solo por debajo de 180 s | Una "mejora" hay que medirla también donde ya funcionaba |
| **La regla de 180 s se validó solo con el caso base** | Las instancias de prueba: P3, P6 y R_b1_180 terminaron sin solución a 180 s; a 170 s resolvieron todas | Se recomienda 170 s para casos nuevos y se declara como limitación (la app se dio por terminada) | Un umbral ajustado sobre un solo caso puede no generalizar; las instancias de prueba sirvieron justamente para detectarlo |
| **El CLI y la web daban resultados distintos** | El CLI no cargaba la capacidad real por plan (ruta relativa) ni usaba warm start | Ruta de respaldo a `data/` y la misma lógica en ambos | Dos puntos de entrada divergen si no comparten el código |
| **La pasada 3 no optimizaba nada** | El resultado era idéntico al punto de partida; `peso_min = 0`; se había atribuido a una "relajación débil" | Punto de partida ajustado + búsqueda por vecindarios | Antes de culpar a la formulación, verificar si el solver se movió del punto de partida |
| La referencia del Kiwi Arrow estaba fija en la UI | Revisión del pedido de comparar contra el plan real de cada buque | Referencia ingresada por el usuario | — |
| Cloud no recargaba `src/` tras un push | Error en producción tras un despliegue | Recarga automática del núcleo | Probar el despliegue, no solo el código |

### Uso de IA generativa (declararlo)

El enunciado permite usar IA para estudiar alternativas, no para decidir. En las sesiones documentadas en `docs/reportes_sesion/` se usó un asistente de código (Claude Code) para implementar, depurar y medir. Las decisiones de alcance las tomó el dueño del proyecto: están marcadas como "a pedido explícito" en CLAUDE.md (reabrir el balance de peso, la capacidad real por plan, el plan de referencia, la búsqueda por vecindarios tras ver la investigación). El generador de instancias (`src/generador_instancias.py`) también se escribió con ese asistente, a pedido del dueño del proyecto, el 25-sep-2026. El enunciado exige anexar el código del generador y los prompts usados: el pedido fue preparar las instancias de prueba y los análisis de sensibilidad que exigen los informes, sin modificar la app. El código lleva comentado el método (perturbación del caso base, una variable por instancia).

---

## 15. Registro de cifras obsoletas

| Cifra obsoleta | Dónde aparece | Cifra vigente | Por qué cambió |
|---|---|---|---|
| Makespan 57,59 h | `01_Contexto…`, `Resumen_Trabajo_Realizado.md` | **59,67 h** | Rotación empatada (ya no vigente) |
| Makespan 58,19 h (−4,0%) | `00_LEEME…`, `04_Prompt…` | **59,67 h (−1,6%)** | Capacidad real por plan |
| Mejora "3 horas (5%)" | `00_LEEME…`, `Resumen…` | **0,94 h (1,6%)** | Ídem |
| Desbalance 0,1% / 0,2% | Varios | **5,8%** | Configuración y pasadas actuales |
| Desbalance 9,36% | CLAUDE.md antes del 25-sep | **5,8%** | Pasada 3 por vecindarios |
| Fragmentación 21 / 22 ("peor") | Varios | **11 (mejor que 14)** | La pasada 2 ahora sí resuelve |
| "275 unidades sin reconciliar" | `00_LEEME…`, `01_…`, `Resumen…` | **Resuelto: PROGRAMA LQN** | Sección 3 |
| "Gap 0,195%" | Varios | **3,29% / 3,24% / 9,19%** | El gap se lee bien desde el 24-sep |
| "La pasada 2 no resuelve" | Varios | **Resuelve** (gap 3,24%) | Warm start; verificado con A/B |
| Pasada 3 con gap ~64% | CLAUDE.md antes del 25-sep | **9,19%** | Búsqueda por vecindarios |
| "Acortamiento descartado, era del Eagle Arrow" | `00_LEEME…`, `Resumen…` | **Parcialmente confirmado** en las bodegas 4, 5, 7 y 8 | Revisión de las 8 hojas |
| 2 pasadas | Varios | **3 pasadas** | Balance de peso |
| "Página no desplegada" | `04_Prompt…` | **Desplegada** | 24-sep |
| "El usuario sube el Excel" | `04_Prompt…` | **Se edita en pantalla** | Diseño real de la web |
| Validación de horas "error 0,01 h" | Varios | **Máximo 0,023 h** (0,01-0,02 en la práctica) | Re-verificada con código el 22-sep |
| CBC 57,12 / HiGHS 56,88 h | `01_…`, `00_LEEME…` | Medición histórica de otra versión del modelo | Citar como tal o repetirla |

---

## 16. Tareas del equipo (lo que falta y solo el equipo puede hacer)

**Ya resuelto para los informes:** todo el contenido técnico (secciones 1-15) y los análisis que exigen los informes (sección 18: instancias de prueba, sensibilidad a rendimientos t/h y a tamaño).

**Tareas pendientes.** Ningún asistente puede hacerlas: requieren acceso a fuentes, a la app o a las personas del equipo. El asistente que redacte deja el marcador `[PENDIENTE EQUIPO: T#]` donde falte cada una.

| # | Tarea | Para qué sección | Cómo hacerla | Terminada cuando |
|---|---|---|---|---|
| **T1** | **Verificar las referencias APA 7 en la fuente original** | Técnico, subtarea 8 (métodos con citas; parte de los 35 puntos de Modelo y método). Cierre de ambos informes (referencias) | Por cada referencia, abrir el paper o libro original y confirmar autor, año, título, revista, páginas y que diga lo que se le atribuye. Si no se encontró literatura del caso exacto (celulosa unitizada en open hatch), documentar la búsqueda hecha (bases, términos, fechas): un vacío se demuestra con el rastreo, no se afirma | Cada cita del texto tiene su entrada APA 7 verificada contra la fuente, y hay un párrafo con el rastreo de literatura |
| **T2** | **Tomar las capturas de la app desplegada** | Técnico, manual de usuario: subtareas 15 (acceso) y 17 (ejemplo paso a paso) | En https://prestow.streamlit.app: Inicio → cargar caso demo → Configuración (nombre del buque y plan de referencia) → Ejecutar a **180 s** → Resultados (indicadores y comparación, vista del buque, planimetría con izadas, balance de peso, detalles técnicos) → Excel descargado. Una captura por paso | Hay una captura por paso y la del resultado muestra **59 h 40 min (59,67 h)**, la misma cifra del resumen ejecutivo y de la comparación con el plan manual |
| **T3** | **Llenar o reconstruir la bitácora semanal** (`planificacion/Bitacora_Semanal_Prestow_Lirquen.xlsx`) | Académico, sección 2 "Proceso de desarrollo" (subtareas 3-4): es su única fuente | Completar semana por semana qué se hizo, qué se decidió y qué problemas hubo. Apoyo para reconstruir: la cronología de la sección 12, el historial de git (`git log`) y los reportes de `docs/reportes_sesion/`. Lo que no se pueda reconstruir con evidencia se declara como no registrado, en vez de rellenarlo de memoria | Cada semana del proyecto tiene su entrada, respaldada por alguna evidencia |
| **T4** | **Escribir las autoevaluaciones individuales** | Académico, sección 10 "Conclusiones" (subtarea 28) | Cada integrante escribe la suya. Vara común para que las cinco midan lo mismo: la propuesta de valor de la sección 1 ("reproducir la calidad del plan manual en minutos en lugar de días") | Están las 5 autoevaluaciones, escritas por cada integrante |
| **T5** | **Conseguir el enunciado oficial del curso y adjuntarlo** | Ambos informes: rúbrica y puntajes definitivos, requisitos literales (por ejemplo, anexar prompts de IA) | Descargarlo de la plataforma del curso y adjuntarlo al chat que redacte, junto con este documento y las guías en PDF. Si difiere de las guías (`Guia_Informe_Tecnico…`, `Guia_de_tareas…`), manda el enunciado | El asistente tiene el enunciado adjunto y las secciones se revisaron contra su rúbrica |

**Nota sobre la tarea T5 y el uso de IA:** si el enunciado exige anexar los prompts usados para generar código con IA (la guía de tareas lo dice para el generador de instancias, subtarea 12 del Académico), el equipo decide cómo documentarlo. El generador se construyó con un asistente de código a pedido del dueño del proyecto; ver la sección 14, "Uso de IA generativa".

**Se declaran tal cual en los informes** (no son tareas):

- La entrada se edita en pantalla; la carga de un archivo propio es trabajo futuro.
- El KPI de aprovechamiento de superficie (96,3% en el plan manual) no se calcula para el plan del modelo: no incluirlo en la tabla comparativa, o declararlo.
- Las izadas del plan manual no están documentadas: en la comparación, "sin dato".
- La comparación CBC contra HiGHS (57,12 contra 56,88 h) es de una versión anterior del modelo: citarla como medición histórica.
- Desde 180 s por pasada el sistema puede terminar sin solución en casos distintos del demo; la recomendación es 170 s (sección 18.1).

---

## 17. Glosario

| Término | Definición |
|---|---|
| Prestow | Plan de estiba previo a la carga: qué va en cada bodega y capa |
| Bodega (hold, LH) | Compartimento de carga del buque; el Kiwi Arrow tiene 8 |
| Plan | Capa horizontal de carga dentro de una bodega (1 = fondo, hasta 11) |
| Open hatch | Buque con escotillas del ancho de la bodega, sin cubiertas intermedias |
| Cuadrilla | Equipo de estiba; cada una trabaja un par fijo de bodegas |
| Izada | Un ciclo de grúa; hasta 16 unidades |
| Unidad | Fardo de celulosa unitizada (2,02 t en el caso base) |
| Huella | Largo × ancho de una unidad sobre el piso |
| Planimetría | Dibujo de cómo se acomodan las unidades en el piso de una capa |
| Rotación | Orden de los puertos de descarga |
| Overstowage | Carga de un puerto posterior encima de carga de uno anterior |
| Rehandle (shift) | Sacar y volver a cargar unidades por overstowage |
| Makespan | Horas de la cuadrilla más cargada; define cuándo zarpa el buque |
| Desbalance entre cuadrillas | (máx − mín) / promedio de horas por cuadrilla |
| Fragmentación | Suma, por destino, de cuántas bodegas llevan carga de ese destino |
| Balance de peso | Diferencia en toneladas entre la bodega más y la menos cargada al zarpar |
| Stowage factor | Volumen que ocupa una tonelada de carga |
| Crane split | Reparto del trabajo de grúa entre bodegas o cuadrillas |
| MILP | Programación lineal entera mixta |
| Variable de decisión | Lo que el modelo decide (p. ej. unidades por bodega y plan). Distinto de las decisiones del usuario |
| Restricción dura | Condición que toda solución debe cumplir |
| Función objetivo | Lo que se minimiza |
| Lexicográfico | Optimizar objetivos en orden de prioridad, fijando cada uno antes del siguiente |
| Min-max | Minimizar el máximo (aquí, la cuadrilla más cargada) |
| Gap | Distancia máxima posible entre la solución encontrada y el óptimo, según la cota probada |
| Cota dual | Valor que ninguna solución puede mejorar, según lo que el solver probó |
| Factibilidad | Cumplir todas las restricciones |
| Warm start | Entregarle al solver una solución inicial factible |
| Búsqueda por vecindarios | Mejorar una solución resolviendo subproblemas chicos (aquí, dos bodegas a la vez) |
| Heurística / metaheurística | Método que busca buenas soluciones sin garantía de optimalidad |
| NP-difícil | Clase de problemas sin algoritmo eficiente conocido para el óptimo garantizado |
| Packer 2D | Módulo que calcula cuántas unidades caben en el piso de una capa |

---

## 18. Análisis para los informes: instancias de prueba, rendimientos y tamaño

Hechos el 25-sep-2026 con el modelo vigente, sin modificar la app. Las instancias se generan con `src/generador_instancias.py` (perturbación del caso base: cada instancia cambia **una** cosa y responde **una** pregunta) y se corren con `src/analisis_informes.py`, que llama a la misma función que la web. Los datos de cada instancia están en `data/instancias/<id>/` (CSV + `instancia.json` con su pregunta) y todos los resultados en `data/resultados_analisis/resultados.csv`. Una corrida por instancia; HiGHS; las 4 verificaciones automáticas (no-overstowage, cobertura, contigüidad, capacidad) se aplicaron a cada plan obtenido.

### 18.1 Hallazgo de método: el límite de 180 s puede dejar sin solución

A **180 s o más** por pasada, la pasada 1 arranca sin punto de partida (la regla de la sección 6). En el caso base HiGHS encuentra su primera solución cerca del segundo 134, con poco margen: **en 3 de las 8 instancias que debían resolverse a 180 s (P3, P6 y R_b1_180) no encontró ninguna solución**. A **170 s** (punto de partida activo) **las 12 instancias corridas resolvieron**, todas con las 4 verificaciones OK. Costo: en el caso base, 170 s da 60,18 h en vez de 59,67 h.

**Cómo usarlo en los informes:** el resultado principal del caso base sigue siendo 59,67 h (180 s). La recomendación de uso para instancias nuevas es un límite **menor a 180 s (por ejemplo 170 s)**, que siempre entregó un plan válido; a 180 s o más, el sistema puede terminar sin solución. Además, el mensaje de error de la app en ese caso dice "sube el límite", cuando lo que resuelve es bajarlo por debajo de 180 s: declararlo como limitación conocida (la app se da por terminada).

### 18.2 Instancias de prueba (Técnico, subtarea 21; Académico, subtarea 11)

| ID | Pregunta | Tamaño (bodegas / destinos / productos / unidades) | Límite | Resultado | Makespan | Gap makespan | ¿No-overstowage? | Línea base |
|---|---|---|---|---|---|---|---|---|
| P0 | ¿Reproduce el plan real y cómo se compara? | 8 / 4 / 5 / 29.332 | 180 s | Resuelta | 59,67 h | 3,29% | Sí | Plan manual 60,61 h |
| P1 | ¿Qué pasa con un solo destino (sin riesgo de overstowage)? | 8 / 1 / 5 / 29.332 | 180 s | Resuelta | 57,52 h | 0,05% | Sí | — |
| P2 | ¿Qué pasa con un solo producto, el de mayor huella (buque casi lleno)? | 8 / 4 / 1 / 29.332 | 180 s | Resuelta | 58,17 h | 0,10% | Sí | — |
| P3 | ¿Funciona con bodegas vacías (3 y 6), como en viajes reales parciales? | 6 / 4 / 5 / 21.999 | 180 s | **Sin solución** en 180 s | — | — | — | — |
| P3 | ídem | ídem | 170 s | Resuelta | 61,02 h | 14,36% | Sí | — |
| P4 | ¿Cómo reparte con el buque a media carga? | 8 / 4 / 5 / 14.667 | 180 s | Resuelta | 27,65 h | 0,48% | Sí | — |
| P5 | ¿Qué pasa si el 70% de la carga es del último destino? | 8 / 4 / 5 / 29.331 | 180 s | Resuelta | 58,47 h | 1,29% | Sí | — |
| P6 | ¿Qué pasa con seis destinos? | 8 / 6 / 5 / 29.332 | 180 s | **Sin solución** en 180 s | — | — | — | — |
| P6 | ídem | ídem | 170 s | Resuelta | 58,24 h | 0,90% | Sí | — |
| P7 | ¿Rechaza con un mensaje claro una carga que no cabe (130%)? | 8 / 4 / 5 / 38.130 | — | **Rechazada** al validar, en 0 s: "La demanda requiere 46.352 m² pero solo hay 39.815 m² en las bodegas activas" | — | — | — | — |

Otros indicadores (izadas, fragmentación, desbalance, peso) en `resultados.csv`. Lectura de cada instancia:

- **P1:** sin varios destinos no hay restricciones de apilamiento entre ellos y el solver llega prácticamente al óptimo (gap 0,05%). Muestra que la no-overstowage es lo que hace difícil el problema.
- **P2:** con un solo producto no hay capas mixtas; aun con el buque casi lleno (la huella de ARAUCO_EKP es la mayor) se resuelve con gap 0,10%.
- **P3:** con dos cuadrillas que atienden una sola bodega (5 y 4), el desbalance entre cuadrillas sale alto (68%) por construcción (esas cuadrillas tienen la mitad de trabajo posible), y el gap del makespan es el más alto de todas (14,4%).
- **P4:** a media carga, el makespan baja a 27,65 h, menos de la mitad del caso base.
- **P5:** con el fondo pesado (70% al último destino) se sigue cumpliendo la no-overstowage; el makespan casi no cambia (58,47 h).
- **P6:** seis destinos se resuelven bien a 170 s (gap 0,90%). Ver 18.5 sobre lo que esto implica para el caso base.
- **P7:** el sistema no intenta resolver datos imposibles: los rechaza antes, con el motivo.

### 18.3 Sensibilidad a los rendimientos t/h (el análisis que la guía llama obligatorio)

El rendimiento de la bodega 1 (140 t/h contra 270 t/h del resto) es el supuesto sin confirmar que crea el cuello de botella. El tiempo por izada es inversamente proporcional al rendimiento (tc = tc_base × r_base / r). Todas a 170 s, comparadas con el caso base a 170 s (60,18 h):

| ID | Supuesto | Tiempo por izada bodega 1 | Makespan | Diferencia con 60,18 h | Gap makespan |
|---|---|---|---|---|---|
| P0 (170 s) | Bodega 1 a 140 t/h (caso base) | 13,91 min | 60,18 h | — | 4,10% |
| R_b1_180 | Bodega 1 a 180 t/h | 10,82 min | 59,51 h | −0,67 h (−1,1%) | 4,60% |
| R_b1_220 | Bodega 1 a 220 t/h | 8,85 min | 57,89 h | −2,28 h (−3,8%) | 3,34% |
| R_b1_270 | Bodega 1 a 270 t/h (igual que el resto) | 7,21 min | 55,99 h | −4,19 h (−7,0%) | 0,27% |
| R_todas_menos10 | Todas las bodegas rinden 10% menos | 15,46 min | 66,24 h | +6,06 h (+10,1%) | 3,23% |
| R_todas_mas10 | Todas las bodegas rinden 10% más | 12,65 min | 54,40 h | −5,78 h (−9,6%) | 3,52% |

**Lectura:** el makespan escala casi uno a uno con el rendimiento general (±10% de rendimiento → ∓10% de makespan): **el resultado absoluto depende directamente de un supuesto sin confirmar**. El rendimiento de la bodega 1, en cambio, mueve el resultado bastante menos: aun igualándola al resto (270 t/h, casi la mitad del tiempo por izada), el makespan baja 7%. Una explicación plausible, no verificada con un experimento aparte, es que la bodega 1 lleva poca carga (2.256 de 29.332 unidades en el plan del caso base). Para la comparación con el plan manual: las horas del plan manual se calcularon con los mismos rendimientos, así que si el supuesto fuera falso cambiarían ambas cifras. Conviene presentar la comparación con el plan manual, que depende menos del supuesto, antes que la cifra absoluta.

### 18.4 Sensibilidad al tamaño (Técnico, subtareas 16 y 19)

Carga proporcional al número de bodegas; bodegas agregadas idénticas a las 2-8; todas a 170 s.

| ID | Bodegas / destinos / unidades | Makespan | Gap pasada 1 (makespan) | Gap pasada 2 (izadas + fragmentación) | Fragmentación | Tiempo total |
|---|---|---|---|---|---|---|
| T4x2 | 4 / 2 / 14.667 | 54,88 h | 0,02% | 0,00% (óptimo) | 4 | 228 s |
| T6x3 | 6 / 3 / 21.998 | 55,24 h | 0,70% | 1,38% | 7 | 399 s |
| P0 (170 s) | 8 / 4 / 29.332 | 60,18 h | 4,10% | 3,74% | 11 | 421 s |
| T10x5 | 10 / 5 / 36.665 | 59,73 h | 4,43% | 4,26% | 14 | 460 s |
| T12x6 | 12 / 6 / 43.999 | 59,02 h | 4,32% | **20,47%** | **70** | 511 s |

**Lectura:** el tiempo total está acotado por el límite (3 pasadas × 170 s como máximo). Lo que cambia con el tamaño es la **calidad**: hasta 4-6 bodegas el solver llega prácticamente al óptimo; en el tamaño del caso base y hasta 10 bodegas / 5 destinos el makespan queda a ~4% del óptimo; con 12 bodegas / 6 destinos el makespan sigue bien (4,3%), pero la pasada 2 no alcanza a ordenar la carga y la fragmentación se dispara (70). El gap de 100% de la pasada 3 en T4x2 y T6x3 no es un mal resultado: con bodegas idénticas la cota del solver es 0 t, y cualquier diferencia positiva da 100%.

**Redacción para el manual (subtarea 19):** «Para buques de hasta 10 bodegas y 5 destinos, el sistema entrega en unos 7 minutos un plan con makespan a lo más a ~4,5% del óptimo. Para 12 bodegas y 6 destinos, el makespan mantiene esa calidad, pero la fragmentación puede quedar alta: revisar el plan antes de usarlo. En todos los casos, usar un límite menor a 180 s por pasada (por ejemplo 170 s).»

### 18.5 Consecuencia para el caso base: el óptimo está entre 57,49 y 58,24 h

- **Cota superior 58,24 h (P6):** todo plan de P6 es también un plan válido para el caso base (basta juntar DESTINO_5 con Qingdao y DESTINO_6 con Kunsan: se mantiene el orden de descarga y todas las demás restricciones, con el mismo makespan). Por lo tanto existe un plan del caso base de 58,24 h.
- **Cota inferior 57,49 h (P1):** todo plan del caso base es válido para P1 (un solo destino tiene menos restricciones), así que el óptimo del caso base no puede ser menor que el de P1, que el solver acotó en 57,49 h (57,52 h con gap 0,05%).

El resultado informado (59,67 h) está a lo más 2,2 h por encima del óptimo teórico, y existe un plan concreto 1,4 h mejor. Es coherente con el gap de 3,29%: con más tiempo o con otra búsqueda, el sistema podría mejorar el caso base. Para el Informe Académico, es un buen ejemplo de uso de instancias relacionadas para acotar la calidad de una solución sin probar optimalidad.

