"""
Tests de la comparación contra el plan de referencia (app/components/referencia.py):
los KPIs clave que el usuario ingresa en Configuración en vez de las cifras
fijas del Kiwi Arrow que había antes.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from components.referencia import (  # noqa: E402
    KPIS_REFERENCIA,
    REFERENCIA_KIWI_ARROW,
    comparar,
    formatear,
    hay_referencia,
    referencia_vacia,
)


def _resultado(makespan=59.6702, desbalance=9.36, frag=10.0, izadas=1844.0):
    return SimpleNamespace(
        makespan=makespan,
        kpis={
            "desbalance_pct": desbalance,
            "fragmentacion_bodegas_destino": frag,
            "izadas_totales": izadas,
        },
    )


def test_caso_base_contra_plan_manual_kiwi_arrow():
    # Tabla de CLAUDE.md sección 3: makespan y fragmentación mejores,
    # desbalance peor; izadas del plan manual sin dato.
    filas = {c["kpi"].clave: c for c in comparar(_resultado(), REFERENCIA_KIWI_ARROW)}
    assert filas["makespan_h"]["veredicto"] == "mejor"
    assert round(filas["makespan_h"]["diferencia"], 2) == -0.94
    assert filas["desbalance_pct"]["veredicto"] == "peor"
    assert filas["fragmentacion"]["veredicto"] == "mejor"
    assert filas["fragmentacion"]["diferencia"] == -4
    assert filas["izadas"]["referencia"] is None
    assert filas["izadas"]["veredicto"] is None


def test_sin_referencia_no_compara():
    assert not hay_referencia(None)
    assert not hay_referencia(referencia_vacia())
    assert all(c["veredicto"] is None for c in comparar(_resultado(), None))


def test_referencia_parcial_solo_compara_lo_ingresado():
    ref = referencia_vacia() | {"izadas": 1900}
    assert hay_referencia(ref)
    filas = comparar(_resultado(), ref)
    assert [c["veredicto"] for c in filas] == [None, None, None, "mejor"]


def test_igual_dentro_de_la_precision_mostrada():
    ref = referencia_vacia() | {"makespan_h": 59.67}
    fila = comparar(_resultado(makespan=59.6702), ref)[0]
    assert fila["veredicto"] == "igual"


def test_formato_con_coma_decimal():
    makespan, desbalance, frag, izadas = KPIS_REFERENCIA
    assert formatear(60.61, makespan) == "60,61 h"
    assert formatear(6.9, desbalance) == "6,9%"
    assert formatear(1844, izadas) == "1.844"
    assert formatear(None, frag) == "—"


def test_cero_es_sin_dato_salvo_en_desbalance():
    ref = {"makespan_h": 0, "desbalance_pct": 0, "fragmentacion": 0, "izadas": 0}
    filas = {c["kpi"].clave: c for c in comparar(_resultado(), ref)}
    assert filas["makespan_h"]["referencia"] is None
    assert filas["fragmentacion"]["referencia"] is None
    assert filas["izadas"]["referencia"] is None
    assert filas["desbalance_pct"]["referencia"] == 0
    assert filas["desbalance_pct"]["veredicto"] == "peor"
    assert hay_referencia(ref)
    assert not hay_referencia({"makespan_h": 0, "izadas": 0})
