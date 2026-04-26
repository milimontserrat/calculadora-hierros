"""
Calculadora de Hierros — entrypoint.

Login simple. Si está autenticado, muestra el "home" con un CTA hacia Nuevo Proyecto.
Si no, muestra el form de login. Las pages bajo pages/ están protegidas con un guard.
"""
from __future__ import annotations

import streamlit as st

from core.styles import aplicar_estilo

st.set_page_config(
    page_title="Calculadora de Hierros",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="auto",
)
aplicar_estilo()

USUARIO_VALIDO = "mili"


def _password_correcto(intento: str) -> bool:
    try:
        esperado = st.secrets["auth"]["password"]
    except (KeyError, FileNotFoundError):
        st.error(
            "Falta configurar `.streamlit/secrets.toml` con `[auth] password=...`. "
            "Copiá `secrets.toml.example` y ajustá el valor."
        )
        return False
    return intento == esperado


def render_login() -> None:
    st.title("¡Hola!")
    st.caption("Bienvenida a tu calculadora de hierros. Ingresá para empezar.")
    st.write("")

    with st.form("login", clear_on_submit=False):
        usuario = st.text_input(
            "Usuario",
            value="",
            placeholder="Ingresá tu usuario",
            autocomplete="username",
        )
        contrasena = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Ingresá tu contraseña",
            autocomplete="current-password",
        )
        submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")

    if submit:
        if usuario.strip().lower() == USUARIO_VALIDO and _password_correcto(contrasena):
            st.session_state["authenticated"] = True
            st.session_state["usuario"] = usuario.strip().lower()
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos. Probá de nuevo.")


def render_home() -> None:
    usuario = st.session_state.get("usuario", "")
    st.title(f"¡Hola, {usuario}!")
    st.caption("Calculadora de Hierros — optimizador de compra de armadura")
    st.write("")

    st.markdown(
        "Empezá un nuevo proyecto o abrí uno guardado desde el menú de la izquierda."
    )

    st.divider()
    col_a, col_b, _ = st.columns([1, 1, 2])
    with col_a:
        st.page_link("pages/1_Nuevo_Proyecto.py", label="Nuevo proyecto")
    with col_b:
        st.page_link("pages/2_Mis_Proyectos.py", label="Mis proyectos")


def main() -> None:
    if not st.session_state.get("authenticated"):
        render_login()
        return
    from core.auth import render_sidebar
    render_sidebar()
    render_home()


if __name__ == "__main__":
    main()
else:
    main()
