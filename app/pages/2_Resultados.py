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
)
from components.vista_buque import (
    plot_balance_peso,
    plot_capas_bodega,
    plot_heatmap_destinos,
    plot_planimetria_capa,
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
st.caption(
    "De arriba hacia abajo: **indicadores clave** (qué tan bueno es el plan), "
    "**vista del buque** (dónde queda cada destino), **planimetría** (cómo se "
    "acomoda cada unidad dentro de una bodega y en qué orden la grúa las levanta), "
    "**balance de peso** (informativo), la **tabla completa** y la **descarga**."
)

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
makespan_manual = meta.get("makespan_manual_h")
hay_referencia = makespan_manual is not None
if hay_referencia:
    ahorro = makespan_manual - resultado.makespan
    ahorro_pct = (ahorro / makespan_manual) * 100

# --- Geometría (huellas de producto + piso de bodega): se usa en varias
# secciones de abajo (Planimetría, Balance de peso, Excel de descarga) — se
# calcula una sola vez acá para no repetir la lectura del Excel/carpeta de
# datos tres veces por corrida.
huellas: dict = {}
geometria: dict = {}
rot: dict = {d: i + 1 for i, d in enumerate(meta.get("destinos", ["TAICHUNG", "QINGDAO", "KUNSAN", "ULSAN"]))}
if resultado.plan:
    try:
        if "huellas_productos" not in st.session_state:
            from layout_capa import obtener_geometria_bodegas, obtener_huellas
            ruta_datos = st.session_state.get("ruta_datos", "")
            st.session_state["huellas_productos"] = obtener_huellas(ruta_datos)
            st.session_state["geometria_bodegas"] = obtener_geometria_bodegas(ruta_datos)
        huellas = st.session_state["huellas_productos"]
        geometria = st.session_state["geometria_bodegas"]
    except Exception:
        huellas, geometria = {}, {}

# ---------------------------------------------------------------------------
# Indicadores clave
# ---------------------------------------------------------------------------
st.markdown("### ⏱️ Indicadores clave")

col1, col2, col3 = st.columns(3)

with col1:
    if hay_referencia:
        # Texto explícito en lugar de depender del signo del delta
        delta_label = f"{ahorro:.2f} h más rápido que el plan de referencia"
        st.metric(
            label="⏱️ Makespan",
            value=formato_horas(resultado.makespan),
            delta=delta_label,
            help=f"Tiempo total de carga. Plan de referencia: {makespan_manual:.2f} h",
        )
    else:
        st.metric(
            label="⏱️ Makespan",
            value=formato_horas(resultado.makespan),
            help="Tiempo total de carga. Caso editado: sin plan de referencia para comparar.",
        )

with col2:
    if hay_referencia:
        st.metric(
            label="📉 Ahorro vs referencia",
            value=f"{ahorro:.2f} h",
            delta=f"{ahorro_pct:.1f}% del tiempo total",
            help=f"El plan de referencia es {makespan_manual:.2f} h.",
        )
    else:
        st.metric(label="📉 Ahorro vs referencia", value="—",
                   help="Sin plan de referencia para este caso editado.")

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
st.caption(
    "**Desbalance:** qué tan parejo es el trabajo entre las 4 cuadrillas — cerca "
    "de 0% es ideal, todas terminan casi al mismo tiempo. **Fragmentación:** en "
    "cuántas bodegas distintas queda repartido cada destino en total — menos es "
    "mejor, porque el puerto de destino tiene que abrir menos bodegas para "
    "descargar. **Izadas totales:** cuántas veces se mueve la grúa en toda la "
    "carga (cada izada mueve hasta 16 unidades)."
)

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
    st.caption(
        "Horas de trabajo de cada cuadrilla. Cada cuadrilla atiende un par fijo de "
        "bodegas (1: bodegas 7+8, 2: 5+6, 3: 3+4, 4: 1+2). El buque zarpa recién "
        "cuando termina la cuadrilla más lenta (en coral) — esa barra es el makespan."
    )
    fig_timeline = plot_timeline_cuadrillas(resultado.horas_por_cuadrilla, resultado.makespan)
    st.plotly_chart(fig_timeline, use_container_width=True, config=_PLOTLY_CONFIG)
else:
    st.info("No hay datos de horas por cuadrilla para mostrar el timeline.")

st.markdown("### 🗺️ Distribución por bodega")
st.caption(
    "Vista lateral del buque, bodega por bodega (1 a la izquierda, 8 a la derecha). "
    "Cada bodega se dibuja con sus planes (alturas) apilados — el plan 1 al fondo, "
    "el de más arriba es el techo de la carga. \"Colorear por\" cambia qué "
    "información muestran los colores."
)

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
    st.caption(
        "Las 11 capas (planes) de una bodega, apiladas como quedan realmente: "
        "plan 1 al fondo, plan 11 arriba. Si una capa mezcla más de un destino "
        "aparece dividida — son pocas, el modelo trata de evitarlo."
    )
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
        st.caption(
            "Cuántas unidades de cada destino hay en cada bodega. Un destino con "
            "números en pocas columnas está poco fragmentado (bien); repartido en "
            "muchas columnas es lo que mide el KPI de fragmentación de más arriba."
        )
        fig_heat = plot_heatmap_destinos(resultado.plan)
        st.plotly_chart(fig_heat, use_container_width=True, config=_PLOTLY_CONFIG)
else:
    st.info("Sin datos de plan para mostrar el dashboard del buque.")

st.divider()

# ---------------------------------------------------------------------------
# Planimetría y secuencia de izadas
# ---------------------------------------------------------------------------
st.markdown("## 🗺️ Planimetría y secuencia de izadas")
st.caption(
    "Vista desde arriba de una sola bodega y plan (capa), elegidos abajo. Cada "
    "cuadrado chico es una unidad de carga real, en su posición y tamaño "
    "aproximados — el color indica producto o destino (selector abajo). Los "
    "cuadrados se agrupan en bloques rectangulares del mismo tamaño con un "
    "número grande encima: eso es una **izada**, lo que la grúa mueve de una sola "
    "vez. El azul marino con \"16\" es una izada llena (la capacidad del marco de "
    "la grúa); el naranja con un número menor es una izada parcial, sobra al "
    "final de la capa. El orden de las izadas sigue la rotación del viaje: se "
    "carga primero lo que se descarga al final."
)

if resultado.plan and huellas and geometria:
    try:
        from layout_capa import layout_para_fila_plan
        from secuencia_izadas import calcular_secuencia

        capas_con_carga = sorted({(f.bodega, f.plan) for f in resultado.plan})
        bodegas_con_carga = sorted({b for b, _ in capas_con_carga})

        col_b, col_p, col_c = st.columns([1, 1, 1.5])
        with col_b:
            bod_sel = st.selectbox("Bodega", options=bodegas_con_carga,
                                    format_func=lambda h: f"Bodega {h}")
        with col_p:
            planes_bodega = sorted({t for b, t in capas_con_carga if b == bod_sel})
            plan_sel = st.selectbox("Plan (capa)", options=planes_bodega,
                                     format_func=lambda t: f"Plan {t}")
        with col_c:
            color_por = st.selectbox("Colorear planimetría por", options=["Producto", "Destino"])

        layout = layout_para_fila_plan(bod_sel, plan_sel, resultado.plan, geometria, huellas)
        izadas = calcular_secuencia(layout, rot)

        largo_piso, ancho_piso = geometria.get(bod_sel, (18.30, 27.40))
        fig_plan = plot_planimetria_capa(layout, largo_piso, ancho_piso,
                                          colorear_por=color_por, izadas=izadas)
        st.plotly_chart(fig_plan, use_container_width=True, config=_PLOTLY_CONFIG)

        packs_completos = sum(1 for iz in izadas if iz.cantidad == 16)
        st.caption(
            f"Bodega {bod_sel}, plan {plan_sel}: {len(layout)} unidades · {len(izadas)} izadas "
            f"({packs_completos} de 16 completas). Posiciones y orden de carga son una "
            "aproximación de visualización (no una restricción verificada del modelo — "
            "ver CLAUDE.md, supuesto 7)."
        )

        with st.expander(f"📋 Secuencia de izadas — bodega {bod_sel}, plan {plan_sel} ({len(izadas)} izadas)"):
            df_izadas = pd.DataFrame([
                {
                    "Izada": iz.numero,
                    "Unidades": iz.cantidad,
                    "Producto(s)": ", ".join(sorted(iz.productos)),
                    "Destino(s)": ", ".join(sorted(iz.destinos)),
                }
                for iz in izadas
            ])
            st.dataframe(df_izadas, hide_index=True, use_container_width=True)
    except Exception as exc:
        st.warning(
            "No se pudo calcular la planimetría de esta capa. "
            f"Detalle técnico: {type(exc).__name__}: {exc}"
        )
else:
    st.info("Sin datos de plan para mostrar la planimetría.")

st.divider()

# ---------------------------------------------------------------------------
# Balance de peso (informativo)
# ---------------------------------------------------------------------------
st.markdown("## ⚖️ Balance de peso")
st.caption(
    "El modelo intenta balancear el peso entre bodegas al momento de zarpar "
    "(tercera prioridad, después de minimizar el tiempo de carga y las "
    "izadas+fragmentación — nunca sacrifica esas dos por mejorar el balance). "
    "**Dispersión relativa** es la diferencia entre la bodega con más y con menos "
    "densidad de carga, como % del promedio — más cerca de 0% es más parejo. "
    "Este panel muestra el resultado ya logrado, es informativo: no hay una "
    "regla dura de \"la diferencia no puede superar X\"."
)

balance = None
if resultado.plan and huellas and geometria:
    try:
        from balance_peso import calcular_balance

        balance = calcular_balance(resultado.plan, huellas, geometria=geometria)

        col_bp1, col_bp2, col_bp3 = st.columns(3)
        with col_bp1:
            st.metric("Dispersión relativa de densidad", f"{balance.dispersion_relativa:.1f}%")
        with col_bp2:
            st.metric("Bodega más cargada", f"Bodega {balance.bodega_mas_cargada}",
                       help=f"{balance.peso_por_bodega[balance.bodega_mas_cargada]:,.0f} t".replace(",", "."))
        with col_bp3:
            st.metric("Bodega menos cargada", f"Bodega {balance.bodega_menos_cargada}",
                       help=f"{balance.peso_por_bodega[balance.bodega_menos_cargada]:,.0f} t".replace(",", "."))

        fig_balance = plot_balance_peso(balance.peso_por_bodega, balance.densidad_por_bodega)
        st.plotly_chart(fig_balance, use_container_width=True, config=_PLOTLY_CONFIG)
    except Exception as exc:
        st.warning(
            "No se pudo calcular el balance de peso. "
            f"Detalle técnico: {type(exc).__name__}: {exc}"
        )
else:
    st.info("Sin datos de plan para mostrar el balance de peso.")

st.divider()

# ---------------------------------------------------------------------------
# Tabla del plan
# ---------------------------------------------------------------------------
st.markdown("### 📋 Plan de estiba por bodega")
st.caption(
    "El plan completo en una tabla, una fila por cada combinación de bodega, "
    "plan (capa) y producto/destino. Es la misma información de la planimetría "
    "y el Excel, pero en formato de lista para filtrar o buscar un valor puntual."
)

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
st.caption(
    "Un solo Excel con todo: Plan de estiba (coloreado, formato del puerto), "
    "Detalle, Indicadores, Izadas y secuencia (todas las capas), Balance de "
    "peso y Parámetros de la corrida."
)

if "resultado_excel_completo" not in st.session_state:
    try:
        st.session_state["resultado_excel_completo"] = generar_excel_bytes(
            resultado,
            huellas=huellas,
            geometria=geometria,
            rot=rot,
            parametros=st.session_state.get("parametros_corrida"),
            balance=balance,
        )
    except Exception as exc:
        st.session_state["resultado_excel_completo"] = None
        st.session_state["resultado_excel_error"] = f"{type(exc).__name__}: {exc}"

col_dl1, col_dl2 = st.columns([2, 1])

with col_dl1:
    excel_bytes = st.session_state.get("resultado_excel_completo")
    if excel_bytes:
        st.download_button(
            label="📥 Descargar reporte completo (Excel)",
            data=excel_bytes,
            file_name="prestow_reporte_completo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.warning(
            "No se pudo generar el Excel. "
            f"Detalle técnico: {st.session_state.get('resultado_excel_error', 'desconocido')}"
        )

with col_dl2:
    if st.button("🔄 Ejecutar de nuevo", use_container_width=True):
        st.switch_page("pages/1_Ejecutar.py")

# ---------------------------------------------------------------------------
# Detalles técnicos
# ---------------------------------------------------------------------------
with st.expander("🔧 Detalles técnicos de la corrida"):
    st.caption(
        "Para quien quiera confirmar que el plan es confiable, no solo que se ve bien."
    )
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
    st.caption(
        "Chequeos automáticos sobre el plan ya calculado, no del solver — deberían "
        "dar siempre OK; si no, hay un problema real que revisar."
    )
    _EXPLICACION_VERIF = {
        "no_overstowage": "ningún destino que se descarga después queda tapando a uno que se descarga antes",
        "cobertura": "se embarcó exactamente la cantidad pedida de cada producto y destino, ni más ni menos",
        "contiguidad": "no hay carga \"flotando\" sobre un plan vacío dentro de una bodega",
        "capacidad": "ninguna capa excede la capacidad física calculada por el packer",
    }
    verif = resultado.verificaciones
    for nombre, errores in verif.items():
        icono = "✅" if not errores else "❌"
        msg = "OK" if not errores else f"{len(errores)} errores"
        explicacion = _EXPLICACION_VERIF.get(nombre, "")
        st.markdown(f"- {icono} **{nombre}**: {msg}" + (f" — {explicacion}" if explicacion else ""))
