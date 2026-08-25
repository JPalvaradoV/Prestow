"""
API pura para el modelo de prestow.

Envuelve modelo_prestow.py con una función pura que no deja estado global
modificado entre llamadas, compatible con Streamlit (múltiples sesiones).

La función resolver_prestow es la única interfaz pública. Las demás son internas.
"""

from __future__ import annotations

import copy
import io
import contextlib
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pulp

try:
    from . import modelo_prestow as _mp
except ImportError:
    import modelo_prestow as _mp  # type: ignore[import]

# Un lock por proceso: garantiza que dos corridas no pisen los globales del módulo
# simultáneamente. Streamlit puede tener varias sesiones, pero las corridas se
# encolan. El lock dura todo el tiempo del solver; es intencional.
_lock = threading.Lock()

# Globales de modelo_prestow que cargar_datos/cargar_capacidades modifican.
# TIEMPO_CICLO_POR_BODEGA, APROVECHAMIENTO, etc. son constantes: no se tocan.
_NOMBRES_GLOBALES = [
    "BODEGAS",
    "PLANES",
    "PRODUCTOS",
    "DESTINOS",
    "CUADRILLAS",
    "ROT",
    "HUELLA",
    "PISO",
    "AREA",
    "DEMANDA",
    "CAPACIDAD",
]

# Ruta absoluta al directorio raíz del proyecto (src/../)
_RAIZ = Path(__file__).parent.parent
_DEFAULT_CAPACIDADES = _RAIZ / "data" / "capacidades.csv"


# =============================================================================
# Tipos de salida
# =============================================================================


@dataclass
class FilaPlan:
    bodega: int
    plan: int
    producto: str
    destino: str
    unidades: int


@dataclass
class ResultadoCorrida:
    makespan: float
    horas_por_cuadrilla: dict[int, float]
    plan: list[FilaPlan]
    izadas_por_capa: dict[tuple[int, int], int]
    kpis: dict[str, float]
    verificaciones: dict[str, list]
    estado_solver: str
    gap: float | None
    tiempo_solver_s: float


# =============================================================================
# Internos
# =============================================================================


def _guardar_globals() -> dict:
    return {k: copy.deepcopy(getattr(_mp, k)) for k in _NOMBRES_GLOBALES}


def _restaurar_globals(estado: dict) -> None:
    for k, v in estado.items():
        setattr(_mp, k, v)


def _construir_solver(nombre: str, limite: int, seed: int | None):
    """Crea el solver con semilla opcional. Cae a CBC si HiGHS no está disponible."""
    if nombre.upper() == "HIGHS":
        try:
            if seed is not None:
                # Intentar pasar la semilla vía options dict (PuLP >= 2.9 / HiGHS >= 1.7)
                try:
                    return pulp.HiGHS(
                        timeLimit=limite, msg=True, options={"random_seed": seed}
                    )
                except TypeError:
                    # La versión instalada no acepta options como dict; ignorar semilla
                    pass
            return pulp.HiGHS(timeLimit=limite, msg=True)
        except Exception:
            print(
                "  AVISO: HiGHS no disponible, se usa CBC. "
                "Instalar con: pip install highspy"
            )
    opts = ["RandomS", str(seed)] if seed is not None else []
    return pulp.PULP_CBC_CMD(timeLimit=limite, msg=1, options=opts)


def _resolver_con_solver(prob, solver) -> dict:
    """
    Resuelve prob con el solver dado capturando el log.
    Devuelve el mismo esquema que _mp.resolver().
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        prob.solve(solver)
    log = buf.getvalue()
    return {
        "estado_pulp": pulp.LpStatus[prob.status],
        "optimo_probado": "Result - Optimal solution found" in log,
        "corto_por_tiempo": "Stopped on time limit" in log,
        "gap": _mp._leer_gap(log),
        "log": log,
    }


def _describir_estado(res: dict) -> str:
    if res["optimo_probado"]:
        return "Óptimo probado"
    gap = res.get("gap")
    if res.get("corto_por_tiempo"):
        return (
            f"Límite de tiempo alcanzado, gap {gap:.2f}%"
            if gap is not None
            else "Límite de tiempo alcanzado, gap desconocido"
        )
    return f"Estado PuLP: {res['estado_pulp']}"


# =============================================================================
# API pública
# =============================================================================


def resolver_prestow(
    ruta_datos: str | Path,
    ruta_capacidades: str | Path | None = None,
    limite_segundos: int = 180,
    solver: str = "HiGHS",
    seed: int | None = None,
) -> ResultadoCorrida:
    """
    Corre el modelo de prestow sobre los datos indicados y retorna un
    ResultadoCorrida estructurado, sin dejar el estado global de modelo_prestow
    modificado entre llamadas.

    Parámetros
    ----------
    ruta_datos:
        Excel (.xlsx) o carpeta con CSV de entrada (buque_*, productos_*,
        viaje_*, rotacion_*).
    ruta_capacidades:
        Tabla de capacidades generada por packer_2d.py. Si es None se usa
        data/capacidades.csv relativo a la raíz del proyecto.
    limite_segundos:
        Límite de tiempo del solver en segundos, por pasada.
    solver:
        "HiGHS" (por defecto) o "CBC".
    seed:
        Semilla para el solver. Solo es efectiva con HiGHS >= 1.7 vía PuLP >= 2.9
        o con CBC. Si la versión instalada no la soporta, se ignora sin error.

    Raises
    ------
    ValueError
        Si los datos de entrada son incoherentes o si el solver no encontró
        ninguna solución factible dentro del límite de tiempo.
    """
    ruta_datos = Path(ruta_datos)
    if ruta_capacidades is None:
        ruta_capacidades = _DEFAULT_CAPACIDADES
    ruta_capacidades = Path(ruta_capacidades)

    with _lock:
        estado_original = _guardar_globals()
        t_inicio = time.perf_counter()

        try:
            # 1. Cargar datos (modifica globales del módulo)
            _mp.cargar_datos(str(ruta_datos))
            _mp.cargar_capacidades(str(ruta_capacidades))

            # 2. Validar coherencia
            errores = _mp.verificar_datos()
            if errores:
                raise ValueError(
                    "Datos de entrada inválidos:\n"
                    + "\n".join(f"  - {e}" for e in errores)
                )

            # 3. Construir modelo MILP
            prob, x, y, z, w, v, T_max, combos = _mp.construir_modelo()

            # 4. Pasada 1: minimizar makespan
            solver_p1 = _construir_solver(solver, limite_segundos, seed)
            res1 = _resolver_con_solver(prob, solver_p1)

            if T_max.value() is None or T_max.value() <= 0:
                raise ValueError(
                    f"El solver no encontró ninguna solución factible en "
                    f"{limite_segundos} s. Sube el límite con limite_segundos=..."
                )

            makespan_p1 = T_max.value()
            solucion_p1 = _mp.capturar_solucion(prob)
            t_tras_p1 = time.perf_counter()

            # 5. Pasada 2: fijar makespan y minimizar términos secundarios
            hay_secundario = _mp.preparar_pasada2(prob, z, w, v, T_max, makespan_p1)
            res_final = res1
            t_fin = t_tras_p1

            if hay_secundario:
                solver_p2 = _construir_solver(solver, limite_segundos, seed)
                res2 = _resolver_con_solver(prob, solver_p2)
                t_fin = time.perf_counter()

                if T_max.value() is None or T_max.value() <= 0:
                    # La pasada 2 no resolvió; conservar la de la pasada 1
                    _mp.restaurar_solucion(prob, solucion_p1)
                    res_final = res1
                else:
                    res_final = res2

            # 6. Extraer el plan
            filas_raw = _mp.extraer_plan(x, z, combos)
            horas = _mp.horas_por_cuadrilla(z)

            plan = [
                FilaPlan(
                    bodega=f["bodega"],
                    plan=f["plan"],
                    producto=f["producto"],
                    destino=f["destino"],
                    unidades=f["unidades"],
                )
                for f in filas_raw
            ]

            izadas_por_capa: dict[tuple[int, int], int] = {
                (h, t): int(round(z[(h, t)].value()))
                for h in _mp.BODEGAS
                for t in _mp.PLANES
                if (z[(h, t)].value() or 0) > 0.5
            }

            # 7. KPIs
            makespan_final = T_max.value()
            prom_horas = sum(horas.values()) / len(horas) if horas else 0.0
            desbalance = (
                (max(horas.values()) - min(horas.values())) / prom_horas * 100
                if prom_horas > 0
                else 0.0
            )

            frag_bodegas: dict[str, set] = defaultdict(set)
            for f in filas_raw:
                frag_bodegas[f["destino"]].add(f["bodega"])
            fragmentacion = sum(len(b) for b in frag_bodegas.values())

            kpis: dict[str, float] = {
                "makespan_h": round(makespan_final, 4),
                "desbalance_pct": round(desbalance, 2),
                "fragmentacion_bodegas_destino": float(fragmentacion),
                "izadas_totales": float(sum(izadas_por_capa.values())),
                "unidades_totales": float(sum(f["unidades"] for f in filas_raw)),
            }

            # 8. Verificaciones de coherencia
            verificaciones: dict[str, list] = {
                "no_overstowage": _mp.verificar_no_overstowage(filas_raw),
                "cobertura": _mp.verificar_cobertura(filas_raw),
                "contiguidad": _mp.verificar_contiguidad(filas_raw),
                "capacidad": _mp.verificar_capacidad(filas_raw),
            }

            return ResultadoCorrida(
                makespan=makespan_final,
                horas_por_cuadrilla=horas,
                plan=plan,
                izadas_por_capa=izadas_por_capa,
                kpis=kpis,
                verificaciones=verificaciones,
                estado_solver=_describir_estado(res_final),
                gap=res_final.get("gap"),
                tiempo_solver_s=round(t_fin - t_inicio, 1),
            )

        finally:
            _restaurar_globals(estado_original)
