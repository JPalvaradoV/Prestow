"""
Tests de la capa de resolucion compartida por la CLI y la web (24-sep-2026):

- diagnosticar_resolucion: con HiGHS, el estado y el gap se leen del objeto
  highspy, no del log (HiGHS escribe desde C y redirect_stdout no captura
  nada; antes el gap quedaba siempre en None).
- resolver_highs_con_punto_inicial: el MIP start se acepta y no cambia el
  resultado de un problema chico.
- _ruta_con_respaldo: la CLI encuentra las capacidades en data/ aunque se
  corra desde otro directorio.
- api._describir_estado: nunca dice "óptimo" sin gap cero.

Son problemas chicos: no corren el modelo completo.
"""

import pulp

import api
import modelo_prestow as mp


def _problema_chico():
    prob = pulp.LpProblem("chico", pulp.LpMinimize)
    a = pulp.LpVariable("a", 0, 10, cat="Integer")
    b = pulp.LpVariable("b", 0, 10, cat="Integer")
    prob += 3 * a + 2 * b
    prob += a + b >= 4
    prob += a - b <= 1
    return prob, a, b


def test_highs_log_no_se_captura_pero_el_gap_si():
    prob, _, _ = _problema_chico()
    res = mp.resolver(prob, limite=10)
    # El log de HiGHS no pasa por sys.stdout: si esto cambia en una versión
    # futura de highspy, el diagnóstico sigue funcionando igual.
    assert res["optimo_probado"] is True
    assert res["corto_por_tiempo"] is False
    assert res["gap"] == 0.0
    assert pulp.value(prob.objective) == 8


def test_punto_inicial_factible_llega_al_mismo_optimo():
    prob, a, b = _problema_chico()
    # (a, b) = (0, 10): factible pero lejos del óptimo (0, 4)
    res = mp.resolver(prob, limite=10, solucion_inicial={"a": 0, "b": 10})
    assert res["optimo_probado"] is True
    assert (a.value(), b.value()) == (0, 4)


def test_cbc_ignora_punto_inicial_y_lee_el_log(monkeypatch):
    monkeypatch.setattr(mp, "SOLVER", "CBC")
    prob, _, _ = _problema_chico()
    res = mp.resolver(prob, limite=10, solucion_inicial={"a": 0, "b": 10})
    assert res["estado_pulp"] == "Optimal"
    assert pulp.value(prob.objective) == 8


def test_capacidades_se_encuentran_desde_otro_directorio(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mp, "CAPACIDAD", {})
    monkeypatch.setattr(mp, "CAPACIDAD_POR_PLAN", {})
    assert mp.cargar_capacidades() is True
    assert mp.cargar_capacidades_por_plan() is True
    assert len(mp.CAPACIDAD) == 40
    assert len(mp.CAPACIDAD_POR_PLAN) == 72


def test_describir_estado_no_dice_optimo_sin_gap_cero():
    base = {"estado_pulp": "Optimal", "corto_por_tiempo": False}
    assert api._describir_estado({**base, "optimo_probado": True, "gap": 0.0}) == "Óptimo probado"
    con_tolerancia = api._describir_estado({**base, "optimo_probado": True, "gap": 0.008})
    assert "Óptimo" not in con_tolerancia and "0.01%" in con_tolerancia
    sin_prueba = api._describir_estado({**base, "optimo_probado": False, "gap": None})
    assert "Optimal" not in sin_prueba and "Óptimo" not in sin_prueba
    por_tiempo = api._describir_estado(
        {**base, "optimo_probado": False, "corto_por_tiempo": True, "gap": 3.29}
    )
    assert por_tiempo == "Límite de tiempo alcanzado, gap 3.29%"
