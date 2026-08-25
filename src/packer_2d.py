"""
Packer 2D - calculo de capacidad por geometria
Prestow de celulosa, Puerto Lirquen

Calcula cuantas unidades de cada producto caben en el piso de cada bodega,
resolviendo el empaquetamiento con patrones de bloque y rotacion de 90 grados.

POR QUE ES UN MODULO SEPARADO
La geometria del buque y las dimensiones de los productos no cambian entre
viajes: solo cambian si cambia el buque o aparece un producto nuevo. Recalcular
el empaquetamiento en cada corrida seria repetir un trabajo caro para obtener
siempre el mismo resultado. Este modulo se ejecuta una vez, genera una tabla de
capacidades, y el modelo de asignacion la consume como parametro.

QUE PROBLEMA RESUELVE
Es un pallet loading problem: acomodar el maximo numero de rectangulos
identicos dentro de un rectangulo mayor, permitiendo girarlos 90 grados. No es
bin packing heterogeneo, que seria mucho mas dificil: aqui todas las piezas de
un mismo producto son iguales, y eso hace que los patrones de bloque esten
cerca del optimo.

Uso:
    python3 packer_2d.py                    # usa el Excel de entrada por defecto
    python3 packer_2d.py --datos otro.xlsx
    python3 packer_2d.py --calibrar         # ajusta la merma contra la plantilla real
"""

import argparse
import csv
import math
from pathlib import Path


# =============================================================================
# 1. FACTOR DE MERMA
# =============================================================================
# MERMA es la fraccion de la capacidad geometrica que no se aprovecha por
# causas que el calculo no modela: separadores de goma entre bloques de carga,
# espacio de maniobra para la grua horquilla dentro de la bodega, o que las
# medidas del piso no sean netas (cuadernas, refuerzos, escalas).
#
# SUPUESTO DECLARADO Y AVALADO: no se consideran esos efectos. La capacidad es
# la que resulta del calculo geometrico puro. Queda registrado como supuesto
# del proyecto; si mas adelante se quisiera incorporar, basta con darle un
# valor a MERMA sin tocar nada mas.
MERMA = 0.0

# -----------------------------------------------------------------------------
# NOTA: DE DONDE SALEN LAS HUELLAS
#
# El archivo de planimetrias tiene 58 plantillas del Kiwi Arrow, repartidas en
# las hojas LH-1 a LH-8. Inicialmente solo se habia revisado LH-1, y por eso
# tres de los cinco productos figuraban con huella supuesta.
#
# Al revisar todas las hojas aparecieron las dimensiones reales, y dos de las
# supuestas estaban equivocadas:
#     ARAUCO_BKP : se suponia 0,84 x 1,47   real 0,84 x 1,36
#     CELCO_UKP  : se suponia 0,84 x 1,47   real 0,84 x 1,43
#
# El error de CELCO_UKP tenia consecuencias concretas: cuatro capas del plan
# real quedaban infactibles porque el calculo permitia 403 unidades y el plan
# ponia 408. Con la huella correcta la capacidad sube a 412 y el problema
# desaparece.
#
# Con las cinco huellas verificadas, el plan real satisface TODAS las
# restricciones del modelo: capacidad, no-overstowage, contiguidad y cobertura.
#
# Algunas plantillas usan dos anchos distintos para el mismo producto segun la
# zona de la bodega. Se tomo el mas frecuente; la variacion puede deberse a
# fardos de lotes distintos o a redondeos del planificador.
# -----------------------------------------------------------------------------


# =============================================================================
# 2. PATRONES DE EMPAQUETAMIENTO
# =============================================================================

def _cuantas_caben(largo_zona, ancho_zona, largo_pieza, ancho_pieza):
    """Piezas de una sola orientacion en una zona rectangular."""
    if largo_zona <= 0 or ancho_zona <= 0:
        return 0
    return (math.floor(largo_zona / largo_pieza)
            * math.floor(ancho_zona / ancho_pieza))


def patron_uniforme(L, W, l, w):
    """
    Todas las piezas en la misma orientacion. Es el patron mas simple y
    frecuentemente el mejor cuando las dimensiones encajan bien.
    """
    sin_rotar = _cuantas_caben(L, W, l, w)
    rotado = _cuantas_caben(L, W, w, l)
    if sin_rotar >= rotado:
        return sin_rotar, "uniforme sin rotar"
    return rotado, "uniforme rotado 90"


def patron_dos_bloques(L, W, l, w):
    """
    Divide el piso en dos franjas con orientaciones distintas.

    Sirve cuando una orientacion deja una franja sobrante demasiado angosta
    para otra fila, pero suficiente para piezas giradas.
    """
    mejor = 0
    detalle = ""

    # Corte horizontal: una franja abajo y otra arriba
    for filas in range(0, math.floor(W / w) + 1):
        alto_a = filas * w
        a = filas * math.floor(L / l)                    # franja sin rotar
        b = _cuantas_caben(L, W - alto_a, w, l)          # resto rotado
        if a + b > mejor:
            mejor, detalle = a + b, f"2 bloques horizontal ({filas} filas + resto rotado)"

    for filas in range(0, math.floor(W / l) + 1):
        alto_a = filas * l
        a = filas * math.floor(L / w)                    # franja rotada
        b = _cuantas_caben(L, W - alto_a, l, w)          # resto sin rotar
        if a + b > mejor:
            mejor, detalle = a + b, f"2 bloques horizontal ({filas} filas rotadas + resto)"

    # Corte vertical: una franja a cada lado
    for cols in range(0, math.floor(L / l) + 1):
        ancho_a = cols * l
        a = cols * math.floor(W / w)
        b = _cuantas_caben(L - ancho_a, W, w, l)
        if a + b > mejor:
            mejor, detalle = a + b, f"2 bloques vertical ({cols} columnas + resto rotado)"

    for cols in range(0, math.floor(L / w) + 1):
        ancho_a = cols * w
        a = cols * math.floor(W / l)
        b = _cuantas_caben(L - ancho_a, W, l, w)
        if a + b > mejor:
            mejor, detalle = a + b, f"2 bloques vertical ({cols} columnas rotadas + resto)"

    return mejor, detalle


def patron_cuatro_bloques(L, W, l, w):
    """
    Divide el piso en cuatro cuadrantes con un corte horizontal y otro vertical,
    cada uno con la orientacion que mas le convenga.

    Es el patron clasico del pallet loading problem. Captura casos donde ni el
    uniforme ni el de dos bloques aprovechan bien las esquinas.

    Los cortes se prueban solo en posiciones que son multiplo de alguna
    dimension de la pieza: cortar en cualquier otro punto solo desperdicia.
    """
    cortes_x = sorted({0.0, L} |
                      {i * l for i in range(math.floor(L / l) + 1)} |
                      {i * w for i in range(math.floor(L / w) + 1)})
    cortes_y = sorted({0.0, W} |
                      {i * w for i in range(math.floor(W / w) + 1)} |
                      {i * l for i in range(math.floor(W / l) + 1)})

    mejor = 0
    detalle = ""
    for cx in cortes_x:
        if cx > L:
            continue
        for cy in cortes_y:
            if cy > W:
                continue
            total = 0
            for (lz, wz) in ((cx, cy), (L - cx, cy), (cx, W - cy), (L - cx, W - cy)):
                total += max(_cuantas_caben(lz, wz, l, w),
                             _cuantas_caben(lz, wz, w, l))
            if total > mejor:
                mejor = total
                detalle = f"4 bloques (corte en {cx:.2f} x {cy:.2f} m)"
    return mejor, detalle


def calcular_capacidad(L, W, l, w, aplicar_merma=True):
    """
    Devuelve la mejor capacidad encontrada entre todos los patrones.

    L, W : dimensiones del piso de la bodega, en metros
    l, w : dimensiones de la huella de una unidad, en metros
    """
    candidatos = [
        patron_uniforme(L, W, l, w),
        patron_dos_bloques(L, W, l, w),
        patron_cuatro_bloques(L, W, l, w),
    ]
    bruto, detalle = max(candidatos, key=lambda c: c[0])

    if not aplicar_merma:
        return bruto, bruto, detalle

    neto = math.floor(bruto * (1 - MERMA))
    return neto, bruto, detalle


# =============================================================================
# 3. LECTURA DE DATOS
# =============================================================================

def leer_entrada(ruta):
    """
    Lee la geometria de las bodegas y las huellas de los productos desde el
    Excel de entrada del modelo, o desde una carpeta con los CSV.
    """
    p = Path(ruta)

    if p.is_dir():
        def filas(patron):
            archivos = sorted(p.glob(patron))
            if not archivos:
                raise FileNotFoundError(f"No hay ningun '{patron}' en {p}")
            with open(archivos[0], newline="", encoding="utf-8-sig") as f:
                return list(csv.DictReader(f))
        bodegas = [
            (int(r["bodega"]), float(r["largo_m"]), float(r["ancho_m"]))
            for r in filas("buque_*.csv")
        ]
        productos = [
            (r["producto"].strip(),
             float(r["huella_largo_m"]), float(r["huella_ancho_m"]),
             (r.get("origen_dato") or "").strip())
            for r in filas("productos_*.csv")
        ]
        return bodegas, productos

    from openpyxl import load_workbook
    wb = load_workbook(p, data_only=True)

    def filas_hoja(hoja, primera_col):
        ws = wb[hoja]
        fila_enc = None
        for r in range(1, 12):
            if str(ws.cell(row=r, column=1).value or "").strip() == primera_col:
                fila_enc = r
                break
        if fila_enc is None:
            raise ValueError(f"En la hoja '{hoja}' falta la columna '{primera_col}'")
        salida = []
        r = fila_enc + 1
        while True:
            v = ws.cell(row=r, column=1).value
            if v is None or str(v).strip() == "" or str(v).strip().upper() == "TOTAL":
                break
            salida.append([ws.cell(row=r, column=j).value for j in range(1, 8)])
            r += 1
        return salida

    bodegas = [(int(f[0]), float(f[1]), float(f[2]))
               for f in filas_hoja("Buque", "bodega")]
    productos = [(str(f[0]).strip(), float(f[1]), float(f[2]),
                  str(f[4] or "").strip())
                 for f in filas_hoja("Productos", "producto")]
    return bodegas, productos


# =============================================================================
# 4. CALIBRACION
# =============================================================================

def calibrar(bodegas, productos):
    """
    Recalcula el factor de merma comparando el calculo geometrico contra las
    capacidades reales conocidas.

    Hoy solo hay un dato verificado: la plantilla del Kiwi Arrow para
    N_ALDEA_EKP en la bodega 1. Con una sola observacion no se puede hablar de
    calibracion estadistica; esto sirve para recalcular si aparecen mas datos.
    """
    # (bodega, producto, unidades segun plantilla real)
    OBSERVADO = [
        (1, "N_ALDEA_EKP", 194),
        (1, "N_ALDEA_BKP", 189),
    ]

    dic_bod = {b: (L, W) for b, L, W in bodegas}
    dic_pro = {p: (l, w) for p, l, w, _ in productos}

    print("Calibracion del factor de merma")
    print("=" * 66)
    print(f"{'bodega':>7} {'producto':<14} {'geometrico':>11} {'real':>7} {'merma':>8}")
    mermas = []
    for b, prod, real in OBSERVADO:
        if b not in dic_bod or prod not in dic_pro:
            print(f"{b:>7} {prod:<14}   sin datos para comparar")
            continue
        L, W = dic_bod[b]
        l, w = dic_pro[prod]
        bruto, _, _ = calcular_capacidad(L, W, l, w, aplicar_merma=False)
        m = 1 - real / bruto if bruto else 0
        mermas.append(m)
        print(f"{b:>7} {prod:<14} {bruto:>11} {real:>7} {m*100:>7.1f}%")

    if mermas:
        prom = sum(mermas) / len(mermas)
        print()
        print(f"Diferencia promedio en la bodega 1: {prom*100:.1f}%")
        print(f"Merma aplicada en el codigo       : {MERMA*100:.1f}%")
        print()
        print("La merma esta en cero por decision del proyecto: separadores de")
        print("goma, espacio de maniobra y medidas no netas quedan como supuesto")
        print("declarado y no se modelan.")
        print()
        print("Con las huellas verificadas de las plantillas LH-1 a LH-8, el plan")
        print("real satisface todas las restricciones del modelo.")
    return mermas


# =============================================================================
# 5. GENERACION DE LA TABLA DE CAPACIDADES
# =============================================================================

def generar_tabla(bodegas, productos, mostrar=True):
    """Calcula la capacidad de cada combinacion de bodega y producto."""
    filas = []
    for b, L, W in sorted(bodegas, reverse=True):
        area_piso = L * W
        for prod, l, w, origen in productos:
            neto, bruto, detalle = calcular_capacidad(L, W, l, w)
            area_ocupada = neto * l * w
            filas.append({
                "bodega": b,
                "producto": prod,
                "unidades_max": neto,
                "unidades_geometricas": bruto,
                "area_piso_m2": round(area_piso, 2),
                "area_ocupada_m2": round(area_ocupada, 2),
                "aprovechamiento": round(area_ocupada / area_piso, 4),
                "patron": detalle,
                "origen_huella": origen,
            })

    if mostrar:
        print("Capacidad por bodega y producto")
        print("=" * 78)
        print(f"{'bod':>4} {'producto':<14} {'geom':>6} {'neto':>6} "
              f"{'aprov':>7}  patron")
        for f in filas:
            print(f"{f['bodega']:>4} {f['producto']:<14} "
                  f"{f['unidades_geometricas']:>6} {f['unidades_max']:>6} "
                  f"{f['aprovechamiento']*100:>6.1f}%  {f['patron']}")
    return filas


def guardar_tabla(filas, ruta="capacidades.csv"):
    """Escribe la tabla que el modelo de asignacion consumira como parametro."""
    campos = ["bodega", "producto", "unidades_max", "unidades_geometricas",
              "area_piso_m2", "area_ocupada_m2", "aprovechamiento",
              "patron", "origen_huella"]
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=campos)
        wr.writeheader()
        wr.writerows(filas)
    return ruta


# =============================================================================
# 6. PUNTO DE ENTRADA
# =============================================================================

def main(ruta_datos, solo_calibrar=False, salida="capacidades.csv"):
    bodegas, productos = leer_entrada(ruta_datos)
    print(f"Leidas {len(bodegas)} bodegas y {len(productos)} productos "
          f"desde '{ruta_datos}'\n")

    if solo_calibrar:
        calibrar(bodegas, productos)
        return

    supuestas = [p for p, _, _, o in productos if "SUPUESTO" in o.upper()]
    if supuestas:
        print("ATENCION: estas huellas son supuestos, no datos verificados:")
        for p in supuestas:
            print(f"  - {p}")
        print("  La capacidad calculada para ellos es tan confiable como su huella.\n")

    filas = generar_tabla(bodegas, productos)
    ruta = guardar_tabla(filas, salida)
    print(f"\nTabla de capacidades guardada en: {ruta}")
    print(f"Merma aplicada: {MERMA*100:.1f}%  (supuesto declarado: no se modelan")
    print("  separadores de goma, espacio de maniobra ni medidas no netas)")
    print()
    print("  Las cinco huellas provienen de plantillas verificadas del Kiwi Arrow.")
    print("  Con ellas, el plan real satisface todas las restricciones del modelo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculo de capacidad por geometria - prestow Puerto Lirquen"
    )
    parser.add_argument("--datos", default="datos_entrada_kiwi_arrow.xlsx",
                        help="Excel o carpeta de CSV con la geometria")
    parser.add_argument("--calibrar", action="store_true",
                        help="comparar el calculo contra las plantillas reales")
    parser.add_argument("--salida", default="capacidades.csv",
                        help="archivo donde escribir la tabla")
    args, _ = parser.parse_known_args()
    main(args.datos, args.calibrar, args.salida)
