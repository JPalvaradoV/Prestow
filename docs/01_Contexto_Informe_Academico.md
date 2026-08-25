# Contexto para avanzar el Informe Académico

**Léeme primero.** Este documento reúne lo necesario para trabajar las 29 subtareas del Informe Académico, que hasta ahora **nunca se recorrieron una por una**. Está pensado para adjuntarlo a un chat nuevo junto con `00_LEEME_PRIMERO_contexto.md` (el contexto general del proyecto).

---

## Qué es este informe y qué lo distingue del Técnico

El Informe Académico **no describe el sistema para un usuario** — eso es el Informe Técnico. Reflexiona sobre el **proceso de desarrollo**: qué se decidió, por qué, qué se comparó, qué salió mal y qué se aprendió. Su lector es el profesor evaluando el proceso, no un planificador portuario.

Reglas transversales del enunciado, válidas para las 29 subtareas:

- Se puede usar IA generativa para **estudiar alternativas**, nunca para que **decida** por el grupo. No es aceptable quedarse con una propuesta de IA sin análisis propio.
- Toda cifra, fecha, nombre propio o cita debe verificarse en la fuente original antes de citarla.
- Los supuestos se redactan con tres partes: qué se asume, por qué, y qué pasaría si fuera falso.

---

## Las 11 secciones y sus 29 subtareas

| # | Sección | Subtareas | Puntos aprox. | Estado |
|---|---|---|---|---|
| 1 | Introducción | 1, 2 | — | Insumo listo |
| 2 | Proceso de Desarrollo | 3, 4 | 10 | Insumo parcial — falta la bitácora llenada |
| 3 | Contexto y Planteamiento | 5, 6, 7 | — | **Insumo completo** |
| 4 | Tratamiento de Datos | 8, 9, 10, 11, 12 | — | **Insumo completo** |
| 5 | Modelamiento | 13, 14, 15, 16 | — | **Insumo completo** |
| 6 | Método de Solución | 17, 18, 19, 20, 21, 22 | 30 | **Insumo completo** |
| 7 | Validación | 23, 24 | — | **Insumo completo** |
| 8 | Resultados | 25, 26 | 20 | **Insumo completo** |
| 9 | Limitaciones | 27 | — | Insumo listo |
| 10 | Conclusiones | 28 | — | Depende de cada integrante |
| 11 | Cierre | 29 | — | Al final |

**Las secciones 3 a 8 tienen todo el contenido técnico ya resuelto** — el modelo está implementado y corrido, así que redactar esas secciones es traducir lo que ya existe, no generar contenido nuevo.

---

## Insumo por sección, con lo que ya se sabe

### 1. Introducción (subtareas 1-2)

- **Problema:** el prestow se arma a mano copiando el archivo del viaje anterior. El archivo no se rehace por buque, crece por acumulación de casos anteriores — evidencia: 4 hojas ocultas del Misago Arrow (2017) mezcladas con el caso real.
- **Particularidad del grupo:** se decidió construir el packer 2D como módulo separado en vez de usar solo capacidades tabuladas — da una palanca de optimización real que el proceso manual no usa.
- **Objetivo general:** minimizar el makespan de la carga del Kiwi Arrow respetando no-overstowage y capacidad real.
- **Propuesta de valor** (cítala igual en Resumen y Conclusiones): *"El sistema no busca mejorar la calidad del plan de estiba: el proceso manual ya alcanza cero overstowage y 6,9% de desbalance. Lo que aporta es velocidad, repetibilidad y escalabilidad."*

### 2. Proceso de Desarrollo (subtareas 3-4)

- **Insumo pendiente:** la bitácora semanal (`Bitacora_Semanal_Prestow_Lirquen.xlsx`) es la única fuente de esta sección. Si no se llenó cada viernes, hay que reconstruirla del historial del proyecto — se nota si se hace de memoria.
- **Decisiones clave documentadas y con su porqué:**
  - Elegir método exacto (MILP) con límite de tiempo, en vez de metaheurística.
  - HiGHS en producción, CPLEX en desarrollo para obtener la referencia de óptimo.
  - Packer como módulo separado y precalculado.
  - Lexicográfico en dos pasadas en vez de pesos — se probó y los pesos hacían que el tercer término se volviera indistinguible.
- **Errores como aprendizaje** (ver tabla completa más abajo, sección 6).

### 3. Contexto y Planteamiento (subtareas 5-7)

- **Descripción del problema:** buque open hatch, 8 bodegas, hasta 11 planes, 4 cuadrillas en pares fijos sobre bodegas contiguas, rotación Taichung → Qingdao → Kunsan/Ulsan.
- **Los 5 KPIs**, con fórmula y por qué no se limitan al resultado básico:

| KPI | Fórmula | Por qué importa |
|---|---|---|
| Rápido (makespan) | max horas entre cuadrillas | Determina cuándo zarpa el buque |
| Parejo (desbalance) | (máx−mín)/promedio × 100 | Mide si el trabajo está bien repartido |
| Lleno (aprovechamiento) | área ocupada/área piso | Mide eficiencia de empaquetamiento |
| Limpio (fragmentación) | bodegas distintas por destino | **Nadie lo mide hoy** — es el costo que Lirquén exporta al puerto de destino |
| Fiel (desviación) | Σ\|LQN−armador\|/Σarmador | Sale de la lista: la cobertura es igualdad estricta en el modelo |

- **Los 9 supuestos** con su estado (ver tabla en `00_LEEME_PRIMERO_contexto.md`) — esta sección es donde van redactados completos, con las tres partes cada uno.

### 4. Tratamiento de Datos (subtareas 8-12)

- **Cómo se convirtieron los datos:** extracción programática de la hoja `PRESTOW N° 06`, generando filas (bodega, plan, producto, destino, unidades, toneladas). Total 29.332 unidades — **275 de diferencia sin reconciliar** con la cifra de 29.057 citada por otra vía.
- **Problemas encontrados, con evidencia concreta:**
  - 4 hojas ocultas del Misago Arrow (2017), mismo formato que el caso real.
  - Sobrantes negativos de hasta 20 metros — físicamente imposible.
  - Bloques con dimensiones idénticas que declaran distinta cantidad de unidades.
  - El mismo producto llamado "CELCO UKP" en unas celdas y "CELCO" en otras.
  - El acortamiento de la bodega en planes altos, que inicialmente se creyó del Kiwi Arrow, resultó ser del Eagle Arrow — hallazgo que obligó a corregir un supuesto ya dado por cerrado.
- **Parámetros con rangos:** tiempo por ciclo de izada 7,11-7,19 min (bodegas 2-8) vs 13,91 min (bodega 1); rendimientos 140-270 t/h.
- **Generador de instancias e IA:** si se usó IA para generar el código del generador de instancias sintéticas, el enunciado exige **anexar los prompts usados**. Guardarlos desde ahora si no se hizo.

### 5. Modelamiento (subtareas 13-16)

- **Formulación completa** con las 11 familias de restricciones (conjuntos, parámetros, variables, función objetivo, restricciones) — está íntegra en `Restricciones_Modelo_Prestow_Lirquen.pdf`, listo para copiar y adaptar al formato del informe.
- **Memorias de cálculo** ya redactadas: derivación del tiempo por ciclo desde el archivo, cálculo de huellas verificadas contra plantillas, cota de big-M ajustada.
- **Reflexión — qué se omitió y por qué:** estabilidad transversal y esfuerzos del casco, reagrupación de bodegas entre cuadrillas, variación de geometría con la altura (solo hay plantillas propias del Kiwi Arrow hasta el plan 6), separadores de goma y espacio de maniobra (avalado por el profesor como supuesto). Todo está listado en la última sección del PDF de restricciones.

### 6. Método de Solución (subtareas 17-22) — 30 puntos, la sección de mayor peso

- **Alternativas comparadas:** exacto en todo, metaheurística en todo, híbrido (exacto en asignación + heurístico en packer). Se eligió **exacto con límite de tiempo** — ni puramente exacto sin límite ni metaheurístico.
- **Comparación medida de solvers**, con datos reales, mismo modelo y mismo límite de 150 s: CBC 57,12 h vs HiGHS 56,88 h — HiGHS alcanza en 150 s lo que CBC necesita 600 s.
- **Origen del método:** documentar que la propuesta inicial de híbrido fue una opinión externa con confianza media, evaluada y **descartada** por el grupo tras medir que el exacto con límite de tiempo daba mejores resultados y era más simple de mantener.
- **Los 7 errores encontrados, con su corrección** — es la sección más rica del informe y ya está redactada en detalle:

| Error | Cómo se manifestó | Corrección |
|---|---|---|
| Contigüidad burlable | La restricción estaba escrita sobre `y`, activable sin carga; el solver dejaba carga flotando | Se agregó `w` con implicación en ambos sentidos |
| Tiempo de ciclo constante | Subestimaba la bodega 1, la que determina el makespan | `tc` por bodega, derivado del archivo |
| Pesos vs. lexicográfico | El tercer término se volvía indistinguible numéricamente | Lexicográfico en dos pasadas |
| Tolerancia relativa | Un makespan mejor en la pasada 1 dejaba menos margen en la 2 | Tolerancia absoluta, en izadas |
| Pérdida de solución entre pasadas | Si la pasada 2 fallaba, se perdía la solución de la 1 | Captura y restauración explícita |
| Estado del solver poco fiable | PuLP reporta "Optimal" en corridas que no probaron optimalidad | Se lee el gap directamente del log |
| Restricción mal formulada (4b) | Una versión agregaba 880 restricciones e imposibilitaba resolver | Reformulada sobre `v`, agrega solo 8 |

- **Complejidad y su evolución:** el modelo pasó de 3.828 a 2.108 restricciones al simplificar la no-overstowage a planes adyacentes (demostrado equivalente, verificado con 211.000 configuraciones).

### 7. Validación (subtareas 23-24)

- **Pruebas realizadas:** 4 verificaciones automáticas (no-overstowage, cobertura, contigüidad, capacidad), corridas sobre el plan real del puerto — **las cuatro pasan**.
- **La validación más fuerte:** con `tc` por bodega, el modelo reproduce las horas del archivo original con error de 0,01-0,02 h en las cuatro cuadrillas (56,62/58,48/57,24/60,62 vs 56,62/58,49/57,26/60,61).
- **Resultado extraño y su explicación:** la fragmentación empeoró de 14 (plan manual) a 21 (modelo) — no es un error, es que la pasada 2 no alcanzó a resolver en 150 s y ese objetivo secundario quedó sin optimizar.

### 8. Resultados (subtareas 25-26) — 20 puntos

- **Tabla principal, ya calculada con datos reales:**

| Indicador | Plan manual | Modelo | Diferencia |
|---|---|---|---|
| Makespan | 60,61 h | **57,59 h** | −5,0% |
| Desbalance | 6,9% | **0,1%** | mucho mejor |
| Fragmentación | 14 | 21 | peor |
| Overstowage | 0 | 0 | igual |

- **Comportamiento ante cambios de parámetros — análisis de sensibilidad ya corrido**, sobre el orden entre Kunsan y Ulsan:

| Hipótesis | Makespan | Desbalance | Fragmentación |
|---|---|---|---|
| Empatados | 57,59 h | 0,1% | 21 |
| Kunsan antes | 57,86 h | 0,2% | 26 |
| Ulsan antes | 58,82 h | 4,0% | 25 |

Conclusión a redactar: el peor caso cuesta 1,23 h (2,1%), frente a las 3 h de mejora sobre el plan manual — el supuesto no es crítico para el resultado.

- **Advertencia a incluir:** gap de 0,195%, no es óptimo probado.

### 9. Limitaciones (subtarea 27)

Lista ya construida, lista para redactar como prosa: warm start pendiente, 275 unidades sin reconciliar, pasada 2 sin resolver en el tiempo disponible, packer sin distinguir altura, sin pruebas automatizadas formales, los 6 supuestos aún sin confirmar con el puerto.

### 10. Conclusiones (subtarea 28)

Requiere que **cada integrante** escriba su autoevaluación individual — no se puede redactar por outsourcing. Sirve tener a mano la propuesta de valor de la sección 1 como vara de medida común, para que las cinco autoevaluaciones no midan éxito con criterios distintos.

### 11. Cierre (subtarea 29)

Referencias APA 7 — **verificar cada una contra la fuente antes de entregarla**. Revisión cruzada final: que alguien que no escribió cada sección la lea antes de entregar.

---

## Lo que falta decidir o hacer antes de escribir

- **Llenar o reconstruir la bitácora** — es el único insumo de la sección 2.
- **Confirmar si se usó IA para el generador de instancias** y guardar los prompts si corresponde (subtarea 12).
- **Las 275 unidades sin reconciliar** — mencionarlo en Limitaciones aunque no se resuelva.
- **Coordinar las 5 autoevaluaciones individuales** de la sección 10.

---

## Errores que no hay que repetir al redactar

- No decir "óptima" sin gap cero probado — el modelo tiene gap de 0,195%.
- No mezclar el objetivo del modelo (makespan) con los beneficios del sistema (velocidad de planificación) — son cosas de naturaleza distinta.
- No usar solo el porcentaje de mejora del makespan como conclusión principal en Resultados — anclar en "minutos versus días" es más defendible porque no depende del signo del resultado.
- No dar el orden de Kunsan/Ulsan por sabido — sigue siendo supuesto, aunque el impacto medido sea bajo.
