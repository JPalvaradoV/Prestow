"""
Página Configuración — formularios editables de Buque, Productos, Viaje y
Rotación (Fase 2). Guardar recalcula automáticamente capacidades.csv con
packer_2d y deja lista una carpeta de datos para Ejecutar.
"""

import sys
import tempfile
from pathlib import Path

_DIR_PAGES = Path(__file__).parent
_DIR_APP = _DIR_PAGES.parent
_RAIZ = _DIR_APP.parent
for _p in [str(_RAIZ / "src"), str(_DIR_APP)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

from components.caso_demo import cargar_caso_demo
from components.config_editable import (
    guardar_tablas_editables,
    leer_tablas_editables,
    recalcular_capacidades,
    resumen_metadata,
    validar_tablas,
)
from components.estilo import aplicar_estilo_global
from components.formato import formato_unidades

st.set_page_config(
    page_title="Configuración",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo_global()

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

st.markdown("# 🛠️ Configuración")
st.caption(
    "Edita el buque, los productos, el viaje y la rotación. Al guardar, la "
    "capacidad por bodega se recalcula automáticamente con el packer — no hace "
    "falta correrlo a mano."
)

# --- Sin caso cargado: ofrecer el caso demo como punto de partida ---
if "ruta_datos" not in st.session_state:
    st.warning("No hay ningún caso cargado. Carga el caso demo para empezar a editarlo.")
    if st.button("▶ Cargar caso demo para editar", type="primary"):
        cargar_caso_demo()
        st.rerun()
    st.stop()

# --- Cargar tablas editables (una vez por sesión, o al restablecer) ---
if "tablas_editables" not in st.session_state:
    try:
        st.session_state["tablas_editables"] = leer_tablas_editables(st.session_state["ruta_datos"])
    except Exception as exc:
        st.error(f"No se pudieron leer los datos actuales: {type(exc).__name__}: {exc}")
        st.stop()

tablas = st.session_state["tablas_editables"]

col_titulo, col_reset = st.columns([4, 1])
with col_reset:
    if st.button("↺ Restablecer al caso demo", use_container_width=True):
        cargar_caso_demo()
        st.session_state.pop("tablas_editables", None)
        st.rerun()

tab_buque, tab_productos, tab_viaje, tab_rotacion = st.tabs(
    ["🚢 Buque", "📦 Productos", "🧭 Viaje", "🗺️ Rotación"]
)

with tab_buque:
    st.caption("Una fila por bodega: dimensiones del piso, planes (alturas) y cuadrilla asignada.")
    buque_editado = st.data_editor(
        tablas["buque"], num_rows="dynamic", use_container_width=True, key="editor_buque",
        column_config={
            "bodega": st.column_config.NumberColumn("Bodega", format="%d"),
            "largo_m": st.column_config.NumberColumn("Largo (m)", format="%.2f", min_value=0.01),
            "ancho_m": st.column_config.NumberColumn("Ancho (m)", format="%.2f", min_value=0.01),
            "planes": st.column_config.NumberColumn("Planes (alturas)", format="%d", min_value=1),
            "cuadrilla": st.column_config.NumberColumn("Cuadrilla", format="%d", min_value=1),
        },
    )

with tab_productos:
    st.caption(
        "Una fila por producto. Agregar una fila nueva dispara el recálculo del packer "
        "al guardar — no hace falta correr nada aparte."
    )
    productos_editado = st.data_editor(
        tablas["productos"], num_rows="dynamic", use_container_width=True, key="editor_productos",
        column_config={
            "producto": st.column_config.TextColumn("Producto"),
            "huella_largo_m": st.column_config.NumberColumn("Huella largo (m)", format="%.3f", min_value=0.01),
            "huella_ancho_m": st.column_config.NumberColumn("Huella ancho (m)", format="%.3f", min_value=0.01),
            "peso_t": st.column_config.NumberColumn("Peso (t/unidad)", format="%.2f", min_value=0.01),
            "origen_dato": st.column_config.TextColumn("Origen del dato"),
        },
    )

with tab_viaje:
    st.caption("Unidades a embarcar por combinación de producto y destino.")
    viaje_editado = st.data_editor(
        tablas["viaje"], num_rows="dynamic", use_container_width=True, key="editor_viaje",
        column_config={
            "producto": st.column_config.TextColumn("Producto"),
            "destino": st.column_config.TextColumn("Destino"),
            "unidades": st.column_config.NumberColumn("Unidades", format="%d", min_value=0),
        },
    )

with tab_rotacion:
    st.caption("Puertos de destino en orden de descarga. 1 = se descarga primero.")
    rotacion_editado = st.data_editor(
        tablas["rotacion"], num_rows="dynamic", use_container_width=True, key="editor_rotacion",
        column_config={
            "destino": st.column_config.TextColumn("Destino"),
            "orden_descarga": st.column_config.NumberColumn("Orden de descarga", format="%d", min_value=1),
            "nota": st.column_config.TextColumn("Nota (opcional)"),
        },
    )

st.divider()

col_guardar, col_info = st.columns([1, 2], gap="medium")

with col_guardar:
    guardar = st.button("💾 Guardar cambios y recalcular", type="primary", use_container_width=True)

with col_info:
    st.info(
        "Al guardar: se valida la coherencia entre las cuatro tablas, se recalcula "
        "capacidades.csv con el packer, y el caso editado queda listo en Ejecutar."
    )

if guardar:
    tablas_nuevas = {
        "buque": buque_editado,
        "productos": productos_editado,
        "viaje": viaje_editado,
        "rotacion": rotacion_editado,
    }

    errores = validar_tablas(tablas_nuevas)
    if errores:
        st.error("No se pudo guardar — revisa lo siguiente:")
        for e in errores:
            st.markdown(f"- {e}")
        st.stop()

    try:
        if "carpeta_config_editada" not in st.session_state:
            st.session_state["carpeta_config_editada"] = tempfile.mkdtemp(prefix="prestow_config_")
        carpeta = st.session_state["carpeta_config_editada"]

        guardar_tablas_editables(tablas_nuevas, carpeta)
        ruta_cap = recalcular_capacidades(carpeta)

        nombre_buque = st.session_state.get("metadata", {}).get("buque", "Buque editado")
        meta_nueva = resumen_metadata(tablas_nuevas, nombre_buque=f"{nombre_buque} (editado)")

        st.session_state["tablas_editables"] = tablas_nuevas
        st.session_state["ruta_datos"] = carpeta
        st.session_state["ruta_capacidades"] = str(ruta_cap)
        st.session_state["metadata"] = meta_nueva
        for clave in ("resultado", "resultado_excel", "resultado_kpis_csv",
                      "resultado_parametros_csv", "huellas_productos", "geometria_bodegas"):
            st.session_state.pop(clave, None)

        st.success(
            f"✅ Guardado — {meta_nueva['bodegas']} bodegas, "
            f"{len(meta_nueva['productos'])} productos, "
            f"{formato_unidades(meta_nueva['unidades'])} unidades a embarcar. "
            "Capacidades recalculadas."
        )
        if st.button("⚙️ Ir a Ejecutar →", type="primary"):
            st.switch_page("pages/1_Ejecutar.py")
    except Exception as exc:
        st.error(f"Error al guardar o recalcular: {type(exc).__name__}: {exc}")
