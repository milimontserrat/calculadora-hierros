"""Guard de autenticación reutilizable para las pages."""
from __future__ import annotations

import streamlit as st


def require_auth() -> None:
    """Si el usuario no está autenticado, muestra mensaje y corta la ejecución de la página."""
    if not st.session_state.get("authenticated"):
        st.warning("No estás autenticado. Volvé al inicio para ingresar.")
        st.page_link("app.py", label="Ir al login")
        st.stop()


def render_sidebar() -> None:
    """Sidebar común a todas las páginas autenticadas. Navegación custom + logout abajo."""
    with st.sidebar:
        st.markdown(f"**Sesión:** {st.session_state.get('usuario', '')}")
        st.divider()

        st.page_link("app.py", label="Inicio")
        st.page_link("pages/2_Mis_Proyectos.py", label="Mis proyectos")
        nombre_proyecto = st.session_state.get("nombre_proyecto") or "Nuevo proyecto"
        st.page_link("pages/1_Nuevo_Proyecto.py", label=nombre_proyecto)

        # Spacer visual: empuja el botón de logout hacia abajo del sidebar
        st.markdown(
            '<div style="height: 55vh;"></div>',
            unsafe_allow_html=True,
        )
        if st.button("Cerrar sesión", use_container_width=True, key="logout_sidebar"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
