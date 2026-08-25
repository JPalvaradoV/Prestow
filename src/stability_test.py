"""
Test de estabilidad: 5 corridas con semillas distintas para medir cuánto varía
la asignación entre corridas que alcanzan un makespan similar.

Produce data/stability_report.csv con una fila por corrida.

Uso:
    python src/stability_test.py --limite 180 --n 5

Este script se pensó para correr en background (15-20 min con --limite 180).
"""

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Al correr como script, Python agrega src/ al path automáticamente.
# Para importar desde la raíz del proyecto, también se agrega el padre.
_RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

try:
    from api import FilaPlan, resolver_prestow
except ImportError:
    from src.api import FilaPlan, resolver_prestow  # type: ignore[import]

_SEMILLAS_POR_DEFECTO = [42, 1337, 0, 271828, 314159]

_DATOS_POR_DEFECTO = str(_RAIZ / "data" / "datos_entrada_kiwi_arrow.xlsx")
_SALIDA_POR_DEFECTO = str(_RAIZ / "data" / "stability_report.csv")


def correr_estabilidad(
    ruta_datos: str,
    limite_segundos: int,
    n: int,
    semillas: list[int],
    ruta_salida: str,
) -> None:
    bodegas = list(range(1, 9))  # Kiwi Arrow: 8 bodegas
    filas_csv: list[dict] = []

    print(f"Test de estabilidad: {n} corridas con limite={limite_segundos} s")
    print(f"Datos: {ruta_datos}")
    print(f"Semillas: {semillas[:n]}\n")

    makespans: list[float] = []

    for i, seed in enumerate(semillas[:n]):
        print(f"[{i + 1}/{n}] Corrida con seed={seed}...")
        try:
            r = resolver_prestow(
                ruta_datos=ruta_datos,
                limite_segundos=limite_segundos,
                solver="HiGHS",
                seed=seed,
            )
        except Exception as e:
            print(f"  ERROR en seed={seed}: {e}")
            continue

        # Unidades por bodega
        unidades_bodega: dict[int, int] = defaultdict(int)
        for fila in r.plan:
            unidades_bodega[fila.bodega] += fila.unidades

        fila_csv: dict = {
            "seed": seed,
            "makespan": round(r.makespan, 4),
            "gap": round(r.gap, 4) if r.gap is not None else "",
        }
        for h in bodegas:
            fila_csv[f"unidades_bodega_{h}"] = unidades_bodega.get(h, 0)

        filas_csv.append(fila_csv)
        makespans.append(r.makespan)
        print(
            f"  makespan={r.makespan:.2f} h  gap={r.gap}  "
            f"estado={r.estado_solver}"
        )

    if not filas_csv:
        print("Sin resultados para escribir.")
        return

    # Escribir CSV
    campos = ["seed", "makespan", "gap"] + [f"unidades_bodega_{h}" for h in bodegas]
    with open(ruta_salida, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=campos)
        wr.writeheader()
        wr.writerows(filas_csv)
    print(f"\nReporte escrito en: {ruta_salida}")

    # Resumen estadístico
    print("\n" + "=" * 60)
    print("RESUMEN DE ESTABILIDAD")
    print("=" * 60)
    if len(makespans) > 1:
        print(f"Makespan — media: {statistics.mean(makespans):.2f} h  "
              f"desv. std: {statistics.stdev(makespans):.4f} h  "
              f"rango: [{min(makespans):.2f}, {max(makespans):.2f}]")
    else:
        print(f"Makespan: {makespans[0]:.2f} h (una sola corrida)")

    # Dispersión por bodega
    print("\nUnidades por bodega (media ± desv. std entre corridas):")
    for h in bodegas:
        valores = [f.get(f"unidades_bodega_{h}", 0) for f in filas_csv]
        media = statistics.mean(valores)
        std = statistics.stdev(valores) if len(valores) > 1 else 0.0
        print(f"  Bodega {h}: {media:7.0f} ± {std:6.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test de estabilidad del modelo de prestow"
    )
    parser.add_argument(
        "--limite", type=int, default=180, metavar="SEG",
        help="límite de tiempo del solver por corrida en segundos (por defecto 180)"
    )
    parser.add_argument(
        "--n", type=int, default=5, metavar="N",
        help="número de corridas (por defecto 5)"
    )
    parser.add_argument(
        "--datos", default=_DATOS_POR_DEFECTO, metavar="RUTA",
        help="Excel o carpeta de CSV de entrada"
    )
    parser.add_argument(
        "--salida", default=_SALIDA_POR_DEFECTO, metavar="RUTA",
        help="archivo CSV de salida"
    )
    args = parser.parse_args()

    semillas = _SEMILLAS_POR_DEFECTO[: args.n]
    if args.n > len(_SEMILLAS_POR_DEFECTO):
        # Extender con semillas adicionales si piden más de 5
        import random
        rng = random.Random(0)
        semillas = semillas + [rng.randint(1, 99999) for _ in range(args.n - len(_SEMILLAS_POR_DEFECTO))]

    correr_estabilidad(
        ruta_datos=args.datos,
        limite_segundos=args.limite,
        n=args.n,
        semillas=semillas,
        ruta_salida=args.salida,
    )


if __name__ == "__main__":
    main()
