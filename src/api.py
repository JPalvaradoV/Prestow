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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pulp

try:
    from . import modelo_prestow as _mp
    from . import solucion_inicial as _si
except ImportError:
    import modelo_prestow as _mp  # type: ignore[import]
    import solucion_inicial as _si  # type: ignore[import]

# Un lock por proceso: garantiza que dos corridas no pisen los globales del módulo
# simultáneamente. Streamlit puede tener varias sesiones, pero las corridas se
# encolan. El lock dura todo el tiempo del solver; es intencional.
_lock = threading.Lock()

# Umbral por debajo del cual la pasada 1 usa el warm start heurístico. Vive
# en modelo_prestow (lo usa también la CLI); ver su comentario.
UMBRAL_WARM_START_PASADA1 = _mp.UMBRAL_WARM_START_PASADA1

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
    "PESO",
    "PISO",
    "AREA",
    "DEMANDA",
    "CAPACIDAD",
    "CAPACIDAD_POR_PLAN",
]

# Ruta absoluta al directorio raíz del proyecto (src/../)
_RAIZ = Path(__file__).parent.parent
_DEFAULT_CAPACIDADES = _RAIZ / "data" / "capacidades.csv"
_DEFAULT_CAPACIDADES_POR_PLAN = _RAIZ / "data" / "capacidades_reales_por_plan.csv"


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
    excel_bytes: bytes
    """
    Excel con el formato visual del prestow (modelo_prestow.exportar_excel):
    Plan de estiba coloreado, Detalle y Indicadores. Se genera aquí, con el
    lock tomado, porque exportar_excel() lee BODEGAS/PLANES/DESTINOS/ROT/
    HUELLA/CUADRILLAS de los globales del módulo — fuera de resolver_prestow
    esos globales ya no corresponden necesariamente a esta corrida.
    """
    gaps_por_pasada: dict[int, float | None] = field(default_factory=dict)
    """
    Gap final (%) de cada pasada que entregó solución: 1 = makespan,
    2 = izadas+fragmentación, 3 = balance de peso. `gap` es el de la última.
    """


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
    return _mp.diagnosticar_resolucion(prob, solver, buf.getvalue())


def _resolver_con_warm_start(prob, solver, solucion_inicial: dict) -> dict:
    """
    Como _resolver_con_solver, pero le pasa a HiGHS la solución de la pasada
    anterior como punto de partida (MIP start) en vez de dejarlo buscar una
    solución factible desde cero.

    POR QUÉ HACE FALTA: PuLP no expone warm start para HiGHS en esta versión
    (pulp.HiGHS.actualSolve() siempre reconstruye el modelo desde cero y no
    acepta un punto inicial). Se prueba empíricamente que sin esto, la pasada
    de balance de peso no encuentra NINGUNA solución factible ni en 900 s,
    pese a que la solución de la pasada anterior ya es una — el problema no
    es el tiempo, es que HiGHS tiene que redescubrir la factibilidad por su
    cuenta después de que se retira la ruptura de simetría.

    La mecánica (inyectar la solución vía highspy) vive en
    modelo_prestow.resolver_highs_con_punto_inicial, compartida con la CLI.

    SOLO sirve con pulp.HiGHS: usa métodos internos de esa clase que CBC no
    tiene. Si solver no es una instancia de pulp.HiGHS, resuelve sin warm
    start (igual que _resolver_con_solver).
    """
    if not isinstance(solver, pulp.HiGHS):
        return _resolver_con_solver(prob, solver)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _mp.resolver_highs_con_punto_inicial(prob, solver, solucion_inicial)

    return _mp.diagnosticar_resolucion(prob, solver, buf.getvalue())


def _describir_estado(res: dict) -> str:
    gap = res.get("gap")
    if res["optimo_probado"]:
        # HiGHS declara óptimo con gap <= 0,01% (su tolerancia por defecto):
        # solo se dice "óptimo" sin matices cuando el gap es exactamente cero.
        if gap is not None and gap > 0:
            return f"Resuelto dentro de la tolerancia del solver, gap {gap:.2f}%"
        return "Óptimo probado"
    if res.get("corto_por_tiempo"):
        return (
            f"Límite de tiempo alcanzado, gap {gap:.2f}%"
            if gap is not None
            else "Límite de tiempo alcanzado, gap desconocido"
        )
    if res["estado_pulp"] == "Optimal":
        # PuLP dice "Optimal" aun sin óptimo probado (CLAUDE.md sección 8)
        return "Solución factible, sin optimalidad probada"
    return f"Estado PuLP: {res['estado_pulp']}"


# =============================================================================
# API pública
# =============================================================================


def resolver_prestow(
    ruta_datos: str | Path,
    ruta_capacidades: str | Path | None = None,
    limite_segundos: int = 180,
    limite_segundos_balance: int | None = None,
    solver: str = "HiGHS",
    seed: int | None = None,
    progreso: Callable[[str], None] | None = None,
    nombre_buque: str | None = None,
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
        Límite de tiempo del solver en segundos, para las pasadas 1 y 2
        (makespan e izadas+fragmentación).
    limite_segundos_balance:
        Límite de tiempo en segundos para la pasada 3 (balance de peso, ver
        modelo_prestow.USAR_BALANCE_PESO y ETAPAS_BALANCE_PESO). Con la
        configuración final (1 sola etapa, la carga inicial) converge bien
        en el mismo tiempo que las pasadas 1 y 2 — se probó con las 4 etapas
        completas darle más tiempo (hasta 900 s) y no ayudó, así que no hace
        falta un límite mayor por defecto. Si es None, usa limite_segundos.
    solver:
        "HiGHS" (por defecto) o "CBC".
    seed:
        Semilla para el solver. Solo es efectiva con HiGHS >= 1.7 vía PuLP >= 2.9
        o con CBC. Si la versión instalada no la soporta, se ignora sin error.
    progreso:
        Callback opcional, llamado con un mensaje corto en español en cada
        etapa (carga de datos, cada pasada). Pensado para que la web muestre
        avance en vivo en vez de un spinner ciego durante los minutos que
        puede tardar el solver — ver app/pages/1_Ejecutar.py, que lo llama
        desde un hilo aparte y va mostrando el último mensaje recibido.
    nombre_buque:
        Nombre del buque evaluado, para el encabezado del Excel. Si es None,
        el Excel dice "sin nombre".

    Raises
    ------
    ValueError
        Si los datos de entrada son incoherentes o si el solver no encontró
        ninguna solución factible dentro del límite de tiempo.
    """
    def _avisar(mensaje: str) -> None:
        if progreso is not None:
            progreso(mensaje)

    if limite_segundos_balance is None:
        limite_segundos_balance = limite_segundos
    ruta_datos = Path(ruta_datos)
    if ruta_capacidades is None:
        ruta_capacidades = _DEFAULT_CAPACIDADES
    ruta_capacidades = Path(ruta_capacidades)

    with _lock:
        estado_original = _guardar_globals()
        t_inicio = time.perf_counter()

        try:
            # 1. Cargar datos (modifica globales del módulo)
            _avisar("Cargando datos de entrada…")
            _mp.cargar_datos(str(ruta_datos))
            _mp.cargar_capacidades(str(ruta_capacidades))
            # Capacidades reales por plan (ver modelo_prestow.CAPACIDAD_POR_PLAN):
            # solo pisa combinaciones (bodega, plan, producto) que coincidan
            # exactamente: si el caso es editado (otros nombres de producto,
            # otras bodegas) simplemente no aplica, sin romper nada.
            _mp.cargar_capacidades_por_plan(str(_DEFAULT_CAPACIDADES_POR_PLAN))

            # 2. Validar coherencia
            errores = _mp.verificar_datos()
            if errores:
                raise ValueError(
                    "Datos de entrada inválidos:\n"
                    + "\n".join(f"  - {e}" for e in errores)
                )

            # 3. Construir modelo MILP
            _avisar("Construyendo el modelo…")
            prob, x, y, z, w, v, T_max, combos, peso_max, peso_min = _mp.construir_modelo()

            # 4. Pasada 1: minimizar makespan
            # Warm start heurístico SOLO por debajo de UMBRAL_WARM_START_PASADA1
            # (ver su comentario): sin él, HiGHS puede tardar más de 120 s solo
            # en encontrar la PRIMERA solución entera factible para este modelo
            # (contiguidad + no-overstowage + llenado mínimo lo hacen difícil
            # para sus heurísticas internas) — con límites bajos simplemente no
            # llega. Pero a partir del umbral, el warm start ancla la búsqueda
            # cerca de su propio punto de partida y termina PEOR que dejar al
            # solver buscar desde cero — así que ahí no se usa. Ver
            # src/solucion_inicial.py para el detalle y las verificaciones que
            # se corren antes de usarlo. Si el heurístico no encuentra o no
            # pasa las verificaciones, devuelve None y se resuelve sin él
            # (igual que antes) — nunca se inyecta una solución sin validar.
            solucion_inicial_p1 = None
            if limite_segundos < UMBRAL_WARM_START_PASADA1:
                _avisar("Preparando punto de partida…")
                solucion_inicial_p1 = _si.construir_solucion_inicial(
                    prob, x, y, w, z, v, T_max, peso_max, peso_min, combos
                )

            solver_p1 = _construir_solver(solver, limite_segundos, seed)
            if solucion_inicial_p1 is not None:
                _avisar(f"Pasada 1 de 3 — makespan (hasta {limite_segundos} s, con punto de partida)…")
                res1 = _resolver_con_warm_start(prob, solver_p1, solucion_inicial_p1)
            else:
                _avisar(f"Pasada 1 de 3 — makespan (hasta {limite_segundos} s)…")
                res1 = _resolver_con_solver(prob, solver_p1)

            if T_max.value() is None or T_max.value() <= 0:
                detalle_gap = (
                    f" Mejor cota encontrada: gap {res1['gap']:.1f}%."
                    if res1.get("gap") is not None
                    else ""
                )
                raise ValueError(
                    f"El solver no encontró ninguna solución factible en "
                    f"{limite_segundos} s.{detalle_gap} Sube el límite e intenta de nuevo "
                    f"(180 s por pasada es lo mínimo verificado para el caso base)."
                )

            makespan_p1 = T_max.value()
            solucion_p1 = _mp.capturar_solucion(prob)
            t_tras_p1 = time.perf_counter()

            # 5. Pasada 2: fijar makespan y minimizar términos secundarios
            hay_secundario = _mp.preparar_pasada2(prob, z, w, v, T_max, makespan_p1)
            res_final = res1
            gaps_por_pasada = {1: res1.get("gap")}
            t_fin = t_tras_p1
            pasada3_exitosa = False

            if hay_secundario:
                # Warm start desde la pasada 1: sin esto, pulp.HiGHS.actualSolve()
                # reconstruye el modelo desde cero y la pasada 2 tiene que
                # redescubrir la factibilidad por su cuenta bajo la nueva
                # restricción de makespan — el mismo problema que motivó el
                # warm start de la pasada 3, y probablemente la causa real del
                # pendiente "la pasada 2 no resuelve en 150-180 s".
                _avisar(f"Pasada 2 de 3 — izadas y fragmentación (hasta {limite_segundos} s)…")
                solver_p2 = _construir_solver(solver, limite_segundos, seed)
                res2 = _resolver_con_warm_start(prob, solver_p2, solucion_p1)
                t_fin = time.perf_counter()

                if T_max.value() is None or T_max.value() <= 0:
                    # La pasada 2 no resolvió; conservar la de la pasada 1
                    _mp.restaurar_solucion(prob, solucion_p1)
                    res_final = res1
                else:
                    res_final = res2
                    gaps_por_pasada[2] = res2.get("gap")

                    # 5b. Pasada 3: fijar izadas+fragmentación y balancear peso
                    valor_pasada2 = pulp.value(prob.objective)
                    solucion_p2 = _mp.capturar_solucion(prob)
                    hay_terciario = _mp.preparar_pasada3(
                        prob, z, w, v, peso_max, peso_min, valor_pasada2
                    )

                    if hay_terciario:
                        _avisar(
                            f"Pasada 3 de 3 — balance de peso (hasta {limite_segundos_balance} s)…"
                        )
                        solver_p3 = _construir_solver(solver, limite_segundos_balance, seed)
                        res3 = _resolver_con_warm_start(prob, solver_p3, solucion_p2)
                        t_fin = time.perf_counter()

                        if T_max.value() is None or T_max.value() <= 0:
                            # La pasada 3 no resolvió; conservar la de la pasada 2
                            # (sus peso_max/peso_min no fueron minimizados: no son
                            # un balance real, así que el KPI no se informa)
                            _mp.restaurar_solucion(prob, solucion_p2)
                            res_final = res2
                        else:
                            res_final = res3
                            gaps_por_pasada[3] = res3.get("gap")
                            pasada3_exitosa = True

            # 6. Extraer el plan
            _avisar("Extrayendo el plan y armando el Excel…")
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

            # Desbalance de peso por etapa del viaje (suma de max-min de cada
            # etapa, en toneladas). Solo se informa si la pasada 3 realmente
            # resolvió: si no, peso_max/peso_min quedan en un valor factible
            # cualquiera de la pasada 2 (nunca se minimizaron) y reportarlo
            # sería un número sin sentido, no un balance real.
            if pasada3_exitosa and all(pm.value() is not None for pm in peso_max.values()):
                kpis["balance_peso_desbalance_ton"] = round(
                    sum(peso_max[k].value() - peso_min[k].value() for k in peso_max), 2
                )

            # 8. Verificaciones de coherencia
            verificaciones: dict[str, list] = {
                "no_overstowage": _mp.verificar_no_overstowage(filas_raw),
                "cobertura": _mp.verificar_cobertura(filas_raw),
                "contiguidad": _mp.verificar_contiguidad(filas_raw),
                "capacidad": _mp.verificar_capacidad(filas_raw),
            }

            # 9. Excel con el formato del prestow — con los globales todavía
            # cargados con los datos de esta corrida (ver docstring del campo).
            buf_excel = io.BytesIO()
            _mp.exportar_excel(
                filas_raw, horas, makespan_final, ruta=buf_excel,
                nombre_buque=nombre_buque or "sin nombre",
            )
            buf_excel.seek(0)
            excel_bytes = buf_excel.read()

            return ResultadoCorrida(
                makespan=makespan_final,
                horas_por_cuadrilla=horas,
                plan=plan,
                izadas_por_capa=izadas_por_capa,
                kpis=kpis,
                verificaciones=verificaciones,
                estado_solver=_describir_estado(res_final),
                gap=res_final.get("gap"),
                gaps_por_pasada=gaps_por_pasada,
                tiempo_solver_s=round(t_fin - t_inicio, 1),
                excel_bytes=excel_bytes,
            )

        finally:
            _restaurar_globals(estado_original)
