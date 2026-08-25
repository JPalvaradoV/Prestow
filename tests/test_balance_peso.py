"""
Tests de src/balance_peso.py.

Cubre dos casos:
  1. Plan manual del Kiwi Arrow (datos reales): verifica que la dispersión
     de densidad sea ~19% (coherente con el 18,9% documentado en CLAUDE.md).
  2. Caso trivial: todas las bodegas con idéntica carga → dispersión = 0.
"""

import pytest
from api import FilaPlan
from balance_peso import BalancePeso, calcular_balance

# Geometría del Kiwi Arrow (CLAUDE.md, sección 9)
GEOMETRIA_KIWI = {h: (18.30, 27.40) for h in range(2, 9)}
GEOMETRIA_KIWI[1] = (16.80, 14.80)

# Huellas verificadas (CLAUDE.md, sección 9)
HUELLAS_KIWI = {
    "N_ALDEA_EKP": (0.84, 1.47),
    "N_ALDEA_BKP": (0.84, 1.48),
    "ARAUCO_EKP": (0.89, 1.41),
    "ARAUCO_BKP": (0.84, 1.47),
    "CELCO_UKP": (0.84, 1.43),
}


def _plan_manual_kiwi() -> list[FilaPlan]:
    """
    Plan manual del caso base: unidades por bodega de CLAUDE.md, sección 9.
    Se modela como una sola capa por bodega para simplificar; el balance
    solo depende del total de unidades, no de la distribución entre planes.
    """
    unidades = {8: 3555, 7: 3863, 6: 4227, 5: 3672, 4: 3823, 3: 3661, 2: 4294, 1: 1962}
    return [
        FilaPlan(
            bodega=h,
            plan=1,
            producto="N_ALDEA_EKP",
            destino="TAICHUNG",
            unidades=u,
        )
        for h, u in unidades.items()
    ]


def test_dispersion_plan_manual():
    """
    Verifica que la dispersión de densidad del plan manual sea aproximadamente
    19% (el valor documentado en CLAUDE.md es 18,9%; se acepta ±1,5 pp).
    """
    plan = _plan_manual_kiwi()
    resultado = calcular_balance(plan, HUELLAS_KIWI, geometria=GEOMETRIA_KIWI)

    assert isinstance(resultado, BalancePeso)
    # Bodega 1 es siempre la menos cargada por unidades/peso
    assert resultado.bodega_menos_cargada == 1
    # Bodega 2 tiene el mayor número de unidades en el plan manual
    assert resultado.bodega_mas_cargada == 2
    # Dispersión de densidad ≈ 18,9% (tolerancia ±1,5 pp)
    assert resultado.dispersion_relativa == pytest.approx(19.1, abs=1.5)
    # Coherencia: todas las bodegas tienen peso positivo
    for h, peso in resultado.peso_por_bodega.items():
        assert peso > 0, f"Bodega {h} tiene peso no positivo: {peso}"
    # Pesos correctos: unidades × 2,02
    assert resultado.peso_por_bodega[1] == pytest.approx(1962 * 2.02, rel=1e-6)
    assert resultado.peso_por_bodega[8] == pytest.approx(3555 * 2.02, rel=1e-6)


def test_dispersion_cero_carga_identica():
    """
    Cuando todas las bodegas tienen exactamente la misma carga en el mismo
    producto y la misma geometría, la dispersión de densidad debe ser 0.
    """
    bodegas = [1, 2, 3, 4]
    geometria = {h: (18.0, 27.0) for h in bodegas}
    plan = [
        FilaPlan(bodega=h, plan=1, producto="N_ALDEA_EKP", destino="TAICHUNG", unidades=200)
        for h in bodegas
    ]
    huellas = {"N_ALDEA_EKP": (0.84, 1.47)}

    resultado = calcular_balance(plan, huellas, geometria=geometria)

    assert resultado.dispersion_relativa == pytest.approx(0.0, abs=1e-6)
    for h in bodegas:
        assert resultado.peso_por_bodega[h] == pytest.approx(200 * 2.02, rel=1e-6)
        assert resultado.densidad_por_bodega[h] == pytest.approx(
            resultado.densidad_por_bodega[bodegas[0]], rel=1e-6
        )
