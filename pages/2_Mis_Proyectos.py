"""
Página: Mis proyectos.

Listado de proyectos guardados en Supabase. Acciones por proyecto:
  - Abrir: carga el proyecto en session_state y navega a Nuevo Proyecto.
  - Duplicar: crea una copia con sufijo "(copia)".
  - Eliminar: borra el proyecto y sus elementos (cascade).
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core import db
from core.auth import render_sidebar, require_auth
from core.styles import aplicar_estilo

st.set_page_config(
    page_title="Mis Proyectos — Calculadora de Hierros",
    layout="wide",
    initial_sidebar_state="auto",
)
aplicar_estilo()

require_auth()
render_sidebar()

st.title("Mis proyectos")
st.caption("Tus proyectos guardados. Abrilos para editar o recalcular.")

# -------------------- Verificar conexión --------------------

if not db.disponible():
    st.error(
        "No pude conectarme a Supabase. "
        "Verificá que `.streamlit/secrets.toml` tenga `[supabase] url` y `anon_key` configurados."
    )
    st.stop()

# -------------------- Botón nuevo proyecto --------------------

col_nuevo, _ = st.columns([1, 5])
with col_nuevo:
    if st.button("+ Nuevo proyecto", type="primary", use_container_width=True):
        # Limpiar estado para empezar de cero
        for k in ("project_id", "nombre_proyecto", "proyecto_df",
                  "ultimo_plan", "ultimo_elementos", "ultimo_ingenuo",
                  "ultimo_largo", "ultimo_nombre"):
            st.session_state.pop(k, None)
        st.session_state["df_version"] = st.session_state.get("df_version", 0) + 1
        st.switch_page("pages/1_Nuevo_Proyecto.py")

st.divider()

# -------------------- Listado --------------------

try:
    proyectos = db.listar_proyectos()
except Exception as ex:
    st.error(f"No pude leer los proyectos: {ex}")
    st.stop()

if not proyectos:
    st.info("Todavía no guardaste ningún proyecto. Creá uno desde «Nuevo proyecto».")
    st.stop()


def _fmt_fecha(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso


for p in proyectos:
    with st.container(border=True):
        col_info, col_acciones = st.columns([3, 2])
        with col_info:
            st.markdown(f"### {p['nombre']}")
            n_elem = p.get("total_elementos", 0)
            st.caption(
                f"Largo de barra: {p['largo_barra']} m · "
                f"{n_elem} elemento{'s' if n_elem != 1 else ''} · "
                f"actualizado {_fmt_fecha(p['updated_at'])}"
            )

        with col_acciones:
            c1, c2, c3 = st.columns(3)
            if c1.button("Abrir", key=f"abrir_{p['id']}", use_container_width=True):
                try:
                    proj, elementos = db.obtener_proyecto(p["id"])
                except Exception as ex:
                    st.error(f"No pude abrir el proyecto: {ex}")
                    st.stop()

                # Cargar en session_state para que Nuevo_Proyecto lo tome
                import pandas as pd
                df = pd.DataFrame([
                    {
                        "Elemento": e.nombre,
                        "phi": e.phi,
                        "Cant. elementos": e.cantidad_elementos,
                        "Repeticiones": e.cantidad_repeticiones,
                        "Medida (m)": e.medida,
                    }
                    for e in elementos
                ])
                st.session_state["project_id"] = p["id"]
                st.session_state["nombre_proyecto"] = proj["nombre"]
                st.session_state["proyecto_df"] = df
                st.session_state["largo_barra_state"] = float(proj["largo_barra"])
                st.session_state["df_version"] = st.session_state.get("df_version", 0) + 1
                # Limpiar resultados anteriores
                for k in ("ultimo_plan", "ultimo_elementos", "ultimo_ingenuo",
                          "ultimo_largo", "ultimo_nombre"):
                    st.session_state.pop(k, None)
                st.switch_page("pages/1_Nuevo_Proyecto.py")

            if c2.button("Duplicar", key=f"dup_{p['id']}", use_container_width=True):
                try:
                    db.duplicar_proyecto(p["id"])
                    st.success(f"Duplicado: «{p['nombre']} (copia)»")
                    st.rerun()
                except Exception as ex:
                    st.error(f"No pude duplicar: {ex}")

            # Eliminar con confirmación de dos clicks via session_state
            confirm_key = f"confirm_del_{p['id']}"
            if st.session_state.get(confirm_key):
                if c3.button("¿Confirmar?", key=f"del2_{p['id']}", type="primary", use_container_width=True):
                    try:
                        db.eliminar_proyecto(p["id"])
                        st.session_state.pop(confirm_key, None)
                        st.success(f"Proyecto «{p['nombre']}» eliminado.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"No pude eliminar: {ex}")
            else:
                if c3.button("Eliminar", key=f"del_{p['id']}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
