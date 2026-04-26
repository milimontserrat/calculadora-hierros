"""
Cliente Supabase y CRUD de proyectos.

Tablas:
  - projects(id, nombre, largo_barra, created_at, updated_at)
  - elements(id, project_id, nombre, phi, cantidad_elementos, cantidad_repeticiones, medida, orden)

El schema está en db/schema.sql; correrlo una sola vez en Supabase SQL Editor.
Credenciales en .streamlit/secrets.toml bajo [supabase] url= ..., anon_key= ...
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import streamlit as st

from core.models import Element

if TYPE_CHECKING:
    from supabase import Client


# -------------------- Cliente --------------------

@st.cache_resource(show_spinner=False)
def _get_client() -> "Client":
    """Cliente Supabase cacheado a nivel de proceso."""
    from supabase import create_client

    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
    except (KeyError, FileNotFoundError) as e:
        raise RuntimeError(
            "Faltan credenciales de Supabase. Configurá .streamlit/secrets.toml con "
            "[supabase] url=\"https://...\" y anon_key=\"...\"."
        ) from e

    if not url or not key:
        raise RuntimeError(
            "Las credenciales de Supabase están vacías en .streamlit/secrets.toml."
        )

    return create_client(url, key)


def disponible() -> bool:
    """True si hay credenciales configuradas y el cliente se puede inicializar."""
    try:
        _get_client()
        return True
    except Exception:
        return False


# -------------------- CRUD --------------------

def listar_proyectos() -> list[dict]:
    """
    Devuelve lista de proyectos ordenados por updated_at desc.
    Cada item: {id, nombre, largo_barra, created_at, updated_at, total_elementos}
    """
    client = _get_client()
    res = client.table("projects").select("*").order("updated_at", desc=True).execute()
    proyectos = res.data or []

    # Conteo de elementos por proyecto (1 query agregada)
    if proyectos:
        ids = [p["id"] for p in proyectos]
        elems = client.table("elements").select("project_id").in_("project_id", ids).execute()
        conteo: dict[str, int] = {}
        for e in (elems.data or []):
            conteo[e["project_id"]] = conteo.get(e["project_id"], 0) + 1
        for p in proyectos:
            p["total_elementos"] = conteo.get(p["id"], 0)
    return proyectos


def obtener_proyecto(project_id: str) -> tuple[dict, list[Element]]:
    """Devuelve (project_dict, lista_elementos) ordenados por orden."""
    client = _get_client()
    proj = (
        client.table("projects")
        .select("*")
        .eq("id", project_id)
        .single()
        .execute()
    )
    elems_res = (
        client.table("elements")
        .select("*")
        .eq("project_id", project_id)
        .order("orden")
        .execute()
    )
    elementos = [
        Element(
            nombre=e["nombre"],
            phi=int(e["phi"]),
            cantidad_elementos=int(e["cantidad_elementos"]),
            cantidad_repeticiones=int(e["cantidad_repeticiones"]),
            medida=float(e["medida"]),
        )
        for e in (elems_res.data or [])
    ]
    return proj.data, elementos


def guardar_proyecto(
    project_id: str | None,
    nombre: str,
    largo_barra: float,
    elementos: list[Element],
) -> str:
    """
    Crea o actualiza un proyecto. Devuelve el project_id.
    En update, reemplaza por completo la lista de elementos.
    """
    client = _get_client()

    if project_id:
        client.table("projects").update({
            "nombre": nombre,
            "largo_barra": largo_barra,
        }).eq("id", project_id).execute()
        # Reemplazar elementos
        client.table("elements").delete().eq("project_id", project_id).execute()
    else:
        ahora = datetime.now(timezone.utc).isoformat()
        res = client.table("projects").insert({
            "nombre": nombre,
            "largo_barra": largo_barra,
            "created_at": ahora,
            "updated_at": ahora,
        }).execute()
        project_id = res.data[0]["id"]

    if elementos:
        rows = [
            {
                "project_id": project_id,
                "nombre": e.nombre,
                "phi": e.phi,
                "cantidad_elementos": e.cantidad_elementos,
                "cantidad_repeticiones": e.cantidad_repeticiones,
                "medida": e.medida,
                "orden": i,
            }
            for i, e in enumerate(elementos)
        ]
        # Insert en chunks por las dudas (Supabase tiene límite por request)
        CHUNK = 500
        for i in range(0, len(rows), CHUNK):
            client.table("elements").insert(rows[i:i + CHUNK]).execute()

    return project_id


def eliminar_proyecto(project_id: str) -> None:
    """Elimina un proyecto (los elementos caen por cascade)."""
    client = _get_client()
    client.table("projects").delete().eq("id", project_id).execute()


def duplicar_proyecto(project_id: str) -> str:
    """Duplica un proyecto con nombre '<nombre> (copia)'. Devuelve el nuevo id."""
    proj, elementos = obtener_proyecto(project_id)
    nuevo_nombre = f"{proj['nombre']} (copia)"
    return guardar_proyecto(
        project_id=None,
        nombre=nuevo_nombre,
        largo_barra=float(proj["largo_barra"]),
        elementos=elementos,
    )
