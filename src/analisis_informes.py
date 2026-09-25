"""
Corre las instancias de generador_instancias.py con el modelo vigente y
guarda los resultados para los informes. No modifica el modelo ni la app:
llama a api.resolver_prestow igual que la web.

Uso:
    python src/analisis_informes.py                 # todas, 180 s por pasada
    python src/analisis_informes.py --solo P1 P2    # algunas
    python src/analisis_informes.py --limite 60

Salidas:
    data/instancias/<id>/            CSV de entrada + instancia.json
    data/resultados_analisis/resultados.csv   una fila por instancia (se va
                                              completando: si se corta, lo
                                              ya corrido queda guardado)
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ / "src"))

import api  # noqa: E402
import generador_instancias as gen  # noqa: E402
import packer_2d  # noqa: E402

CARPETA_INSTANCIAS = _RAIZ / "data" / "instancias"
ARCHIVO_RESULTADOS = _RAIZ / "data" / "resultados_analisis" / "resultados.csv"
COLUMNAS = [
    "id", "grupo", "proposito", "descripcion", "bodegas", "destinos", "productos", "unidades",
    "resultado", "makespan_h", "tiempo_s", "gap_p1_pct", "gap_p2_pct", "gap_p3_pct",
    "izadas", "fragmentacion", "desbalance_cuadrillas_pct", "desbalance_peso_t",
    "no_overstowage", "cobertura", "contiguidad", "capacidad", "mensaje", "limite_s",
]


def _capacidades(carpeta: Path) -> Path:
    bodegas, productos = packer_2d.leer_entrada(carpeta)
    ruta = carpeta / "capacidades.csv"
    packer_2d.guardar_tabla(packer_2d.generar_tabla(bodegas, productos, mostrar=False), str(ruta))
    return ruta


def correr(inst: gen.Instancia, limite: int, sufijo: str = "") -> dict:
    carpeta = gen.escribir_csv(inst, CARPETA_INSTANCIAS / inst.id)
    ruta_cap = _capacidades(carpeta)
    fila = {"id": inst.id + sufijo, "grupo": inst.grupo, "proposito": inst.proposito,
            "descripcion": inst.descripcion, **inst.tamano(), "limite_s": limite}

    # Rendimientos: el tiempo de ciclo es una constante del modelo; se pisa
    # solo durante esta corrida y se restaura siempre.
    original = dict(api._mp.TIEMPO_CICLO_POR_BODEGA)
    if inst.tiempo_ciclo_min:
        api._mp.TIEMPO_CICLO_POR_BODEGA = {h: m / 60 for h, m in inst.tiempo_ciclo_min.items()}
    t0 = time.perf_counter()
    try:
        r = api.resolver_prestow(carpeta, ruta_capacidades=ruta_cap, limite_segundos=limite)
    except ValueError as exc:
        fila.update(resultado="rechazada", tiempo_s=round(time.perf_counter() - t0, 1),
                    mensaje=str(exc).replace("\n", " "))
        return fila
    finally:
        api._mp.TIEMPO_CICLO_POR_BODEGA = original

    g = r.gaps_por_pasada
    ok = {k: ("OK" if not v else f"FALLA ({len(v)})") for k, v in r.verificaciones.items()}
    fila.update(
        resultado="resuelta", makespan_h=round(r.makespan, 4), tiempo_s=round(time.perf_counter() - t0, 1),
        gap_p1_pct=_r(g.get(1)), gap_p2_pct=_r(g.get(2)), gap_p3_pct=_r(g.get(3)),
        izadas=int(r.kpis.get("izadas_totales", 0)),
        fragmentacion=int(r.kpis.get("fragmentacion_bodegas_destino", 0)),
        desbalance_cuadrillas_pct=r.kpis.get("desbalance_pct"),
        desbalance_peso_t=r.kpis.get("balance_peso_desbalance_ton"),
        no_overstowage=ok.get("no_overstowage"), cobertura=ok.get("cobertura"),
        contiguidad=ok.get("contiguidad"), capacidad=ok.get("capacidad"),
        mensaje=r.estado_solver,
    )
    return fila


def _r(x):
    return None if x is None else round(x, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--limite", type=int, default=180)
    parser.add_argument("--solo", nargs="*")
    parser.add_argument(
        "--sufijo", default="",
        help="se agrega al id en resultados.csv (p. ej. _170s para repetir una instancia "
             "con otro limite sin pisar la fila original)",
    )
    args = parser.parse_args()

    instancias = gen.todas(_RAIZ / "data" / "datos_entrada_kiwi_arrow.xlsx")
    if args.solo:
        instancias = [i for i in instancias if i.id in args.solo]

    ARCHIVO_RESULTADOS.parent.mkdir(parents=True, exist_ok=True)
    ya = set()
    if ARCHIVO_RESULTADOS.exists():
        with open(ARCHIVO_RESULTADOS, newline="", encoding="utf-8") as f:
            ya = {row["id"] for row in csv.DictReader(f)}
    else:
        with open(ARCHIVO_RESULTADOS, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNAS).writeheader()

    for inst in instancias:
        id_resultado = inst.id + args.sufijo
        if id_resultado in ya:
            print(f"{id_resultado}: ya corrida, se omite", flush=True)
            continue
        print(f"{id_resultado} ({inst.tamano()})...", flush=True)
        fila = correr(inst, args.limite, args.sufijo)
        with open(ARCHIVO_RESULTADOS, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore").writerow(fila)
        print(f"  -> {fila['resultado']} makespan={fila.get('makespan_h')} t={fila['tiempo_s']} s "
              f"gaps={fila.get('gap_p1_pct')}/{fila.get('gap_p2_pct')}/{fila.get('gap_p3_pct')} "
              f"overstow={fila.get('no_overstowage')} | {fila.get('mensaje', '')[:120]}", flush=True)


if __name__ == "__main__":
    main()
