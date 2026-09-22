"""
Funciones de formato numérico y generación de archivos de descarga.
"""

from __future__ import annotations

import io

PESO_UNIDAD_T: float = 2.02  # constante del caso base Kiwi Arrow


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


def _hoja_tabla(wb, nombre: str, encabezados: list[str], filas: list[tuple]):
    """Crea una hoja con una tabla simple (encabezado gris + bordes), estilo
    consistente con las hojas que ya genera modelo_prestow.exportar_excel."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    FUENTE = "Arial"
    COLOR_ENCABEZADO = "44546A"
    fino = Side(style="thin", color="BFBFBF")
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)

    ws = wb.create_sheet(nombre)
    for j, enc in enumerate(encabezados, start=1):
        c = ws.cell(row=1, column=j, value=enc)
        c.font = Font(name=FUENTE, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=COLOR_ENCABEZADO)
        c.border = borde
        c.alignment = Alignment(horizontal="center", vertical="center")
    for i, fila in enumerate(filas, start=2):
        for j, v in enumerate(fila, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.font = Font(name=FUENTE, size=10)
            c.border = borde
    for j in range(1, len(encabezados) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 22
    ws.freeze_panes = "A2"
    if filas:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(encabezados))}{len(filas) + 1}"
    return ws


def generar_excel_bytes(
    resultado: object,
    huellas: dict[str, tuple[float, float]] | None = None,
    geometria: dict[int, tuple[float, float]] | None = None,
    rot: dict[str, int] | None = None,
    parametros: dict | None = None,
    balance: object | None = None,
) -> bytes:
    """
    Arma el Excel completo de descarga: parte del Excel oficial que ya genera
    el modelo (resultado.excel_bytes — «Plan de estiba» coloreado tipo
    prestow, «Detalle», «Indicadores») y le agrega, cuando los datos están
    disponibles, «Izadas y secuencia» (todas las capas, no solo la que se ve
    en pantalla), «Balance de peso» y «Parámetros de la corrida». Un solo
    archivo con todo, en vez de varios sueltos.

    huellas, geometria, rot: necesarios para la hoja de izadas — se omite si
        falta alguno. balance: BalancePeso (src/balance_peso.py) — se omite
        la hoja si es None. parametros: dict de la corrida (solver, límite,
        fecha, etc.) — si es None solo se documenta el estado del solver.
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(resultado.excel_bytes))  # type: ignore[attr-defined]

    if huellas and geometria and rot:
        from layout_capa import layout_para_fila_plan
        from secuencia_izadas import calcular_secuencia

        filas_izadas = []
        capas = sorted({(f.bodega, f.plan) for f in resultado.plan})  # type: ignore[attr-defined]
        for bodega, plan_n in capas:
            layout = layout_para_fila_plan(bodega, plan_n, resultado.plan, geometria, huellas)  # type: ignore[attr-defined]
            for iz in calcular_secuencia(layout, rot):
                filas_izadas.append((
                    bodega, plan_n, iz.numero, iz.cantidad,
                    ", ".join(sorted(iz.productos)), ", ".join(sorted(iz.destinos)),
                ))
        _hoja_tabla(
            wb, "Izadas y secuencia",
            ["Bodega", "Plan", "Izada", "Unidades", "Producto(s)", "Destino(s)"],
            filas_izadas,
        )

    if balance is not None:
        filas_balance = [
            (h, round(balance.peso_por_bodega[h], 1), round(balance.densidad_por_bodega.get(h, 0.0), 3))
            for h in sorted(balance.peso_por_bodega)
        ]
        ws_bal = _hoja_tabla(wb, "Balance de peso", ["Bodega", "Peso (t)", "Densidad (t/m2)"], filas_balance)
        fila = len(filas_balance) + 3
        from openpyxl.styles import Font
        ws_bal.cell(row=fila, column=1, value="Dispersión relativa de densidad (%)").font = Font(bold=True)
        ws_bal.cell(row=fila, column=2, value=balance.dispersion_relativa)
        ws_bal.cell(row=fila + 1, column=1, value=(
            "Informativo: el modelo no restringe peso ni distribución por bodega "
            "(sin evidencia de problema operativo, ver CLAUDE.md sección 6)."
        )).font = Font(italic=True, size=9, color="595959")

    filas_param = list((parametros or {}).items()) + [
        ("estado_solver", resultado.estado_solver),  # type: ignore[attr-defined]
        ("gap", resultado.gap if resultado.gap is not None else "no disponible"),  # type: ignore[attr-defined]
        ("tiempo_solver_s", resultado.tiempo_solver_s),  # type: ignore[attr-defined]
        ("makespan_h", resultado.kpis.get("makespan_h", "")),  # type: ignore[attr-defined]
    ]
    _hoja_tabla(wb, "Parámetros de la corrida", ["Parámetro", "Valor"], filas_param)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
