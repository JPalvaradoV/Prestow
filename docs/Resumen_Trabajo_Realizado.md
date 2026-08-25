# Qué hemos hecho — resumen explicado

**Proyecto:** optimización del prestow de celulosa, Puerto Lirquén
**Caso base:** buque Kiwi Arrow, hoja `PRESTOW N° 06`
**Estado:** modelo implementado, corrido con datos reales y validado contra el plan del puerto

---

## En una frase

Construimos un sistema que decide qué carga va en cada bodega y en qué capa del buque, minimizando el tiempo que la nave permanece en el muelle. **Con datos reales mejora el plan del puerto en 3 horas (5%)** y equilibra las cuatro cuadrillas casi perfectamente.

---

## 1. Entender el problema

Lo primero fue reconstruir cómo funciona la operación, porque nada de eso estaba escrito.

**El buque.** Ocho bodegas en fila, cada una una caja de 19,26 m de alto sin cubiertas intermedias. La carga se apila en hasta once capas horizontales, que en la jerga del puerto se llaman «planes». La bodega 1 es más pequeña que las demás: 16,80 × 14,80 m contra 18,30 × 27,40 m.

**Las cuadrillas.** Cuatro equipos humanos trabajan en paralelo, cada uno sobre un par fijo de bodegas contiguas: (8+7), (6+5), (4+3), (2+1). Cada cuadrilla atiende sus dos bodegas una después de la otra. **El buque no zarpa hasta que la última termina** — por eso el objetivo es minimizar el máximo entre las cuatro, no la suma.

**El overstowage.** La carga que se descarga primero debe quedar arriba. Si por error queda carga del último puerto debajo de la del primero, en ese puerto hay que sacarla, guardarla en el muelle y volver a cargarla. Eso se llama rehandle y es dinero perdido.

---

## 2. El dato incómodo, y por qué cambió el proyecto

Antes de prometer nada medimos qué tan bueno era el plan manual:

| Métrica | Plan manual |
|---|---|
| Overstowage | **0 en 85 capas** |
| Desbalance entre cuadrillas | **6,9%** |
| Aprovechamiento de superficie | **96,3%** |

**El planificador ya lo hace bien.** El proyecto no compite contra un proceso deficiente: compite contra alguien competente que trabaja a mano.

Eso obligó a replantear la propuesta de valor. No es «mejoramos la calidad del plan» — es **velocidad, repetibilidad y escalabilidad**: producir esa misma calidad en minutos en lugar de días, sin depender de la experiencia de una persona ni de copiar el archivo del viaje anterior.

---

## 3. Los datos: lo que encontramos en el archivo

Esta parte tomó más tiempo del previsto y produjo varios hallazgos.

**Hojas ocultas de otro buque.** El archivo del prestow tiene seis hojas y solo dos están visibles. Cuatro son del Misago Arrow, de 2017. Durante el análisis se construyeron varios turnos de trabajo sobre la hoja equivocada antes de notarlo. **El archivo no se rehace por buque: crece por acumulación de casos anteriores.** Es evidencia concreta de por qué una herramienta aporta valor.

**Planimetrías mezcladas.** Inicialmente se revisó solo la hoja LH-1 y se concluyó que tres productos no tenían plantilla propia. **El archivo tiene 58 plantillas del Kiwi Arrow**, repartidas en LH-1 a LH-8. Las dimensiones reales estaban ahí desde el principio.

**Inconsistencias documentadas.** Sobrantes negativos de hasta 20 metros, físicamente imposibles. Bloques con dimensiones idénticas que declaran distinta cantidad de unidades. El mismo producto llamado «CELCO UKP» en unas celdas y «CELCO» en otras. Rendimientos que cambian entre planes sin explicación.

---

## 4. El modelo matemático

**Qué decide:** cuánto de cada combinación producto-destino va a cada bodega y en qué capa.

**Qué minimiza:** el makespan — las horas de la cuadrilla más cargada.

**Qué respeta:** que la carga que se descarga primero quede arriba, que ninguna capa exceda lo que cabe, que se embarque exactamente lo pedido, que no haya capas flotando sobre planes vacíos, y que una capa esté llena al menos al 90% antes de abrir la siguiente.

### El tamaño real del problema

Un punto que se aclaró varias veces: **las 29.332 unidades no son variables del modelo.** Formulado a nivel de toneladas por bodega, plan, producto y destino, son unas 1.700 variables y 2.100 restricciones. Las unidades individuales aparecen solo dentro de la capa, en el packer. Confundir ambos niveles es lo que hace creer que el problema es intratable.

### Los dos niveles

| | Packer 2D | Asignador |
|---|---|---|
| Qué decide | Cuántas unidades caben en una capa | Qué carga va en cada bodega y plan |
| Tipo de problema | Empaquetamiento geométrico | Asignación con secuenciamiento |
| Cuándo corre | Una vez, precalculado | En cada corrida |

El flujo va en una sola dirección: el packer **entrega** la capacidad, el asignador la **consume** como dato fijo. El modelo de asignación no ve fardos, ve toneladas — no sabe que un fardo mide 0,84 m a menos que alguien se lo diga.

---

## 5. El packer 2D

Se construyó como **módulo separado** porque la geometría no cambia entre viajes: recalcularla en cada corrida sería repetir un trabajo caro para obtener siempre lo mismo.

Implementa tres patrones —uniforme, dos bloques y cuatro bloques—. En las bodegas grandes gana el de cuatro bloques; en la bodega 1 gana el uniforme, así que implementar los tres valió la pena.

### El hallazgo de las huellas

Cuatro capas del plan real ponían 408 unidades donde el cálculo permitía 403. La primera hipótesis fue que faltaba un patrón de empaquetamiento. Pero la cota superior **absoluta** por área con la huella supuesta ya era 406 unidades: ninguna disposición geométrica puede superar la cota de área.

**El problema no estaba en el patrón sino en la huella.** Al revisar todas las hojas de planimetría aparecieron las dimensiones reales, y dos de las tres supuestas estaban mal:

| Producto | Supuesta | Real |
|---|---|---|
| ARAUCO_BKP | 0,84 × 1,47 | **0,84 × 1,36** |
| CELCO_UKP | 0,84 × 1,47 | **0,84 × 1,43** |

Con las huellas correctas, **el plan real del puerto satisface las cuatro restricciones del modelo**.

---

## 6. Cómo se resuelve

**Método:** exacto (MILP) con límite de tiempo, en dos pasadas lexicográficas.

- **Pasada 1:** minimizar el makespan.
- **Pasada 2:** fijar el makespan en su óptimo con una tolerancia de dos izadas, y minimizar lo secundario — izadas totales y fragmentación.

Se usa lexicográfico y no pesos porque con tres términos el tercero se volvía numéricamente indistinguible: se probó, y la fragmentación **empeoraba** al agregarlo.

**Solver:** HiGHS en producción, libre y sin atadura de licencia. Medido en el modelo: alcanza en 150 segundos lo que CBC necesita 600.

**Sobre el estado del solver:** PuLP reporta «Optimal» en corridas que no alcanzaron el óptimo — tres límites de tiempo distintos daban tres valores distintos, todos «Optimal». Por eso el código lee el gap directamente del log del solver en vez de confiar en el estado que devuelve.

---

## 7. Los resultados

Con datos reales, HiGHS, 150 segundos por pasada:

| Indicador | Plan manual | Modelo | Diferencia |
|---|---|---|---|
| **Makespan** | 60,61 h | **57,59 h** | **−3,02 h (−5,0%)** |
| Desbalance entre cuadrillas | 6,9% | **0,1%** | mucho mejor |
| Fragmentación total | 14 | 21 | peor |
| Overstowage | 0 | 0 | igual |

### De dónde sale la mejora

El plan manual deja la cuadrilla 4 en 60,61 h mientras las otras están entre 56 y 58. El modelo reparte casi perfecto, y para lograrlo **le quita carga a la bodega 1**: de 1.962 unidades a 1.616.

Esa palanca solo se hizo visible al descubrir que **el tiempo por izada no es constante entre bodegas**: la bodega 1 tarda 13,91 minutos por izada contra 7,15 del resto, casi el doble. Con un tiempo único, el modelo subestimaba justamente la bodega que determina el makespan.

### La validación más fuerte

Con el tiempo de ciclo por bodega, el modelo **reproduce las horas del archivo del puerto con error de 0,01 h**:

| Cuadrilla | Modelo | Archivo |
|---|---|---|
| 1 (bodegas 8+7) | 56,62 | 56,62 |
| 2 (bodegas 6+5) | 58,48 | 58,49 |
| 3 (bodegas 4+3) | 57,24 | 57,26 |
| 4 (bodegas 2+1) | 60,62 | 60,61 |

### Advertencias sobre el resultado

- **No es óptimo probado.** Gap de 0,195%. Muy cerca, pero conviene decirlo así.
- **La pasada 2 no alcanzó a resolver** en 150 segundos. Por eso la fragmentación empeoró: el modelo no la optimizó.

---

## 8. Los nueve supuestos

Tres se resolvieron, uno se descartó, y aparecieron tres nuevos durante la implementación.

| # | Supuesto | Estado |
|---|---|---|
| 1 | El Puerto fija el tonelaje por bodega | Sin confirmar |
| 2 | Los rendimientos t/h del archivo | Sin confirmar |
| 3 | Los pares de cuadrillas son fijos | Sin confirmar |
| 4 | Definición de unidad y huellas | **Resuelto** — verificadas en 58 plantillas |
| 5 | Acortamiento en los planes altos | **Descartado** — era del Eagle Arrow |
| 6 | Izadas y acomodo interno | **Corregido** — el tiempo por izada varía por bodega |
| 7 | Capas mixtas sin bloqueo entre destinos | Nuevo, declarado |
| 8 | Merma por factores no geométricos | Nuevo, avalado por el profesor |
| 9 | Orden entre Kunsan y Ulsan | Nuevo, medido |

### El supuesto 9, medido

En lugar de dejarlo como incertidumbre, se corrió análisis de sensibilidad con las tres hipótesis:

| Hipótesis | Makespan | Desbalance |
|---|---|---|
| Empatados (3 y 3) | 57,59 h | 0,1% |
| Kunsan antes (3 y 4) | 57,86 h | 0,2% |
| Ulsan antes (4 y 3) | **58,82 h** | 4,0% |

**El peor caso cuesta 1,23 h (2,1%)**, frente a las 3 h que el sistema mejora sobre el plan manual. El supuesto no es crítico, aunque conviene confirmarlo.

---

## 9. Los errores que encontramos

Están documentados porque son material directo para la sección de «aciertos y desaciertos» del informe académico.

| Error | Cómo se manifestó |
|---|---|
| **Contigüidad burlable** | La restricción estaba escrita sobre una variable que puede activarse sin carga. El solver la activaba en planes vacíos para satisfacerla formalmente, dejando carga flotando |
| **Tiempo de ciclo constante** | Subestimaba la bodega 1, que tarda casi el doble por izada y determina el makespan |
| **Pesos en vez de lexicográfico** | Con tres términos el tercero se volvía indistinguible: la fragmentación empeoraba al agregarlo |
| **Tolerancia relativa** | El margen dependía de cuánto logró la pasada 1: un makespan mejor dejaba menos margen |
| **Pérdida de solución entre pasadas** | Si la pasada 2 no encontraba solución, se perdía la de la pasada 1 |
| **Estado del solver poco fiable** | «Optimal» reportado en corridas que no alcanzaron el óptimo |
| **Restricción mal formulada** | Una primera versión agregaba 880 restricciones y volvía el modelo irresoluble |

**La restricción 4 se simplificó** a planes adyacentes en vez de todos los pares. Es equivalente siempre que exista contigüidad, y se verificó con demostración formal más **211.000 configuraciones probadas sin una sola discrepancia**. Redujo el modelo de 3.828 a 2.108 restricciones.

---

## 10. Lo que se entrega

| Archivo | Qué es |
|---|---|
| `modelo_prestow.py` | El modelo de asignación completo, con verificaciones y exportación |
| `packer_2d.py` | El cálculo de capacidad por geometría, precalculado |
| `capacidades.csv` | La tabla que produce el packer y consume el modelo |
| `datos_entrada_kiwi_arrow.xlsx` | Entrada editable, cinco hojas con instrucciones y advertencias |
| `datos/*.csv` | La misma entrada en CSV, para generación automática |
| `plan_estiba.xlsx` | La salida: plan visual tipo prestow, detalle e indicadores |

```
python3 packer_2d.py              # una vez, genera capacidades.csv
python3 modelo_prestow.py         # pregunta de dónde cargar los datos
```

---

## 11. Lo que falta

**Prioritario:**

1. **Warm start desde el plan real.** Ahora que el plan del puerto es factible, pasarlo como solución inicial garantizaría que el resultado nunca sea peor que las 60,61 h actuales.
2. **Las 275 unidades sin reconciliar** en la extracción del prestow.

**Después:**

3. La pasada 2 necesita más tiempo de solver, o un objetivo secundario más simple.
4. El packer no distingue altura: asume que los once planes son iguales.
5. Pruebas automatizadas — todo se verifica a mano, y varias veces una edición rompió algo sin que nadie lo notara hasta correrlo.

**Preguntas para el puerto, si se consigue contacto:**

- ¿Quién fija el tonelaje por bodega?
- ¿De dónde salen los rendimientos t/h?
- ¿Los pares de bodegas por cuadrilla son fijos?
- ¿Kunsan se descarga antes que Ulsan, o al revés?
- ¿Por qué la bodega 1 tarda el doble por izada?

---

*Todas las cifras de este resumen provienen del archivo entregado por el puerto o de corridas del modelo con esos datos. Los supuestos, que son lo que no está confirmado, llevan su propio registro.*
