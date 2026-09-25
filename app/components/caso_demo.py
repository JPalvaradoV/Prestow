"""
Carga los datos del caso demo (Kiwi Arrow) en st.session_state.

No ejecuta el modelo — solo prepara las rutas y metadatos para que
la página Ejecutar los use cuando el usuario haga clic en "Correr".
"""

from pathlib import Path

import streamlit as st

from .referencia import REFERENCIA_KIWI_ARROW

_RAIZ = Path(__file__).parent.parent.parent  # raíz del proyecto


def cargar_caso_demo() -> None:
    """
    Puebla session_state con las rutas y metadatos del caso base.

    Limpia cualquier resultado previo para evitar que la página de
    Resultados muestre datos de una corrida anterior.
    """
    st.session_state["ruta_datos"] = str(_RAIZ / "data" / "datos_entrada_kiwi_arrow.xlsx")
    st.session_state["ruta_capacidades"] = str(_RAIZ / "data" / "capacidades.csv")
    st.session_state["metadata"] = {
        "buque": "Kiwi Arrow",
        "operador": "G2 Ocean",
        "bodegas": 8,
        "unidades": 29_332,
        "toneladas": 59_197,
        "destinos": ["TAICHUNG", "QINGDAO", "KUNSAN", "ULSAN"],
        "productos": ["N_ALDEA_EKP", "N_ALDEA_BKP", "ARAUCO_EKP", "ARAUCO_BKP", "CELCO_UKP"],
        # KPIs del plan manual real, editables en Configuración
        "referencia": dict(REFERENCIA_KIWI_ARROW),
    }
    # Limpiar resultado anterior
    for clave in ("resultado", "resultado_excel_completo", "resultado_excel_error",
                  "huellas_productos", "geometria_bodegas"):
        st.session_state.pop(clave, None)
