"""
Estilo visual de la app: paleta rosa elegante + botones con relieve suave.
Llamar `aplicar_estilo()` al principio de cada page (después de set_page_config).
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');

/* Tipografía global */
html, body, [class*="css"], button, input, textarea, select {
    font-family: 'Montserrat', 'Helvetica Neue', system-ui, -apple-system, sans-serif !important;
    letter-spacing: 0.01em;
}

/* Headings */
h1, h2, h3, h4 {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600 !important;
    color: #6A1B47 !important;
    letter-spacing: -0.01em;
}
h1 { letter-spacing: -0.02em; font-weight: 700 !important; }

/* Caption discreta en tono mauve */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #8E5A75 !important;
}

/* Botones — primary */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #E91E63 0%, #C2185B 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6em 1.6em !important;
    font-weight: 600 !important;
    box-shadow: 0 3px 10px rgba(194, 24, 91, 0.25) !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 5px 16px rgba(194, 24, 91, 0.35) !important;
    filter: brightness(1.05);
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(194, 24, 91, 0.3) !important;
}

/* Botones — secondary */
.stButton > button:not([kind="primary"]),
.stFormSubmitButton > button:not([kind="primary"]) {
    background: #FFFFFF !important;
    color: #C2185B !important;
    border: 1.5px solid #F8BBD0 !important;
    border-radius: 12px !important;
    padding: 0.55em 1.4em !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:not([kind="primary"]):hover,
.stFormSubmitButton > button:not([kind="primary"]):hover {
    background: #FDF2F8 !important;
    border-color: #C2185B !important;
}

/* Inputs / selects con borde rosado tenue */
input, textarea, .stTextInput > div > div, .stNumberInput > div > div {
    border-radius: 10px !important;
}
.stTextInput > div > div:focus-within,
.stNumberInput > div > div:focus-within {
    border-color: #C2185B !important;
    box-shadow: 0 0 0 2px rgba(194, 24, 91, 0.12) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FDF2F8 0%, #FCE4EC 100%) !important;
    border-right: 1px solid #F8BBD0;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #6A1B47 !important;
}

/* Ocultar navegación automática que muestra los nombres de los archivos .py */
[data-testid="stSidebarNav"] { display: none !important; }

/* Métricas */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #F8BBD0;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 2px 8px rgba(194, 24, 91, 0.06);
}
[data-testid="stMetricValue"] {
    color: #C2185B !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #8E5A75 !important;
    font-weight: 500 !important;
}
[data-testid="stMetricDelta"] {
    color: #2E7D32 !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid #F8BBD0 !important;
    border-radius: 12px !important;
    background: #FFFFFF;
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #6A1B47;
}

/* Dataframes — sin overflow:hidden para no recortar toolbar (delete) ni botón "+" */
[data-testid="stDataFrame"] {
    border-radius: 10px;
}

/* Divider con tinte rosa */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #F8BBD0, transparent) !important;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 12px;
}

/* Page links como pills rosadas */
[data-testid="stPageLink"] a {
    background: #FFFFFF;
    border: 1.5px solid #F8BBD0;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    color: #C2185B !important;
    font-weight: 600;
    transition: all 0.2s ease;
}
[data-testid="stPageLink"] a:hover {
    background: #FDF2F8;
    border-color: #C2185B;
    text-decoration: none !important;
}
</style>
"""


def aplicar_estilo() -> None:
    """Inyecta el CSS de la app. Llamar después de st.set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)
