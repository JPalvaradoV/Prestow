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


def _hoja_tabla(wb, nombre: str, encabezados: list[str], filas: list[tuple],
                 nota: str | None = None):
    """Crea una hoja con una tabla simple (encabezado gris + bordes), estilo
    consistente con las hojas que ya genera modelo_prestow.exportar_excel.

    nota: texto explicativo en lenguaje simple, se escribe en una fila propia
        arriba del encabezado (para quien no participó armando el modelo)."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    FUENTE = "Arial"
    COLOR_ENCABEZADO = "44546A"
    fino = Side(style="thin", color="BFBFBF")
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)

    ws = wb.create_sheet(nombre)
    fila_enc = 1
    if nota:
        c = ws.cell(row=1, column=1, value=nota)
        c.font = Font(name=FUENTE, size=9, italic=True, color="595959")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(encabezados), 1))
        ws.row_dimensions[1].height = 30
        fila_enc = 2

    for j, enc in enumerate(encabezados, start=1):
        c = ws.cell(row=fila_enc, column=j, value=enc)
        c.font = Font(name=FUENTE, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=COLOR_ENCABEZADO)
        c.border = borde
        c.alignment = Alignment(horizontal="center", vertical="center")
    for i, fila in enumerate(filas, start=fila_enc + 1):
        for j, v in enumerate(fila, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.font = Font(name=FUENTE, size=10)
            c.border = borde
    for j in range(1, len(encabezados) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 22
    ws.freeze_panes = f"A{fila_enc + 1}"
    if filas:
        ws.auto_filter.ref = f"A{fila_enc}:{get_column_letter(len(encabezados))}{fila_enc + len(filas)}"
    return ws


_COLOR_PRODUCTO_XL = {
    "N_ALDEA_EKP": "0F3D5A",
    "N_ALDEA_BKP": "0891B2",
    "ARAUCO_EKP": "C89B3C",
    "ARAUCO_BKP": "F97316",
    "CELCO_UKP": "10B981",
}
_COLOR_RESERVA_XL = "94A3B8"


def _hoja_planimetria(wb, capas_layout: dict):
    """
    Grilla visual (una celda = una unidad) de cada capa cargada, coloreada
    por producto y con el número de izada dentro de cada celda. Complementa
    la hoja «Izadas y secuencia» (tabular) con una vista espacial precisa:
    usa la posición real de cada unidad (layout_capa.py, fila/columna dentro
    de la grilla de su propio grupo producto+destino) en vez de solo contar.

    capas_layout: {(bodega, plan): (layout, izadas)} — ver generar_excel_bytes.
    """
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    FUENTE = "Arial"
    fino = Side(style="thin", color="FFFFFF")
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)

    ws = wb.create_sheet("Planimetría")
    ws.sheet_view.showGridLines = False
    for j in range(1, 40):
        ws.column_dimensions[get_column_letter(j)].width = 3.6

    ws.cell(row=1, column=1, value=(
        "Vista desde arriba de cada bodega y plan (capa), tal como quedan las "
        "unidades acomodadas en el piso. Una celda = una unidad de carga real, en "
        "su posición aproximada. El color es el producto (ver referencia abajo); el "
        "número dentro de la celda es la izada a la que pertenece esa unidad — "
        "unidades con el mismo número se mueven juntas en un solo viaje de la grúa "
        "(hasta 16 a la vez, agrupadas en el bloque más compacto posible, no en "
        "cualquier orden). Si una capa mezcla más de un producto o destino, cada "
        "grupo se dibuja en su propia franja — es una aproximación de "
        "visualización, no una restricción real del modelo (ver layout_capa.py)."
    )).font = Font(name=FUENTE, size=9, italic=True, color="595959")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=20)
    ws.row_dimensions[1].height = 60

    col_leyenda = 1
    for producto, color in _COLOR_PRODUCTO_XL.items():
        ws.merge_cells(start_row=2, start_column=col_leyenda, end_row=2, end_column=col_leyenda + 2)
        c = ws.cell(row=2, column=col_leyenda, value=producto)
        c.fill = PatternFill("solid", fgColor=color)
        c.font = Font(name=FUENTE, size=8, bold=True, color="FFFFFF")
        c.alignment = Alignment(horizontal="center", vertical="center")
        col_leyenda += 4

    fila_actual = 4
    for (bodega, plan_n), (layout, izadas) in capas_layout.items():
        if not layout:
            continue
        unidad_a_izada = {id(u): iz.numero for iz in izadas for u in iz.unidades}

        ws.cell(row=fila_actual, column=1, value=(
            f"Bodega {bodega} · Plan {plan_n} — {len(layout)} unidades · {len(izadas)} izadas"
        )).font = Font(name=FUENTE, size=11, bold=True, color="0F3D5A")
        fila_actual += 1
        fila_grilla_inicio = fila_actual

        grupos: dict[tuple[str, str], list] = {}
        for u in layout:
            grupos.setdefault((u.producto, u.destino), []).append(u)

        col_offset = 0
        max_filas = 0
        for (producto, _destino), unidades in grupos.items():
            color = _COLOR_PRODUCTO_XL.get(producto, _COLOR_RESERVA_XL)
            for u in unidades:
                cel = ws.cell(
                    row=fila_grilla_inicio + u.fila,
                    column=1 + col_offset + u.columna,
                    value=unidad_a_izada.get(id(u), ""),
                )
                cel.fill = PatternFill("solid", fgColor=color)
                cel.font = Font(name=FUENTE, size=7, bold=True, color="FFFFFF")
                cel.border = borde
                cel.alignment = Alignment(horizontal="center", vertical="center")
            n_cols_grupo = max(u.columna for u in unidades) + 1
            n_filas_grupo = max(u.fila for u in unidades) + 1
            max_filas = max(max_filas, n_filas_grupo)
            col_offset += n_cols_grupo + 1

        for i in range(max_filas):
            ws.row_dimensions[fila_grilla_inicio + i].height = 14

        fila_actual = fila_grilla_inicio + max_filas + 2

    ws.freeze_panes = "A3"
    return ws


def generar_excel_bytes(
    resultado: object,
    huellas: dict[str, tuple[float, float]] | None = None,
    geometria: dict[int, tuple[float, float]] | None = None,
    rot: dict[str, int] | None = None,
    parametros: dict | None = None,
    balance: object | None = None,
    referencia: dict | None = None,
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
        referencia: KPIs del plan de referencia (components/referencia.py) —
        si hay al menos uno, se agrega la hoja «Comparación con referencia».
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(resultado.excel_bytes))  # type: ignore[attr-defined]

    if huellas and geometria and rot:
        from layout_capa import layout_para_fila_plan
        from secuencia_izadas import calcular_secuencia

        capas = sorted({(f.bodega, f.plan) for f in resultado.plan})  # type: ignore[attr-defined]
        capas_layout = {}
        filas_izadas = []
        for bodega, plan_n in capas:
            layout = layout_para_fila_plan(bodega, plan_n, resultado.plan, geometria, huellas)  # type: ignore[attr-defined]
            izadas = calcular_secuencia(layout, rot)
            capas_layout[(bodega, plan_n)] = (layout, izadas)
            for iz in izadas:
                filas_izadas.append((
                    bodega, plan_n, iz.numero, iz.cantidad,
                    ", ".join(sorted(iz.productos)), ", ".join(sorted(iz.destinos)),
                ))
        _hoja_tabla(
            wb, "Izadas y secuencia",
            ["Bodega", "Plan", "Izada", "Unidades", "Producto(s)", "Destino(s)"],
            filas_izadas,
            nota=(
                "Cada fila es una izada: un grupo de unidades que la grúa mueve de "
                "una sola vez (hasta 16). El orden de las filas es el orden de carga "
                "sugerido. Ver la hoja «Planimetría» para la posición exacta de cada "
                "unidad dentro de cada izada."
            ),
        )
        _hoja_planimetria(wb, capas_layout)

    if balance is not None:
        filas_balance = [
            (h, round(balance.peso_por_bodega[h], 1), round(balance.densidad_por_bodega.get(h, 0.0), 3))
            for h in sorted(balance.peso_por_bodega)
        ]
        ws_bal = _hoja_tabla(
            wb, "Balance de peso", ["Bodega", "Peso (t)", "Densidad (t/m2)"], filas_balance,
            nota=(
                "Peso total y densidad (t por m² de piso) de cada bodega, con la carga "
                "completa antes de zarpar. El modelo intenta balancear esto como "
                "tercera prioridad — nunca a costa del tiempo de carga ni de las "
                "izadas+fragmentación."
            ),
        )
        fila = 3 + len(filas_balance) + 1
        from openpyxl.styles import Font
        ws_bal.cell(row=fila, column=1, value="Dispersión relativa de densidad (%)").font = Font(bold=True)
        ws_bal.cell(row=fila, column=2, value=balance.dispersion_relativa)
        ws_bal.cell(row=fila + 1, column=1, value=(
            "Diferencia entre la bodega más y menos cargada, como % del promedio. "
            "Más cerca de 0% es más parejo."
        )).font = Font(italic=True, size=9, color="595959")

    filas_param = list((parametros or {}).items()) + [
        ("estado_solver", resultado.estado_solver),  # type: ignore[attr-defined]
    ] + [
        (f"gap_pasada_{n}_pct", round(g, 2) if g is not None else "no disponible")
        for n, g in sorted((getattr(resultado, "gaps_por_pasada", {}) or {}).items())
    ] + [
        ("tiempo_solver_s", resultado.tiempo_solver_s),  # type: ignore[attr-defined]
        ("makespan_h", resultado.kpis.get("makespan_h", "")),  # type: ignore[attr-defined]
    ]
    _hoja_tabla(
        wb, "Parámetros de la corrida", ["Parámetro", "Valor"], filas_param,
        nota=(
            "Con qué configuración se calculó este plan y qué tan confiable es el "
            "resultado — para poder reproducir la corrida o justificar los números "
            "frente al puerto. \"gap\" es qué tan lejos puede estar el resultado del "
            "óptimo teórico; 0 significa óptimo probado."
        ),
    )

    from .referencia import comparar, hay_referencia

    if hay_referencia(referencia):
        _VEREDICTO = {"mejor": "Mejor", "igual": "Igual", "peor": "Peor", None: "Sin dato"}
        filas_comp = [
            (
                c["kpi"].etiqueta + (f" ({c['kpi'].unidad})" if c["kpi"].unidad else ""),
                round(c["modelo"], c["kpi"].decimales) if c["modelo"] is not None else "",
                c["referencia"] if c["referencia"] is not None else "sin dato",
                round(c["diferencia"], c["kpi"].decimales) if c["diferencia"] is not None else "",
                _VEREDICTO[c["veredicto"]],
            )
            for c in comparar(resultado, referencia)
        ]
        _hoja_tabla(
            wb, "Comparación con referencia",
            ["KPI", "Modelo", "Referencia", "Diferencia (modelo − referencia)", "Resultado"],
            filas_comp,
            nota=(
                "KPIs del plan del modelo frente a los del plan de referencia "
                "ingresados en la web (normalmente el plan manual del puerto). En "
                "los cuatro, menos es mejor: una diferencia negativa es una mejora."
            ),
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
