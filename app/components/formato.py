"""
Funciones de formato numérico y generación de archivos de descarga.
"""

from __future__ import annotations

import io

import pandas as pd

PESO_UNIDAD_T: float = 2.02  # constante del caso base Kiwi Arrow

_LABELS_KPI: dict[str, str] = {
    "makespan_h": "Makespan (h)",
    "desbalance_pct": "Desbalance cuadrillas (%)",
    "fragmentacion_bodegas_destino": "Fragmentación (bodegas×destino)",
    "izadas_totales": "Izadas totales",
    "unidades_totales": "Unidades totales",
}


def formato_horas(h: float) -> str:
    """58.096 → '58 h 6 min'."""
    horas_ent = int(h)
    minutos = int(round((h - horas_ent) * 60))
    if minutos == 0:
        return f"{horas_ent} h"
    return f"{horas_ent} h {minutos} min"


def formato_unidades(u: int) -> str:
    """29332 → '29.332'  (separador de miles con punto, estilo español)."""
    return f"{u:,}".replace(",", ".")


def formato_toneladas(t: float) -> str:
    """59197.0 → '59.197,0'."""
    # Se genera con coma como separador de miles primero y luego se invierte
    partes = f"{t:,.1f}".split(".")
    entero = partes[0].replace(",", ".")
    decimal = partes[1] if len(partes) > 1 else "0"
    return f"{entero},{decimal}"


def formato_diferencia(delta: float, unidad: str) -> tuple[str, str]:
    """
    Formatea una diferencia con signo y devuelve (texto, color_hex).
    Verde cuando delta es negativo (mejora en makespan).
    """
    if delta < -0.001:
        return f"−{abs(delta):.2f} {unidad}", "#10B981"   # verde esmeralda
    elif delta > 0.001:
        return f"+{delta:.2f} {unidad}", "#DC2626"         # rojo
    else:
        return f"0 {unidad}", "#64748B"                    # gris neutro


def generar_excel_bytes(resultado: object) -> bytes:
    """
    Genera el Excel de plan de estiba en memoria a partir de un ResultadoCorrida.

    Produce dos hojas:
    - «Plan de estiba»: filas del plan ordenadas por bodega y plan.
    - «KPIs»: indicadores de la corrida.
    """
    filas = []
    for f in resultado.plan:  # type: ignore[attr-defined]
        filas.append(
            {
                "Bodega": f.bodega,
                "Plan": f.plan,
                "Producto": f.producto,
                "Destino": f.destino,
                "Unidades": f.unidades,
                "Toneladas": round(f.unidades * PESO_UNIDAD_T, 1),
            }
        )
    df_plan = (
        pd.DataFrame(filas).sort_values(["Bodega", "Plan"])
        if filas
        else pd.DataFrame(columns=["Bodega", "Plan", "Producto", "Destino", "Unidades", "Toneladas"])
    )

    kpis_rows = [
        {"Indicador": _LABELS_KPI.get(k, k), "Valor": v}
        for k, v in resultado.kpis.items()  # type: ignore[attr-defined]
    ]
    df_kpis = pd.DataFrame(kpis_rows)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_plan.to_excel(writer, sheet_name="Plan de estiba", index=False)
        df_kpis.to_excel(writer, sheet_name="KPIs", index=False)
    buf.seek(0)
    return buf.read()


def generar_kpis_csv(resultado: object) -> str:
    """Genera un CSV con los KPIs del resultado."""
    lines = ["Indicador,Valor"]
    for k, v in resultado.kpis.items():  # type: ignore[attr-defined]
        label = _LABELS_KPI.get(k, k)
        lines.append(f"{label},{v}")
    return "\n".join(lines)
