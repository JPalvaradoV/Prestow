"""
Extrae capacidades reales por (bodega, plan, producto) desde las plantillas
del puerto (PLANIMETRIAS_MN_KIWI_ARROW_2025.xls, hojas LH-1 a LH-8).

POR QUE ES UN MODULO SEPARADO
packer_2d.py calcula la capacidad geometricamente, asumiendo que el piso no
cambia con la altura (mismo largo x ancho en los 11 planes). Este modulo lee
los datos REALES de las plantillas del puerto -- que muestran capacidad por
plan concreto -- y produce una tabla de excepciones que modelo_prestow.py usa
para pisar el calculo geometrico donde hay dato verificado (ver
CAPACIDAD_POR_PLAN en modelo_prestow.py). No reemplaza a packer_2d.py: donde
no hay dato real, el calculo geometrico sigue siendo el que manda.

QUE SE ENCONTRO (sesion del 22 de septiembre de 2026)
Se penso por mucho tiempo que "para el Kiwi Arrow solo hay plantillas propias
de los planes 1 a 6" -- eso salio de revisar solo la hoja LH-1 (bodega 1),
que en efecto solo tiene Kiwi Arrow hasta el plan 6 (el resto son plantillas
del Eagle Arrow, otro buque, mezcladas en el mismo archivo). Al revisar las 8
hojas completas aparecieron 57 plantillas propias del Kiwi Arrow cubriendo
planes 1 a 11 en las bodegas 2 a 8. Comparando la MISMA combinacion bodega +
producto entre distintos planes: la mayoria de las bodegas no muestran
variacion real (0-3%, dentro del ruido de transcripcion), pero las bodegas 4,
5, 7 y 8 si muestran una caida real de 3-13% en los planes altos (8-10)
respecto de los bajos/medios -- consistente con que cerca de la cubierta hay
menos piso util (vigas, escotilla mas angosta que la bodega).

CRITERIO DE LIMPIEZA -- que se excluye y por que
No se inventa ningun numero: donde el dato es ambiguo o contradictorio, se
descarta esa combinacion entera (queda con el valor por defecto del packer).

1. Producto ambiguo: plantillas que mezclan 2 productos en una sola celda
   (ej. "ARAUCO BKP / EKP") -- no hay forma de saber a cual de los dos
   atribuir el numero. Se descartan.
2. Conflictos: la misma combinacion (bodega, plan, producto) aparece en dos
   plantillas distintas del archivo con valores DISTINTOS (ej. bodega 4,
   plan 9, ARAUCO_EKP: 362 en una plantilla, 341 en otra). Son 10 casos. Se
   descartan enteros -- no hay forma de saber cual de los dos es correcto sin
   volver a la fuente original con el puerto.
3. Valor extremo sin poder confirmar: bodega 5, plan 10, ARAUCO_EKP = 174,
   un salto de -55% respecto del resto de esa bodega (que ronda 379-385).
   Podria ser un dato real (una reduccion de piso mucho mas fuerte que en
   cualquier otra combinacion) o un error de tipeo en la planilla del
   puerto -- no se puede distinguir sin la fuente original. Se descarta a
   mano hasta poder confirmarlo.

Con esas exclusiones quedan 72 combinaciones limpias, guardadas en
data/capacidades_reales_por_plan.csv.

Uso:
    python3 src/extraer_capacidades_reales.py
    python3 src/extraer_capacidades_reales.py --raw otra_ruta.xls --salida otra_salida.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ORDINALES = {
    "PRIMER": 1, "SEGUNDO": 2, "TERCER": 3, "CUARTO": 4, "QUINTO": 5,
    "SEXTO": 6, "SEPTIMO": 7, "OCTAVO": 8, "NOVENO": 9, "DECIMO": 10,
    "UNDECIMO": 11,
}

# Mapeo a los nombres canonicos del proyecto (CLAUDE.md seccion 9). Entradas
# ambiguas (mezclan 2 productos) se dejan fuera a propósito: no se mapean, y
# por lo tanto se descartan en la extraccion.
MAPEO_PRODUCTO = {
    "N. ALDEA EKP": "N_ALDEA_EKP",
    "N ALDEA EKP": "N_ALDEA_EKP",
    "ALDEA BKP": "N_ALDEA_BKP",
    "N. ALDEA BKP": "N_ALDEA_BKP",
    "ARAUCO EKP": "ARAUCO_EKP",
    "ARAUCO BKP": "ARAUCO_BKP",
    "CELCO": "CELCO_UKP",
    "CELCO UKP": "CELCO_UKP",
}

# Combinaciones (bodega, plan, producto) excluidas a mano tras revisar el
# archivo: valores extremos que no se pudieron confirmar contra la fuente
# (ver criterio de limpieza en el docstring del modulo, punto 3).
EXCLUSION_MANUAL = {
    (5, 10, "ARAUCO_EKP"),  # 174 u/plan, -55% vs el resto de la bodega 5
}

_RAIZ = Path(__file__).parent.parent
RUTA_RAW_DEFECTO = _RAIZ / "data" / "raw" / "PLANIMETRIAS_MN_KIWI_ARROW_2025.xls"
RUTA_SALIDA_DEFECTO = _RAIZ / "data" / "capacidades_reales_por_plan.csv"


def _parsear_planes(texto: str) -> list[int]:
    """'PRIMER A SEXTO PLAN' -> [1..6]. 'SEPTIMO Y OCTAVO PLAN' -> [7,8].
    'OCTAVO PLAN' -> [8]."""
    t = texto.upper().replace("�", "E")
    palabras = [ORDINALES[p] for p in ORDINALES if p in t]
    if " A " in t and len(palabras) >= 2:
        return list(range(min(palabras), max(palabras) + 1))
    if " Y " in t and len(palabras) >= 2:
        return sorted(set(palabras))
    return palabras


def _leer_plantillas_crudas(ruta: Path) -> list[dict]:
    """Lee las hojas LH-* del archivo y devuelve una plantilla por bloque
    ('PLANTILLA SECUENCIADA...KIWI ARROW', bodega, unidades/plan, producto,
    rango de planes), sin normalizar ni filtrar todavia."""
    import xlrd

    wb = xlrd.open_workbook(str(ruta))
    crudos = []
    for hoja_nombre in wb.sheet_names():
        if "LH" not in hoja_nombre.upper():
            continue
        ws = wb.sheet_by_name(hoja_nombre)
        bodega_hoja_m = re.search(r"\d+", hoja_nombre)
        bodega_hoja = int(bodega_hoja_m.group()) if bodega_hoja_m else None
        if bodega_hoja is None:
            continue

        r = 0
        while r < ws.nrows - 2:
            v0 = next(
                (ws.cell_value(r, c) for c in range(ws.ncols)
                 if isinstance(ws.cell_value(r, c), str) and "PLANTILLA" in ws.cell_value(r, c).upper()),
                None,
            )
            if v0 is not None and "KIWI" in v0.upper():
                fila_b = [ws.cell_value(r + 1, c) for c in range(ws.ncols)]
                fila_p = [ws.cell_value(r + 2, c) for c in range(ws.ncols)]
                unit_txt = next((str(x) for x in fila_b if isinstance(x, str) and "UNIT" in x.upper()), "")
                producto_raw = next(
                    (str(x) for x in fila_p if isinstance(x, str) and x.strip() and "PROA" not in x.upper()), ""
                ).strip().upper()
                plan_txt = next((str(x) for x in fila_p if isinstance(x, str) and "PLAN" in x.upper()), "")
                unidades_m = re.search(r"\d+", unit_txt)
                planes = _parsear_planes(plan_txt) if plan_txt else []
                if unidades_m and planes and producto_raw:
                    crudos.append({
                        "bodega": bodega_hoja,
                        "producto_raw": producto_raw,
                        "unidades_plan": int(unidades_m.group()),
                        "planes": planes,
                    })
            r += 1
    return crudos


def extraer(ruta_raw: Path = RUTA_RAW_DEFECTO) -> tuple[list[tuple[int, int, str, int]], list[str]]:
    """
    Devuelve (filas_limpias, avisos). filas_limpias: lista de
    (bodega, plan, producto, unidades_max_real). avisos: mensajes sobre lo
    que se descartó y por qué (productos ambiguos, conflictos, exclusión
    manual) -- para dejar constancia, no solo para la consola.
    """
    crudos = _leer_plantillas_crudas(ruta_raw)

    observaciones: dict[tuple[int, int, str], list[int]] = defaultdict(list)
    ambiguos_vistos: set[str] = set()
    for c in crudos:
        prod = MAPEO_PRODUCTO.get(c["producto_raw"])
        if prod is None:
            ambiguos_vistos.add(c["producto_raw"])
            continue
        for p in c["planes"]:
            observaciones[(c["bodega"], p, prod)].append(c["unidades_plan"])

    avisos = []
    if ambiguos_vistos:
        avisos.append(
            "Productos ambiguos descartados (mezclan 2 productos, no se puede "
            "atribuir el numero a uno solo): " + ", ".join(sorted(ambiguos_vistos))
        )

    conflictos = {k: v for k, v in observaciones.items() if len(set(v)) > 1}
    for k, v in sorted(conflictos.items()):
        avisos.append(f"Conflicto descartado {k}: plantillas distintas dan {sorted(set(v))}")

    filas = []
    for (bodega, plan, prod), valores in sorted(observaciones.items()):
        unicos = set(valores)
        if len(unicos) > 1:
            continue
        if (bodega, plan, prod) in EXCLUSION_MANUAL:
            avisos.append(f"Exclusión manual {(bodega, plan, prod)}: valor extremo sin confirmar")
            continue
        filas.append((bodega, plan, prod, unicos.pop()))

    return filas, avisos


def guardar(filas: list[tuple[int, int, str, int]], ruta_salida: Path = RUTA_SALIDA_DEFECTO) -> Path:
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_salida, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["bodega", "plan", "producto", "unidades_max_real"])
        wr.writerows(filas)
    return ruta_salida


def main(ruta_raw: str | None = None, ruta_salida: str | None = None) -> None:
    raw = Path(ruta_raw) if ruta_raw else RUTA_RAW_DEFECTO
    salida = Path(ruta_salida) if ruta_salida else RUTA_SALIDA_DEFECTO

    if not raw.exists():
        print(f"No se encontró '{raw}'.")
        print("Este archivo no se versiona (data/raw/ está en .gitignore) -- "
              "cada integrante necesita su copia local del original del puerto.")
        return

    filas, avisos = extraer(raw)
    print(f"Leídas {len(filas)} combinaciones (bodega, plan, producto) con dato real limpio.")
    if avisos:
        print(f"\n{len(avisos)} advertencias (descartes, no se inventó ningún número):")
        for a in avisos:
            print(f"  - {a}")

    ruta = guardar(filas, salida)
    print(f"\nGuardado en: {ruta}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default=None, help="ruta al PLANIMETRIAS_*.xls original")
    parser.add_argument("--salida", default=None, help="ruta del CSV de salida")
    args = parser.parse_args()
    main(args.raw, args.salida)
