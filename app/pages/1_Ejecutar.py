"""
Página Ejecutar — configura parámetros del solver y corre la optimización.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

_DIR_PAGES = Path(__file__).parent
_DIR_APP = _DIR_PAGES.parent
_RAIZ = _DIR_APP.parent
for _p in [str(_RAIZ / "src"), str(_DIR_APP)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

from components.caso_demo import cargar_caso_demo
from components.estilo import AZUL_MARINO, TEAL, aplicar_estilo_global
from components.formato import (
    generar_excel_bytes,
    generar_kpis_csv,
    generar_reporte_parametros,
)

st.set_page_config(
    page_title="Ejecutar",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo_global()

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

st.markdown("# ⚙️ Ejecutar optimización")

# --- Sin datos cargados ---
if "metadata" not in st.session_state:
    st.warning("No hay datos cargados. Carga un caso primero.")
    if st.button("← Volver al inicio"):
        st.switch_page("app.py")
    st.stop()

meta = st.session_state["metadata"]

# --- Grilla de 6 cards con los datos del caso ---
st.markdown(
    """
<style>
.card-metric { min-height: 120px; }
</style>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
cards_fila1 = [
    ("🚢", meta["buque"], "Buque"),
    ("📦", str(meta["bodegas"]), "Bodegas activas"),
    ("🎯", str(len(meta["destinos"])), "Puertos destino"),
]
cards_fila2 = [
    ("📊", f"{meta['unidades']:,}".replace(",", "."), "Unidades a embarcar"),
    ("⚖️", f"{meta['toneladas']:,} t".replace(",", "."), "Peso total"),
    ("🧭", str(len(meta["productos"])), "Tipos de producto"),
]

for col, (icono, valor, label) in zip([col1, col2, col3], cards_fila1):
    with col:
        st.markdown(
            f"<div class='card-prestow card-metric' style='border-left:4px solid {TEAL}; text-align:center;'>"
            f"<span class='card-metric-icon'>{icono}</span>"
            f"<span class='card-metric-value'>{valor}</span>"
            f"<span class='card-metric-label'>{label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

col4, col5, col6 = st.columns(3)
for col, (icono, valor, label) in zip([col4, col5, col6], cards_fila2):
    with col:
        st.markdown(
            f"<div class='card-prestow card-metric' style='border-left:4px solid {TEAL}; text-align:center;'>"
            f"<span class='card-metric-icon'>{icono}</span>"
            f"<span class='card-metric-value'>{valor}</span>"
            f"<span class='card-metric-label'>{label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.caption(
    "Datos precargados del caso demo · Puedes ejecutar directamente o ajustar parámetros abajo."
)

# --- Parámetros del solver ---
# Los widgets siempre se evalúan; el expander solo controla la visibilidad.
with st.expander("⚙️ Parámetros del solver (opcional)", expanded=False):
    col_s, col_t = st.columns(2)
    with col_s:
        solver = st.selectbox(
            "Solver",
            options=["HiGHS", "CBC"],
            index=0,
            help="HiGHS es más rápido. CBC como respaldo si HiGHS no está disponible.",
        )
    with col_t:
        limite = st.slider(
            "Límite de tiempo por pasada (segundos)",
            min_value=30,
            max_value=300,
            value=180,
            step=30,
            help="Se aplica a cada una de las dos pasadas del solver. "
                 "Valores más bajos dan resultados más rápidos pero menos precisos.",
        )
    st.caption(
        f"Tiempo estimado total: ~{max(1, round(limite * 2 / 60))} minutos. "
        "El solver puede terminar antes si encuentra la solución exacta."
    )

# --- Resultado previo ---
if "resultado" in st.session_state:
    st.success(
        f"Ya existe un resultado (makespan: {st.session_state['resultado'].makespan:.2f} h). "
        "Puedes ver los resultados o correr de nuevo."
    )
    if st.button("📊 Ver resultados anteriores", use_container_width=False):
        st.switch_page("pages/2_Resultados.py")

st.divider()

# --- Botón principal ---
col_run, col_info = st.columns([1, 2], gap="medium")

with col_run:
    correr = st.button(
        "🚀 Calcular plan de estiba",
        type="primary",
        use_container_width=True,
    )

with col_info:
    estimado_min = max(1, round(limite * 2 / 60))
    st.info(
        f"⏱️ El cálculo demora alrededor de **{estimado_min} minutos** "
        f"con límite de {limite} s por pasada. "
        "No cierres esta ventana mientras se ejecuta."
    )

# --- Ejecución ---
if correr:
    from api import resolver_prestow

    ruta_datos = st.session_state.get("ruta_datos", "")
    ruta_cap = st.session_state.get("ruta_capacidades", None)

    if not ruta_datos or not Path(ruta_datos).exists():
        st.error("No se encontró el archivo de datos. Vuelve al inicio y carga el caso demo.")
        st.stop()

    aviso = st.empty()
    aviso.markdown(
        f"<div class='card-prestow card-accion'>"
        f"<b>Ejecutando optimización en dos pasadas:</b><br>"
        f"<ol style='margin:8px 0 0 0;'>"
        f"<li>Minimizar el tiempo total de carga (makespan)</li>"
        f"<li>Reducir izadas y fragmentación, manteniendo el makespan obtenido</li>"
        f"</ol><br>Por favor no cierres esta ventana."
        f"</div>",
        unsafe_allow_html=True,
    )

    error_msg = None
    resultado = None

    with st.spinner("Calculando..."):
        try:
            resultado = resolver_prestow(
                ruta_datos=ruta_datos,
                ruta_capacidades=ruta_cap,
                limite_segundos=limite,
                solver=solver,
            )
        except FileNotFoundError as exc:
            error_msg = f"Archivo no encontrado: {exc}"
        except Exception as exc:
            error_msg = (
                "Ocurrió un error durante la optimización. "
                "Verifica que los archivos de datos estén completos y vuelve a intentar.\n\n"
                f"Detalle técnico: {type(exc).__name__}: {exc}"
            )

    aviso.empty()

    if error_msg:
        st.error(error_msg)
        st.stop()

    st.session_state["resultado"] = resultado
    st.session_state["parametros_corrida"] = {
        "solver": solver,
        "limite_segundos": limite,
        "ruta_datos": ruta_datos,
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        st.session_state["resultado_excel"] = generar_excel_bytes(resultado)
        st.session_state["resultado_kpis_csv"] = generar_kpis_csv(resultado)
        st.session_state["resultado_parametros_csv"] = generar_reporte_parametros(
            resultado, st.session_state["parametros_corrida"]
        )
    except Exception:
        pass

    makespan_manual = meta.get("makespan_manual_h")

    if makespan_manual is not None:
        ahorro = makespan_manual - resultado.makespan
        st.success(
            f"✅ Optimización completada — Makespan: **{resultado.makespan:.2f} h** "
            f"({ahorro:.2f} h más rápido que el plan de referencia)"
        )
    else:
        st.success(
            f"✅ Optimización completada — Makespan: **{resultado.makespan:.2f} h**. "
            "Este es un caso editado: no hay plan de referencia para comparar."
        )
    st.balloons()

    if st.button("📊 Ver resultados completos →", type="primary"):
        st.switch_page("pages/2_Resultados.py")
