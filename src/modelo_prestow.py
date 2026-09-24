"""
Modelo de asignacion del prestow de celulosa - Puerto Lirquen
Buque Kiwi Arrow

Minimiza el makespan: las horas de la cuadrilla mas cargada, que determinan
cuando puede zarpar el buque.

ESTADO: modelo completo con DATOS REALES del caso base, extraidos de la hoja
PRESTOW N 06 del archivo del puerto y de las plantillas de planimetria.

Autor: equipo Capstone Analytics 2026-02
"""

import argparse
import csv
import io
import re
import contextlib
from collections import defaultdict
from pathlib import Path

import pulp


# =============================================================================
# 1. DATOS
# =============================================================================
# DATOS REALES del caso base: buque Kiwi Arrow, archivo PRESTOW_N_10, hoja
# "PRESTOW N 06". Extraidos programaticamente de las celdas UNITS/TONS de cada
# bodega y plan (tarea maestra 5).
#
# RECONCILIACION (resuelta 22-sep-2026): la extraccion suma 29.332 unidades,
# que calza exacto (unidades y toneladas) con el "PROGRAMA LQN" de la hoja --
# el programa propio de Lirquen. La cifra 29.057 que circulo antes es la suma
# de "HOLD NRO.", que difiere de LQN en las bodegas 3, 5 y 7 (+193, -68,
# +150 = 275). El propio archivo del puerto ya marcaba esa brecha en la fila
# 73. Detalle en CLAUDE.md, seccion 10, pendiente #3. Sigue siendo decision
# declarada fusionar "CELCO" a secas con "CELCO UKP" (filas 18, 23, 68).

# --- Conjuntos ---------------------------------------------------------------

BODEGAS = [1, 2, 3, 4, 5, 6, 7, 8]      # las 8 bodegas van cargadas en el caso base
PLANES = list(range(1, 12))              # 1 = al fondo, 11 = arriba
PRODUCTOS = ["ARAUCO_BKP", "ARAUCO_EKP", "CELCO_UKP", "N_ALDEA_BKP", "N_ALDEA_EKP"]
DESTINOS = ["TAICHUNG", "QINGDAO", "KUNSAN", "ULSAN"]

# Pares fijos de bodegas por cuadrilla. SUPUESTO 3, sin confirmar. Verificado
# aritmeticamente contra la fila de horas por cuadrilla del archivo original.
CUADRILLAS = {
    1: [8, 7],
    2: [6, 5],
    3: [4, 3],
    4: [2, 1],
}

# --- Parametros --------------------------------------------------------------

# rot[d]: posicion en la rotacion de descarga. 1 = se descarga primero.
# CONFIRMADO con el puerto: Ulsan es el ultimo destino de la rotacion. Antes se
# asumia que Kunsan y Ulsan compartian posicion 3, porque nunca aparecen juntos
# en una misma bodega del caso base y su orden no se podia deducir de los datos.
ROT = {
    "TAICHUNG": 1,
    "QINGDAO": 2,
    "KUNSAN": 3,
    "ULSAN": 4,
}

# a[p]: huella de una unidad, en m2.
# Solo dos productos tienen plantilla propia del Kiwi Arrow en las planimetrias:
# N_ALDEA_EKP (194 u/plan, verificado) y N_ALDEA_BKP (documentado en la hoja
# como "ALDEA BKP", 189 u/plan -- posible inconsistencia de nombre con el
# prestow, que lo llama "N. ALDEA BKP"; se asume el mismo producto).
# Para ARAUCO_BKP, ARAUCO_EKP y CELCO_UKP no hay plantilla propia del Kiwi
# Arrow: se usa la huella tipica de fardo de celulosa como SUPUESTO declarado.
HUELLA = {
    "N_ALDEA_EKP": 0.84 * 1.47,   # verificado, plantilla Kiwi Arrow
    "N_ALDEA_BKP": 0.84 * 1.48,   # verificado como "ALDEA BKP", posible inconsistencia de nombre
    "ARAUCO_EKP":  0.89 * 1.41,   # SUPUESTO: sin plantilla propia del Kiwi Arrow
    "ARAUCO_BKP":  0.84 * 1.47,   # SUPUESTO: sin plantilla propia del Kiwi Arrow
    "CELCO_UKP":   0.84 * 1.47,   # SUPUESTO: sin plantilla propia del Kiwi Arrow
}

# peso[p]: peso de una unidad del producto p, en toneladas. Se usa solo para
# el termino de balance de peso (restriccion 10, seccion USAR_BALANCE_PESO
# mas abajo) -- no afecta capacidad, izadas ni makespan.
# Dato real del caso base: las cinco huellas verificadas del Kiwi Arrow
# declaran 2.02 t/unidad, constante entre productos.
PESO = {
    "N_ALDEA_EKP": 2.02,
    "N_ALDEA_BKP": 2.02,
    "ARAUCO_EKP":  2.02,
    "ARAUCO_BKP":  2.02,
    "CELCO_UKP":   2.02,
}

# Respaldo si un producto no tiene peso declarado (por ejemplo datos de un
# caso editado a mano sin llenar la columna peso_t). Mismo valor que el caso
# base para no introducir un salto artificial.
PESO_UNIDAD_RESPALDO = 2.02

# Geometria del piso por bodega, en metros. Verificado del caso base.
# La bodega 1 es mas pequena que el resto.
PISO = {h: (18.30, 27.40) for h in BODEGAS}
PISO[1] = (16.80, 14.80)

# Fraccion del piso aprovechable, usada SOLO como respaldo.
#
# Lo correcto es usar la tabla de capacidades que genera packer_2d.py, que
# calcula el empaquetamiento real por combinacion de bodega y producto. Este
# valor unico se usa unicamente si esa tabla no esta disponible.
#
# SUPUESTO: 0.963, medido en la plantilla real de la bodega 1 (194 unidades
# sobre 248,64 m2), aplicado a todas las bodegas, alturas y productos.
APROVECHAMIENTO = 0.963

# Tabla de capacidades por geometria, generada por packer_2d.py.
# Contiene, para cada bodega y producto, cuantas unidades caben realmente
# segun el mejor patron de empaquetamiento encontrado.
#
# Si el archivo existe, el modelo lo usa y la capacidad deja de ser una
# aproximacion por area: pasa a ser el resultado del calculo geometrico.
#
# SUPUESTO DECLARADO Y AVALADO: el calculo no descuenta separadores de goma
# entre bloques, espacio de maniobra para la grua horquilla, ni medidas de piso
# no netas. Se usa la capacidad geometrica pura.
#
# VALIDADO: con las huellas verificadas de las plantillas LH-1 a LH-8, el plan
# real del caso base satisface las cuatro restricciones del modelo (capacidad,
# no-overstowage, contiguidad y cobertura). Eso da confianza en que el modelo
# representa correctamente lo que el puerto hace en la practica.
#
# Rutas relativas al directorio de trabajo; si ahi no existen, se buscan en
# data/ de la raiz del proyecto (ver _ruta_con_respaldo). Sin ese respaldo,
# el comando documentado (python3 src/modelo_prestow.py ... desde la raiz)
# no encontraba capacidades_reales_por_plan.csv -- vive solo en data/ -- y
# corria sin avisar con la capacidad uniforme vieja (detectado 24-sep-2026).
ARCHIVO_CAPACIDADES = "capacidades.csv"
ARCHIVO_CAPACIDADES_POR_PLAN = "capacidades_reales_por_plan.csv"
_CARPETA_DATOS_PROYECTO = Path(__file__).resolve().parent.parent / "data"

# CAPACIDAD[(bodega, producto)] = unidades maximas que caben en una capa,
# EL MISMO VALOR PARA TODOS LOS PLANES. Vacio significa que se usa la
# aproximacion por area. Sigue siendo el valor por defecto: CAPACIDAD_POR_PLAN
# (abajo) lo pisa solo donde hay un dato real verificado de un plan concreto.
CAPACIDAD = {}

# CAPACIDAD_POR_PLAN[(bodega, plan, producto)] = unidades maximas reales para
# esa combinacion EXACTA, extraidas de las plantillas del puerto (LH-1 a
# LH-8, archivo PLANIMETRIAS_MN_KIWI_ARROW). Pisa a CAPACIDAD cuando existe.
#
# HISTORIAL: se penso por mucho tiempo que "para el Kiwi Arrow solo hay
# plantillas propias de los planes 1 a 6" -- eso salio de revisar solo la
# hoja LH-1 (bodega 1), que en efecto solo tiene Kiwi Arrow hasta el plan 6
# (el resto son plantillas del Eagle Arrow, otro buque). Al revisar las 8
# hojas completas (sesion del 22 de septiembre de 2026) aparecieron 57
# plantillas propias del Kiwi Arrow cubriendo planes 1 a 11 en las bodegas 2
# a 8. Comparando la MISMA combinacion bodega+producto entre distintos
# planes, la mayoria de las bodegas no muestran variacion real (0-3%, dentro
# del ruido), pero las bodegas 4, 5, 7 y 8 sí muestran una caida real de
# 3-13% en los planes altos (8-10) respecto de los bajos/medios -- consistente
# con que cerca de la cubierta hay menos piso util (vigas, escotilla mas
# angosta que la bodega).
#
# CRITERIO DE LIMPIEZA (ver src/extraer_capacidades_reales.py para el
# detalle): se excluyeron (a) las plantillas con producto ambiguo (mezclan 2
# productos en una sola celda, ej "ARAUCO BKP / EKP" -- no se puede saber a
# cual atribuir el numero), (b) 10 combinaciones bodega+plan+producto donde
# dos plantillas distintas del mismo archivo daban valores distintos (ej.
# bodega 4 plan 9 ARAUCO_EKP: 362 en una plantilla, 341 en otra), y (c) un
# valor extremo (bodega 5, plan 10, ARAUCO_EKP = 174, un salto de -55%
# respecto del resto de esa bodega) que no se pudo confirmar si es un dato
# real o un error de tipeo en la planilla del puerto. No se inventa ningun
# numero: donde no hay dato limpio, se usa el valor por defecto de CAPACIDAD.
CAPACIDAD_POR_PLAN = {}

# A[h,t]: area utilizable del piso en el plan t de la bodega h, en m2. Sigue
# siendo una aproximacion uniforme (no varia con t) -- ver CAPACIDAD_POR_PLAN
# arriba para las combinaciones donde SI hay un dato real de capacidad por
# plan; AREA solo se usa como respaldo cuando ni eso ni CAPACIDAD existen.
AREA = {
    (h, t): PISO[h][0] * PISO[h][1] * APROVECHAMIENTO
    for h in BODEGAS
    for t in PLANES
}

# u: unidades que mueve el marco de la grua por izada. Dato del equipo.
UNIDADES_POR_IZADA = 16

# tc[h]: tiempo por ciclo de izada en la bodega h, en horas.
#
# NO ES CONSTANTE ENTRE BODEGAS. Derivado del archivo original, dividiendo las
# horas declaradas de cada bodega por sus izadas:
#
#     bodega 8: 26,55 h / 223 izadas =  7,14 min      bodega 4:  7,15 min
#     bodega 7: 30,07 h / 251 izadas =  7,19 min      bodega 3:  7,16 min
#     bodega 6: 31,42 h / 265 izadas =  7,11 min      bodega 2:  7,16 min
#     bodega 5: 27,07 h / 226 izadas =  7,19 min      bodega 1: 13,91 min
#
# La bodega 1 tarda casi el DOBLE por izada que el resto. Es coherente con que
# el archivo le asigne 140 t/h contra 270 t/h de las demas. La causa no esta
# confirmada; lo mas probable es que su menor superficie deje poco espacio de
# maniobra para la grua horquilla, o que el alcance de la grua sea peor ahi.
#
# Usar un tiempo unico subestimaria la bodega 1, que es justamente la que
# determina el makespan en el plan real. Por eso se define por bodega.
#
# SUPUESTO: estos valores derivan de los rendimientos t/h del archivo, que son
# el supuesto 2 y no estan confirmados con la contraparte.
TIEMPO_CICLO_POR_BODEGA = {
    8: 7.14 / 60,
    7: 7.19 / 60,
    6: 7.11 / 60,
    5: 7.19 / 60,
    4: 7.15 / 60,
    3: 7.16 / 60,
    2: 7.16 / 60,
    1: 13.91 / 60,
}

# Valor de respaldo para bodegas sin dato propio: el promedio de las que rinden
# normal. NO se usa el promedio general, porque la bodega 1 lo distorsiona.
TIEMPO_CICLO = 7.16 / 60


def tiempo_ciclo(h):
    """Tiempo por ciclo de izada de la bodega h, en horas."""
    return TIEMPO_CICLO_POR_BODEGA.get(h, TIEMPO_CICLO)

# Q[p,d]: unidades a embarcar de cada combinacion producto-destino.
# DATOS REALES, extraidos de la hoja PRESTOW N 06 (ver nota de reconciliacion
# arriba). Suma 29.332 unidades.
DEMANDA = {
    ("ARAUCO_BKP", "QINGDAO"): 5808,
    ("ARAUCO_BKP", "ULSAN"): 702,
    ("ARAUCO_EKP", "KUNSAN"): 1820,
    ("ARAUCO_EKP", "QINGDAO"): 5487,
    ("ARAUCO_EKP", "TAICHUNG"): 1040,
    ("ARAUCO_EKP", "ULSAN"): 3338,
    ("CELCO_UKP", "KUNSAN"): 1090,
    ("CELCO_UKP", "TAICHUNG"): 1091,
    ("N_ALDEA_BKP", "QINGDAO"): 858,
    ("N_ALDEA_BKP", "TAICHUNG"): 468,
    ("N_ALDEA_EKP", "KUNSAN"): 4390,
    ("N_ALDEA_EKP", "QINGDAO"): 1290,
    ("N_ALDEA_EKP", "TAICHUNG"): 1950,
}

# Solver a usar. Medido en este modelo con limite de 150 s:
#   CBC   -> makespan 57,12 h
#   HiGHS -> makespan 56,88 h   (mismo valor que CBC necesito 600 s para alcanzar)
# HiGHS es libre, se instala con "pip install highspy" y no tiene atadura de
# licencia, asi que sirve tanto en desarrollo como en el despliegue de la
# aplicacion. CBC queda como respaldo por si highspy no esta disponible.
SOLVER = "HiGHS"          # "HiGHS" o "CBC"

# Limite de tiempo del solver, en segundos. Parametro configurable.
# ATENCION: con datos reales (29.332 unidades, ~13 combinaciones producto-
# destino) el modelo es sustancialmente mas grande que con los datos ficticios
# usados para las primeras pruebas. Verificar tiempo de resolucion antes de
# asumir que 120 s alcanza.
LIMITE_SEGUNDOS = 120

# Limite de tiempo propio para la pasada 3 (balance de peso). Con la
# configuracion final (ETAPAS_BALANCE_PESO=1, ver su comentario) converge
# bien en el mismo tiempo que las pasadas 1 y 2, asi que no hace falta darle
# mas -- se probo con las 4 etapas completas y ni 900 s alcanzaban.
# --limite en la linea de comandos pisa tambien este valor.
LIMITE_SEGUNDOS_BALANCE = LIMITE_SEGUNDOS

# Umbral (segundos) por debajo del cual la pasada 1 usa el warm start
# heuristico de solucion_inicial.py. Medido el 22-sep-2026 (caso base, ver
# docs/05_Estado_app_web.md): el warm start ANCLA la busqueda cerca de su
# propio punto de partida (~60 h) -- a 180 s con warm start el gap solo baja a
# 4,1% y el resultado final es 60,18 h, peor que los 59,67 h que el solver ya
# lograba buscando desde cero en el mismo tiempo. Por debajo de este umbral
# la pasada 1 sin warm start directamente NO encuentra ninguna solucion
# factible (verificado a 30/60/90 s), asi que ahi el warm start es
# estrictamente una mejora. Lo usan main() (linea de comandos) y api.py (web).
UMBRAL_WARM_START_PASADA1 = 180

# --- Objetivo secundario -----------------------------------------------------
# El makespan es el objetivo primario. Pero entre todas las soluciones con el
# mismo makespan hay unas mejores que otras, y el solver devuelve una cualquiera.
#
# Se resuelve con OPTIMIZACION LEXICOGRAFICA en dos pasadas, no con pesos:
#   Pasada 1: minimizar el makespan.
#   Pasada 2: fijar el makespan en su optimo (con tolerancia) y minimizar lo
#             secundario.
#
# Por que no pesos: obligan a que cada nivel sea mucho menor que el anterior,
# y con tres niveles el tercero se vuelve numericamente indistinguible de cero.
# Se probo empiricamente y la fragmentacion EMPEORO al agregar el tercer termino.
#
# 1. Izadas totales: reduce el trabajo real del puerto y empuja a llenar las
#    capas en multiplos de 16.
# 2. Fragmentacion: concentra cada destino en menos bodegas. Reduce el costo que
#    Lirquen exporta al puerto de destino.
# 3. Planes usados: compacta la carga hacia abajo. Se solapa con el termino de
#    izadas; apagado por defecto.
USAR_IZADAS = True
USAR_FRAGMENTACION = True
USAR_PLANES = False

# Peso relativo entre los terminos secundarios de la pasada 2.
# Aqui si se pueden usar pesos sin problema numerico, porque todos los terminos
# son del mismo orden de magnitud y ninguno compite con el makespan.
PESO_IZADAS = 1.0
PESO_FRAGMENTACION = 10.0     # una bodega menos vale como diez izadas menos
PESO_PLANES = 1.0

# Tolerancia sobre el makespan optimo en la pasada 2, en NUMERO DE IZADAS.
#
# Se usa tolerancia ABSOLUTA, no relativa (no un porcentaje). Razon: con
# tolerancia relativa el margen de la pasada 2 depende de cuanto logro la
# pasada 1, y eso lo hace impredecible. Se verifico experimentalmente:
#   pasada 1 = 57,12 h  ->  techo 57,40 h  ->  fragmentacion 9
#   pasada 1 = 56,88 h  ->  techo 57,16 h  ->  fragmentacion 16
# Es decir, un makespan MEJOR en la pasada 1 dejaba MENOS margen y empeoraba
# la fragmentacion. Con tolerancia absoluta el margen es siempre el mismo.
#
# Con 0 es lexicografica pura: el makespan no puede empeorar nada.
# Con 2 se aceptan hasta 2 izadas mas (unos 14 minutos) si eso mejora lo demas.
TOLERANCIA_IZADAS = 2

# --- Balance de peso (pasada 3, opcional) ------------------------------------
# Lexicografica despues de izadas+fragmentacion: para cada ETAPA del viaje
# calcula cuanto peso queda en cada bodega y minimiza la diferencia entre la
# bodega mas y la menos cargada de esa etapa, sumada sobre todas las etapas
# consideradas (ver ETAPAS_BALANCE_PESO).
#
# REABRE UNA DECISION CERRADA (ver CLAUDE.md seccion 6, y el historial de
# docs/05_Estado_app_web.md): se habia medido que sin esta restriccion el
# modelo tiene 36.8% de dispersion de densidad contra 18.9% del plan manual,
# sin evidencia de problema operativo, y se decidio no restringir peso.
# Se reactiva a pedido explicito del dueno del proyecto: la web genera un
# plan desde cero para alguien sin plan de referencia, no solo reproduce el
# plan manual, y prefiere pagar makespan por un buque mejor balanceado.
#
# OJO CRITICO: con esto activo, la restriccion (9) de ruptura de simetria
# deja de ser valida (ver su propio comentario "OJO" mas abajo: exige que
# una bodega de cada par gemelo cargue "al menos tanto como" la otra, lo que
# le impide al modelo balancear peso ENTRE esas dos bodegas). preparar_
# pasada3() la retira del problema justo antes de resolver esa pasada.
USAR_BALANCE_PESO = True

# Cuantas etapas del viaje se balancean. k=0 es la carga inicial (zarpe, todo
# a bordo); k=1 es el tramo despues de descargar en el primer puerto, y asi
# sucesivamente hasta len(DESTINOS)-1 (el ultimo tramo, solo con la carga del
# ultimo puerto).
#
# HISTORIAL DE LA INVESTIGACION (sesion del 21 de septiembre de 2026):
#   1. Con las 4 etapas completas y SIN warm start: el solver no encontraba
#      NINGUNA solucion factible para esta pasada ni en 180 s ni en 900 s.
#      No era falta de tiempo: sin la ruptura de simetria (ver OJO arriba)
#      HiGHS no lograba ni siquiera tropezar por su cuenta con un punto
#      factible, pese a que la solucion de la pasada 2 ya es una.
#   2. Se agrego warm start (ver api._resolver_con_warm_start: PuLP no lo
#      expone para HiGHS de fabrica en esta version, asi que resolver_
#      prestow() arma la llamada a mano). Con eso, las 4 etapas SI
#      encuentran una solucion factible -- pero se estanca ahi: 180 s, 600 s
#      y hasta con la tolerancia de la pasada 2 mucho mas floja (20 en vez
#      de 2), el gap se quedo pegado entre 75% y 77%. El primal bound de la
#      corrida de 180 s y la de 600 s dio EXACTAMENTE igual (30031.34): el
#      solver exploro muchisimos mas nodos sin encontrar nada mejor. La
#      causa mas probable es que "minimizar la suma de rangos max-min en 4
#      etapas, sin ruptura de simetria" tiene una relajacion LP demasiado
#      debil para este solver -- arreglarlo de verdad necesitaria
#      desigualdades validas mas sofisticadas, no ajustar parametros.
#   3. Con 1 SOLA etapa (la carga inicial, que es ademas la que ya se habia
#      medido antes del proyecto: 36.8% vs 18.9%), con warm start y el
#      tiempo estandar (180 s), el gap converge a ~16% -- un resultado real
#      y razonablemente bueno, muy por encima de las 4 etapas.
#
# CONCLUSION: se deja en 1 SOLA etapa (departure/carga inicial) como
# configuracion final. Antes de volver a subir este numero, hay que resolver
# el problema de fondo de la relajacion debil, no solo darle mas tiempo o
# tolerancia -- ya se probo que ninguna de las dos alcanza.
ETAPAS_BALANCE_PESO: int | None = 1


def _n_etapas_balance() -> int:
    """Cuantas etapas balancear: todas las de la rotacion actual, o el tope
    de ETAPAS_BALANCE_PESO si es mas chico."""
    if ETAPAS_BALANCE_PESO is None:
        return len(DESTINOS)
    return min(ETAPAS_BALANCE_PESO, len(DESTINOS))


# Solo hay un termino en la pasada 3 hoy; este peso no compite con nada.
# Queda declarado por si se agrega otro termino a esa pasada en el futuro.
PESO_BALANCE = 1.0

# Tolerancia ABSOLUTA (en unidades del objetivo ponderado de la pasada 2:
# izadas + 10 x bodegas de fragmentacion) al fijar ese objetivo para poder
# pasar a la pasada 3. Mismo criterio que TOLERANCIA_IZADAS: un margen fijo,
# no relativo, para que no dependa de cuanto logro la pasada 2.
TOLERANCIA_PASADA3 = 2.0

# Fraccion minima del area que debe ocupar una capa para poder abrir la de
# encima. Con 0 se desactiva.
#
# Sin esta restriccion, la contiguidad permite poner una sola unidad en un plan
# y con eso habilitar el de arriba: fisicamente absurdo, y ademas desperdicia
# una izada completa. Con 0.90 se exige que la capa este al menos al 90% antes
# de abrir la siguiente.
#
# OJO: si se pone demasiado alto puede volver infactible el modelo, porque las
# unidades son discretas y no siempre se puede llenar una capa exactamente.
# El plan real del caso base llena sus capas por encima del 98%, asi que 0.90
# deja margen suficiente.
FRACCION_MINIMA_CAPA = 0.90

# (Aqui existia una bandera SEPARAR_ROTACION_EMPATADA, eliminada al confirmarse
#  con el puerto que Ulsan es el ultimo destino de la rotacion. Con ordenes
#  distintos para cada destino, la restriccion 4 los separa correctamente por si
#  sola y no hace falta ningun tratamiento especial.)

# Romper la simetria entre bodegas equivalentes.
# SUPUESTO: dentro de una misma cuadrilla, las bodegas con igual geometria son
# intercambiables. Solo aplica a pares donde ambas bodegas tienen el mismo piso.
ROMPER_SIMETRIA = True


# =============================================================================
# 1b. CARGA DESDE ARCHIVOS CSV
# =============================================================================
# Los datos de arriba son el caso base cableado, util para probar rapido. Pero
# el sistema debe poder operar sobre cualquier viaje sin tocar el codigo, asi
# que tambien se pueden cargar desde CSV.
#
# Cuatro archivos, separados segun su naturaleza:
#
#   CONFIGURACION DEL BUQUE (cambia solo si cambia el buque)
#     buque_*.csv      : bodega, largo_m, ancho_m, planes, cuadrilla
#     productos_*.csv  : producto, huella_largo_m, huella_ancho_m, peso_t, origen_dato
#
#   DATOS DEL VIAJE (cambian en cada corrida)
#     viaje_*.csv      : producto, destino, unidades
#     rotacion_*.csv   : destino, orden_descarga, nota
#
# Ver la carpeta "datos/" para los archivos de ejemplo con el caso base real.

def cargar_desde_csv(carpeta):
    """
    Lee los cuatro CSV de una carpeta y sobreescribe los datos del modulo.

    Devuelve la lista de advertencias encontradas. No lanza excepcion ante
    datos faltantes: las reporta para que el usuario las vea.
    """
    global BODEGAS, PLANES, PRODUCTOS, DESTINOS, CUADRILLAS
    global ROT, HUELLA, PESO, PISO, AREA, DEMANDA

    ruta = Path(carpeta)
    avisos = []

    def leer(patron, obligatorio=True):
        encontrados = sorted(ruta.glob(patron))
        if not encontrados:
            if obligatorio:
                raise FileNotFoundError(
                    f"No se encontro ningun archivo '{patron}' en {ruta}"
                )
            return []
        if len(encontrados) > 1:
            avisos.append(
                f"Hay {len(encontrados)} archivos '{patron}'; se usa "
                f"{encontrados[0].name}"
            )
        with open(encontrados[0], newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    # --- buque ---
    filas_buque = leer("buque_*.csv")
    BODEGAS = []
    PISO = {}
    cuadrillas_tmp = defaultdict(list)
    n_planes = None
    for r in filas_buque:
        h = int(r["bodega"])
        BODEGAS.append(h)
        PISO[h] = (float(r["largo_m"]), float(r["ancho_m"]))
        cuadrillas_tmp[int(r["cuadrilla"])].append(h)
        p_ = int(r["planes"])
        if n_planes is not None and p_ != n_planes:
            avisos.append(
                f"La bodega {h} declara {p_} planes y otra declara {n_planes}. "
                f"El modelo asume el mismo numero para todas; se usa el mayor."
            )
        n_planes = max(n_planes or 0, p_)
    BODEGAS.sort()
    PLANES = list(range(1, n_planes + 1))
    CUADRILLAS = {g: sorted(hs, reverse=True) for g, hs in sorted(cuadrillas_tmp.items())}

    # --- productos ---
    HUELLA = {}
    PESO = {}
    PRODUCTOS = []
    for r in leer("productos_*.csv"):
        p = r["producto"].strip()
        PRODUCTOS.append(p)
        HUELLA[p] = float(r["huella_largo_m"]) * float(r["huella_ancho_m"])
        peso_t = r.get("peso_t")
        PESO[p] = float(peso_t) if peso_t not in (None, "") else PESO_UNIDAD_RESPALDO
        origen = (r.get("origen_dato") or "").upper()
        if "SUPUESTO" in origen:
            avisos.append(f"La huella de {p} es un SUPUESTO, no un dato verificado")

    # --- rotacion ---
    ROT = {}
    DESTINOS = []
    for r in leer("rotacion_*.csv"):
        d = r["destino"].strip().upper()
        DESTINOS.append(d)
        ROT[d] = int(r["orden_descarga"])
        nota = (r.get("nota") or "").strip()
        if nota:
            avisos.append(f"{d}: {nota}")

    # --- viaje ---
    DEMANDA = {}
    for r in leer("viaje_*.csv"):
        p = r["producto"].strip()
        d = r["destino"].strip().upper()
        u = int(r["unidades"])
        if u <= 0:
            continue
        DEMANDA[(p, d)] = DEMANDA.get((p, d), 0) + u

    # --- derivados ---
    AREA = {
        (h, t): PISO[h][0] * PISO[h][1] * APROVECHAMIENTO
        for h in BODEGAS
        for t in PLANES
    }
    return avisos



def cargar_desde_excel(ruta_excel):
    """
    Lee los datos desde un Excel con cuatro hojas: Viaje, Rotacion, Buque y
    Productos. Es la alternativa a los CSV, mas comoda para que el usuario
    modifique los datos a mano.

    Devuelve la lista de advertencias encontradas.
    """
    global BODEGAS, PLANES, PRODUCTOS, DESTINOS, CUADRILLAS
    global ROT, HUELLA, PESO, PISO, AREA, DEMANDA

    from openpyxl import load_workbook

    wb = load_workbook(ruta_excel, data_only=True)
    avisos = []

    faltantes = [h for h in ("Viaje", "Rotacion", "Buque", "Productos")
                 if h not in wb.sheetnames]
    if faltantes:
        raise ValueError(
            f"Al archivo le faltan estas hojas: {', '.join(faltantes)}. "
            f"Tiene: {', '.join(wb.sheetnames)}"
        )

    def filas(hoja, columnas):
        """Lee una hoja saltando titulos, hasta la primera fila vacia."""
        ws = wb[hoja]
        # La fila de encabezado es la que contiene el primer nombre de columna
        fila_enc = None
        for r in range(1, 12):
            if str(ws.cell(row=r, column=1).value or "").strip() == columnas[0]:
                fila_enc = r
                break
        if fila_enc is None:
            raise ValueError(
                f"En la hoja '{hoja}' no se encontro la columna '{columnas[0]}'"
            )
        salida = []
        r = fila_enc + 1
        while True:
            primera = ws.cell(row=r, column=1).value
            if primera is None or str(primera).strip() == "":
                break
            if str(primera).strip().upper() == "TOTAL":
                break
            salida.append({
                col: ws.cell(row=r, column=j).value
                for j, col in enumerate(columnas, start=1)
            })
            r += 1
        return salida

    # --- Buque ---
    BODEGAS = []
    PISO = {}
    cuadrillas_tmp = defaultdict(list)
    n_planes = 0
    for r in filas("Buque", ["bodega", "largo_m", "ancho_m", "planes", "cuadrilla"]):
        h = int(r["bodega"])
        BODEGAS.append(h)
        PISO[h] = (float(r["largo_m"]), float(r["ancho_m"]))
        cuadrillas_tmp[int(r["cuadrilla"])].append(h)
        n_planes = max(n_planes, int(r["planes"]))
    BODEGAS.sort()
    PLANES = list(range(1, n_planes + 1))
    CUADRILLAS = {g: sorted(hs, reverse=True)
                  for g, hs in sorted(cuadrillas_tmp.items())}

    # --- Productos ---
    HUELLA = {}
    PESO = {}
    PRODUCTOS = []
    for r in filas("Productos", ["producto", "huella_largo_m", "huella_ancho_m",
                                 "peso_t", "origen_dato"]):
        p_ = str(r["producto"]).strip()
        PRODUCTOS.append(p_)
        HUELLA[p_] = float(r["huella_largo_m"]) * float(r["huella_ancho_m"])
        peso_t = r.get("peso_t")
        PESO[p_] = float(peso_t) if peso_t not in (None, "") else PESO_UNIDAD_RESPALDO
        if "SUPUESTO" in str(r.get("origen_dato") or "").upper():
            avisos.append(f"La huella de {p_} es un SUPUESTO, no un dato verificado")

    # --- Rotacion ---
    ROT = {}
    DESTINOS = []
    for r in filas("Rotacion", ["destino", "orden_descarga", "nota"]):
        d = str(r["destino"]).strip().upper()
        DESTINOS.append(d)
        ROT[d] = int(r["orden_descarga"])
        nota = str(r.get("nota") or "").strip()
        if nota:
            avisos.append(f"{d}: {nota}")

    # --- Viaje ---
    DEMANDA = {}
    for r in filas("Viaje", ["producto", "destino", "unidades"]):
        p_ = str(r["producto"]).strip()
        d = str(r["destino"]).strip().upper()
        u = int(r["unidades"])
        if u > 0:
            DEMANDA[(p_, d)] = DEMANDA.get((p_, d), 0) + u

    AREA = {
        (h, t): PISO[h][0] * PISO[h][1] * APROVECHAMIENTO
        for h in BODEGAS
        for t in PLANES
    }
    return avisos



def _ruta_con_respaldo(nombre):
    """
    Devuelve nombre (relativo al directorio de trabajo) si existe; si no, la
    misma ruta dentro de data/ de la raiz del proyecto.
    """
    ruta = Path(nombre)
    if ruta.exists():
        return ruta
    return _CARPETA_DATOS_PROYECTO / ruta.name


def cargar_capacidades(ruta=None):
    """
    Lee la tabla de capacidades generada por packer_2d.py.

    Devuelve True si se cargo, False si el archivo no existe. Sin la tabla el
    modelo sigue funcionando con la aproximacion por area, pero la capacidad de
    cada capa deja de estar respaldada por un calculo geometrico.
    """
    global CAPACIDAD
    ruta = Path(ruta) if ruta else _ruta_con_respaldo(ARCHIVO_CAPACIDADES)
    if not ruta.exists():
        return False

    CAPACIDAD = {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            CAPACIDAD[(int(r["bodega"]), r["producto"].strip())] = int(r["unidades_max"])
    return True


def cargar_capacidades_por_plan(ruta=None):
    """
    Lee la tabla de capacidades reales por plan (ver CAPACIDAD_POR_PLAN),
    generada por src/extraer_capacidades_reales.py a partir de las
    plantillas del puerto. Devuelve True si se cargo, False si el archivo no
    existe -- sin ella el modelo sigue funcionando igual, solo que con
    CAPACIDAD (un valor por bodega+producto para todos los planes).
    """
    global CAPACIDAD_POR_PLAN
    ruta = Path(ruta) if ruta else _ruta_con_respaldo(ARCHIVO_CAPACIDADES_POR_PLAN)
    if not ruta.exists():
        return False

    CAPACIDAD_POR_PLAN = {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            clave = (int(r["bodega"]), int(r["plan"]), r["producto"].strip())
            CAPACIDAD_POR_PLAN[clave] = int(r["unidades_max_real"])
    return True


def capacidad_unidades(h, p, t=None):
    """
    Unidades del producto p que caben en una capa de la bodega h.

    Si se da el plan t y hay un dato real verificado para esa combinacion
    exacta (bodega, plan, producto) en CAPACIDAD_POR_PLAN, se usa ese valor
    -- viene de las plantillas del puerto, mas preciso que el calculo
    geometrico porque refleja la geometria real de ESE plan, no un promedio.
    Si no, cae a CAPACIDAD (tabla del packer, mismo valor para todos los
    planes) y despues a la aproximacion por area.
    """
    if t is not None and CAPACIDAD_POR_PLAN:
        v = CAPACIDAD_POR_PLAN.get((h, t, p))
        if v is not None:
            return v
    if CAPACIDAD:
        v = CAPACIDAD.get((h, p))
        if v is not None:
            return v
    return AREA[(h, 1)] / HUELLA[p]


# =============================================================================
# 2. VERIFICACIONES PREVIAS
# =============================================================================
# La factibilidad del tonelaje es responsabilidad de la validacion de entrada,
# no del modelo: si la demanda no cabe, se rechaza antes de resolver.

def verificar_datos():
    """Comprueba que los datos de entrada sean coherentes antes de modelar."""
    errores = []

    for (p, d) in DEMANDA:
        if p not in PRODUCTOS:
            errores.append(f"Producto desconocido en la demanda: {p}")
        if d not in DESTINOS:
            errores.append(f"Destino fuera de la rotacion declarada: {d}")

    for p in PRODUCTOS:
        if p not in HUELLA:
            errores.append(f"Falta la huella del producto {p}")

    for d in DESTINOS:
        if d not in ROT:
            errores.append(f"Falta la posicion de rotacion del destino {d}")

    bodegas_cuadrillas = [h for hs in CUADRILLAS.values() for h in hs]
    if sorted(bodegas_cuadrillas) != sorted(BODEGAS):
        errores.append(
            "Las bodegas de las cuadrillas no coinciden con las bodegas activas"
        )

    # Factibilidad de area: la demanda total debe caber en el area total.
    area_necesaria = sum(
        q * HUELLA[p] for (p, d), q in DEMANDA.items()
    )
    area_disponible = sum(AREA.values())
    if area_necesaria > area_disponible:
        errores.append(
            f"La demanda requiere {area_necesaria:,.0f} m2 pero solo hay "
            f"{area_disponible:,.0f} m2 en las bodegas activas. "
            f"Reduce el tonelaje o activa mas bodegas."
        )

    return errores


# =============================================================================
# 3. CONSTRUCCION DEL MODELO
# =============================================================================

def construir_modelo():
    """Arma el modelo MILP y devuelve el problema y sus variables."""

    prob = pulp.LpProblem("prestow_kiwi_arrow", pulp.LpMinimize)

    combos = list(DEMANDA.keys())          # pares (producto, destino) con demanda

    # --- Variables de decision ---

    # x[h,t,p,d]: unidades del producto p con destino d en el plan t de la bodega h
    # La cota superior no es cosmetica: sin ella la relajacion lineal es mas
    # debil y el solver tarda mas en cerrar el gap. Una combinacion no puede
    # poner en una capa mas unidades de las que caben, ni mas de las que hay
    # que embarcar en total.
    x = {
        (h, t, p, d): pulp.LpVariable(
            f"x_{h}_{t}_{p}_{d}", lowBound=0, cat="Integer",
            upBound=min(capacidad_unidades(h, p, t), DEMANDA[(p, d)]),
        )
        for h in BODEGAS for t in PLANES for (p, d) in combos
    }

    # y[h,t,d]: 1 si el destino d ocupa el plan t de la bodega h
    y = {
        (h, t, d): pulp.LpVariable(f"y_{h}_{t}_{d}", cat="Binary")
        for h in BODEGAS for t in PLANES for d in DESTINOS
    }

    # w[h,t]: 1 si el plan t de la bodega h tiene alguna carga.
    # Es distinta de y: y marca que un destino esta presente, w marca que el
    # plan esta fisicamente ocupado. La contiguidad se escribe sobre w.
    w = {
        (h, t): pulp.LpVariable(f"w_{h}_{t}", cat="Binary")
        for h in BODEGAS for t in PLANES
    }

    # z[h,t]: izadas necesarias para el plan t de la bodega h
    z = {
        (h, t): pulp.LpVariable(f"z_{h}_{t}", lowBound=0, cat="Integer")
        for h in BODEGAS for t in PLANES
    }

    # T_max: makespan, las horas de la cuadrilla mas cargada
    T_max = pulp.LpVariable("T_max", lowBound=0, cat="Continuous")

    # v[h,d]: 1 si el destino d usa la bodega h. Sirve para medir fragmentacion:
    # cuantas bodegas distintas debe abrir cada destino en su puerto.
    v = {
        (h, d): pulp.LpVariable(f"v_{h}_{d}", cat="Binary")
        for h in BODEGAS for d in DESTINOS
    }

    # peso_max[k], peso_min[k]: bodega mas y menos cargada (en toneladas) en
    # la etapa k del viaje. k=0 es la carga inicial (nada descargado aun);
    # k=len(DESTINOS)-1 es el ultimo tramo, con solo la carga del ultimo
    # puerto a bordo. Solo se crean si USAR_BALANCE_PESO esta activo.
    peso_max: dict[int, "pulp.LpVariable"] = {}
    peso_min: dict[int, "pulp.LpVariable"] = {}
    if USAR_BALANCE_PESO:
        for k in range(_n_etapas_balance()):
            peso_max[k] = pulp.LpVariable(f"peso_max_{k}", lowBound=0, cat="Continuous")
            peso_min[k] = pulp.LpVariable(f"peso_min_{k}", lowBound=0, cat="Continuous")

    # --- Funcion objetivo ---
    # En la pasada 1 solo se minimiza el makespan. El objetivo secundario se
    # cambia despues, en fijar_makespan_y_cambiar_objetivo().
    prob += T_max, "minimizar_makespan"

    # --- Cotas para el enlace (restriccion 3) ---
    # Se usa la cota mas ajustada posible para apretar la relajacion lineal:
    # el minimo entre lo que cabe fisicamente y lo que hay que embarcar.
    # --- Cotas para el enlace (restriccion 3) ---
    # Se usa la cota mas ajustada posible para apretar la relajacion lineal.
    # Cuanto menor sea el big-M, mas fuerte es la restriccion cuando y es
    # fraccionario, y mejor la cota inferior que obtiene el solver.
    #
    # Tres cotas, se toma la menor:
    #   (a) lo que cabe fisicamente en esa capa segun el area
    #   (b) toda la demanda de esa combinacion producto-destino
    #   (c) lo que cabe en una capa considerando que el area es compartida:
    #       si otras combinaciones tambien deben ocupar espacio en el buque,
    #       ninguna sola puede llenar la capa entera salvo que su demanda lo
    #       permita. Se aproxima con el area de la capa menos el area minima
    #       que necesitan las demas combinaciones que solo caben ahi. Como esa
    #       cuenta es cara, se usa la version simple: (a) y (b).
    #
    # Cota adicional efectiva: una combinacion no puede ocupar mas unidades en
    # una capa que las que caben tras descontar la unidad minima de las demas
    # combinaciones que deben repartirse en el buque. Se omite por costo.
    M = {
        (h, t, p, d): min(
            capacidad_unidades(h, p, t),      # (a) limite fisico de la capa
            DEMANDA[(p, d)],                 # (b) limite de demanda
        )
        for h in BODEGAS for t in PLANES for (p, d) in combos
    }

    # --- (1) Cobertura ---
    # Todo lo que hay que embarcar se embarca, exactamente.
    for (p, d) in combos:
        prob += (
            pulp.lpSum(x[(h, t, p, d)] for h in BODEGAS for t in PLANES)
            == DEMANDA[(p, d)],
            f"cobertura_{p}_{d}",
        )

    # --- (2) Capacidad de la capa ---
    # Cada producto ocupa una fraccion de la capa igual a las unidades puestas
    # divididas por las que caben si la capa fuera solo de ese producto. La
    # suma de fracciones no puede pasar de 1.
    #
    # Con la tabla del packer, "las que caben" viene del calculo geometrico
    # real. Sin ella, se aproxima por area, que ignora la forma de las piezas.
    #
    # SIMPLIFICACION: en capas mixtas esto sigue siendo una aproximacion. Dos
    # productos con patrones distintos no comparten el piso tan limpiamente
    # como sugiere la suma de fracciones. Son 5 de 85 capas en el caso base.
    for h in BODEGAS:
        for t in PLANES:
            prob += (
                pulp.lpSum(
                    x[(h, t, p, d)] / capacidad_unidades(h, p, t)
                    for (p, d) in combos
                ) <= 1,
                f"capacidad_{h}_{t}",
            )

    # --- (3) Enlace entre x e y ---
    # Si hay carga de un destino en un plan, la binaria correspondiente se activa.
    for h in BODEGAS:
        for t in PLANES:
            for (p, d) in combos:
                prob += (
                    x[(h, t, p, d)] <= M[(h, t, p, d)] * y[(h, t, d)],
                    f"enlace_{h}_{t}_{p}_{d}",
                )

    # --- (4) No-overstowage ---
    # Lo que se descarga primero queda arriba. Prohibe que un destino de
    # rotacion posterior quede por encima de uno anterior.
    # SUPUESTO: dentro de una misma capa no hay bloqueo entre destinos.
    #
    # Solo se impone entre planes ADYACENTES, no entre todos los pares. Es
    # equivalente, y reduce las restricciones de ~2.200 a ~400.
    #
    # DEMOSTRACION. Que el par (t, t+1) no viole significa que para todo d en t
    # y d' en t+1 se cumple rot[d'] <= rot[d], o sea max(rot en t+1) <= min(rot
    # en t). Aplicando lo mismo a (t+1, t+2) y encadenando:
    #     max(rot en t+2) <= min(rot en t+1) <= max(rot en t+1) <= min(rot en t)
    # luego para todo d en t y d' en t+2 se cumple rot[d'] <= rot[d]: no viola.
    # Por induccion se extiende a cualquier t' > t.
    #
    # La condicion que lo hace valido es la CONTIGUIDAD (restriccion 5): si
    # hubiera capas vacias intermedias la cadena se romperia. Si alguna vez se
    # elimina la contiguidad, hay que volver a la formulacion sobre todos los
    # pares.
    #
    # Verificado ademas empiricamente: 0 discrepancias en 211.000 configuraciones
    # de 3, 4 y 5 capas con hasta 3 destinos por capa.
    for h in BODEGAS:
        for t in PLANES[:-1]:
            for d in DESTINOS:
                for d2 in DESTINOS:
                    if ROT[d2] > ROT[d]:
                        prob += (
                            y[(h, t, d)] + y[(h, t + 1, d2)] <= 1,
                            f"overstow_{h}_{t}_{d}_{d2}",
                        )

    # --- (5) Ocupacion y contiguidad ---
    # La carga se apila desde el fondo: no puede haber capas flotando sobre
    # un plan vacio.
    #
    # OJO: la contiguidad NO se puede escribir sobre y. La restriccion (3) solo
    # obliga a que y=1 cuando hay carga, pero no impide que y=1 sin carga. El
    # solver aprovecharia ese hueco activando y en planes vacios para satisfacer
    # la contiguidad formalmente, dejando carga flotando. Por eso hace falta w,
    # con la implicacion en los dos sentidos.
    cap_unidades = {
        (h, t): AREA[(h, t)] / min(HUELLA.values())
        for h in BODEGAS for t in PLANES
    }

    for h in BODEGAS:
        for t in PLANES:
            carga = pulp.lpSum(x[(h, t, p, d)] for (p, d) in combos)
            # (5a) si hay carga, w se activa
            prob += (carga >= w[(h, t)], f"ocupacion_min_{h}_{t}")
            # (5b) si no hay carga, w queda en cero
            prob += (
                carga <= cap_unidades[(h, t)] * w[(h, t)],
                f"ocupacion_max_{h}_{t}",
            )

    for h in BODEGAS:
        for t in PLANES[:-1]:
            # (5c) un plan solo se ocupa si el de abajo tambien lo esta
            prob += (w[(h, t + 1)] <= w[(h, t)], f"contiguidad_{h}_{t}")

    # --- (5d) Llenado minimo antes de abrir la capa siguiente ---
    # La contiguidad por si sola permite algo fisicamente absurdo: poner UNA
    # unidad en un plan y con eso habilitar el plan de arriba. Ademas de ser
    # irreal, desperdicia una izada completa (el ciclo de grua tarda lo mismo
    # trayendo 1 unidad que 16).
    #
    # Esta restriccion exige que una capa este llena al menos en un FRACCION_
    # MINIMA de su area antes de poder abrir la de encima. La ultima capa
    # ocupada de cada bodega queda exenta, que es donde naturalmente queda el
    # remanente.
    if FRACCION_MINIMA_CAPA > 0:
        for h in BODEGAS:
            for t in PLANES[:-1]:
                fraccion_ocupada = pulp.lpSum(
                    x[(h, t, p, d)] / capacidad_unidades(h, p, t)
                    for (p, d) in combos
                )
                prob += (
                    fraccion_ocupada >= FRACCION_MINIMA_CAPA * w[(h, t + 1)],
                    f"llenado_minimo_{h}_{t}",
                )

    # --- (6) Izadas ---
    # Cada izada mueve hasta 16 unidades. El solver minimiza z por si mismo,
    # porque z entra en el makespan: no hace falta forzar el techo exacto.
    for h in BODEGAS:
        for t in PLANES:
            prob += (
                UNIDADES_POR_IZADA * z[(h, t)]
                >= pulp.lpSum(x[(h, t, p, d)] for (p, d) in combos),
                f"izadas_{h}_{t}",
            )

    # --- (7) Makespan ---
    # El buque zarpa cuando termina la ultima cuadrilla, no la primera.
    for g, bodegas_g in CUADRILLAS.items():
        prob += (
            T_max
            >= pulp.lpSum(
                z[(h, t)] * tiempo_ciclo(h) for h in bodegas_g for t in PLANES
            ),
            f"makespan_cuadrilla_{g}",
        )

    # --- (8) Enlace de fragmentacion ---
    # v[h,d] se activa si el destino d tiene carga en la bodega h.
    # Solo hace falta la implicacion en un sentido: el objetivo empuja v hacia
    # abajo, asi que el solver no la activara sin necesidad.
    # Enlace de v, que mide en cuantas bodegas distintas queda cada destino.
    if USAR_FRAGMENTACION:
        for h in BODEGAS:
            for d in DESTINOS:
                prob += (
                    pulp.lpSum(
                        y[(h, t, d)] for t in PLANES
                    ) <= len(PLANES) * v[(h, d)],
                    f"fragmentacion_{h}_{d}",
                )

    # --- (9) Ruptura de simetria ---
    # Dentro de cada cuadrilla, si dos bodegas tienen la misma geometria son
    # intercambiables: cualquier solucion tiene un gemelo con el contenido
    # permutado y el mismo makespan. El solver exploraria ambos sin saberlo.
    # Se impone un orden arbitrario para que solo explore uno.
    #
    # OJO: solo es valido si las bodegas son realmente intercambiables. Si el
    # armador fijara tonelaje por bodega, o si hubiera restricciones de trim,
    # dejarian de serlo y esta restriccion cortaria soluciones validas.
    #
    # Con USAR_BALANCE_PESO activo, esa restriccion es exactamente una
    # restriccion de trim, y forzar "h1 carga al menos tanto como h2" le
    # impediria al modelo balancear peso ENTRE las dos bodegas gemelas — pero
    # SOLO en la pasada 3: en las pasadas 1 y 2 (makespan, izadas,
    # fragmentacion) la simetria no molesta y ayuda mucho al solver a
    # encontrar factibilidad rapido. Se deja activa aca y preparar_pasada3()
    # la retira del problema justo antes de resolver esa pasada.
    if ROMPER_SIMETRIA:
        for g, bodegas_g in CUADRILLAS.items():
            for i in range(len(bodegas_g) - 1):
                h1, h2 = bodegas_g[i], bodegas_g[i + 1]
                if PISO[h1] != PISO[h2]:
                    continue          # geometrias distintas: no son intercambiables
                prob += (
                    pulp.lpSum(x[(h1, t, p, d)] for t in PLANES for (p, d) in combos)
                    >= pulp.lpSum(x[(h2, t, p, d)] for t in PLANES for (p, d) in combos),
                    f"simetria_{h1}_{h2}",
                )

    # --- (10) Balance de peso por etapa del viaje (opcional) ---
    # peso_restante[h,k]: toneladas que quedan en la bodega h en la etapa k,
    # es decir la carga de los destinos que ROT ubica despues de la etapa k
    # (todavia no descargados). Ver USAR_BALANCE_PESO mas arriba.
    if USAR_BALANCE_PESO:
        for k in range(_n_etapas_balance()):
            for h in BODEGAS:
                peso_restante_hk = pulp.lpSum(
                    x[(h, t, p, d)] * PESO.get(p, PESO_UNIDAD_RESPALDO)
                    for t in PLANES
                    for (p, d) in combos
                    if ROT[d] > k
                )
                prob += (peso_max[k] >= peso_restante_hk, f"balance_max_{h}_{k}")
                prob += (peso_min[k] <= peso_restante_hk, f"balance_min_{h}_{k}")

    return prob, x, y, z, w, v, T_max, combos, peso_max, peso_min


# =============================================================================
# 4. RESOLUCION EN DOS PASADAS
# =============================================================================

def _crear_solver(limite):
    """
    Devuelve el solver configurado. Cae a CBC si HiGHS no esta instalado.
    """
    if SOLVER.upper() == "HIGHS":
        try:
            return pulp.HiGHS(timeLimit=limite, msg=True)
        except Exception:
            print("  AVISO: HiGHS no disponible, se usa CBC. "
                  "Instalar con: pip install highspy")
    return pulp.PULP_CBC_CMD(timeLimit=limite, msg=1)


def resolver_highs_con_punto_inicial(prob, solver, valores):
    """
    Resuelve prob con HiGHS partiendo de una solucion conocida (MIP start).

    valores: dict nombre_variable -> valor, mismo formato que
    capturar_solucion(). Tiene que ser una solucion factible del modelo
    actual (por ejemplo, la de la pasada anterior).

    POR QUE HACE FALTA: pulp.HiGHS.actualSolve() siempre reconstruye el modelo
    desde cero y no acepta un punto inicial. Sin punto de partida, HiGHS puede
    tardar mas de 120 s solo en encontrar la primera solucion entera factible
    de este modelo, y en la pasada 3 no la encuentra ni en 900 s. Se reproduce
    a mano la secuencia interna de actualSolve() (createAndConfigureSolver ->
    buildSolverModel -> callSolver -> findSolutionValues) para inyectar la
    solucion justo despues de que buildSolverModel asigna var.index, que es el
    orden de columnas que espera HiGHS.

    SOLO sirve con pulp.HiGHS (usa metodos internos que CBC no tiene). No
    captura la salida: quien llama decide si redirigir stdout para leer el log.
    """
    import highspy

    solver.createAndConfigureSolver(prob)
    solver.buildSolverModel(prob)

    sol = highspy.HighsSolution()
    sol.value_valid = True
    col_values = [0.0] * len(prob.variables())
    for var in prob.variables():
        col_values[var.index] = valores.get(var.name) or 0.0
    sol.col_value = col_values
    prob.solverModel.setSolution(sol)

    solver.callSolver(prob)
    status, sol_status = solver.findSolutionValues(prob)
    prob.assignStatus(status, sol_status)


def resolver(prob, limite=LIMITE_SEGUNDOS, mostrar_log=False, solucion_inicial=None):
    """
    Resuelve el modelo con limite de tiempo.

    Devuelve un diccionario con el estado reportado por PuLP y, sobre todo, con
    lo que CBC realmente dijo en su log.

    POR QUE NO BASTA EL ESTADO DE PuLP: se verifico empiricamente que PuLP
    reporta "Optimal" en corridas que NO alcanzaron el optimo. Tres corridas del
    mismo modelo con limites de 300, 600 y 1000 segundos reportaron las tres
    "Optimal", pero la de 300 s devolvio 57,00 h y las otras dos 56,88 h. Si el
    optimo estuviera probado, el valor no podria depender del tiempo disponible.
    Por eso se lee el log de CBC directamente.

    solucion_inicial: si se entrega (dict nombre_variable -> valor) y el
    solver es HiGHS, se usa como punto de partida -- ver
    resolver_highs_con_punto_inicial. Con CBC se ignora.
    """
    buffer = io.StringIO()
    solver = _crear_solver(limite)
    with contextlib.redirect_stdout(buffer):
        if solucion_inicial is not None and isinstance(solver, pulp.HiGHS):
            resolver_highs_con_punto_inicial(prob, solver, solucion_inicial)
        else:
            prob.solve(solver)
    log = buffer.getvalue()

    if mostrar_log:
        print(log)

    return diagnosticar_resolucion(prob, solver, log)


def diagnosticar_resolucion(prob, solver, log):
    """
    Arma el diccionario de resultado de una resolucion: estado de PuLP, si se
    probo el optimo, si corto por tiempo y el gap final (en %).

    Con HiGHS, el estado y el gap se leen DIRECTO del objeto highspy
    (prob.solverModel), no del log: HiGHS escribe su log desde C, por fuera
    de sys.stdout, asi que contextlib.redirect_stdout no lo captura y el log
    llega vacio. Hasta el 24-sep-2026 eso dejaba el gap siempre en None y
    optimo_probado siempre en False (se buscaban ademas textos propios de
    CBC), y la web mostraba "gap no disponible". Con CBC se sigue leyendo el
    log, que si se captura.
    """
    resultado = {
        "estado_pulp": pulp.LpStatus[prob.status],
        "optimo_probado": "Result - Optimal solution found" in log,
        "corto_por_tiempo": "Stopped on time limit" in log,
        "gap": _leer_gap(log),
        "log": log,
    }
    modelo = getattr(prob, "solverModel", None)
    if isinstance(solver, pulp.HiGHS) and modelo is not None:
        try:
            import highspy
            estado = modelo.getModelStatus()
            gap = modelo.getInfo().mip_gap
        except Exception:
            return resultado
        resultado["optimo_probado"] = estado == highspy.HighsModelStatus.kOptimal
        resultado["corto_por_tiempo"] = estado == highspy.HighsModelStatus.kTimeLimit
        # mip_gap es una fraccion; infinito si no hay solucion factible
        resultado["gap"] = gap * 100 if gap is not None and gap < float("inf") else None
    return resultado


def _leer_gap(log):
    """
    Extrae el gap final del log de CBC, en porcentaje.

    CBC lo reporta en lineas del tipo:
      Cbc0010I After N nodes, ... best solution, best possible X (Y seconds)
    o al cerrar:
      Gap:  0.05
    Devuelve None si no se pudo determinar.
    """
    mejor_solucion = None
    mejor_cota = None

    for linea in log.splitlines():
        # Formato de HiGHS: "Gap               1.23%" o "Gap  ...  1.23%"
        m = re.search(r"Gap\s+.*?([\d.]+)%", linea)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

        m = re.search(r"best objective ([\d.eE+-]+), best possible ([\d.eE+-]+)", linea)
        if m:
            try:
                mejor_solucion = float(m.group(1))
                mejor_cota = float(m.group(2))
            except ValueError:
                pass
        m = re.search(r"Gap:\s+([\d.eE+-]+)", linea)
        if m:
            try:
                return float(m.group(1)) * 100
            except ValueError:
                pass

    if mejor_solucion is not None and mejor_cota is not None:
        if abs(mejor_solucion) > 1e-9:
            return abs(mejor_solucion - mejor_cota) / abs(mejor_solucion) * 100
        return 0.0
    return None


def describir_resolucion(res, etiqueta):
    """Imprime lo que realmente hizo el solver, sin confiar en el estado de PuLP."""
    if res["optimo_probado"]:
        print(f"  {etiqueta}: optimo probado por CBC")
    elif res["corto_por_tiempo"]:
        gap = res["gap"]
        detalle = f", gap {gap:.2f}%" if gap is not None else ", gap desconocido"
        print(f"  {etiqueta}: ATENCION - se corto por limite de tiempo{detalle}")
        print(f"           El resultado NO es optimo probado.")
    else:
        print(f"  {etiqueta}: estado PuLP = {res['estado_pulp']} "
              f"(CBC no confirmo optimalidad)")


def capturar_solucion(prob):
    """
    Guarda el valor de todas las variables.

    Hace falta porque la pasada 2 reutiliza el mismo objeto del problema: si no
    encuentra solucion factible dentro de su limite de tiempo, PuLP deja las
    variables en None y se pierde la solucion que la pasada 1 si habia
    encontrado.
    """
    return {v.name: v.value() for v in prob.variables()}


def restaurar_solucion(prob, guardada):
    """Devuelve las variables a los valores capturados antes."""
    for v in prob.variables():
        if v.name in guardada:
            v.varValue = guardada[v.name]


def preparar_pasada2(prob, z, w, v, T_max, makespan_optimo):
    """
    Prepara la segunda pasada de la optimizacion lexicografica.

    Fija el makespan en su valor optimo (mas la tolerancia declarada) y cambia
    el objetivo por los terminos secundarios. El makespan deja de ser objetivo
    y pasa a ser restriccion.
    """
    # Tolerancia ABSOLUTA: se permite empeorar el makespan en como maximo
    # TOLERANCIA_IZADAS izadas. Asi el margen no depende de cuanto logro la
    # pasada 1, que es lo que hacia impredecible el resultado con tolerancia
    # relativa.
    cota = makespan_optimo + TOLERANCIA_IZADAS * TIEMPO_CICLO
    prob += (T_max <= cota, "makespan_fijado")

    terminos = []
    if USAR_IZADAS:
        terminos.append(PESO_IZADAS * pulp.lpSum(
            z[(h, t)] for h in BODEGAS for t in PLANES
        ))
    if USAR_FRAGMENTACION:
        terminos.append(PESO_FRAGMENTACION * pulp.lpSum(
            v[(h, d)] for h in BODEGAS for d in DESTINOS
        ))
    if USAR_PLANES:
        terminos.append(PESO_PLANES * pulp.lpSum(
            w[(h, t)] for h in BODEGAS for t in PLANES
        ))

    if not terminos:
        return False              # no hay nada secundario que optimizar

    prob.setObjective(pulp.lpSum(terminos))
    return True


def preparar_pasada3(prob, z, w, v, peso_max, peso_min, valor_pasada2):
    """
    Prepara la tercera pasada de la optimizacion lexicografica: balance de
    peso por etapa del viaje (ver USAR_BALANCE_PESO).

    Fija el objetivo de la pasada 2 (izadas + fragmentacion ponderadas) en su
    valor optimo mas una tolerancia absoluta, y cambia el objetivo a
    minimizar el desbalance de peso. El makespan sigue fijado desde la
    pasada 2 (esa restriccion no se toca aca).

    Tambien retira del problema la restriccion (9) de ruptura de simetria
    (ver su comentario "OJO" en construir_modelo): esa restriccion ayuda al
    solver en las pasadas 1 y 2, pero en esta pasada le impediria balancear
    peso entre bodegas gemelas.

    Devuelve False si USAR_BALANCE_PESO esta apagado, o si construir_modelo()
    no armo peso_max/peso_min (mismo flag).
    """
    if not USAR_BALANCE_PESO or not peso_max:
        return False

    if ROMPER_SIMETRIA:
        for bodegas_g in CUADRILLAS.values():
            for i in range(len(bodegas_g) - 1):
                h1, h2 = bodegas_g[i], bodegas_g[i + 1]
                nombre = f"simetria_{h1}_{h2}"
                if nombre in prob.constraints:
                    del prob.constraints[nombre]

    terminos_pasada2 = []
    if USAR_IZADAS:
        terminos_pasada2.append(PESO_IZADAS * pulp.lpSum(
            z[(h, t)] for h in BODEGAS for t in PLANES
        ))
    if USAR_FRAGMENTACION:
        terminos_pasada2.append(PESO_FRAGMENTACION * pulp.lpSum(
            v[(h, d)] for h in BODEGAS for d in DESTINOS
        ))
    if USAR_PLANES:
        terminos_pasada2.append(PESO_PLANES * pulp.lpSum(
            w[(h, t)] for h in BODEGAS for t in PLANES
        ))

    if terminos_pasada2:
        prob += (
            pulp.lpSum(terminos_pasada2) <= valor_pasada2 + TOLERANCIA_PASADA3,
            "secundario_fijado",
        )

    prob.setObjective(
        PESO_BALANCE * pulp.lpSum(peso_max[k] - peso_min[k] for k in peso_max)
    )
    return True


# =============================================================================
# 5. EXTRACCION Y VERIFICACION DE RESULTADOS
# =============================================================================

def extraer_plan(x, z, combos):
    """Devuelve el plan de estiba como lista de filas."""
    filas = []
    for h in BODEGAS:
        for t in PLANES:
            for (p, d) in combos:
                v = x[(h, t, p, d)].value()
                if v and v > 0.5:
                    filas.append({
                        "bodega": h,
                        "plan": t,
                        "producto": p,
                        "destino": d,
                        "unidades": int(round(v)),
                    })
    return filas


def horas_por_cuadrilla(z):
    """Calcula las horas de cada cuadrilla a partir de las izadas."""
    horas = {}
    for g, bodegas_g in CUADRILLAS.items():
        horas[g] = sum(
            (z[(h, t)].value() or 0) * tiempo_ciclo(h)
            for h in bodegas_g for t in PLANES
        )
    return horas


def verificar_no_overstowage(filas):
    """
    Verifica que ningun destino de rotacion posterior quede sobre uno anterior.
    Devuelve la lista de violaciones. Sobre una solucion valida debe venir vacia.
    """
    violaciones = []
    por_bodega = defaultdict(lambda: defaultdict(set))
    for f in filas:
        por_bodega[f["bodega"]][f["plan"]].add(f["destino"])

    for h, planes in por_bodega.items():
        for t in sorted(planes):
            for t2 in sorted(planes):
                if t2 <= t:
                    continue
                for d in planes[t]:
                    for d2 in planes[t2]:
                        if ROT[d2] > ROT[d]:
                            violaciones.append((h, t, d, t2, d2))
    return violaciones


def verificar_cobertura(filas):
    """Verifica que se haya embarcado exactamente la demanda."""
    cargado = defaultdict(int)
    for f in filas:
        cargado[(f["producto"], f["destino"])] += f["unidades"]
    faltantes = []
    for (p, d), q in DEMANDA.items():
        if cargado[(p, d)] != q:
            faltantes.append((p, d, q, cargado[(p, d)]))
    return faltantes


def verificar_contiguidad(filas):
    """Verifica que no haya planes ocupados con el plan de abajo vacio."""
    ocupados = defaultdict(set)
    for f in filas:
        ocupados[f["bodega"]].add(f["plan"])
    huecos = []
    for h, planes in ocupados.items():
        if not planes:
            continue
        for t in range(1, max(planes) + 1):
            if t not in planes:
                huecos.append((h, t))
    return huecos


def verificar_capacidad(filas):
    """Verifica que ninguna capa exceda su capacidad."""
    fraccion = defaultdict(float)
    for f in filas:
        fraccion[(f["bodega"], f["plan"])] += (
            f["unidades"] / capacidad_unidades(f["bodega"], f["producto"], f["plan"])
        )
    excesos = []
    for (h, t), fr in fraccion.items():
        if fr > 1 + 1e-6:
            excesos.append((h, t, round(fr * 100, 1)))
    return excesos


# =============================================================================
# 6. INFORME DE RESULTADOS
# =============================================================================

def informar(res, prob, x, y, z, T_max, combos):
    print("=" * 72)
    print("RESULTADO")
    print("=" * 72)

    # No se reporta "Optimal" a secas: se dice lo que CBC realmente confirmo.
    if res["optimo_probado"]:
        print("Estado del solver : optimo probado por CBC")
    else:
        gap = res["gap"]
        detalle = f"gap {gap:.2f}%" if gap is not None else "gap desconocido"
        print(f"Estado del solver : SIN optimalidad probada ({detalle})")

    if T_max.value() is None or T_max.value() <= 0:
        print("\nNo se encontro ninguna solucion factible.")
        print("Posibles causas:")
        print("  - el limite de tiempo fue insuficiente: subir --limite")
        print("  - los datos de entrada no admiten solucion: revisar capacidades")
        return

    filas = extraer_plan(x, z, combos)
    horas = horas_por_cuadrilla(z)
    izadas_total = sum((z[(h, t)].value() or 0) for h in BODEGAS for t in PLANES)
    unidades_total = sum(f["unidades"] for f in filas)

    print(f"Makespan          : {T_max.value():.2f} h")
    print(f"Izadas totales    : {int(izadas_total):,}")
    print(f"Unidades ubicadas : {unidades_total:,}")

    print("\nHoras por cuadrilla")
    for g in sorted(horas):
        bodegas = "+".join(str(h) for h in CUADRILLAS[g])
        marca = "  <- determina el makespan" if abs(horas[g] - T_max.value()) < 1e-4 else ""
        print(f"  Cuadrilla {g} (bodegas {bodegas}): {horas[g]:6.2f} h{marca}")

    prom = sum(horas.values()) / len(horas) if horas else 0
    if prom > 0:
        desbalance = (max(horas.values()) - min(horas.values())) / prom * 100
        print(f"\nDesbalance entre cuadrillas: {desbalance:.1f}%")

    print("\nUnidades por bodega")
    por_bodega = defaultdict(int)
    for f in filas:
        por_bodega[f["bodega"]] += f["unidades"]
    for h in BODEGAS:
        print(f"  Bodega {h}: {por_bodega[h]:6,} unidades")

    print("\nFragmentacion: bodegas distintas que debe abrir cada destino")
    frag = defaultdict(set)
    for f in filas:
        frag[f["destino"]].add(f["bodega"])
    for d in DESTINOS:
        if frag[d]:
            print(f"  {d:10}: {len(frag[d])} bodegas  {sorted(frag[d])}")

    print("\n" + "-" * 72)
    print("VERIFICACIONES DE COHERENCIA")
    print("-" * 72)

    pruebas = [
        ("No-overstowage", verificar_no_overstowage(filas)),
        ("Cobertura de la demanda", verificar_cobertura(filas)),
        ("Contiguidad de las capas", verificar_contiguidad(filas)),
        ("Capacidad por area", verificar_capacidad(filas)),
    ]
    for nombre, fallas in pruebas:
        if fallas:
            print(f"  FALLA  {nombre}: {len(fallas)} problemas")
            for f in fallas[:5]:
                print(f"           {f}")
        else:
            print(f"  OK     {nombre}")




# =============================================================================
# 7. EXPORTACION A EXCEL CON FORMATO DE PRESTOW
# =============================================================================
# Genera un archivo que imita la estructura visual del prestow del puerto:
# una columna por bodega, una fila por plan, con la carga de cada capa dentro
# de la celda. El color de fondo distingue el destino; el texto nombra el
# producto y las unidades.

# Un color por destino, para que el orden vertical se lea de un vistazo.
COLOR_DESTINO = {
    "TAICHUNG": "C6E0B4",   # verde
    "QINGDAO":  "BDD7EE",   # azul
    "KUNSAN":   "FFE699",   # ambar
    "ULSAN":    "F8CBAD",   # naranjo
}
COLOR_VACIO = "F2F2F2"
COLOR_ENCABEZADO = "44546A"


def exportar_excel(filas, horas, T_max_valor, ruta="plan_estiba.xlsx"):
    """
    Escribe el plan de estiba en un Excel con el formato visual del prestow.

    Hoja 1 "Plan de estiba": vista bodega x plan, coloreada por destino.
    Hoja 2 "Detalle": una fila por asignacion, para filtrar y analizar.
    Hoja 3 "Indicadores": los KPIs de la corrida.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    FUENTE = "Arial"
    fino = Side(style="thin", color="BFBFBF")
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)

    # Indexar las filas por bodega y plan
    celdas = defaultdict(list)
    for f in filas:
        celdas[(f["bodega"], f["plan"])].append(f)

    wb = Workbook()

    # ---------------------------------------------------------------- HOJA 1
    ws = wb.active
    ws.title = "Plan de estiba"

    ws["A1"] = "Plan de estiba generado por el modelo"
    ws["A1"].font = Font(name=FUENTE, size=14, bold=True)
    ws["A2"] = (f"Makespan {T_max_valor:.2f} h  ·  "
                f"{sum(f['unidades'] for f in filas):,} unidades  ·  "
                f"buque Kiwi Arrow")
    ws["A2"].font = Font(name=FUENTE, size=10, italic=True, color="595959")

    FILA_ENC = 4
    ws.cell(row=FILA_ENC, column=1, value="Plan")
    for j, h in enumerate(sorted(BODEGAS, reverse=True), start=2):
        ws.cell(row=FILA_ENC, column=j, value=f"Bodega {h}")
    for j in range(1, len(BODEGAS) + 2):
        c = ws.cell(row=FILA_ENC, column=j)
        c.font = Font(name=FUENTE, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=COLOR_ENCABEZADO)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = borde

    # Los planes se dibujan de arriba hacia abajo: el 11 arriba, el 1 al fondo,
    # igual que en el prestow del puerto y que en la bodega real.
    for i, t in enumerate(sorted(PLANES, reverse=True)):
        fila = FILA_ENC + 1 + i
        c = ws.cell(row=fila, column=1, value=t)
        c.font = Font(name=FUENTE, size=10, bold=True)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = borde

        for j, h in enumerate(sorted(BODEGAS, reverse=True), start=2):
            cel = ws.cell(row=fila, column=j)
            cel.border = borde
            cel.alignment = Alignment(horizontal="center", vertical="center",
                                      wrap_text=True)
            cel.font = Font(name=FUENTE, size=8.5)

            contenido = celdas.get((h, t), [])
            if not contenido:
                cel.fill = PatternFill("solid", fgColor=COLOR_VACIO)
                continue

            texto = "\n".join(
                f"{x['destino']}\n{x['producto']} · {x['unidades']:,} u"
                for x in contenido
            )
            cel.value = texto
            # Si la capa es mixta se colorea por el destino que se descarga
            # primero, que es el que manda para el orden vertical.
            dest = min((x["destino"] for x in contenido), key=lambda d: ROT[d])
            cel.fill = PatternFill("solid", fgColor=COLOR_DESTINO.get(dest, COLOR_VACIO))
            if len(contenido) > 1:
                cel.font = Font(name=FUENTE, size=8.5, bold=True)

    ws.column_dimensions["A"].width = 6
    for j in range(2, len(BODEGAS) + 2):
        ws.column_dimensions[get_column_letter(j)].width = 22
    for i in range(len(PLANES)):
        ws.row_dimensions[FILA_ENC + 1 + i].height = 42

    # Leyenda
    fila_leyenda = FILA_ENC + len(PLANES) + 2
    ws.cell(row=fila_leyenda, column=1, value="Leyenda").font = Font(
        name=FUENTE, size=10, bold=True)
    for k, d in enumerate(sorted(DESTINOS, key=lambda x: ROT[x])):
        c = ws.cell(row=fila_leyenda + 1 + k, column=1)
        c.fill = PatternFill("solid", fgColor=COLOR_DESTINO.get(d, COLOR_VACIO))
        c.border = borde
        ws.cell(row=fila_leyenda + 1 + k, column=2,
                value=f"{d}  (posicion {ROT[d]} en la rotacion)").font = Font(
                    name=FUENTE, size=9)
    fin_leyenda = fila_leyenda + len(DESTINOS) + 2
    ws.cell(row=fin_leyenda, column=1,
            value="Las capas en negrita contienen mas de un destino. El color "
                  "corresponde al destino que se descarga primero.").font = Font(
                      name=FUENTE, size=9, italic=True, color="595959")
    ws.cell(row=fin_leyenda + 1, column=1,
            value="El plan 1 va al fondo de la bodega y el 11 arriba, igual que "
                  "en la estiba real.").font = Font(
                      name=FUENTE, size=9, italic=True, color="595959")

    ws.freeze_panes = "B5"

    # ---------------------------------------------------------------- HOJA 2
    ws2 = wb.create_sheet("Detalle")
    encabezados = ["Bodega", "Plan", "Producto", "Destino", "Unidades",
                   "Rotacion", "Area ocupada (m2)"]
    for j, hh in enumerate(encabezados, start=1):
        c = ws2.cell(row=1, column=j, value=hh)
        c.font = Font(name=FUENTE, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=COLOR_ENCABEZADO)
        c.border = borde

    orden = sorted(filas, key=lambda f: (-f["bodega"], -f["plan"]))
    for i, f in enumerate(orden, start=2):
        valores = [f["bodega"], f["plan"], f["producto"], f["destino"],
                   f["unidades"], ROT[f["destino"]],
                   round(f["unidades"] * HUELLA[f["producto"]], 2)]
        for j, v in enumerate(valores, start=1):
            c = ws2.cell(row=i, column=j, value=v)
            c.font = Font(name=FUENTE, size=10)
            c.border = borde
        ws2.cell(row=i, column=4).fill = PatternFill(
            "solid", fgColor=COLOR_DESTINO.get(f["destino"], COLOR_VACIO))

    for j, ancho in enumerate([9, 7, 16, 13, 11, 10, 17], start=1):
        ws2.column_dimensions[get_column_letter(j)].width = ancho
    ws2.freeze_panes = "A2"
    ws2.auto_filter.ref = f"A1:G{len(orden) + 1}"

    # ---------------------------------------------------------------- HOJA 3
    ws3 = wb.create_sheet("Indicadores")
    ws3["A1"] = "Indicadores de la corrida"
    ws3["A1"].font = Font(name=FUENTE, size=13, bold=True)

    frag = defaultdict(set)
    por_bodega = defaultdict(int)
    for f in filas:
        frag[f["destino"]].add(f["bodega"])
        por_bodega[f["bodega"]] += f["unidades"]

    prom = sum(horas.values()) / len(horas) if horas else 0
    desbalance = ((max(horas.values()) - min(horas.values())) / prom * 100
                  if prom > 0 else 0)

    fila = 3
    bloques = [
        ("Makespan (h)", round(T_max_valor, 2)),
        ("Desbalance entre cuadrillas (%)", round(desbalance, 1)),
        ("Unidades totales", sum(f["unidades"] for f in filas)),
        ("Fragmentacion total (bodegas-destino)", sum(len(v) for v in frag.values())),
    ]
    for etiqueta, valor in bloques:
        ws3.cell(row=fila, column=1, value=etiqueta).font = Font(
            name=FUENTE, size=10, bold=True)
        ws3.cell(row=fila, column=2, value=valor).font = Font(name=FUENTE, size=10)
        fila += 1

    fila += 1
    ws3.cell(row=fila, column=1, value="Horas por cuadrilla").font = Font(
        name=FUENTE, size=11, bold=True)
    fila += 1
    for g in sorted(horas):
        bodegas_txt = " + ".join(str(h) for h in CUADRILLAS[g])
        ws3.cell(row=fila, column=1,
                 value=f"Cuadrilla {g} (bodegas {bodegas_txt})").font = Font(
                     name=FUENTE, size=10)
        c = ws3.cell(row=fila, column=2, value=round(horas[g], 2))
        c.font = Font(name=FUENTE, size=10,
                      bold=abs(horas[g] - T_max_valor) < 1e-4)
        fila += 1

    fila += 1
    ws3.cell(row=fila, column=1, value="Fragmentacion por destino").font = Font(
        name=FUENTE, size=11, bold=True)
    fila += 1
    for d in sorted(DESTINOS, key=lambda x: ROT[x]):
        if not frag[d]:
            continue
        ws3.cell(row=fila, column=1, value=d).font = Font(name=FUENTE, size=10)
        ws3.cell(row=fila, column=1).fill = PatternFill(
            "solid", fgColor=COLOR_DESTINO.get(d, COLOR_VACIO))
        ws3.cell(row=fila, column=2, value=len(frag[d])).font = Font(
            name=FUENTE, size=10)
        ws3.cell(row=fila, column=3,
                 value="bodegas " + ", ".join(str(b) for b in sorted(frag[d]))).font = Font(
                     name=FUENTE, size=10, color="595959")
        fila += 1

    fila += 1
    ws3.cell(row=fila, column=1, value="Unidades por bodega").font = Font(
        name=FUENTE, size=11, bold=True)
    fila += 1
    for h in sorted(BODEGAS, reverse=True):
        ws3.cell(row=fila, column=1, value=f"Bodega {h}").font = Font(
            name=FUENTE, size=10)
        ws3.cell(row=fila, column=2, value=por_bodega[h]).font = Font(
            name=FUENTE, size=10)
        fila += 1

    fila += 2
    ws3.cell(row=fila, column=1,
             value="ATENCION: los parametros de tiempo por izada y area "
                   "utilizable son supuestos declarados, sin confirmar con la "
                   "contraparte. Ver el registro de supuestos.").font = Font(
                       name=FUENTE, size=9, italic=True, color="C00000")

    ws3.column_dimensions["A"].width = 38
    ws3.column_dimensions["B"].width = 14
    ws3.column_dimensions["C"].width = 30

    wb.save(ruta)
    return ruta


# =============================================================================
# 8. PUNTO DE ENTRADA
# =============================================================================

def elegir_origen_datos():
    """
    Pregunta al usuario de donde cargar los datos.

    Ofrece los Excel y las carpetas de CSV que encuentre en el directorio
    actual. Devuelve la ruta elegida, o None para usar el caso base cableado.
    """
    opciones = []
    for f in sorted(Path(".").glob("*.xlsx")):
        if not f.name.startswith("~$"):
            opciones.append(("excel", f))
    for d in sorted(Path(".").iterdir()):
        if d.is_dir() and list(d.glob("viaje_*.csv")):
            opciones.append(("csv", d))

    print("De donde cargar los datos:")
    print("  0) Usar el caso base cableado en el codigo (Kiwi Arrow)")
    for i, (tipo, ruta) in enumerate(opciones, start=1):
        etiqueta = "Excel" if tipo == "excel" else "Carpeta de CSV"
        print(f"  {i}) {etiqueta}: {ruta}")
    print(f"  {len(opciones) + 1}) Escribir otra ruta")

    try:
        eleccion = input("\nOpcion [0]: ").strip() or "0"
    except EOFError:
        return None

    if eleccion == "0":
        return None
    if eleccion == str(len(opciones) + 1):
        return input("Ruta del Excel o de la carpeta con CSV: ").strip() or None
    try:
        return str(opciones[int(eleccion) - 1][1])
    except (ValueError, IndexError):
        print("Opcion no valida. Se usan los datos del codigo.")
        return None


def cargar_datos(ruta):
    """
    Carga los datos desde un Excel o desde una carpeta de CSV, segun lo que sea.
    """
    p = Path(ruta)
    if p.is_dir():
        return cargar_desde_csv(p)
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        return cargar_desde_excel(p)
    raise ValueError(
        f"No se reconoce '{ruta}'. Debe ser un archivo .xlsx o una carpeta con "
        f"los CSV de entrada."
    )


def main(carpeta_datos=None, interactivo=True):
    if carpeta_datos is None and interactivo:
        carpeta_datos = elegir_origen_datos()

    if carpeta_datos:
        print(f"\nCargando datos desde '{carpeta_datos}'...")
        try:
            avisos = cargar_datos(carpeta_datos)
        except (FileNotFoundError, KeyError, ValueError) as e:
            print(f"  No se pudieron cargar los datos: {e}")
            return
        print(f"  {len(BODEGAS)} bodegas, {len(PLANES)} planes, "
              f"{len(PRODUCTOS)} productos, {len(DESTINOS)} destinos")
        print(f"  {sum(DEMANDA.values()):,} unidades a embarcar")
        if avisos:
            print("\n  Advertencias sobre los datos cargados:")
            for a in avisos:
                print(f"    - {a}")
    else:
        print("\nUsando el caso base cableado en el codigo.")

    if cargar_capacidades():
        print(f"\nCapacidades cargadas de '{ARCHIVO_CAPACIDADES}': "
              f"{len(CAPACIDAD)} combinaciones bodega-producto")
        print("  La capacidad de cada capa viene del calculo geometrico del packer.")
    else:
        print(f"\nNo se encontro '{ARCHIVO_CAPACIDADES}'.")
        print("  Se usa la aproximacion por area, que ignora la forma de las piezas.")
        print("  Para el calculo geometrico real, ejecutar antes: python3 packer_2d.py")

    if cargar_capacidades_por_plan():
        print(f"Capacidades reales por plan cargadas de '{ARCHIVO_CAPACIDADES_POR_PLAN}': "
              f"{len(CAPACIDAD_POR_PLAN)} combinaciones bodega-plan-producto verificadas")
        print("  Estas pisan el calculo geometrico donde hay dato real del puerto.")

    print("\nVerificando datos de entrada...")
    errores = verificar_datos()
    if errores:
        print("\nLos datos de entrada tienen problemas:")
        for e in errores:
            print(f"  - {e}")
        return

    print("Datos correctos. Construyendo el modelo...")
    prob, x, y, z, w, v, T_max, combos, peso_max, peso_min = construir_modelo()
    print(f"  Variables    : {len(prob.variables()):,}")
    print(f"  Restricciones: {len(prob.constraints):,}")

    n_pasadas = 3 if USAR_BALANCE_PESO else 2

    # --- Pasada 1: minimizar el makespan ---
    print(f"\nPasada 1 de {n_pasadas}: minimizando el makespan (limite {LIMITE_SEGUNDOS} s)...")
    # OJO: pasar limite= explicito, no confiar en el default de resolver().
    # El default (limite=LIMITE_SEGUNDOS) se evalua UNA VEZ, cuando Python
    # define la funcion -- si --limite reasigna el global LIMITE_SEGUNDOS
    # despues (en main(), mas abajo), el default de resolver() sigue
    # apuntando al valor viejo. Bug real detectado el 22-sep-2026: con
    # --limite 30 el CLI igual resolvia con 120 s (el valor del modulo al
    # cargar), sin avisar.
    #
    # Warm start heuristico solo por debajo de UMBRAL_WARM_START_PASADA1 (ver
    # su comentario), igual que api.py. solucion_inicial.py verifica la
    # solucion contra todas las restricciones de prob; si no pasa devuelve
    # None y se resuelve sin punto de partida.
    solucion_inicial_p1 = None
    if LIMITE_SEGUNDOS < UMBRAL_WARM_START_PASADA1:
        try:
            from . import solucion_inicial as _si
        except ImportError:
            import solucion_inicial as _si
        solucion_inicial_p1 = _si.construir_solucion_inicial(
            prob, x, y, w, z, v, T_max, peso_max, peso_min, combos
        )
        if solucion_inicial_p1 is not None:
            print("  Limite bajo: se parte de una solucion heuristica verificada.")
    res1 = resolver(prob, limite=LIMITE_SEGUNDOS, solucion_inicial=solucion_inicial_p1)
    if T_max.value() is None:
        print(f"  Sin solucion. Estado PuLP: {res1['estado_pulp']}")
        return

    makespan_pasada1 = T_max.value()
    print(f"  Makespan alcanzado: {makespan_pasada1:.2f} h")
    describir_resolucion(res1, "Pasada 1")

    # --- Pasada 2: desempatar entre soluciones de igual makespan ---
    hay_secundario = preparar_pasada2(prob, z, w, v, T_max, makespan_pasada1)
    if hay_secundario:
        cota = makespan_pasada1 + TOLERANCIA_IZADAS * TIEMPO_CICLO
        print(f"\nPasada 2 de {n_pasadas}: makespan acotado a <= {cota:.2f} h "
              f"(+{TOLERANCIA_IZADAS} izadas de tolerancia)")
        print(f"  Minimizando terminos secundarios (limite {LIMITE_SEGUNDOS} s)...")
        solucion_pasada1 = capturar_solucion(prob)
        # Warm start desde la pasada 1 (ver nota de la pasada 1 sobre limite=)
        res2 = resolver(prob, limite=LIMITE_SEGUNDOS, solucion_inicial=solucion_pasada1)

        if T_max.value() is None or T_max.value() <= 0:
            # La pasada 2 no encontro solucion dentro de su limite de tiempo.
            # Se vuelve a la de la pasada 1, que es valida: solo le falta el
            # desempate entre soluciones de igual makespan.
            print("  La pasada 2 no encontro solucion dentro del limite.")
            print("  Se conserva el resultado de la pasada 1.")
            print("  Para que la pasada 2 alcance a resolver, subir --limite.")
            restaurar_solucion(prob, solucion_pasada1)
            res_final = res1
        else:
            print(f"  Makespan final: {T_max.value():.2f} h")
            describir_resolucion(res2, "Pasada 2")
            res_final = res2

            # --- Pasada 3: balance de peso por etapa del viaje ---
            valor_pasada2 = pulp.value(prob.objective)
            hay_terciario = preparar_pasada3(prob, z, w, v, peso_max, peso_min, valor_pasada2)
            if hay_terciario:
                print(f"\nPasada 3 de {n_pasadas}: objetivo secundario acotado a "
                      f"<= {valor_pasada2 + TOLERANCIA_PASADA3:.2f}")
                print(f"  Minimizando desbalance de peso (limite {LIMITE_SEGUNDOS_BALANCE} s)...")
                solucion_pasada2 = capturar_solucion(prob)
                # Sin warm start desde la pasada 2 esta pasada no encuentra
                # ninguna solucion factible (ver resolver_highs_con_punto_inicial)
                res3 = resolver(prob, limite=LIMITE_SEGUNDOS_BALANCE,
                                solucion_inicial=solucion_pasada2)

                if T_max.value() is None or T_max.value() <= 0:
                    print("  La pasada 3 no encontro solucion dentro del limite.")
                    print("  Se conserva el resultado de la pasada 2.")
                    restaurar_solucion(prob, solucion_pasada2)
                    res_final = res2
                else:
                    desbalance_ton = sum(
                        peso_max[k].value() - peso_min[k].value() for k in peso_max
                    )
                    print(f"  Desbalance de peso final: {desbalance_ton:.1f} t "
                          f"(suma de max-min de cada etapa del viaje)")
                    describir_resolucion(res3, "Pasada 3")
                    res_final = res3
    else:
        print("\nSin terminos secundarios activos: se omite la pasada 2.")
        res_final = res1

    print()
    informar(res_final, prob, x, y, z, T_max, combos)

    # --- Exportacion ---
    if T_max.value() is None or T_max.value() <= 0:
        print("\nNo se exporta el plan: no hay solucion que exportar.")
        return

    filas = extraer_plan(x, z, combos)
    horas = horas_por_cuadrilla(z)
    try:
        ruta = exportar_excel(filas, horas, T_max.value())
        print(f"\nPlan de estiba exportado a: {ruta}")
    except ImportError:
        print("\nNo se pudo exportar a Excel: falta openpyxl (pip install openpyxl)")

def _en_notebook():
    """
    Detecta si el modulo corre dentro de Jupyter, Colab o similar.

    Hace falta porque en un notebook el kernel recibe argumentos propios
    (por ejemplo "-f /root/.../kernel-xxxx.json") que argparse no reconoce y
    que lo hacen terminar el proceso con SystemExit: 2.
    """
    try:
        from IPython import get_ipython
        shell = get_ipython()
        if shell is None:
            return False
        return shell.__class__.__name__ in (
            "ZMQInteractiveShell",       # Jupyter / Colab
            "Shell",                     # Colab en algunas versiones
        )
    except ImportError:
        return False


def ejecutar_desde_linea_de_comandos():
    """Lee los argumentos de la terminal y llama a main()."""
    global LIMITE_SEGUNDOS, LIMITE_SEGUNDOS_BALANCE

    parser = argparse.ArgumentParser(
        description="Modelo de asignacion del prestow de celulosa - Puerto Lirquen"
    )
    parser.add_argument(
        "--datos", metavar="CARPETA",
        help="Excel o carpeta de CSV con los datos; si se omite, se pregunta",
    )
    parser.add_argument(
        "--caso-base", action="store_true",
        help="usar los datos cableados sin preguntar",
    )
    parser.add_argument(
        "--limite", type=int, metavar="SEG",
        help=f"limite de tiempo del solver en segundos (por defecto {LIMITE_SEGUNDOS})",
    )

    # parse_known_args ignora argumentos ajenos en vez de abortar. Es la red de
    # seguridad para entornos que inyectan sus propios parametros.
    args, ignorados = parser.parse_known_args()
    if ignorados:
        print(f"Argumentos ignorados: {' '.join(ignorados)}\n")

    if args.limite:
        LIMITE_SEGUNDOS = args.limite
        LIMITE_SEGUNDOS_BALANCE = args.limite

    main(carpeta_datos=args.datos, interactivo=not args.caso_base)


if __name__ == "__main__":
    if _en_notebook():
        # En Jupyter o Colab no hay argumentos de linea de comandos utiles, y
        # tampoco input() confiable en todos los casos. Se corre el caso base.
        # Para cargar CSV desde un notebook, llamar directamente:
        #     main(carpeta_datos="datos", interactivo=False)
        print("Ejecutando dentro de un notebook: se usa el caso base.\n"
              "Para cargar datos desde CSV, ejecutar en una celda:\n"
              "    main(carpeta_datos='datos', interactivo=False)\n")
        main(carpeta_datos=None, interactivo=False)
    else:
        # Se corre a traves del modulo importado ("modelo_prestow"), no de
        # esta copia "__main__": solucion_inicial.py hace "import
        # modelo_prestow" y lee sus globales (DEMANDA, ROT, CAPACIDAD...). Si
        # main() corriera en "__main__", los datos cargados quedarian en esta
        # copia y el heuristico leeria los del caso base cableado, sin aviso.
        import modelo_prestow
        modelo_prestow.ejecutar_desde_linea_de_comandos()
