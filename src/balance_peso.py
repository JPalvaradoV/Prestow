"""
Balance de peso por bodega — módulo informativo.

Calcula peso y densidad por bodega a partir del plan de estiba. El resultado
es solo para visualizar en la web; no es una restricción del modelo.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

try:
    from .api import FilaPlan
except ImportError:
    from api import FilaPlan  # type: ignore[import]


@dataclass
class BalancePeso:
    peso_por_bodega: dict[int, float]
    """Toneladas totales por bodega."""

    densidad_por_bodega: dict[int, float]
    """
    t/m² del piso de la bodega.
    Si no se entrega la geometría, se calcula sobre el área ocupada por la
    carga, no sobre el área total del piso.
    """

    dispersion_relativa: float
    """(máx - mín) / promedio de la densidad entre bodegas, en %."""

    bodega_mas_cargada: int
    """Bodega con mayor peso total."""

    bodega_menos_cargada: int
    """Bodega con menor peso total."""


def calcular_balance(
    plan: list[FilaPlan],
    huellas: dict[str, tuple[float, float]],
    peso_unidad_t: float = 2.02,
    geometria: dict[int, tuple[float, float]] | None = None,
) -> BalancePeso:
    """
    Calcula el balance de peso a partir de un plan de estiba.

    Parámetros
    ----------
    plan:
        Lista de FilaPlan (salida de resolver_prestow).
    huellas:
        Dimensiones de cada producto: {nombre: (largo_m, ancho_m)}.
    peso_unidad_t:
        Peso por unidad en toneladas. Se asume constante para todos los
        productos (supuesto del caso base: 2,02 t/u).
    geometria:
        Dimensiones del piso por bodega: {bodega: (largo_m, ancho_m)}.
        Si es None, la densidad se calcula sobre el área ocupada por la carga
        en vez de sobre el área total del piso.

    Returns
    -------
    BalancePeso con peso, densidad y métricas de dispersión por bodega.
    """
    # Acumular unidades y área ocupada por bodega
    unidades_por_bodega: dict[int, int] = defaultdict(int)
    area_ocupada_por_bodega: dict[int, float] = defaultdict(float)

    for fila in plan:
        l, w = huellas[fila.producto]
        unidades_por_bodega[fila.bodega] += fila.unidades
        area_ocupada_por_bodega[fila.bodega] += fila.unidades * l * w

    bodegas_con_carga = sorted(unidades_por_bodega)

    # Peso total por bodega
    peso_por_bodega = {
        h: unidades_por_bodega[h] * peso_unidad_t for h in bodegas_con_carga
    }

    # Densidad por bodega (t/m² del piso o del área ocupada)
    densidad_por_bodega: dict[int, float] = {}
    for h in bodegas_con_carga:
        if geometria is not None and h in geometria:
            largo, ancho = geometria[h]
            area_ref = largo * ancho
        else:
            area_ref = area_ocupada_por_bodega[h]

        densidad_por_bodega[h] = (
            peso_por_bodega[h] / area_ref if area_ref > 0 else 0.0
        )

    # Dispersión relativa sobre la densidad
    densidades = list(densidad_por_bodega.values())
    if len(densidades) > 1:
        media = sum(densidades) / len(densidades)
        dispersion = (max(densidades) - min(densidades)) / media * 100 if media > 0 else 0.0
    else:
        dispersion = 0.0

    bodega_mas = max(peso_por_bodega, key=lambda h: peso_por_bodega[h])
    bodega_menos = min(peso_por_bodega, key=lambda h: peso_por_bodega[h])

    return BalancePeso(
        peso_por_bodega=dict(peso_por_bodega),
        densidad_por_bodega=densidad_por_bodega,
        dispersion_relativa=round(dispersion, 2),
        bodega_mas_cargada=bodega_mas,
        bodega_menos_cargada=bodega_menos,
    )
