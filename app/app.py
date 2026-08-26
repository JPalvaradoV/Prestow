"""
Página de inicio — Sistema Prestow.

Entry point: streamlit run app/app.py
"""

import sys
from pathlib import Path

_DIR_APP = Path(__file__).parent
_RAIZ = _DIR_APP.parent
for _p in [str(_RAIZ / "src"), str(_DIR_APP)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

from components.caso_demo import cargar_caso_demo
from components.estilo import aplicar_estilo_global

st.set_page_config(
    page_title="Inicio",
    page_icon="🚢",
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
    st.caption("© 2026", help="")

# --- Hero con ondas SVG inline ---
st.markdown(
    """
<div class="hero-prestow">
  <svg style="position:absolute;bottom:0;left:0;width:100%;height:55%;
              opacity:0.05;pointer-events:none;"
       viewBox="0 0 1440 180" preserveAspectRatio="none"
       xmlns="http://www.w3.org/2000/svg">
    <path d="M0,90 C360,40 720,140 1080,90 C1260,65 1380,110 1440,90
             L1440,180 L0,180 Z" fill="white"/>
    <path d="M0,130 C240,90 480,170 720,130 C960,90 1200,160 1440,130
             L1440,180 L0,180 Z" fill="white"/>
  </svg>
  <div style="position:relative;z-index:1;">
    <h1>Sistema de optimización de plan de estiba</h1>
    <p class="hero-subtitle">
      Genera el plan de carga más eficiente para operaciones de embarque de
      madera en rollo, minimizando el tiempo total y respetando la secuencia
      de descarga en cada puerto destino.
    </p>
    <ol>
      <li>Ingresa los datos del viaje (buque, productos, destinos y unidades)</li>
      <li>Ejecuta la optimización con un clic — resuelve en minutos</li>
      <li>Descarga el plan en Excel, listo para el equipo de planificación</li>
    </ol>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

# --- Cuerpo en dos columnas ---
col_texto, col_entregables = st.columns([3, 2], gap="large")

with col_texto:
    st.markdown(
        """
### ¿Qué hace este sistema?

Asigna cada unidad de carga a una bodega y un plan del buque de forma automática,
usando un modelo matemático exacto que considera los rendimientos reales de las
cuadrillas, las restricciones de descarga en cada puerto y la capacidad geométrica
de cada bodega.

El resultado es un plan verificado con:
- **Tiempo de carga mínimo** dentro del límite de tiempo de cómputo configurado
- **Cero overstowage** — garantía formal de que ninguna carga bloquea otra
- **Balance de cuadrillas** optimizado en una segunda pasada
        """
    )

with col_entregables:
    st.markdown(
        """
<div class="card-prestow card-info">
<h3 style="margin-top:0;">📦 ¿Qué genera el sistema?</h3>
<ul style="margin:12px 0 0 0; padding-left:20px; line-height:2.1; font-size:15px;">
  <li>📄 <b>Plan de estiba en Excel</b> — bodega × plan por cada unidad</li>
  <li>📊 <b>KPIs verificados</b> — makespan, desbalance, fragmentación</li>
  <li>🗺️ <b>Vista visual del buque</b> — distribución coloreada por destino</li>
  <li>📋 <b>Reporte técnico</b> — parámetros, estado del solver y validaciones</li>
</ul>
</div>
        """,
        unsafe_allow_html=True,
    )

# --- Sección demo ---
st.divider()
st.markdown("### ▶ Probar ahora con el caso demo")

col_btn, col_desc = st.columns([1, 3], gap="medium")

with col_btn:
    demo_click = st.button(
        "▶ Ejecutar caso demo",
        type="primary",
        use_container_width=True,
        help="Carga los datos del caso base y abre la pantalla de ejecución",
    )

with col_desc:
    st.markdown(
        "El caso demo incluye 8 bodegas, 5 productos y 4 puertos de destino. "
        "Podrás ajustar el límite de tiempo del solver antes de correr.\n\n"
        "El cálculo completo toma alrededor de **6 minutos** con los parámetros por defecto "
        "(puedes usar 60 s por pasada para un resultado preliminar en ~2 minutos)."
    )

if demo_click:
    cargar_caso_demo()
    st.switch_page("pages/1_Ejecutar.py")
