"""
Estilos globales y paleta de colores de la aplicación Prestow.

Exporta constantes de color usadas por otros módulos y
la función aplicar_estilo_global() que inyecta el CSS en la página activa.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Paleta de colores (exportada)
# ---------------------------------------------------------------------------
AZUL_MARINO = "#0F3D5A"       # primario — headers, fondos oscuros
TEAL = "#0891B2"              # acento vivo — botones secundarios, hovers
DORADO = "#C89B3C"            # highlights, badges especiales
CORAL = "#F97316"             # elementos que requieren atención
VERDE = "#10B981"             # éxito, mejoras
GRIS_FONDO = "#F5F7FA"
GRIS_BORDE = "#E2E8F0"
TEXTO_PRINCIPAL = "#1E293B"
TEXTO_SECUNDARIO = "#64748B"

# ---------------------------------------------------------------------------
# CSS inyectado
# ---------------------------------------------------------------------------
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* --- Fuente global --- */
html, body, .stApp, [class^="st-"], [class*=" st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* --- Tipografía --- */
.stApp h1 {
    font-size: 32px !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #0F3D5A;
}
.stApp h2 {
    font-size: 24px !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #0F3D5A;
}
.stApp h3 {
    font-size: 18px !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    color: #0F3D5A;
}

/* --- Hero de inicio --- */
.hero-prestow {
    background: linear-gradient(135deg, #0F3D5A 0%, #164D6E 60%, #1A5E84 100%);
    border-radius: 16px;
    padding: 48px 52px;
    color: white;
    position: relative;
    overflow: hidden;
    margin-bottom: 28px;
}
.hero-prestow h1 {
    color: white !important;
    font-size: 34px !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    margin: 0 0 10px 0;
}
.hero-prestow .hero-subtitle {
    color: rgba(255, 255, 255, 0.72);
    font-size: 17px;
    margin: 0 0 28px 0;
    line-height: 1.5;
}
.hero-prestow ol {
    color: white;
    padding-left: 20px;
    line-height: 2;
    font-size: 15px;
    margin: 0;
}
.hero-prestow li {
    color: rgba(255, 255, 255, 0.88);
}

/* --- Card base --- */
.card-prestow {
    background: white;
    border-radius: 12px;
    padding: 24px 28px;
    box-shadow: 0 4px 12px rgba(15, 61, 90, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
    margin-bottom: 20px;
}

/* Variantes de borde izquierdo según categoría */
.card-info    { border-left: 4px solid #0891B2; }   /* teal */
.card-datos   { border-left: 4px solid #0F3D5A; }   /* navy */
.card-accion  { border-left: 4px solid #F97316; }   /* coral */
.card-resultado { border-left: 4px solid #10B981; } /* verde */

/* --- Cards de métricas (grilla 6 tarjetas) --- */
.card-metric {
    background: white;
    border-radius: 12px;
    padding: 24px 16px 20px;
    box-shadow: 0 4px 12px rgba(15, 61, 90, 0.08);
    border-left: 4px solid #0891B2;
    text-align: center;
    margin-bottom: 16px;
    transition: box-shadow 0.18s ease, transform 0.18s ease;
    cursor: default;
}
.card-metric:hover {
    box-shadow: 0 8px 20px rgba(15, 61, 90, 0.14);
    transform: translateY(-2px);
}
.card-metric-icon {
    font-size: 28px;
    line-height: 1;
    margin-bottom: 10px;
    display: block;
}
.card-metric-value {
    font-size: 26px;
    font-weight: 700;
    color: #0F3D5A;
    letter-spacing: -0.02em;
    margin-bottom: 6px;
    display: block;
    font-family: 'Inter', sans-serif;
}
.card-metric-label {
    font-size: 11px;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    display: block;
}

/* --- Métricas Streamlit con fondo blanco --- */
[data-testid="stMetric"] {
    background-color: white;
    border-radius: 10px;
    padding: 18px 22px;
    box-shadow: 0 4px 12px rgba(15, 61, 90, 0.07);
}

/* --- Botones --- */
.stButton > button[kind="primary"] {
    background-color: #0F3D5A !important;
    border-color: #0F3D5A !important;
    color: white !important;
    font-size: 15px;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.01em;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}
.stButton > button[kind="primary"]:hover {
    background-color: #0891B2 !important;
    border-color: #0891B2 !important;
}

/* --- Sidebar --- */
[data-testid="stSidebar"] hr {
    border-color: rgba(15, 61, 90, 0.12);
}

/* --- DataFrames compactos --- */
[data-testid="stDataFrame"] {
    font-size: 13px;
}

/* --- Header de sección con línea inferior --- */
.header-prestow {
    border-bottom: 3px solid #0F3D5A;
    padding-bottom: 10px;
    margin-bottom: 24px;
}
</style>
"""


def aplicar_estilo_global() -> None:
    """Inyecta el CSS global en la página activa."""
    st.markdown(_CSS, unsafe_allow_html=True)
