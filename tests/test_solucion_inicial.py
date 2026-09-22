"""
Tests del heuristico de solucion inicial (warm start de la pasada 1),
agregado el 22 de septiembre de 2026 -- ver docs/05_Estado_app_web.md y el
docstring de src/solucion_inicial.py para el porque.

Cubre: que la asignacion heuristica sea factible sobre el caso base real
(cobertura exacta, y CERO violaciones contra TODAS las restricciones del
modelo real -- no solo las 4 verificar_*), y que el diccionario final quede
completo (una entrada por variable del problema).
"""

import api
import modelo_prestow as mp
import solucion_inicial as si


def _cargar_caso_base():
    mp.CAPACIDAD = {}
    mp.CAPACIDAD_POR_PLAN = {}
    mp.cargar_capacidades("data/capacidades.csv")
    mp.cargar_capacidades_por_plan("data/capacidades_reales_por_plan.csv")


def test_asignacion_heuristica_cubre_toda_la_demanda():
    _cargar_caso_base()
    asignacion = si.construir_asignacion_heuristica()
    assert asignacion is not None
    assert sum(asignacion.values()) == sum(mp.DEMANDA.values())


def test_asignacion_heuristica_no_viola_ninguna_restriccion_real():
    """La prueba mas importante: arma el problema real (construir_modelo) y
    evalua TODAS sus restricciones contra la asignacion heuristica -- no solo
    las 4 que cubren verificar_cobertura/capacidad/contiguidad/
    no_overstowage. Se detecto en la practica (22-sep-2026) que pasar esas 4
    no alcanzaba: el heuristico violaba la restriccion (5b) y, despues de
    corregir eso, la (5d) -- ver el docstring del modulo."""
    _cargar_caso_base()
    prob, x, y, z, w, v, T_max, combos, peso_max, peso_min = mp.construir_modelo()
    asignacion = si.construir_asignacion_heuristica()
    assert asignacion is not None

    valores = si._construir_valores(asignacion, x, y, w, z, v, T_max, peso_max, peso_min)
    violaciones = si._violaciones(prob, valores)
    assert violaciones == []


def test_construir_solucion_inicial_devuelve_valor_para_cada_variable():
    _cargar_caso_base()
    prob, x, y, z, w, v, T_max, combos, peso_max, peso_min = mp.construir_modelo()
    valores = si.construir_solucion_inicial(prob, x, y, w, z, v, T_max, peso_max, peso_min, combos)
    assert valores is not None
    nombres_variables = {var.name for var in prob.variables()}
    assert set(valores.keys()) == nombres_variables


def test_construir_solucion_inicial_T_max_coherente_con_izadas():
    """El T_max del warm start tiene que ser >= lo que exige la restriccion
    (7) para cada cuadrilla, calculado a partir de las mismas izadas (z) que
    quedaron en el diccionario -- si no, HiGHS lo rechaza de entrada."""
    _cargar_caso_base()
    prob, x, y, z, w, v, T_max, combos, peso_max, peso_min = mp.construir_modelo()
    valores = si.construir_solucion_inicial(prob, x, y, w, z, v, T_max, peso_max, peso_min, combos)
    assert valores is not None

    for g, bodegas_g in mp.CUADRILLAS.items():
        horas_g = sum(
            valores[z[(h, t)].name] * mp.tiempo_ciclo(h) for h in bodegas_g for t in mp.PLANES
        )
        assert valores[T_max.name] >= horas_g - 1e-6


def test_asignacion_heuristica_contra_datos_cargados_desde_excel():
    """Regresion (22-sep-2026): con los globales del modulo cargados via
    cargar_datos() (el camino real de api.resolver_prestow(), que es lo que
    usa la web) en vez de los valores harcodeados de modelo_prestow.py, el
    heuristico violaba una restriccion de no-overstowage y otra de llenado
    minimo que no aparecian con los globales por defecto -- ver el reparo de
    simetria en solucion_inicial.py, que movia unidades sin chequear esas
    dos restricciones. No alcanza con probar solo el caso harcodeado."""
    estado_original = api._guardar_globals()
    try:
        mp.CAPACIDAD = {}
        mp.CAPACIDAD_POR_PLAN = {}
        mp.cargar_datos("data/datos_entrada_kiwi_arrow.xlsx")
        mp.cargar_capacidades("data/capacidades.csv")
        mp.cargar_capacidades_por_plan("data/capacidades_reales_por_plan.csv")

        prob, x, y, z, w, v, T_max, combos, peso_max, peso_min = mp.construir_modelo()
        asignacion = si.construir_asignacion_heuristica()
        assert asignacion is not None
        assert sum(asignacion.values()) == sum(mp.DEMANDA.values())

        valores = si._construir_valores(asignacion, x, y, w, z, v, T_max, peso_max, peso_min)
        assert si._violaciones(prob, valores) == []
    finally:
        api._restaurar_globals(estado_original)


def test_sin_demanda_no_rompe():
    mp.CAPACIDAD = {}
    mp.CAPACIDAD_POR_PLAN = {}
    demanda_original = dict(mp.DEMANDA)
    try:
        mp.DEMANDA = {}
        assert si.construir_asignacion_heuristica() is None
    finally:
        mp.DEMANDA = demanda_original
