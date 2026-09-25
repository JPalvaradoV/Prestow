"""
Página Configuración — formularios editables de Buque, Productos, Viaje y
Rotación (Fase 2). Guardar recalcula automáticamente capacidades.csv con
packer_2d y deja lista una carpeta de datos para Ejecutar.

Agregar y eliminar filas se hace con botones explícitos (no con la grilla de
Streamlit en modo "dynamic"): es más accesible — funciona con teclado y
lector de pantalla, y no depende de gestos de mouse poco descubribles como
seleccionar una fila y presionar Supr.
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

from components.nucleo import asegurar_nucleo_actualizado  # noqa: E402

# src/ al día tras un push (Streamlit Cloud no lo recarga solo; ver nucleo.py)
asegurar_nucleo_actualizado()

import pandas as pd
import streamlit as st

from components.caso_demo import cargar_caso_demo
from components.config_editable import (
    PUERTOS_CELULOSA_REFERENCIA,
    guardar_tablas_editables,
    leer_tablas_editables,
    recalcular_capacidades,
    resumen_metadata,
    validar_tablas,
)
from components.estilo import aplicar_estilo_global
from components.formato import formato_unidades
from components.referencia import KPIS_REFERENCIA, normalizar

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
    "Indica qué buque estás evaluando y los KPIs de su plan de referencia, y "
    "edita el buque, los productos, el viaje y la rotación. Al guardar, la "
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

# ---------------------------------------------------------------------------
# Helpers de agregar / eliminar filas (versión de clave para forzar que la
# grilla se recargue desde session_state después de un cambio programático)
# ---------------------------------------------------------------------------

def _version(nombre: str) -> int:
    return st.session_state.setdefault("editor_version", {}).get(nombre, 0)


def _agregar_fila(nombre: str, df_actual: pd.DataFrame, fila_nueva: dict) -> None:
    nuevo = pd.concat([df_actual, pd.DataFrame([fila_nueva])], ignore_index=True)
    st.session_state["tablas_editables"][nombre] = nuevo
    st.session_state["editor_version"][nombre] = _version(nombre) + 1
    st.rerun()


def _eliminar_fila(nombre: str, df_actual: pd.DataFrame, idx: int) -> None:
    nuevo = df_actual.drop(index=df_actual.index[idx]).reset_index(drop=True)
    st.session_state["tablas_editables"][nombre] = nuevo
    st.session_state["editor_version"][nombre] = _version(nombre) + 1
    st.rerun()


def _control_eliminar(nombre: str, df_actual: pd.DataFrame, etiqueta_fn) -> None:
    """Selectbox + botón para eliminar una fila. Alternativa explícita y
    accesible al borrado desde la grilla."""
    if df_actual.empty:
        st.caption("No hay filas para eliminar.")
        return
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        idx = st.selectbox(
            "Fila a eliminar", options=list(range(len(df_actual))),
            format_func=lambda i: etiqueta_fn(df_actual.iloc[i]),
            key=f"sel_eliminar_{nombre}_{_version(nombre)}",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("🗑️ Eliminar fila", key=f"btn_eliminar_{nombre}_{_version(nombre)}",
                     use_container_width=True):
            _eliminar_fila(nombre, df_actual, idx)


tablas = st.session_state["tablas_editables"]
_CLAVE_NOMBRE = "cfg_nombre_buque"
_CLAVE_REF = "cfg_ref_"

col_titulo, col_reset = st.columns([4, 1])
with col_reset:
    if st.button("↺ Restablecer al caso demo", use_container_width=True):
        cargar_caso_demo()
        st.session_state.pop("tablas_editables", None)
        st.session_state.pop("editor_version", None)
        for _k in [_CLAVE_NOMBRE] + [_CLAVE_REF + k.clave for k in KPIS_REFERENCIA]:
            st.session_state.pop(_k, None)
        st.rerun()

# ---------------------------------------------------------------------------
# Buque evaluado y plan de referencia
# ---------------------------------------------------------------------------
# Se guardan directo en metadata (no hace falta "Guardar"): Resultados, Ejecutar
# y el Excel comparan contra estos valores. Los widgets se inicializan desde
# metadata porque Streamlit borra el estado de un widget cuando se navega a
# otra página donde no se dibuja.
st.markdown("### 🚢 Buque evaluado y plan de referencia")
st.caption(
    "Los KPIs de referencia son los del plan con que se cargó (o se cargaría) "
    "este buque sin el modelo — normalmente el plan manual del puerto. Resultados "
    "compara contra estos valores. Deja en blanco los que no tengas: ese KPI se "
    "muestra sin comparación."
)
meta = st.session_state.setdefault("metadata", {})
referencia_actual = dict(meta.get("referencia") or {})
if _CLAVE_NOMBRE not in st.session_state:
    st.session_state[_CLAVE_NOMBRE] = meta.get("buque", "")
for _kpi in KPIS_REFERENCIA:
    if _CLAVE_REF + _kpi.clave not in st.session_state:
        _v = referencia_actual.get(_kpi.clave)
        # float siempre: number_input no admite mezclar int con min_value float
        st.session_state[_CLAVE_REF + _kpi.clave] = None if _v is None else float(_v)

nombre_buque = st.text_input(
    "Nombre del buque", key=_CLAVE_NOMBRE, placeholder="Ej.: Kiwi Arrow",
    help="Aparece en las pantallas de resumen y en el Excel de descarga.",
).strip()
if not nombre_buque:
    st.warning("Escribe el nombre del buque que estás evaluando.")

cols_ref = st.columns(len(KPIS_REFERENCIA))
referencia_nueva = {}
for _col, _kpi in zip(cols_ref, KPIS_REFERENCIA):
    with _col:
        etiqueta = f"{_kpi.etiqueta} ({_kpi.unidad})" if _kpi.unidad else _kpi.etiqueta
        valor = st.number_input(
            etiqueta, key=_CLAVE_REF + _kpi.clave, min_value=0.0,
            step=1.0 if _kpi.decimales == 0 else 0.1,
            format=f"%.{_kpi.decimales}f", help=_kpi.ayuda, placeholder="Sin dato",
        )
        referencia_nueva[_kpi.clave] = normalizar(valor, _kpi)

if nombre_buque and (nombre_buque != meta.get("buque") or referencia_nueva != referencia_actual):
    meta["buque"] = nombre_buque
    meta["referencia"] = referencia_nueva
    # El Excel de descarga ya armado lleva la referencia anterior: se rehace
    st.session_state.pop("resultado_excel_completo", None)
    st.session_state.pop("resultado_excel_error", None)

st.divider()

tab_buque, tab_productos, tab_viaje, tab_rotacion = st.tabs(
    ["🚢 Buque", "📦 Productos", "🧭 Viaje", "🗺️ Rotación"]
)

# ---------------------------------------------------------------------------
# Buque
# ---------------------------------------------------------------------------
with tab_buque:
    st.caption("Una fila por bodega: dimensiones del piso, planes (alturas) y cuadrilla asignada.")
    df_buque = tablas["buque"]
    buque_editado = st.data_editor(
        df_buque, num_rows="fixed", use_container_width=True,
        key=f"editor_buque_{_version('buque')}",
        column_config={
            "bodega": st.column_config.NumberColumn("Bodega", format="%d", min_value=1),
            "largo_m": st.column_config.NumberColumn("Largo (m)", format="%.2f", min_value=0.01),
            "ancho_m": st.column_config.NumberColumn("Ancho (m)", format="%.2f", min_value=0.01),
            "planes": st.column_config.NumberColumn("Planes (alturas)", format="%d", min_value=1),
            "cuadrilla": st.column_config.NumberColumn("Cuadrilla", format="%d", min_value=1),
        },
    )
    col_add, col_del = st.columns([1, 2])
    with col_add:
        if st.button("➕ Agregar bodega", key="btn_agregar_buque", use_container_width=True):
            siguiente = int(buque_editado["bodega"].max()) + 1 if not buque_editado.empty else 1
            _agregar_fila("buque", buque_editado, {
                "bodega": siguiente, "largo_m": 18.30, "ancho_m": 27.40,
                "planes": 11, "cuadrilla": 1,
            })
    with col_del:
        _control_eliminar("buque", buque_editado, lambda r: f"Bodega {int(r['bodega'])}")

# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------
with tab_productos:
    st.caption(
        "Una fila por producto. Agregar una fila nueva dispara el recálculo del packer "
        "al guardar — no hace falta correr nada aparte."
    )
    df_productos = tablas["productos"]
    productos_editado = st.data_editor(
        df_productos, num_rows="fixed", use_container_width=True,
        key=f"editor_productos_{_version('productos')}",
        column_config={
            "producto": st.column_config.TextColumn("Producto"),
            "huella_largo_m": st.column_config.NumberColumn("Huella largo (m)", format="%.3f", min_value=0.01),
            "huella_ancho_m": st.column_config.NumberColumn("Huella ancho (m)", format="%.3f", min_value=0.01),
            "peso_t": st.column_config.NumberColumn("Peso (t/unidad)", format="%.2f", min_value=0.01),
            "origen_dato": st.column_config.TextColumn(
                "Origen del dato",
                help=(
                    "De dónde sale la medida de la huella de este producto. "
                    "'verificado - plantillas ...' significa que se midió en una "
                    "plantilla real del buque; 'SUPUESTO' significa que no había "
                    "plantilla propia y se usó un valor estimado — la capacidad "
                    "calculada para ese producto es tan confiable como ese supuesto."
                ),
            ),
        },
    )
    col_add, col_del = st.columns([1, 2])
    with col_add:
        if st.button("➕ Agregar producto", key="btn_agregar_productos", use_container_width=True):
            _agregar_fila("productos", productos_editado, {
                "producto": f"PRODUCTO_NUEVO_{len(productos_editado) + 1}",
                "huella_largo_m": 1.0, "huella_ancho_m": 1.0, "peso_t": 2.02,
                "origen_dato": "ingresado por usuario — sin verificar",
            })
    with col_del:
        _control_eliminar("productos", productos_editado, lambda r: str(r["producto"]))

# ---------------------------------------------------------------------------
# Rotación (se calcula antes que Viaje: Viaje necesita la lista de destinos)
# ---------------------------------------------------------------------------
with tab_rotacion:
    st.caption(
        "Puertos de destino en orden de descarga. 1 = se descarga primero. "
        "El destino se elige de una lista para evitar errores de tipeo; si falta "
        "un puerto, se puede escribir directamente en la celda."
    )
    df_rotacion = tablas["rotacion"]
    destinos_actuales = df_rotacion["destino"].astype(str).str.strip().str.upper().tolist()
    opciones_destino = sorted(set(PUERTOS_CELULOSA_REFERENCIA) | set(destinos_actuales))

    rotacion_editado = st.data_editor(
        df_rotacion, num_rows="fixed", use_container_width=True,
        key=f"editor_rotacion_{_version('rotacion')}",
        column_config={
            "destino": st.column_config.SelectboxColumn(
                "Destino", options=opciones_destino,
                help="Lista de referencia de puertos que reciben celulosa (no verificada por el puerto).",
            ),
            "orden_descarga": st.column_config.NumberColumn("Orden de descarga", format="%d", min_value=1),
            "nota": st.column_config.TextColumn("Nota (opcional)"),
        },
    )

    st.markdown("**Agregar puerto**")
    col_pick, col_add, col_del = st.columns([2, 1, 2])
    with col_pick:
        no_usados = [p for p in PUERTOS_CELULOSA_REFERENCIA if p not in destinos_actuales]
        puerto_nuevo = st.selectbox(
            "Puerto a agregar", options=no_usados or PUERTOS_CELULOSA_REFERENCIA,
            key="sel_puerto_nuevo", label_visibility="collapsed",
        )
    with col_add:
        if st.button("➕ Agregar", key="btn_agregar_rotacion", use_container_width=True):
            siguiente_orden = (
                int(rotacion_editado["orden_descarga"].max()) + 1 if not rotacion_editado.empty else 1
            )
            _agregar_fila("rotacion", rotacion_editado, {
                "destino": puerto_nuevo, "orden_descarga": siguiente_orden, "nota": "",
            })
    with col_del:
        _control_eliminar("rotacion", rotacion_editado, lambda r: str(r["destino"]))

# ---------------------------------------------------------------------------
# Viaje (usa las listas ya editadas de Productos y Rotación)
# ---------------------------------------------------------------------------
with tab_viaje:
    st.caption(
        "Unidades a embarcar por combinación de producto y destino. Producto y "
        "destino se eligen de listas desplegables (los que existen en las tablas "
        "de Productos y Rotación) para que no se puedan escribir mal."
    )
    df_viaje = tablas["viaje"]

    productos_disponibles = sorted(
        set(productos_editado["producto"].astype(str).str.strip())
        | set(df_viaje["producto"].astype(str).str.strip())
    )
    destinos_disponibles = sorted(
        set(rotacion_editado["destino"].astype(str).str.strip().str.upper())
        | set(df_viaje["destino"].astype(str).str.strip().str.upper())
    )

    if not productos_disponibles:
        st.warning("No hay productos declarados todavía — agrega al menos uno en la pestaña Productos.")
    if not destinos_disponibles:
        st.warning("No hay destinos declarados todavía — agrega al menos uno en la pestaña Rotación.")

    viaje_editado = st.data_editor(
        df_viaje, num_rows="fixed", use_container_width=True,
        key=f"editor_viaje_{_version('viaje')}",
        column_config={
            "producto": st.column_config.SelectboxColumn("Producto", options=productos_disponibles),
            "destino": st.column_config.SelectboxColumn("Destino", options=destinos_disponibles),
            "unidades": st.column_config.NumberColumn("Unidades", format="%d", min_value=0),
        },
    )
    col_add, col_del = st.columns([1, 2])
    with col_add:
        if st.button("➕ Agregar fila", key="btn_agregar_viaje", use_container_width=True,
                     disabled=not (productos_disponibles and destinos_disponibles)):
            _agregar_fila("viaje", viaje_editado, {
                "producto": productos_disponibles[0], "destino": destinos_disponibles[0], "unidades": 0,
            })
    with col_del:
        _control_eliminar("viaje", viaje_editado, lambda r: f"{r['producto']} → {r['destino']}")

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

        meta_actual = st.session_state.get("metadata", {})
        meta_nueva = resumen_metadata(
            tablas_nuevas,
            nombre_buque=meta_actual.get("buque") or "Buque editado",
            referencia=meta_actual.get("referencia"),
        )

        st.session_state["tablas_editables"] = tablas_nuevas
        st.session_state["ruta_datos"] = carpeta
        st.session_state["ruta_capacidades"] = str(ruta_cap)
        st.session_state["metadata"] = meta_nueva
        for clave in ("resultado", "resultado_excel_completo", "resultado_excel_error",
                      "huellas_productos", "geometria_bodegas"):
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
