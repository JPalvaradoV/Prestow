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
from components.referencia import KPIS_REFERENCIA, formatear, hay_referencia, normalizar

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

# --- Plan de referencia (se ingresa en Configuración) ---
referencia = meta.get("referencia") or {}
if hay_referencia(referencia):
    partes = [
        f"{k.etiqueta}: **{formatear(normalizar(referencia.get(k.clave), k), k)}**"
        for k in KPIS_REFERENCIA
        if normalizar(referencia.get(k.clave), k) is not None
    ]
    st.info("📋 Plan de referencia para comparar — " + " · ".join(partes))
else:
    st.warning(
        "📋 Sin plan de referencia: los resultados se van a mostrar sin comparación. "
        "Si tienes los KPIs del plan manual de este buque, ingrésalos en Configuración."
    )
if st.button("🛠️ Cambiar buque o plan de referencia"):
    st.switch_page("pages/0_Configuracion.py")

st.caption("Puedes ejecutar directamente o ajustar parámetros abajo.")

# --- Parámetros del solver ---
# Los widgets siempre se evalúan; el expander solo controla la visibilidad.
with st.expander("⚙️ Parámetros del solver (opcional)", expanded=False):
    col_s, col_t = st.columns(2)
    with col_s:
        solver = st.selectbox(
            "Solver",
            options=["HiGHS", "CBC"],
            index=0,
            help="HiGHS es más rápido y usa un punto de partida propio para no "
                 "empezar de cero (ver más abajo) — se recomienda dejarlo. CBC "
                 "es el respaldo si HiGHS no está disponible, pero no usa ese "
                 "punto de partida, así que necesita más tiempo.",
        )
    with col_t:
        limite = st.slider(
            "Límite de tiempo por pasada (segundos)",
            min_value=30,
            max_value=360,
            value=180,
            step=30,
            help="Se aplica a cada una de las tres pasadas del solver (makespan, "
                 "izadas+fragmentación, balance de peso) — el tiempo total es el "
                 "triple de este valor. Máximo 360 s por pasada (18 minutos en total). "
                 "Con HiGHS, el solver arranca desde un punto de partida ya factible "
                 "(no óptimo) en vez de buscar una solución desde cero, así que incluso "
                 "límites bajos como 30 s devuelven un plan válido — solo que con menos "
                 "tiempo para mejorarlo. 180 s por pasada es lo que se probó a fondo "
                 "contra el caso base.",
        )
    st.caption(
        f"Tiempo estimado total: ~{max(1, round(limite * 3 / 60))} minutos (máximo 18). "
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
    estimado_min = max(1, round(limite * 3 / 60))
    st.info(
        f"⏱️ El cálculo demora alrededor de **{estimado_min} minutos** "
        f"con límite de {limite} s por pasada. "
        "No cierres esta ventana mientras se ejecuta."
    )

# --- Ejecución ---
if correr:
    import threading

    from api import resolver_prestow

    ruta_datos = st.session_state.get("ruta_datos", "")
    ruta_cap = st.session_state.get("ruta_capacidades", None)

    if not ruta_datos or not Path(ruta_datos).exists():
        st.error("No se encontró el archivo de datos. Vuelve al inicio y carga el caso demo.")
        st.stop()

    aviso = st.empty()
    aviso.markdown(
        f"<div class='card-prestow card-accion'>"
        f"<b>Ejecutando optimización en tres pasadas:</b><br>"
        f"<ol style='margin:8px 0 0 0;'>"
        f"<li>Minimizar el tiempo total de carga (makespan)</li>"
        f"<li>Reducir izadas y fragmentación, manteniendo el makespan obtenido</li>"
        f"<li>Balancear el peso entre bodegas al zarpar, sin empeorar lo anterior</li>"
        f"</ol><br>Por favor no cierres esta ventana."
        f"</div>",
        unsafe_allow_html=True,
    )

    # La corrida se lanza en un hilo aparte y este bucle sondea su estado
    # cada segundo para mostrar avance en vivo (etapa actual + tiempo
    # transcurrido) — sin esto, la página quedaba con un spinner ciego
    # durante los minutos que puede tardar el solver, sin forma de saber si
    # seguía calculando o se había colgado (reportado por el usuario el
    # 22-sep-2026).
    estado_hilo = {"mensaje": "Iniciando…", "resultado": None, "error": None, "terminado": False}

    def _correr_en_hilo():
        try:
            estado_hilo["resultado"] = resolver_prestow(
                ruta_datos=ruta_datos,
                ruta_capacidades=ruta_cap,
                limite_segundos=limite,
                solver=solver,
                progreso=lambda m: estado_hilo.update(mensaje=m),
                nombre_buque=meta.get("buque"),
            )
        except FileNotFoundError as exc:
            estado_hilo["error"] = f"Archivo no encontrado: {exc}"
        except Exception as exc:
            estado_hilo["error"] = (
                "Ocurrió un error durante la optimización. "
                "Verifica que los archivos de datos estén completos y vuelve a intentar.\n\n"
                f"Detalle técnico: {type(exc).__name__}: {exc}"
            )
        finally:
            estado_hilo["terminado"] = True

    hilo = threading.Thread(target=_correr_en_hilo, daemon=True)
    t_inicio_corrida = time.time()
    hilo.start()

    progreso_ui = st.empty()
    while not estado_hilo["terminado"]:
        transcurrido = int(time.time() - t_inicio_corrida)
        minutos, segundos = divmod(transcurrido, 60)
        progreso_ui.markdown(
            f"<div class='card-prestow card-accion'>"
            f"⏳ <b>{estado_hilo['mensaje']}</b><br>"
            f"<span style='opacity:0.7;'>Tiempo transcurrido: {minutos} min {segundos:02d} s</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        time.sleep(1)

    hilo.join()
    progreso_ui.empty()
    aviso.empty()

    error_msg = estado_hilo["error"]
    resultado = estado_hilo["resultado"]

    if error_msg:
        st.error(error_msg)
        st.stop()

    st.session_state["resultado"] = resultado
    st.session_state["parametros_corrida"] = {
        "solver": solver,
        "limite_segundos": limite,
        "ruta_datos": ruta_datos,
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "buque": meta.get("buque", ""),
    }
    # El Excel completo (con izadas y balance de peso) se arma en Resultados,
    # la primera vez que se abre esa página — ahí ya están las huellas y la
    # geometría cacheadas. Acá solo limpiamos cualquier reporte de una
    # corrida anterior para que no se mezcle con este resultado nuevo.
    for clave in ("resultado_excel_completo", "resultado_excel_error"):
        st.session_state.pop(clave, None)

    makespan_ref = normalizar((meta.get("referencia") or {}).get("makespan_h"), KPIS_REFERENCIA[0])

    if makespan_ref is not None:
        diferencia = makespan_ref - resultado.makespan
        comparacion = (
            f"{diferencia:.2f} h más rápido que el plan de referencia"
            if diferencia >= 0
            else f"{-diferencia:.2f} h más lento que el plan de referencia"
        )
        st.success(
            f"✅ Optimización completada — Makespan: **{resultado.makespan:.2f} h** ({comparacion})"
        )
    else:
        st.success(
            f"✅ Optimización completada — Makespan: **{resultado.makespan:.2f} h**. "
            "Sin makespan de referencia para comparar."
        )
    st.balloons()

    if st.button("📊 Ver resultados completos →", type="primary"):
        st.switch_page("pages/2_Resultados.py")
