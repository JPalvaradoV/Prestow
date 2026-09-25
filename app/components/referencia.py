"""
Plan de referencia: los KPIs clave del plan manual con que se cargó (o se
cargaría) el buque, ingresados por el usuario en Configuración. Resultados,
Ejecutar y el Excel comparan el plan del modelo contra estos valores.

Antes la comparación usaba cifras fijas del Kiwi Arrow (60,61 h, 6,9%, 14),
aunque el caso fuera otro buque. Ahora cada KPI de referencia es opcional:
si el usuario no lo tiene, simplemente no se compara ese KPI.

Sin dependencias de Streamlit: se puede testear directo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KpiReferencia:
    clave: str          # clave en el dict de referencia
    etiqueta: str       # texto para mostrar
    unidad: str         # "h", "%", "" ...
    decimales: int      # para mostrar y para el campo de entrada
    ayuda: str          # explicación para el usuario
    clave_modelo: str   # clave en ResultadoCorrida.kpis ("makespan" = resultado.makespan)
    cero_valido: bool = False  # solo el desbalance puede ser 0 (balance perfecto)


# Los 4 KPIs clave, en todos "menos es mejor".
KPIS_REFERENCIA: list[KpiReferencia] = [
    KpiReferencia(
        "makespan_h", "Makespan", "h", 2,
        "Horas de la cuadrilla más cargada: cuánto demora la carga completa del buque.",
        "makespan",
    ),
    KpiReferencia(
        "desbalance_pct", "Desbalance entre cuadrillas", "%", 1,
        "(horas de la cuadrilla más cargada − la menos cargada) / promedio de horas por cuadrilla, en %.",
        "desbalance_pct", cero_valido=True,
    ),
    KpiReferencia(
        "fragmentacion", "Fragmentación (bodegas × destino)", "", 0,
        "Suma, por destino, de cuántas bodegas llevan carga de ese destino.",
        "fragmentacion_bodegas_destino",
    ),
    KpiReferencia(
        "izadas", "Izadas totales", "", 0,
        "Veces que la grúa levanta un marco (hasta 16 unidades) en toda la carga.",
        "izadas_totales",
    ),
]

# Plan manual real del Kiwi Arrow (PRESTOW N° 06 del puerto, CLAUDE.md
# sección 3). Las izadas del plan manual no están documentadas: quedan en
# None en vez de inventar una cifra.
REFERENCIA_KIWI_ARROW: dict[str, float | None] = {
    "makespan_h": 60.61,
    "desbalance_pct": 6.9,
    "fragmentacion": 14,
    "izadas": None,
}


def normalizar(valor: float | None, kpi: KpiReferencia) -> float | int | None:
    """
    Valor tal como se guarda: None si no hay dato, o si es 0 en un KPI donde
    0 es imposible (makespan, fragmentación, izadas) — un campo que quedó en
    0 se trata como vacío, en vez de comparar contra 0 (y dividir por 0).
    """
    if valor is None or valor < 0 or (valor == 0 and not kpi.cero_valido):
        return None
    return int(round(valor)) if kpi.decimales == 0 else float(valor)


def referencia_vacia() -> dict[str, float | None]:
    return {k.clave: None for k in KPIS_REFERENCIA}


def hay_referencia(referencia: dict | None) -> bool:
    """True si hay al menos un KPI de referencia ingresado."""
    return bool(referencia) and any(
        normalizar(referencia.get(k.clave), k) is not None for k in KPIS_REFERENCIA
    )


def valor_modelo(resultado: object, kpi: KpiReferencia) -> float | None:
    if kpi.clave_modelo == "makespan":
        return resultado.makespan  # type: ignore[attr-defined]
    valor = resultado.kpis.get(kpi.clave_modelo)  # type: ignore[attr-defined]
    return float(valor) if valor is not None else None


def formatear(valor: float | None, kpi: KpiReferencia) -> str:
    """Formato con coma decimal, como el resto de la web."""
    if valor is None:
        return "—"
    texto = f"{valor:,.{kpi.decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto} {kpi.unidad}".strip() if kpi.unidad != "%" else f"{texto}%"


def comparar(resultado: object, referencia: dict | None) -> list[dict]:
    """
    Una fila por KPI clave: valor del modelo, valor de referencia (o None),
    diferencia modelo − referencia, diferencia en % de la referencia, y si
    el modelo es mejor, igual o peor (todos los KPIs: menos es mejor).
    """
    referencia = referencia or {}
    filas = []
    for kpi in KPIS_REFERENCIA:
        modelo = valor_modelo(resultado, kpi)
        ref = normalizar(referencia.get(kpi.clave), kpi)
        fila = {
            "kpi": kpi,
            "modelo": modelo,
            "referencia": ref,
            "diferencia": None,
            "diferencia_pct": None,
            "veredicto": None,  # "mejor" | "igual" | "peor" | None
        }
        if modelo is not None and ref is not None:
            dif = modelo - ref
            fila["diferencia"] = dif
            fila["diferencia_pct"] = dif / ref * 100 if ref else None
            tolerancia = 0.5 * 10 ** (-kpi.decimales)
            fila["veredicto"] = (
                "igual" if abs(dif) < tolerancia else "mejor" if dif < 0 else "peor"
            )
        filas.append(fila)
    return filas
