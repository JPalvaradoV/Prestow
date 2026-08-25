# Instrucciones para afinar el modelo

**Para el chat donde se trabaje el código.** Este documento dice en qué estado está el modelo, qué se corrigió hace poco, y qué conviene atacar. Léelo junto con `00_LEEME_PRIMERO_contexto.md`.

---

## Cambios recientes, aplicados en esta ronda

### 1. La rotación quedó confirmada

**Ulsan es el último destino.** Antes se asumía que Kunsan y Ulsan compartían la posición 3, porque nunca aparecen juntos en una misma bodega del caso base y su orden no se podía deducir de los datos.

```
TAICHUNG  1     <- se descarga primero, va arriba en la bodega
QINGDAO   2
KUNSAN    3
ULSAN     4     <- se descarga al final, va al fondo
```

Actualizado en el código, en el Excel de entrada y en los CSV.

**Consecuencia en el modelo:** la restricción de no-overstowage pasó de 400 a 480 restricciones — ahora separa correctamente Kunsan de Ulsan, cosa que antes no hacía porque la condición `rot[d2] > rot[d]` no se activaba entre destinos con el mismo orden.

**El supuesto 9 del registro queda cerrado.** Ya no es un supuesto, es un dato.

### 2. Se eliminó la restricción de rotación empatada

Existía una bandera `SEPARAR_ROTACION_EMPATADA` que prohibía que dos destinos con el mismo orden de rotación compartieran bodega. Era una respuesta conservadora a la incertidumbre sobre Kunsan y Ulsan.

**Con la rotación confirmada ya no tiene sentido**, así que se eliminó por completo: la bandera, la restricción y el enlace condicional que dependía de ella. Si en el futuro apareciera otro caso de destinos con orden empatado, hay que decidirlo de nuevo — pero conviene no reintroducir esa restricción sin antes releer por qué se descartó (estaba confundiendo "no sabemos el orden" con "se descargan juntos").

### 3. Se regeneró el `plan_estiba.xlsx`

⚠️ **El archivo anterior estaba desactualizado y produjo un análisis con conclusiones invertidas.**

Lo que pasó: se cambió una bandera de configuración y no se volvió a correr el modelo, así que el Excel quedó pegado de una corrida anterior (63,92 h, desbalance 34,5%). Después se midió la distribución de peso sobre ese archivo creyendo que era el resultado bueno, y todo el análisis salió al revés. Nadie lo detectó hasta que otra persona corrió el modelo por su cuenta.

**Esto es el argumento más fuerte para las pruebas automatizadas** (ver más abajo).

---

## Lo que hay que atacar, en orden

### Prioridad 1 — Estabilidad de la solución

**El problema:** no se sabe cuánto varía la asignación entre corridas que dan el mismo makespan. Un MILP con límite de tiempo no es determinista, y el modo de falla que importa no es que cambie el makespan sino que **cambie la asignación manteniéndolo**.

Esto invalida cualquier medición hecha sobre una solución concreta — distribución de peso, fragmentación por bodega, densidad por bodega — mientras no se sepa.

**Qué hacer:** 5 corridas con semillas distintas, mismo límite de tiempo, y medir cuánto varía la asignación por bodega. Si varía mucho, cualquier análisis sobre "en qué bodega quedó qué" es ruido.

**Referencia externa:** una corrida en otra máquina con 120 s reprodujo 57,59 h exacto (con la rotación empatada anterior), pero terminó sin optimalidad probada y con gap desconocido. Confianza estimada en que el makespan se reproduce en hardware similar: **alta, ~85%**. Confianza en que la asignación se reproduce: **sin base para estimar**.

### Prioridad 2 — Warm start desde el plan real

El plan del puerto satisface las cuatro restricciones del modelo. Pasarlo como solución inicial garantizaría que el resultado nunca sea peor que las 60,61 h que el puerto logra hoy.

**Evidencia de que hace falta:** en una corrida documentada, HiGHS pasó **21 segundos sin encontrar ningún incumbente** (`BestSol = inf`) con la cota inferior ya en 57,41. El solver anda a ciegas al principio, y eso es exactamente lo que un warm start resuelve.

⚠️ PuLP soporta `warmStart=True` con CBC y CPLEX, pero **no siempre con HiGHS**. Verificar antes de asumir que funciona con el solver de producción.

### Prioridad 3 — La pasada 2 no resuelve

Con 150 a 180 segundos, la segunda pasada no encuentra solución factible dentro de la cota de makespan, así que el objetivo secundario —izadas y fragmentación— **nunca se aplica**. Todos los resultados actuales tienen la fragmentación sin optimizar.

Opciones a evaluar: subir bastante el límite, simplificar el objetivo secundario a un solo término, o darle a la pasada 2 el resultado de la pasada 1 como warm start.

### Prioridad 4 — Pruebas automatizadas

Hoy todo se verifica a mano. El incidente del `plan_estiba.xlsx` desactualizado muestra el costo: un cambio de bandera sin regenerar produjo un análisis completo con conclusiones invertidas.

**Mínimo viable:** un archivo de tests que corra las cuatro verificaciones sobre el plan real del puerto, más una comprobación de que el artefacto exportado corresponde a la configuración actual del código.

### Prioridad 5 — La planimetría visual

Pendiente y **no resuelto**. Ver la sección siguiente.

---

## El asunto de la planimetría, sin cerrar

Se intentó decodificar la plantilla del puerto —bodega 1, N. ALDEA EKP, 194 unidades por plan— y **no se logró reconstruir el algoritmo**.

### Lo que sí está verificado

**Cada fila del bloque numérico es internamente consistente.** Las seis columnas son `dimensión | medida de la unidad | división | entero usado | ocupado | sobrante`, y en las cinco filas se cumple que `dimensión / medida = división`, `entero × medida = ocupado`, y `dimensión − ocupado = sobrante`.

**Los círculos del dibujo son izadas, no unidades sueltas.** La imagen tiene 12 círculos de 16 más uno de 02: exactamente las 13 izadas que resultan de `techo(194/16)`. Eso valida directamente la restricción de izadas del modelo.

### Lo que no está resuelto

**Las filas transcritas no reconstruyen el total de 194.** Los enteros usados son 11, 16, 2, 0 y 10 — verificado releyendo la imagen original. Con esos números no se llega a 194 por ninguna combinación evidente.

Se probaron dos hipótesis y ambas se descartaron:
- Que los enteros fueran (10, 17) en vez de (0, 10) — la imagen dice claramente 0 y 10.
- Que el patrón fuera el de dos bloques ya implementado — el packer elige `uniforme sin rotar` para esa celda, con 200 unidades.

**Los números 64 y 512 del encabezado no se pudieron interpretar.** Una lectura posible es que 64 sea 16 columnas × 4 filas, pero es especulación. El 512 sigue sin explicación.

### Un hallazgo que sí sirve, y cambia la pregunta

Al revisar el archivo original apareció que **las plantillas no usan todas el mismo piso**:

```
BODEGA N° 1 · N. ALDEA EKP · 194 UNIT POR PLAN   ->  usa 16,80 m
BODEGA N° 1 · ALDEA BKP    · 189 UNIT POR PLAN   ->  usa 16,65 m
```

Eso explica por qué las dos plantillas de la misma bodega dan brechas de capacidad distintas (3,0% y 12,5%) sin necesidad de postular una merma variable: **están calculadas sobre largos distintos**.

⚠️ Y en la misma bodega hay una plantilla con **sobrante negativo**:
```
16,65 | 1,48 | 11,25 | 11,00 | 16,28 |  0,37
 0,37 | 1,47 |  0,25 |  2,00 |  2,94 | -2,57
```
Usa 2 donde la división da 0,25. Es una inconsistencia aritmética **dentro de una plantilla que el proyecto usa como fuente de verdad**. Debilita el supuesto de que "la verdad está en los dibujos".

### La pregunta que hay que responder antes de construir nada

**¿194 es la capacidad máxima de esa capa, o es simplemente lo que ese plan en particular cargó?**

Si es lo primero, hay una brecha de capacidad que explicar. Si es lo segundo, no hay nada que explicar — el puerto usa un layout estándar que no agota el piso.

Evidencia a favor de la primera lectura: el plan real pone 408 unidades de CELCO_UKP donde el máximo geométrico es 412, o sea 99,0%. Si el puerto usara sistemáticamente plantillas que no agotan el piso, no se vería un 99%.

**Sin resolver esto, construir el generador de planimetría es prematuro:** no se sabría si el dibujo generado debe reproducir el layout del puerto o el óptimo geométrico, que son cosas distintas.

---

## Lo que NO conviene hacer

**No agregar restricciones de peso ni de distribución.** Se midió y no hay caso: la dispersión relativa del modelo es 36,8% contra 18,9% del plan manual, con la bodega 1 dentro del rango de densidad del resto. Y cada unidad que se le devuelva a la bodega 1 cuesta 1,95× más tiempo por izada.

Además, nadie ha verificado que la dispersión de peso sea un problema operativo real: el modelo no calcula estabilidad ni trim, y no hay dato del puerto sobre qué distribución acepta el buque.

**No medir nada sobre una asignación concreta** hasta resolver la prioridad 1. Es el error que ya se cometió una vez.

**No dar por reconstruida la planimetría.** Dos lecturas cuidadosas de las mismas cinco filas dieron totales distintos (188 y 180). Eso es señal de que falta información, no un detalle a reconciliar.

---

## Preguntas abiertas para el puerto

- ¿Quién fija el tonelaje por bodega?
- ¿De dónde salen los rendimientos t/h?
- ¿Los pares de bodegas por cuadrilla son fijos?
- ¿Por qué la bodega 1 tarda el doble por izada?
- ¿Qué son los números 64 y 512 del encabezado de las plantillas?
- ¿Por qué distintas plantillas de la misma bodega usan largos distintos (16,80 vs 16,65 m)?
- ¿194 unidades por plan es el máximo de esa capa o el estándar de esa plantilla?
