"""
Página Resultados — KPIs, vista del buque, tabla y descarga.
"""

import sys
from pathlib import Path

_DIR_PAGES = Path(__file__).parent
_DIR_APP = _DIR_PAGES.parent
_RAIZ = _DIR_APP.parent
for _p in [str(_RAIZ / "src"), str(_DIR_APP)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd
import streamlit as st

from components.estilo import CORAL, TEXTO_SECUNDARIO, VERDE, aplicar_estilo_global
from components.formato import (
    PESO_UNIDAD_T,
    formato_horas,
    formato_unidades,
    generar_excel_bytes,
    generar_kpis_csv,
)
from components.vista_buque import (
    plot_capas_bodega,
    plot_heatmap_destinos,
    plot_timeline_cuadrillas,
    plot_vista_lateral,
)

st.set_page_config(
    page_title="Resultados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo_global()

_PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🚢 Prestow")
    st.caption("Optimizador de plan de estiba")
    st.divider()
    try:
        from api import resolver_prestow as _chk  # noqa: F401
        st.success("✅ Modelo listo")
    except Exception:
        st.error("❌ Error al cargar el modelo")
    st.divider()
    st.caption("© 2026")

st.markdown("# 📊 Resultados de la optimización")

# --- Estado vacío ---
if "resultado" not in st.session_state:
    st.markdown(
        "<div class='card-prestow card-datos' style='text-align:center; padding:48px;'>"
        "<h3 style='color:#64748B;'>Aún no hay ningún resultado</h3>"
        "<p style='color:#94A3B8;'>Ve a Ejecutar, carga el caso demo y calcula el plan.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("⚙️ Ir a Ejecutar", type="primary"):
        st.switch_page("pages/1_Ejecutar.py")
    st.stop()

resultado = st.session_state["resultado"]
meta = st.session_state.get("metadata", {})
makespan_manual = meta.get("makespan_manual_h", 60.61)
ahorro = makespan_manual - resultado.makespan
ahorro_pct = (ahorro / makespan_manual) * 100

# ---------------------------------------------------------------------------
# Indicadores clave
# ---------------------------------------------------------------------------
st.markdown("### ⏱️ Indicadores clave")

col1, col2, col3 = st.columns(3)

with col1:
    # Texto explícito en lugar de depender del signo del delta
    delta_label = f"{ahorro:.2f} h más rápido que el plan de referencia"
    st.metric(
        label="⏱️ Makespan",
        value=formato_horas(resultado.makespan),
        delta=delta_label,
        help=f"Tiempo total de carga. Plan de referencia: {makespan_manual:.2f} h",
    )

with col2:
    st.metric(
        label="📉 Ahorro vs referencia",
        value=f"{ahorro:.2f} h",
        delta=f"{ahorro_pct:.1f}% del tiempo total",
        help=f"El plan de referencia es {makespan_manual:.2f} h.",
    )

with col3:
    seg = resultado.tiempo_solver_s
    tiempo_str = (
        f"{int(seg // 60)} min {int(seg % 60)} s"
        if seg >= 60
        else f"{int(seg)} s"
    )
    st.metric(
        label="⏳ Tiempo de cálculo",
        value=tiempo_str,
        help="Tiempo total incluyendo las dos pasadas del solver.",
    )

st.divider()

# ---------------------------------------------------------------------------
# KPIs completos
# ---------------------------------------------------------------------------
st.markdown("### 📊 KPIs completos")

kpis = resultado.kpis
kpi_c1, kpi_c2 = st.columns(2)

with kpi_c1:
    desbalance = kpis.get("desbalance_pct", 0.0)
    c_desb = VERDE if desbalance < 5 else "#F59E0B" if desbalance < 10 else CORAL
    st.markdown(
        f"<div class='card-prestow card-resultado'>"
        f"<p style='margin:0; color:{TEXTO_SECUNDARIO}; font-size:13px;'>"
        f"Desbalance entre cuadrillas</p>"
        f"<p style='margin:4px 0 0 0; font-size:28px; font-weight:700; color:{c_desb};'>"
        f"{desbalance:.1f}%</p>"
        f"<p style='margin:4px 0 0 0; font-size:12px; color:#94A3B8;'>Referencia: 6,9%</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

with kpi_c2:
    frag = kpis.get("fragmentacion_bodegas_destino", 0)
    st.markdown(
        f"<div class='card-prestow card-datos'>"
        f"<p style='margin:0; color:{TEXTO_SECUNDARIO}; font-size:13px;'>"
        f"Fragmentación (bodegas × destino)</p>"
        f"<p style='margin:4px 0 0 0; font-size:28px; font-weight:700; color:#0F3D5A;'>"
        f"{frag:.0f}</p>"
        f"<p style='margin:4px 0 0 0; font-size:12px; color:#94A3B8;'>Referencia: 14</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

kpi_c3, kpi_c4 = st.columns(2)
with kpi_c3:
    izadas = kpis.get("izadas_totales", 0)
    st.markdown(
        f"<div class='card-prestow card-info'>"
        f"<p style='margin:0; color:{TEXTO_SECUNDARIO}; font-size:13px;'>Izadas totales</p>"
        f"<p style='margin:4px 0 0 0; font-size:28px; font-weight:700; color:#0F3D5A;'>"
        f"{formato_unidades(int(izadas))}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
with kpi_c4:
    unidades_tot = kpis.get("unidades_totales", 0)
    st.markdown(
        f"<div class='card-prestow card-info'>"
        f"<p style='margin:0; color:{TEXTO_SECUNDARIO}; font-size:13px;'>Unidades embarcadas</p>"
        f"<p style='margin:4px 0 0 0; font-size:28px; font-weight:700; color:#0F3D5A;'>"
        f"{formato_unidades(int(unidades_tot))}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Vista del buque
# ---------------------------------------------------------------------------
st.markdown("## ⚓ Vista del buque")

# 4a. Timeline de cuadrillas
if resultado.horas_por_cuadrilla:
    fig_timeline = plot_timeline_cuadrillas(resultado.horas_por_cuadrilla, resultado.makespan)
    st.plotly_chart(fig_timeline, use_container_width=True, config=_PLOTLY_CONFIG)
else:
    st.info("No hay datos de horas por cuadrilla para mostrar el timeline.")

st.markdown("### 🗺️ Distribución por bodega")

if resultado.plan:
    # Selector de modo
    modo = st.selectbox(
        "Colorear por",
        options=["Destinos", "Llenado", "Cuadrillas", "Izadas"],
        index=0,
        help=(
            "Destinos: color según el destino con más carga. "
            "Llenado: intensidad proporcional al número de unidades. "
            "Cuadrillas: una por par de bodegas. "
            "Izadas: intensidad proporcional al número de izadas."
        ),
    )

    fig_buque = plot_vista_lateral(resultado.plan, modo=modo)
    st.plotly_chart(fig_buque, use_container_width=True, config=_PLOTLY_CONFIG)

    # 4c. Detalle por bodega
    st.markdown("#### 📦 Detalle de capas por bodega")
    bodega_sel = st.selectbox(
        "Ver detalle de bodega",
        options=list(range(1, 9)),
        format_func=lambda h: f"Bodega {h}",
        index=0,
    )

    fig_capas = plot_capas_bodega(resultado.plan, bodega_sel)
    st.plotly_chart(fig_capas, use_container_width=True, config=_PLOTLY_CONFIG)

    # 4d. Heatmap en expander
    with st.expander("🗺️ Fragmentación por destino", expanded=False):
        fig_heat = plot_heatmap_destinos(resultado.plan)
        st.plotly_chart(fig_heat, use_container_width=True, config=_PLOTLY_CONFIG)
else:
    st.info("Sin datos de plan para mostrar el dashboard del buque.")

st.divider()

# ---------------------------------------------------------------------------
# Tabla del plan
# ---------------------------------------------------------------------------
st.markdown("### 📋 Plan de estiba por bodega")

if resultado.plan:
    filas = [
        {
            "Bodega": f.bodega,
            "Plan": f.plan,
            "Producto": f.producto,
            "Destino": f.destino,
            "Unidades": f.unidades,
            "Toneladas": round(f.unidades * PESO_UNIDAD_T, 1),
        }
        for f in resultado.plan
    ]
    df = pd.DataFrame(filas).sort_values(["Bodega", "Plan"])
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Bodega": st.column_config.NumberColumn(format="%d"),
            "Plan": st.column_config.NumberColumn(format="%d"),
            "Unidades": st.column_config.NumberColumn(format="%d"),
            "Toneladas": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    st.caption(
        f"Total: {formato_unidades(sum(f['Unidades'] for f in filas))} unidades — "
        f"{sum(f['Toneladas'] for f in filas):,.0f} t"
    )
else:
    st.info("El plan está vacío — el solver no encontró solución factible.")

st.divider()

# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------
st.markdown("### ⬇️ Descargar resultados")

if "resultado_excel" not in st.session_state:
    try:
        st.session_state["resultado_excel"] = generar_excel_bytes(resultado)
    except Exception:
        st.session_state["resultado_excel"] = None

if "resultado_kpis_csv" not in st.session_state:
    try:
        st.session_state["resultado_kpis_csv"] = generar_kpis_csv(resultado)
    except Exception:
        st.session_state["resultado_kpis_csv"] = None

col_dl1, col_dl2, col_dl3 = st.columns(3)

with col_dl1:
    excel_bytes = st.session_state.get("resultado_excel")
    if excel_bytes:
        st.download_button(
            label="📥 Plan de estiba (Excel)",
            data=excel_bytes,
            file_name="plan_estiba.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.warning("No se pudo generar el Excel.")

with col_dl2:
    kpis_csv = st.session_state.get("resultado_kpis_csv")
    if kpis_csv:
        st.download_button(
            label="📥 KPIs (CSV)",
            data=kpis_csv,
            file_name="kpis_prestow.csv",
            mime="text/csv",
            use_container_width=True,
        )

with col_dl3:
    if st.button("🔄 Ejecutar de nuevo", use_container_width=True):
        st.switch_page("pages/1_Ejecutar.py")

# ---------------------------------------------------------------------------
# Detalles técnicos
# ---------------------------------------------------------------------------
with st.expander("🔧 Detalles técnicos de la corrida"):
    # Bug fix: no mostrar "Estado PuLP: Optimal" directamente
    if resultado.plan:
        st.markdown("**Estado:** Solución encontrada dentro del tiempo asignado")
    else:
        st.markdown("**Estado:** No se encontró solución factible")

    if resultado.gap is not None:
        gap_pct = resultado.gap * 100
        st.markdown(f"**Gap:** {resultado.gap:.4f} ({gap_pct:.2f}%)")
        if resultado.gap > 0:
            st.caption(
                "La solución es factible pero no se verificó que sea la mejor posible "
                "dentro del límite de tiempo configurado. Con más tiempo de cómputo "
                "el makespan podría reducirse hasta un "
                f"{gap_pct:.2f}% adicional."
            )
    else:
        st.caption(
            "Gap no disponible (limitación conocida de HiGHS + Python). "
            "Consulta la consola de Streamlit para ver el log completo del solver."
        )

    st.markdown("**Verificaciones:**")
    verif = resultado.verificaciones
    for nombre, errores in verif.items():
        icono = "✅" if not errores else "❌"
        msg = "OK" if not errores else f"{len(errores)} errores"
        st.markdown(f"- {icono} {nombre}: {msg}")
