# Avanzar el Informe Técnico

**Para el chat donde se redacte este informe.** Dice qué se puede escribir ya, qué está bloqueado y por qué, y con qué material se redacta cada sección. Léelo junto con `00_LEEME_PRIMERO_contexto.md`.

---

## Qué es este informe y para quién

**El Informe Técnico es para el usuario, no para el evaluador técnico.** Su propósito declarado es que alguien pueda usar la solución y, si el proceso cambia con el tiempo, modificarla. Eso decide todo lo demás:

- El modelo matemático formal va en **anexo**; la explicación en prosa va en el cuerpo.
- El manual de usuario pesa **20 de 100 puntos**; modelo y método, **35**.
- El lector es un planificador portuario, no un ingeniero de optimización.

No confundir con el Informe Académico, que reflexiona sobre el **proceso de desarrollo** y tiene otro lector.

---

## Estado de las 28 subtareas

| # | Sección | Subtareas | Puede escribirse ya |
|---|---|---|---|
| 1 | Resumen Ejecutivo | 1 | **Sí** |
| 2 | Problema y Alcance | 2, 3, 4, 5 | **Sí** |
| 4 | Modelo y Método | 6, 7, 8, 9, 10 | **Sí, salvo la 8** |
| 5 | Arquitectura | 11 | **Sí** |
| 6 | Datos de Entrada | 12, 13, 14 | **Sí** |
| 7 | Manual de Usuario | 15, 16, 17, 18, 19, 20 | **Parcial** — ver abajo |
| 8 | Validación y Testeo | 21, 22, 23 | **Parcial** |
| 9 | Anexos | 24, 25, 26 | **Sí, salvo la 26** |
| 10 | Cierre | 27, 28 | Al final |

**19 de las 28 se pueden escribir hoy.** Las nueve bloqueadas dependen de cosas que aún no existen: la página web desplegada, el generador de instancias, y las referencias APA verificadas.

---

## Sección 1 · Resumen Ejecutivo (subtarea 1)

**Se puede escribir.** Cuatro elementos:

- **Problema:** el prestow se arma a mano copiando el archivo del viaje anterior. El archivo no se rehace por buque, crece por acumulación: contiene 4 hojas ocultas del Misago Arrow de 2017 mezcladas con el caso real.
- **Tipo de solución:** optimización. Asignación de carga a bodegas y capas, minimizando el tiempo de la cuadrilla más cargada.
- **Beneficios:** velocidad, repetibilidad, escalabilidad.
- **Resultado principal:** ver más abajo, en la sección 8.

⚠️ **La trampa de esta sección.** El plan manual ya logra cero overstowage y 6,9% de desbalance. Escribir "mejora la calidad de la planificación" invita a que pidan el número que lo respalde. La redacción que se sostiene:

> «El sistema reproduce la calidad del plan manual —cero overstowage, balance equivalente o mejor— en minutos en lugar de días, sobre cualquier configuración de carga, sin depender de la experiencia de una persona ni de copiar el archivo del viaje anterior.»

**La cifra del resultado de esta sección debe coincidir exactamente con la de la subtarea 22 y con la última captura del manual (subtarea 17).** Se escriben en momentos distintos y por personas distintas: es la contradicción más probable de todo el informe.

---

## Sección 2 · Problema y Alcance (subtareas 2-5)

**Se puede escribir toda.**

### Subtarea 2 · Sistema y stakeholders

Buque open hatch, 8 bodegas en fila, cada una una caja de 19,26 m sin cubiertas intermedias, hasta 11 capas horizontales. Cuatro cuadrillas en pares fijos de bodegas contiguas. El buque zarpa cuando termina la última.

**Los stakeholders, con qué gana o pierde cada uno** — esta columna no es relleno, es lo que da sentido a la sección:

| Stakeholder | Qué gana o pierde |
|---|---|
| Planificador del puerto | Gana velocidad, con certeza |
| Armador (G2 Ocean) | Gana horas de buque, con certeza. El beneficio más claro |
| Puerto como organización | Gana **solo si** puede llenar el sitio liberado; podría perder si factura por horas de cuadrilla |
| Cuadrillas individuales | Puede haber ganadoras y perdedoras según cómo se redistribuya el balance |
| Puertos de destino | Cargan con la fragmentación sin haber decidido nada |

⚠️ Los productores de celulosa (Arauco, Nueva Aldea) **no son stakeholders de esta sección**: entregan materia prima, pero no usan la información del prestow ni toman decisiones con la salida del sistema.

### Subtarea 3 · Restricciones y supuestos

Los nueve supuestos, cada uno con estructura de tres partes: **qué se asume, por qué, y qué pasaría si fuera falso**. Ver la tabla en `00_LEEME_PRIMERO_contexto.md`.

Distinguir claramente restricción de supuesto: una **restricción** verificada es algo que el modelo debe garantizar siempre; un **supuesto** es algo que el modelo trata como cierto pero podría estar equivocado, y que si se confirma falso **relaja** el modelo en vez de romperlo.

### Subtarea 4 · Qué hace y qué NO hace

Lo que NO hace, con su razón — declararlo suma puntos:

| No hace | Por qué |
|---|---|
| No decide la rotación de puertos | La recibe como dato de entrada |
| No considera estabilidad transversal ni esfuerzos del casco | Las bodegas ocupan todo el ancho del buque; se recomienda verificar trim con el loading computer antes de ejecutar |
| No valida contra el loading computer real | Fuera de alcance declarado |
| No planifica varios buques simultáneamente | Un buque configurado por archivo |
| No implementa control de acceso de usuarios | Queda como trabajo futuro |
| No modela separadores de goma ni espacio de maniobra | Supuesto declarado y avalado |

### Subtarea 5 · Qué optimiza

> «El objetivo es minimizar el makespan, sujeto a condiciones particulares que se deben cumplir, principalmente las restricciones de capacidad, no-overstowage, rotación de puertos y tonelaje comprometido.»

⚠️ No mezclar el objetivo del modelo (makespan) con los beneficios del sistema (velocidad de planificación): son de naturaleza distinta y confunden al lector.

---

## Sección 4 · Modelo y Método (subtareas 6-10)

### Subtarea 6 · El modelo en prosa · **se puede escribir**

Redacción que pasa el test de "un compañero de otra carrera lo entiende":

> «El sistema decide qué carga va en cada bodega y en qué orden, de modo que las cuatro cuadrillas terminen su trabajo lo más parejo posible entre sí, porque el buque no puede zarpar hasta que la última cuadrilla termine. Al mismo tiempo, respeta que la carga que se descarga primero en el viaje quede siempre arriba, para no tener que sacar y volver a meter carga en los puertos intermedios.»

Nótese que no aparecen las palabras modelo, restricción, función objetivo ni algoritmo.

### Subtarea 7 · Modelo formal en anexo · **se puede escribir**

Está completo en `Restricciones_Modelo_Prestow_Lirquen.pdf`: conjuntos, parámetros, variables, función objetivo y las once familias de restricciones, cada una con su justificación. Es copiar y adaptar al formato del informe.

### Subtarea 8 · Métodos con citas APA 7 · **BLOQUEADA**

Requiere que las referencias estén verificadas en la fuente original, y eso no se ha hecho. Las citas están listadas en la memoria del proyecto pero **ninguna fue confirmada contra el paper**.

Frase modelo, para cuando se desbloquee:

> «No se encontró literatura académica que aborde específicamente la estiba de celulosa unitizada en buques open hatch. El problema se posiciona como un híbrido entre la estiba RoRo —dimensión horizontal de piso continuo— y el CSPP de contenedores —dimensión vertical de no-overstowage y rotación de puertos—, adaptando formulaciones de ambas familias al caso particular del Kiwi Arrow.»

Un vacío de literatura **se demuestra mostrando el rastreo hecho**, no se afirma.

### Subtarea 9 · Arquitectura conceptual · **se puede escribir**

Diagrama del flujo del método: entrada → packer 2D (calcula capacidad por geometría) → asignador (decide bodega y plan) → validación de no-overstowage → cálculo de makespan → plan final.

⚠️ Es distinto del diagrama de módulos: este describe **el razonamiento del método**, no el software.

### Subtarea 10 · Pseudocódigo · **se puede escribir**

El código de `modelo_prestow.py` y `packer_2d.py` está comentado y es traducible directo a pseudocódigo. Un ejemplo ya redactado, el validador de no-overstowage, está en el PDF de restricciones.

---

## Sección 5 · Arquitectura (subtarea 11) · **se puede escribir**

Lenguaje: Python. Librerías con versión: PuLP 3.3.2, HiGHS (highspy), openpyxl. Módulos: `packer_2d.py` (cálculo de capacidad, precalculado) y `modelo_prestow.py` (lectura, modelo, resolución en dos pasadas, verificaciones, exportación).

⚠️ Documenta la arquitectura **real**, no la planeada. Y las versiones no son adorno: alguien que quiera correr el código en el futuro necesita saber qué instalar.

---

## Sección 6 · Datos de Entrada (subtareas 12-14) · **se puede escribir toda**

### Subtarea 12 · Archivos requeridos

Son **dos naturalezas de datos**, no una:

- **Configuración del buque** — geometría de bodegas, huellas de productos. Cambia solo si cambia el buque.
- **Datos del viaje** — tonelaje por producto y destino, rotación. Cambia en cada corrida.

Ambas viven en `datos_entrada_kiwi_arrow.xlsx`, con cinco hojas: Instrucciones, Viaje, Rotación, Buque, Productos. Hay también versión en CSV para generación automática.

**El flujo decidido:** el usuario descarga la plantilla, la edita en Excel, y la sube. **No hay formularios en pantalla** — se evaluó y se descartó porque el archivo tiene 15 a 20 filas que en Excel se llenan copiando y pegando, y porque el planificador ya trabaja en Excel.

### Subtarea 13 · Tabla de campos

Formato de tabla, no prosa — el lector escanea buscando su campo, no lee de corrido:

| Campo | Tipo | Unidad | Rango válido | Oblig. | Si falta |
|---|---|---|---|---|---|
| bodega | entero | — | 1 a 8 | sí | rechaza el archivo |
| producto | texto | — | de la lista de productos | sí | rechaza el archivo |
| destino | texto | — | de la rotación declarada | sí | rechaza el archivo |
| unidades | entero | u | mayor que 0 | sí | rechaza el archivo |
| largo_m / ancho_m | decimal | m | por bodega | sí | error de configuración |
| huella_largo_m / huella_ancho_m | decimal | m | por producto | sí | error de configuración |
| orden_descarga | entero | — | 1 en adelante | sí | rechaza el archivo |

### Subtarea 14 · Extracto y archivos de muestra

El archivo adjunto es `datos_entrada_kiwi_arrow.xlsx`. El **extracto dentro del texto** son dos o tres filas mostradas en la propia sección — sirve para entender de un vistazo mientras se lee, mientras que el adjunto sirve para operar de verdad. Son complementarios, no redundantes.

---

## Sección 7 · Manual de Usuario (subtareas 15-20) · **PARCIAL**

| Subtarea | Estado | Por qué |
|---|---|---|
| 15 · Instalación y acceso | **Bloqueada** | No hay página desplegada; no existe el enlace |
| 16 · Cómo ejecutar y parámetros | **Parcial** | Los parámetros existen; falta el análisis de sensibilidad que da los valores recomendados |
| 17 · Ejemplo paso a paso | **Bloqueada** | Requiere capturas de la página funcionando |
| 18 · Resultados y archivos de salida | **Se puede escribir** | Los tres archivos ya existen |
| 19 · Limitaciones | **Parcial** | Falta la tabla de sensibilidad al tamaño |
| 20 · Recomendaciones y acceso | **Se puede escribir** | Es declaración de política |

### Lo que sí se puede escribir ahora

**Subtarea 16, parcialmente.** Los parámetros configurables son: límite de tiempo del solver, número de bodegas activas, fracción mínima de llenado, tolerancia de la pasada 2, y elección de solver (HiGHS o CBC). Cada uno necesita **qué hace, qué rango admite y qué valor recomendar** — lo último requiere el análisis de sensibilidad, que no existe.

**Subtarea 18.** Los tres archivos de salida, con qué decide el usuario con cada uno:

| Archivo | Qué permite decidir |
|---|---|
| Plan de estiba | Comunicar la asignación a las cuadrillas antes de iniciar la carga |
| Reporte de KPIs | Si el plan es aceptable tal cual o conviene ajustar la entrada y reejecutar |
| Parámetros de la corrida | Reproducir exactamente ese resultado más adelante |

⚠️ Distinguir "qué contiene el archivo" (anexo) de "qué decisión permite tomar" (cuerpo). Y no confundir las **variables de decisión del modelo** con las **decisiones del usuario**: son cosas distintas.

**Subtarea 20.** Declaración de política, sin construir nada: el planificador del puerto como usuario principal; y dado que no existe autenticación en esta versión, recomendar no cargar datos comercialmente sensibles más allá de lo necesario y tratar el enlace como de uso interno.

---

## Sección 8 · Validación y Testeo (subtareas 21-23) · **PARCIAL**

### Subtarea 21 · Instancias de prueba · **BLOQUEADA**

Requiere el generador de instancias sintéticas, que no está construido. La tabla necesita seis columnas: ID, propósito (la pregunta que la instancia contesta), tamaño, resultado, si cumplió no-overstowage, y comparación con línea base.

### Subtarea 22 · Comparación contra el plan manual · **se puede escribir**

Resultado con datos reales, rotación confirmada, HiGHS, 180 s por pasada:

| Indicador | Plan manual | Modelo | Diferencia |
|---|---|---|---|
| Makespan | 60,61 h | **58,19 h** | −2,42 h (−4,0%) |
| Desbalance entre cuadrillas | 6,9% | **0,2%** | mucho mejor |
| Fragmentación total | 14 | 22 | peor |
| Overstowage | 0 | 0 | igual |

Redacción propuesta:

> «En el caso base, el sistema encontró una solución con makespan de 58,19 horas, 2,42 horas por debajo de las 60,61 del plan manual: una mejora de aproximadamente 4,0%. La mejora proviene del balance entre cuadrillas, que pasa de 6,9% a 0,2% de desbalance. El resultado más significativo no es esa reducción, sino que el sistema alcanza una calidad equivalente o superior al plan manual en minutos, frente a los días que toma hoy el proceso manual.»

⚠️ **Tres advertencias:**
- **No usar la palabra "óptima"** — el solver terminó sin optimalidad probada.
- **La fragmentación empeoró** y hay que explicarlo: la pasada 2 no alcanzó a resolver en el tiempo dado, así que el objetivo secundario nunca se aplicó.
- **Un resultado anterior de 57,59 h circuló en documentos previos.** Correspondía a la rotación con Kunsan y Ulsan empatados, que ya no es la configuración vigente. No citarlo.

### Subtarea 23 · Pruebas de coherencia · **se puede escribir**

Cuatro verificaciones automáticas, todas pasan sobre el plan real del puerto:

| Verificación | Qué comprueba |
|---|---|
| No-overstowage | Que ningún destino de rotación posterior quede sobre uno anterior |
| Cobertura | Que se embarque exactamente la demanda |
| Contigüidad | Que no haya capas flotando sobre planes vacíos |
| Capacidad | Que ninguna capa exceda lo que cabe |

**La validación más fuerte del proyecto:** con el tiempo de ciclo por bodega, el modelo reproduce las horas del archivo del puerto con error de 0,01 h en las cuatro cuadrillas.

⚠️ El enunciado exige que estas pruebas sean **automáticas y ejecutables**, no una revisión visual hecha una vez. Hoy están implementadas en código, pero no hay un archivo de tests formal — mencionarlo en limitaciones.

---

## Sección 9 · Anexos (subtareas 24-26)

| Subtarea | Estado |
|---|---|
| 24 · Código fuente comentado | **Se puede** — `modelo_prestow.py` y `packer_2d.py` están comentados |
| 25 · Diccionario y glosario | **Se puede** — ver lista de términos abajo |
| 26 · Casos de prueba con resultados conocidos | **Bloqueada** — requiere el generador de instancias |

**Glosario, términos que deben estar:** prestow, plan (capa), bodega, cuadrilla, izada, overstowage, rehandle o shift, unidad, planimetría, rotación, stowage factor, crane split, makespan, gap, factibilidad, restricción dura, variable de decisión, min-max, heurística, metaheurística, NP-difícil.

---

## Sección 10 · Cierre (subtareas 27-28)

**Subtarea 27 · Extensión.** Límites por sección: Resumen Ejecutivo 1 página, Problema y Contexto 2, Objetivos 1, Modelo y Método 4, Arquitectura 1, Datos de Entrada 2, Instrucciones de Uso 5, Validación y Testeo 3. Excederse sin avisar pierde puntos.

**Subtarea 28 · Revisión cruzada.** Cada integrante lee secciones que no escribió, buscando **contradicciones entre secciones**, no ortografía. Los tres puntos de contradicción más probables:

1. La cifra del Resumen Ejecutivo contra la de la subtarea 22 contra la captura del manual.
2. Las limitaciones de la sección 2 contra las del manual (subtarea 19).
3. Que el glosario cubra los términos efectivamente usados.

---

## Lo que hay que desbloquear, en orden

1. **Verificar las referencias APA 7** en la fuente original — desbloquea la subtarea 8, que es parte del rubro de 35 puntos.
2. **Construir el generador de instancias** — desbloquea las subtareas 21 y 26.
3. **Correr el análisis de sensibilidad al tamaño** — desbloquea las subtareas 16 y 19 completas.
4. **Desplegar la página** — desbloquea las subtareas 15 y 17.

---

## Errores de redacción ya identificados, no repetir

| No escribir | Por qué |
|---|---|
| "El objetivo es cumplir las restricciones y minimizar el makespan" | Mezcla dos categorías: las restricciones son la condición, no parte del objetivo |
| "El modelo, usando fórmulas y algoritmos, obtiene una solución rápida" | Es cierto de cualquier software de optimización; no dice nada del proyecto |
| "Reducir las horas de trabajo de la grúa" | El objetivo es el **máximo** entre cuadrillas, no el trabajo total |
| "Encontramos un punto de creación" (sobre el vacío de literatura) | No verificable; un vacío se demuestra con el rastreo |
| "La solución óptima" sin gap cero verificado | "Óptimo" tiene significado matemático preciso |
| "No entrega solución si el tonelaje excede la capacidad" como limitación | No es limitación: es lo que la validación de entrada resuelve correctamente |
| Las variables de decisión del modelo como respuesta a "qué decide el usuario" | Confunde la decisión del solver con la del planificador |
