"""
Visualizaciones interactivas del plan de estiba usando Plotly.

Todas las funciones reciben datos puros (listas, dicts) y devuelven
figuras de Plotly. No tienen efectos secundarios ni acceden a st.session_state.

Estructura esperada de FilaPlan:
    FilaPlan(bodega: int, plan: int, producto: str, destino: str, unidades: int)
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import TYPE_CHECKING

import plotly.graph_objects as go

if TYPE_CHECKING:
    pass  # FilaPlan solo se usa como type hint en comentarios

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
AZUL_MARINO = "#0F3D5A"
TEAL = "#0891B2"
DORADO = "#C89B3C"
CORAL = "#F97316"
VERDE = "#10B981"
GRIS = "#94A3B8"
GRIS_BORDE = "#E2E8F0"
BLANCO = "#FFFFFF"
TEXTO_PRINCIPAL = "#1E293B"
TEXTO_SECUNDARIO = "#64748B"

# Cuadrilla → bodegas asignadas (según CLAUDE.md sección 9, pares (8+7),(6+5),(4+3),(2+1))
_CUADRILLA_BODEGAS: dict[int, tuple[int, int]] = {
    1: (7, 8),
    2: (5, 6),
    3: (3, 4),
    4: (1, 2),
}
_BODEGA_CUADRILLA: dict[int, int] = {
    h: c for c, bhs in _CUADRILLA_BODEGAS.items() for h in bhs
}

# Colores por destino
_COLOR_DESTINO: dict[str, str] = {
    "TAICHUNG": TEAL,
    "QINGDAO": DORADO,
    "KUNSAN": AZUL_MARINO,
    "ULSAN": CORAL,
}
_COLOR_CUADRILLA: dict[int, str] = {
    1: TEAL,
    2: DORADO,
    3: CORAL,
    4: VERDE,
}

# Geometría del buque (metros)
_W_NORMAL = 27.40    # ancho de bodegas 2-8
_W_BODEGA1 = 14.80   # ancho de bodega 1 (proa)
_ESCALA = 1.0 / _W_NORMAL  # unidades normalizadas

# Número total de planes (capas)
N_PLANES = 11
# Unidades por izada
UNIDADES_IZADA = 16


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _agregar_por_bodega(plan: list) -> dict[int, int]:
    """Suma unidades por bodega."""
    totales: dict[int, int] = defaultdict(int)
    for f in plan:
        totales[f.bodega] += f.unidades
    return dict(totales)


def _unidades_bodega_destino(plan: list) -> dict[int, dict[str, int]]:
    """Unidades por (bodega, destino)."""
    result: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in plan:
        result[f.bodega][f.destino] += f.unidades
    return {h: dict(d) for h, d in result.items()}


def _destino_dominante(dist: dict[str, int]) -> tuple[str, bool]:
    """Retorna (destino_con_más_unidades, es_mixto)."""
    if not dist:
        return "—", False
    dom = max(dist, key=dist.__getitem__)
    return dom, len(dist) > 1


def _izadas_por_bodega(izadas_por_capa: dict[tuple[int, int], int]) -> dict[int, int]:
    """Suma izadas de todos los planes de cada bodega."""
    totales: dict[int, int] = defaultdict(int)
    for (bodega, _plan), n in izadas_por_capa.items():
        totales[bodega] += n
    return dict(totales)


def _interpolar_color(t: float, c_min: str, c_max: str) -> str:
    """Interpola linealmente dos colores hex para t ∈ [0, 1]."""
    def parse(c: str) -> tuple[int, int, int]:
        c = c.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

    r1, g1, b1 = parse(c_min)
    r2, g2, b2 = parse(c_max)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


_LAYOUT_BASE = dict(
    paper_bgcolor=BLANCO,
    plot_bgcolor=BLANCO,
    font=dict(family="Inter, sans-serif", color=AZUL_MARINO, size=12),
)


# ---------------------------------------------------------------------------
# 4a. Timeline de cuadrillas
# ---------------------------------------------------------------------------

def plot_timeline_cuadrillas(
    horas_por_cuadrilla: dict[int, float],
    makespan: float,
) -> go.Figure:
    """
    Barras horizontales de horas trabajadas por cuadrilla.
    La cuadrilla con más horas (= makespan) se colorea en coral.
    """
    labels = []
    valores = []
    for c in sorted(horas_por_cuadrilla):
        bhs = _CUADRILLA_BODEGAS.get(c, ())
        bhs_str = "+".join(str(b) for b in sorted(bhs)) if bhs else "—"
        labels.append(f"Cuadrilla {c}  (bod. {bhs_str})")
        valores.append(horas_por_cuadrilla[c])

    max_v = max(valores) if valores else 1.0
    colores = [CORAL if abs(v - max_v) < 0.001 else TEAL for v in valores]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=valores,
            y=labels,
            orientation="h",
            marker_color=colores,
            text=[f"{v:.2f} h" for v in valores],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.2f} h<extra></extra>",
        )
    )

    # Línea del makespan
    fig.add_vline(
        x=makespan,
        line_dash="dot",
        line_color=AZUL_MARINO,
        line_width=2,
        annotation_text=f"Makespan: {makespan:.2f} h",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color=AZUL_MARINO,
    )

    x_max = max(max_v * 1.18, makespan * 1.08)
    fig.update_layout(
        **_LAYOUT_BASE,
        height=200,
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis=dict(
            range=[0, x_max],
            title="Horas",
            showgrid=True,
            gridcolor=GRIS_BORDE,
            zeroline=False,
        ),
        yaxis=dict(showgrid=False, autorange="reversed"),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# 4b. Vista lateral del buque
# ---------------------------------------------------------------------------

def _coords_bodega(bodega: int) -> tuple[float, float, float, float]:
    """
    Retorna (x0, x1, y0, y1) en unidades normalizadas para la bodega dada.

    Bodega 8 es la más a la izquierda (popa); bodega 1 la más a la derecha (proa).
    Las bodegas 2-8 tienen ancho 1.0; bodega 1 tiene ancho W_BODEGA1/W_NORMAL.
    """
    h = bodega
    if h == 1:
        x0 = 7.0
        x1 = 7.0 + _W_BODEGA1 * _ESCALA
    else:
        idx = 8 - h   # bodega 8 → idx 0, bodega 2 → idx 6
        x0 = float(idx)
        x1 = float(idx + 1)
    return x0, x1, 0.0, 1.0


def plot_vista_lateral(plan: list, modo: str = "Destinos") -> go.Figure:
    """
    Silueta lateral del buque con 8 bodegas coloreadas según el modo elegido.

    Modos: "Destinos", "Llenado", "Cuadrillas", "Izadas".
    """
    totales = _agregar_por_bodega(plan)
    dist_bd = _unidades_bodega_destino(plan)

    # Calcular colores según el modo
    if modo == "Destinos":
        colores: dict[int, str] = {}
        es_mixto: dict[int, bool] = {}
        for h in range(1, 9):
            dist = dist_bd.get(h, {})
            dom, mixto = _destino_dominante(dist)
            colores[h] = _COLOR_DESTINO.get(dom, GRIS)
            es_mixto[h] = mixto

    elif modo == "Llenado":
        max_u = max(totales.values()) if totales else 1
        min_u = min(totales.values()) if totales else 0
        rango = max_u - min_u or 1
        colores = {
            h: _interpolar_color((totales.get(h, 0) - min_u) / rango, "#BFE8F0", AZUL_MARINO)
            for h in range(1, 9)
        }
        es_mixto = {h: False for h in range(1, 9)}

    elif modo == "Cuadrillas":
        colores = {h: _COLOR_CUADRILLA.get(_BODEGA_CUADRILLA.get(h, 1), GRIS) for h in range(1, 9)}
        es_mixto = {h: False for h in range(1, 9)}

    elif modo == "Izadas":
        iz_h: dict[int, int] = defaultdict(int)
        for f in plan:
            iz_h[f.bodega] += math.ceil(f.unidades / UNIDADES_IZADA)
        max_iz = max(iz_h.values()) if iz_h else 1
        colores = {
            h: _interpolar_color(iz_h.get(h, 0) / max_iz, "#FDE8D8", CORAL)
            for h in range(1, 9)
        }
        es_mixto = {h: False for h in range(1, 9)}
    else:
        colores = {h: TEAL for h in range(1, 9)}
        es_mixto = {h: False for h in range(1, 9)}

    fig = go.Figure()

    # --- Dibujar casco (hull externo) ---
    w1 = _W_BODEGA1 * _ESCALA
    proa_x = 7.0 + w1 + 0.55    # punta de la proa
    # Forma de casco: rectángulo con punta derecha
    hull_x = [0, 7.0 + w1, proa_x, 7.0 + w1, 0, 0]
    hull_y = [-0.08, -0.08, 0.5, 1.08, 1.08, -0.08]
    fig.add_trace(go.Scatter(
        x=hull_x, y=hull_y,
        fill="toself",
        fillcolor="#D0E8F2",
        line=dict(color=AZUL_MARINO, width=2.5),
        mode="lines",
        hoverinfo="skip",
        showlegend=False,
    ))

    # --- Dibujar cada bodega como rectángulo con color ---
    PESO_T = 2.02
    for h in range(1, 9):
        x0, x1, y0, y1 = _coords_bodega(h)
        u = totales.get(h, 0)
        t = round(u * PESO_T, 1)
        cuad = _BODEGA_CUADRILLA.get(h, "—")
        dist = dist_bd.get(h, {})
        destinos_str = ", ".join(f"{d}: {n}" for d, n in sorted(dist.items()))
        horas_cuad = "—"  # se añade en la página si hay horas

        fig.add_shape(
            type="rect",
            x0=x0 + 0.03, y0=y0 + 0.03,
            x1=x1 - 0.03, y1=y1 - 0.03,
            fillcolor=colores[h],
            line=dict(color="white", width=2),
        )

        # Hover invisible encima del rectángulo
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        fig.add_trace(go.Scatter(
            x=[cx], y=[cy],
            mode="markers",
            marker=dict(size=1, opacity=0),
            hovertemplate=(
                f"<b>Bodega {h}</b><br>"
                f"Unidades: {u:,}<br>"
                f"Toneladas: {t:,.1f} t<br>"
                f"Destinos: {destinos_str or '—'}<br>"
                f"Cuadrilla: {cuad}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

        # Etiqueta número de bodega (arriba, dentro)
        fig.add_annotation(
            x=cx, y=0.72,
            text=f"<b>{h}</b>",
            font=dict(size=18, color="white", family="Inter, sans-serif"),
            showarrow=False,
            xanchor="center",
        )
        # Etiqueta unidades (abajo, dentro)
        fig.add_annotation(
            x=cx, y=0.30,
            text=f"{u:,}",
            font=dict(size=10, color="white", family="Inter, sans-serif"),
            showarrow=False,
            xanchor="center",
        )
        # Etiqueta cuadrilla (debajo del casco)
        fig.add_annotation(
            x=cx, y=-0.22,
            text=f"C{cuad}",
            font=dict(size=10, color=AZUL_MARINO, family="Inter, sans-serif"),
            showarrow=False,
            xanchor="center",
        )
        # Badge "mixto"
        if es_mixto.get(h, False):
            fig.add_annotation(
                x=x1 - 0.08, y=y1 - 0.05,
                text="mix",
                font=dict(size=8, color="white"),
                bgcolor=DORADO,
                borderpad=2,
                showarrow=False,
                xanchor="right",
                yanchor="top",
            )

    # Etiqueta POPA / PROA
    fig.add_annotation(x=0.3, y=1.18, text="POPA", font=dict(size=10, color=GRIS), showarrow=False)
    fig.add_annotation(
        x=7.0 + w1 + 0.25, y=1.18, text="PROA",
        font=dict(size=10, color=GRIS), showarrow=False, xanchor="center"
    )

    # Línea de agua
    fig.add_shape(
        type="line",
        x0=-0.15, x1=7.0 + w1 + 0.6,
        y0=-0.22, y1=-0.22,
        line=dict(color="#93C5FD", width=1.5, dash="dot"),
    )

    # Leyenda de colores por modo
    if modo == "Destinos":
        for i, (dest, color) in enumerate(
            [("TAICHUNG", TEAL), ("QINGDAO", DORADO), ("KUNSAN", AZUL_MARINO), ("ULSAN", CORAL)]
        ):
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=color, symbol="square"),
                name=dest,
                showlegend=True,
            ))
    elif modo == "Cuadrillas":
        for c, color in _COLOR_CUADRILLA.items():
            bhs = "+".join(str(b) for b in sorted(_CUADRILLA_BODEGAS[c]))
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=color, symbol="square"),
                name=f"Cuadrilla {c} (bod. {bhs})",
                showlegend=True,
            ))

    total_x = 7.0 + w1 + 0.75
    fig.update_layout(
        **_LAYOUT_BASE,
        height=280,
        xaxis=dict(
            range=[-0.2, total_x],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            range=[-0.38, 1.35],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=3.5,
        ),
        showlegend=(modo in ("Destinos", "Cuadrillas")),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.05,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
        margin=dict(l=8, r=8, t=20, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# 4c. Detalle de capas de una bodega
# ---------------------------------------------------------------------------

def plot_capas_bodega(plan: list, bodega: int) -> go.Figure:
    """
    Vista vertical de los planes (capas) de una bodega específica.
    Plan 1 en la base, plan 11 arriba. Coloreado por destino.
    Si una capa es mixta se divide proporcionalmente.
    """
    PESO_T = 2.02
    # Agrupar por (plan, destino)
    por_plan: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in plan:
        if f.bodega == bodega:
            por_plan[f.plan][f.destino] += f.unidades

    planes_con_carga = sorted(por_plan.keys())
    if not planes_con_carga:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Bodega {bodega} sin carga asignada",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=GRIS),
        )
        fig.update_layout(**_LAYOUT_BASE, height=200)
        return fig

    total_u = sum(sum(d.values()) for d in por_plan.values())
    cuad = _BODEGA_CUADRILLA.get(bodega, "—")
    titulo = (
        f"Bodega {bodega} · {total_u:,} unidades · "
        f"{total_u * PESO_T:,.0f} t · Cuadrilla {cuad}"
    )

    fig = go.Figure()
    BAR_H = 0.82   # altura de cada barra (deja hueco visible entre capas)
    TEXTO_X = N_PLANES + 0.3  # posición x para las anotaciones

    destinos_vistos: set[str] = set()

    for plan_num in range(1, N_PLANES + 1):
        dist = por_plan.get(plan_num, {})
        y_centro = plan_num - 1  # plan 1 en y=0, plan 11 en y=10

        if not dist:
            # Capa vacía — franja gris muy tenue
            fig.add_shape(
                type="rect",
                x0=0, x1=1, y0=y_centro - BAR_H / 2, y1=y_centro + BAR_H / 2,
                fillcolor="#F1F5F9",
                line=dict(color=GRIS_BORDE, width=0.5),
            )
            fig.add_annotation(
                x=0.5, y=y_centro,
                text="vacío",
                font=dict(size=9, color="#CBD5E1"),
                showarrow=False, xanchor="center",
            )
            continue

        total_plan = sum(dist.values())
        destinos_ord = sorted(dist.keys(), key=dist.__getitem__, reverse=True)
        x_cursor = 0.0

        for dest in destinos_ord:
            n = dist[dest]
            ancho = n / total_plan
            color = _COLOR_DESTINO.get(dest, GRIS)
            show_leg = dest not in destinos_vistos
            destinos_vistos.add(dest)

            fig.add_trace(go.Bar(
                x=[ancho],
                y=[y_centro],
                orientation="h",
                base=x_cursor,
                marker_color=color,
                name=dest,
                showlegend=show_leg,
                legendgroup=dest,
                hovertemplate=(
                    f"<b>Plan {plan_num} — {dest}</b><br>"
                    f"{n:,} unidades · {n * PESO_T:,.0f} t"
                    "<extra></extra>"
                ),
                width=BAR_H,
            ))
            x_cursor += ancho

        # Etiqueta lateral: info de la capa
        prod_uniq = list({f.producto for f in plan if f.bodega == bodega and f.plan == plan_num})
        prod_str = prod_uniq[0] if len(prod_uniq) == 1 else "varios"
        dest_str = "/".join(destinos_ord)
        label = f"Plan {plan_num} · {dest_str} · {total_plan:,} u"

        fig.add_annotation(
            x=1.01, y=y_centro,
            text=label,
            font=dict(size=9, color=TEXTO_PRINCIPAL),
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            xref="x", yref="y",
        )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=titulo, font=dict(size=13, color=AZUL_MARINO), x=0, pad=dict(l=0)),
        height=520,
        barmode="stack",
        xaxis=dict(
            range=[0, 2.8],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(N_PLANES)),
            ticktext=[f"P{i + 1}" for i in range(N_PLANES)],
            showgrid=True,
            gridcolor=GRIS_BORDE,
            zeroline=False,
            range=[-0.7, N_PLANES - 0.3],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.12,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
        margin=dict(l=32, r=8, t=40, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# 4d. Heatmap de fragmentación destino × bodega
# ---------------------------------------------------------------------------

def plot_heatmap_destinos(plan: list) -> go.Figure:
    """
    Heatmap bodega × destino con unidades en cada celda.
    Escala secuencial Blues de Plotly.
    """
    dist_bd = _unidades_bodega_destino(plan)
    bodegas = list(range(1, 9))
    destinos = sorted({f.destino for f in plan})

    z = []
    text_ann = []
    for dest in destinos:
        row_z = []
        row_t = []
        for h in bodegas:
            val = dist_bd.get(h, {}).get(dest, 0)
            row_z.append(val)
            row_t.append(str(val) if val > 0 else "")
        z.append(row_z)
        text_ann.append(row_t)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f"Bod. {h}" for h in bodegas],
        y=destinos,
        text=text_ann,
        texttemplate="%{text}",
        colorscale="Blues",
        showscale=True,
        hovertemplate="<b>Bodega %{x} — %{y}</b><br>%{z:,} unidades<extra></extra>",
    ))

    # Calcular fragmentación: bodegas con carga no nula por destino
    fragmentacion = sum(
        1 for dest in destinos for h in bodegas
        if dist_bd.get(h, {}).get(dest, 0) > 0
    )
    dest_max = max(
        destinos,
        key=lambda d: sum(1 for h in bodegas if dist_bd.get(h, {}).get(d, 0) > 0),
        default="—",
    )
    n_bodegas_dest_max = sum(
        1 for h in bodegas if dist_bd.get(h, {}).get(dest_max, 0) > 0
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        height=260,
        xaxis=dict(showgrid=False, side="bottom"),
        yaxis=dict(showgrid=False, autorange="reversed"),
        margin=dict(l=80, r=40, t=16, b=48),
        annotations=[
            dict(
                text=(
                    f"Fragmentación total: {fragmentacion} celdas · "
                    f"{dest_max} ocupa {n_bodegas_dest_max} bodegas"
                ),
                x=0.5, y=-0.28,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=11, color=TEXTO_SECUNDARIO),
                xanchor="center",
            )
        ],
    )
    return fig


# ---------------------------------------------------------------------------
# 4e. Planimetría de una capa (posiciones reales, tipo prestow)
# ---------------------------------------------------------------------------
# Paleta por producto (hasta 5 productos del caso base + un color de reserva)
_COLOR_PRODUCTO: dict[str, str] = {
    "N_ALDEA_EKP": AZUL_MARINO,
    "N_ALDEA_BKP": TEAL,
    "ARAUCO_EKP": DORADO,
    "ARAUCO_BKP": CORAL,
    "CELCO_UKP": VERDE,
}
_COLOR_RESERVA = "#94A3B8"

_BORDE_UNIDAD = "#1E293B"       # borde oscuro: separa visualmente cada "paquete"
_MARGEN_UNIDAD = 0.12           # fracción de la huella que se achica por lado (hueco visible)
_BORDE_IZADA = "#DC2626"        # contorno de cada grupo de izada
_FONDO_ETIQUETA_IZADA = "#FFFFFF"


def _trazo_rectangulos(unidades: list, color: str, nombre: str) -> go.Scatter:
    """
    Un solo trace de Plotly con muchos rectángulos: cada rectángulo se cierra
    y se separa del siguiente con None, truco estándar para dibujar cientos
    de polígonos sin crear un trace por unidad (rendimiento).

    Cada rectángulo se dibuja levemente achicado hacia adentro (no ocupa el
    100% de su celda) y con borde oscuro, para que se vean como paquetes
    separados en vez de un bloque de color continuo.
    """
    xs: list[float | None] = []
    ys: list[float | None] = []
    for u in unidades:
        mx = u.largo * _MARGEN_UNIDAD
        my = u.ancho * _MARGEN_UNIDAD
        x0, y0 = u.x + mx, u.y + my
        x1, y1 = u.x + u.largo - mx, u.y + u.ancho - my
        xs += [x0, x1, x1, x0, x0, None]
        ys += [y0, y0, y1, y1, y0, None]

    return go.Scatter(
        x=xs, y=ys,
        mode="lines",
        fill="toself",
        fillcolor=color,
        line=dict(color=_BORDE_UNIDAD, width=1),
        name=nombre,
        legendgroup=nombre,
        hoverinfo="skip",
    )


def plot_planimetria_capa(
    layout: list,
    largo_piso: float,
    ancho_piso: float,
    colorear_por: str = "Producto",
    izadas: list | None = None,
) -> go.Figure:
    """
    Dibuja el piso de una bodega con la posición real de cada unidad
    (salida de layout_capa.calcular_layout_capa), coloreada por destino o
    producto, cada una como un paquete separado (borde oscuro + hueco).

    Si se pasan izadas (salida de secuencia_izadas.calcular_secuencia), se
    dibuja además un recuadro punteado alrededor de cada grupo de unidades
    que se mueve en una sola izada, con un número encima indicando cuántas
    unidades son — lo óptimo es que diga 16 (capacidad del marco de la
    grúa); menos que eso significa una izada parcial.

    layout: lista de objetos con .x, .y, .largo, .ancho, .producto, .destino
        (UnidadPosicion de src/layout_capa.py).
    """
    fig = go.Figure()

    if not layout:
        fig.update_layout(**_LAYOUT_BASE, height=260,
                           annotations=[dict(text="Sin unidades para mostrar en esta capa",
                                              x=0.5, y=0.5, xref="paper", yref="paper",
                                              showarrow=False, font=dict(color=TEXTO_SECUNDARIO))])
        return fig

    if colorear_por == "Producto":
        grupos: dict[str, list] = defaultdict(list)
        for u in layout:
            grupos[u.producto].append(u)
        for nombre, unidades in grupos.items():
            color = _COLOR_PRODUCTO.get(nombre, _COLOR_RESERVA)
            fig.add_trace(_trazo_rectangulos(unidades, color, nombre))
    else:  # "Destino"
        grupos = defaultdict(list)
        for u in layout:
            grupos[u.destino].append(u)
        for nombre, unidades in grupos.items():
            color = _COLOR_DESTINO.get(nombre, _COLOR_RESERVA)
            fig.add_trace(_trazo_rectangulos(unidades, color, nombre))

    anotaciones = []
    if izadas:
        for iz in izadas:
            if not iz.unidades:
                continue
            x0 = min(u.x for u in iz.unidades)
            y0 = min(u.y for u in iz.unidades)
            x1 = max(u.x + u.largo for u in iz.unidades)
            y1 = max(u.y + u.ancho for u in iz.unidades)
            fig.add_shape(
                type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                line=dict(color=_BORDE_IZADA, width=1.5, dash="dash"),
                fillcolor="rgba(0,0,0,0)",
            )
            completa = iz.cantidad == 16
            anotaciones.append(dict(
                x=(x0 + x1) / 2, y=y1,
                text=f"<b>{iz.cantidad}</b>",
                showarrow=False,
                yshift=10,
                font=dict(size=12, color=_BORDE_IZADA if not completa else AZUL_MARINO),
                bgcolor=_FONDO_ETIQUETA_IZADA,
                bordercolor=_BORDE_IZADA,
                borderwidth=1,
                borderpad=2,
            ))

    fig.add_shape(
        type="rect", x0=0, y0=0, x1=largo_piso, y1=ancho_piso,
        line=dict(color=AZUL_MARINO, width=2), fillcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        height=460,
        xaxis=dict(range=[-0.5, largo_piso + 0.5], showgrid=False, zeroline=False,
                   title="metros (eslora)"),
        yaxis=dict(range=[-0.5, ancho_piso + 1.5], showgrid=False, zeroline=False,
                   title="metros (manga)", scaleanchor="x", scaleratio=1),
        margin=dict(l=48, r=16, t=16, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        showlegend=True,
        annotations=anotaciones,
    )
    return fig


# ---------------------------------------------------------------------------
# 4f. Balance de peso por bodega (informativo, no es restricción del modelo)
# ---------------------------------------------------------------------------

def plot_balance_peso(peso_por_bodega: dict[int, float],
                       densidad_por_bodega: dict[int, float]) -> go.Figure:
    """
    Barras de peso por bodega (eje izquierdo) con la densidad como línea
    (eje derecho). Puramente informativo: el modelo no restringe peso ni
    distribución (CLAUDE.md sección 6).
    """
    bodegas = sorted(peso_por_bodega)
    pesos = [peso_por_bodega[h] for h in bodegas]
    densidades = [densidad_por_bodega.get(h, 0.0) for h in bodegas]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"Bod. {h}" for h in bodegas],
        y=pesos,
        marker_color=TEAL,
        name="Peso (t)",
        text=[f"{p:,.0f} t".replace(",", ".") for p in pesos],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x}: %{y:,.0f} t<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[f"Bod. {h}" for h in bodegas],
        y=densidades,
        mode="lines+markers",
        name="Densidad (t/m²)",
        marker_color=CORAL,
        yaxis="y2",
        hovertemplate="%{x}: %{y:.2f} t/m²<extra></extra>",
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        height=320,
        margin=dict(l=48, r=48, t=16, b=32),
        xaxis=dict(showgrid=False),
        yaxis=dict(title="Peso (t)", showgrid=True, gridcolor=GRIS_BORDE),
        yaxis2=dict(title="Densidad (t/m²)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig
