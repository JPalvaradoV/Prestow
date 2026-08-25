# Contexto para continuar el proyecto en otra conversación

**Léeme primero.** Este archivo contiene lo que hay que saber para retomar el trabajo sin repetir lo ya hecho ni volver a cometer los errores que ya se corrigieron.

---

## Qué es el proyecto

Capstone Analytics 2026-02, Ingeniería UDD. Equipo de 5 personas, 7 semanas más una de colchón.

Optimizar el **prestow** — el plan de estiba — de celulosa en Puerto Lirquén, para el buque Kiwi Arrow. El sistema decide qué carga va en cada bodega y en qué capa, minimizando el tiempo que la nave permanece en el muelle.

**No hay contacto con la contraparte.** Todo lo que no se puede deducir de los archivos se declara como supuesto.

---

## Estado actual, en tres frases

El modelo está **implementado, corrido con datos reales y validado**: mejora el plan del puerto en 3 horas (5%), y reproduce las horas del archivo original con error de 0,01 h.

Los **entregables de planificación** están completos: carta Gantt con 36 tareas maestras y 84 subtareas, bitácora, cuatro presentaciones y seis guías en PDF.

**No se ha ejecutado nada del proyecto real todavía** — todo lo construido es preparación y prototipo.

---

## Lo que hay que saber antes de tocar el modelo

### Errores que ya se cometieron y no hay que repetir

| Error | Qué pasó |
|---|---|
| **Leer solo la hoja LH-1 de planimetrías** | Hay 58 plantillas del Kiwi Arrow repartidas en LH-1 a LH-8. Por leer solo una, tres huellas se dieron por supuestas y dos estaban mal |
| **Trabajar sobre la hoja oculta equivocada** | El archivo del prestow tiene 6 hojas y solo 2 visibles; 4 son del Misago Arrow de 2017. Se construyeron varios turnos de análisis sobre el buque equivocado |
| **Confundir el acortamiento del Eagle Arrow con el Kiwi** | La caída de capacidad de 194 a 124 unidades en los planes altos es del Eagle Arrow. El Kiwi Arrow no tiene ese dato |
| **Escribir la contigüidad sobre `y`** | La variable `y` puede activarse sin carga. El solver la activaba en planes vacíos para satisfacer la restricción formalmente, dejando carga flotando |
| **Asumir tiempo de izada constante** | La bodega 1 tarda 13,91 min por izada contra ~7,15 del resto. Con un valor único, el modelo subestimaba justamente la bodega que determina el makespan |
| **Usar pesos en vez de lexicográfico** | Con tres términos, el tercero se vuelve numéricamente indistinguible: la fragmentación empeoraba al agregarlo |
| **Confiar en el estado del solver** | PuLP reporta "Optimal" en corridas que no alcanzaron el óptimo. Hay que leer el gap del log |
| **Cambiar configuración sin regenerar artefactos** | Se cambió una bandera y no se volvió a correr el modelo: el `plan_estiba.xlsx` quedó de una corrida anterior. Se midió sobre él y todo un análisis salió con conclusiones invertidas |

### Decisiones tomadas que no conviene reabrir sin razón

- **Método:** MILP exacto con límite de tiempo, dos pasadas lexicográficas.
- **Solver:** HiGHS en producción (libre, sin licencia). Medido: alcanza en 150 s lo que CBC necesita 600 s.
- **Librería:** PuLP.
- **Packer como módulo separado**, precalculado. La geometría no cambia entre viajes.
- **Capacidad en fracciones**, no en área cruda ni en unidades absolutas.
- **Restricción 4 solo entre planes adyacentes** — demostrado equivalente y verificado con 211.000 configuraciones.
- **Se eliminó la restricción de rotación empatada.** Existía para el caso en que dos destinos compartieran orden; con Ulsan confirmado como último ya no hace falta. Si reaparece el caso, releer por qué se descartó antes de reintroducirla.
- **Merma de capacidad = 0**, avalada por el profesor como supuesto declarado.

---

## Los nueve supuestos

| # | Supuesto | Estado |
|---|---|---|
| 1 | El Puerto fija el tonelaje por bodega | Sin confirmar |
| 2 | Los rendimientos t/h del archivo (140 en bodega 1, 270 en el resto) | Sin confirmar |
| 3 | Los pares de cuadrillas son fijos: (8+7), (6+5), (4+3), (2+1) | Sin confirmar |
| 4 | Huellas de los productos | **Resuelto** — verificadas en 58 plantillas |
| 5 | Acortamiento de la bodega en los planes altos | **Descartado** — era del Eagle Arrow |
| 6 | Tiempo por izada | **Corregido** — varía por bodega |
| 7 | Sin bloqueo entre destinos dentro de una misma capa | Declarado |
| 8 | Sin merma por separadores, maniobra ni medidas no netas | Avalado por el profesor |
| 9 | Orden entre Kunsan y Ulsan | **CERRADO** — confirmado con el puerto: Ulsan es el último (orden 4) |

---

## Cifras del caso base

```
Buque             Kiwi Arrow, 8 bodegas cargadas
Unidades          29.332 según la extracción (29.057 por otra vía, 275 sin reconciliar)
Toneladas         59.197
Capas con carga   85, de las cuales 5 son mixtas
Overstowage       0
Destinos          Taichung (1) -> Qingdao (2) -> Kunsan (3) -> Ulsan (4)
                  Ulsan es el ultimo: confirmado con el puerto

Horas por cuadrilla del plan manual
  Cuadrilla 1 (bodegas 8+7)   56,62 h
  Cuadrilla 2 (bodegas 6+5)   58,49 h
  Cuadrilla 3 (bodegas 4+3)   57,26 h
  Cuadrilla 4 (bodegas 2+1)   60,61 h   <- determina el makespan
Desbalance                     6,9%

Geometria
  bodegas 2 a 8   18,30 x 27,40 m
  bodega 1        16,80 x 14,80 m
  altura          19,26 m, hasta 11 planes

Huellas verificadas (m)
  N_ALDEA_EKP   0,84 x 1,47      ARAUCO_BKP   0,84 x 1,36
  N_ALDEA_BKP   0,84 x 1,36      CELCO_UKP    0,84 x 1,43
  ARAUCO_EKP    0,89 x 1,41
  peso por unidad: 2,02 t · marco de grua: 16 unidades por izada

Tiempo por ciclo de izada
  bodegas 2 a 8   7,11 a 7,19 min
  bodega 1        13,91 min
```

---

## Resultado obtenido

| Indicador | Plan manual | Modelo | |
|---|---|---|---|
| Makespan | 60,61 h | **58,19 h** | −4,0% |
| Desbalance | 6,9% | **0,2%** | mucho mejor |
| Fragmentación | 14 | 22 | peor |
| Overstowage | 0 | 0 | igual |

Corrida con la rotación confirmada (Ulsan último), HiGHS, 180 s por pasada. Sin optimalidad probada. La pasada 2 no alcanza a resolver, por eso la fragmentación quedó sin optimizar.

⚠️ Un resultado anterior de 57,59 h circuló en documentos previos: correspondía a la rotación con Kunsan y Ulsan empatados en posición 3, que ya no es la configuración vigente.

**El plan real del puerto satisface las cuatro verificaciones del modelo**, y el modelo reproduce sus horas con error de 0,01 h. Esa es la validación más fuerte que existe.

---

## Cómo se corre

```
python3 packer_2d.py              # una vez, genera capacidades.csv
python3 modelo_prestow.py         # pregunta de dónde cargar los datos

python3 modelo_prestow.py --datos datos_entrada_kiwi_arrow.xlsx --limite 300
python3 modelo_prestow.py --caso-base
```

En Jupyter o Colab, argparse choca con los argumentos del kernel. El código lo detecta y corre el caso base. Para cargar datos desde un notebook:

```python
main(carpeta_datos='datos_entrada_kiwi_arrow.xlsx', interactivo=False)
```

---

## Lo que falta, en orden

0. **Verificar estabilidad de la solución.** No se sabe cuánto varía la asignación entre corridas con el mismo makespan. Mientras no se sepa, cualquier medición sobre una asignación concreta —peso por bodega, densidad, fragmentación por bodega— puede ser ruido. Hacen falta 5 corridas con semillas distintas.
1. **Warm start desde el plan real.** Ahora que el plan del puerto es factible, pasarlo como solución inicial garantizaría que el resultado nunca sea peor que las 60,61 h actuales. Es lo de mayor impacto.
2. **Las 275 unidades sin reconciliar.** Parte se explica porque el archivo llama al mismo producto `CELCO UKP` y `CELCO` en celdas distintas; el resto no se rastreó.
3. **La pasada 2 no resuelve en 150 s.** Necesita más tiempo o un objetivo secundario más simple.
4. **El packer no distingue altura.** Asume que los once planes son iguales.
5. **Pruebas automatizadas.** Todo se verifica a mano, y varias veces una edición rompió algo sin que nadie lo notara hasta correrlo.

### Trabajo de planificación pendiente

- Recorrido tarea por tarea del **Informe Académico** (29 subtareas). Nunca se hizo.
- Las **tareas maestras 17 a 36** de la carta Gantt tampoco se revisaron una por una.
- El PDF `Guia_Pagina_Web` dice "24 de 27 en ruta crítica"; la cifra correcta es **22**.

### Preguntas para el puerto, si se consigue contacto

- ¿Quién fija el tonelaje por bodega?
- ¿De dónde salen los rendimientos t/h?
- ¿Los pares de bodegas por cuadrilla son fijos?
- ¿Kunsan se descarga antes que Ulsan, o al revés?
- ¿Por qué la bodega 1 tarda el doble por izada?

---

## Estructura del equipo

Un **pivote** y cuatro **encargados**: Datos y Método, Página web, Informe Técnico, Informe Académico. El encargado responde por que el entregable se cumpla; no necesariamente lo ejecuta.

Reglas acordadas: ninguna tarea se marca terminada sin su artefacto verificable · la semana 8 es colchón, no trabajo planificado · después del congelamiento no se agrega funcionalidad · la bitácora se llena cada viernes.

---

## Cómo prefiero trabajar

Modo socrático en temas que requieren criterio —decisiones, evaluaciones, análisis—: preguntas antes que respuestas terminadas. Respuesta directa en tareas de ejecución.

Objetividad sobre validación. Si algo está mal, decirlo. Distinguir hecho verificado de supuesto de especulación. Avisar cuándo conviene verificar cifras, fechas, nombres y citas en la fuente original.
