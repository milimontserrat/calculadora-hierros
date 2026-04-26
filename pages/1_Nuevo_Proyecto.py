"""
Página: Nuevo Proyecto.

Tabla editable con elementos de la planilla. La usuaria carga, presiona Calcular,
y la app le muestra el plan de corte optimizado + cuánto se ahorra vs. el método ingenuo.

Sin persistencia (Fase 4) ni import de Excel (Fase 3).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.auth import require_auth, render_sidebar
from core import db
from core.excel_export import generar_excel
from core.excel_import import parse_excel
from core.models import Element
from core.optimizer import metodo_ingenuo, optimize
from core.styles import aplicar_estilo

st.set_page_config(
    page_title="Nuevo Proyecto — Calculadora de Hierros",
    layout="wide",
    initial_sidebar_state="auto",
)
aplicar_estilo()

require_auth()
render_sidebar()

# -------------------- Gate: pedir nombre del proyecto antes de empezar --------------------

if not st.session_state.get("nombre_proyecto"):
    st.title("Nuevo proyecto")
    st.caption("Antes de empezar, ¿cómo se llama el proyecto?")
    st.write("")

    with st.form("form_nombre_proyecto", clear_on_submit=False):
        nombre = st.text_input(
            "Nombre del proyecto",
            value="",
            placeholder="Ej: Edificio Salguero 1234",
            label_visibility="collapsed",
        )
        submit_nombre = st.form_submit_button("Empezar", type="primary", use_container_width=False)

    if submit_nombre:
        if nombre.strip():
            st.session_state["nombre_proyecto"] = nombre.strip()
            st.rerun()
        else:
            st.error("Necesito un nombre para empezar.")
    st.stop()

# -------------------- Encabezado del proyecto activo --------------------

nombre_proyecto = st.session_state["nombre_proyecto"]

col_titulo, col_renombrar = st.columns([5, 1])
with col_titulo:
    st.title(nombre_proyecto)
    st.caption("Calculadora de Hierros · proyecto en edición")
with col_renombrar:
    st.write("")  # alineación vertical
    if st.button("Cambiar nombre", key="renombrar_proyecto", use_container_width=True):
        st.session_state["nombre_proyecto"] = ""
        st.rerun()

st.divider()

# -------------------- Configuración --------------------

if "largo_barra_state" not in st.session_state:
    st.session_state["largo_barra_state"] = 12.0

col_a, _ = st.columns([1, 3])
with col_a:
    largo_barra = st.number_input(
        "Largo de barra (m)",
        min_value=1.0, max_value=24.0, step=0.5,
        key="largo_barra_state",
    )

# -------------------- Importar desde Excel --------------------

with st.expander("Importar desde Excel", expanded=False):
    st.caption("Subí un archivo .xlsx con tu planilla. La app detecta las columnas automáticamente.")
    archivo = st.file_uploader(
        "Archivo .xlsx",
        type=["xlsx"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key="uploader_xlsx",
    )

    if archivo is not None:
        try:
            elementos_importados = parse_excel(archivo.getvalue())
        except ValueError as ex:
            st.error(str(ex))
            elementos_importados = []

        if elementos_importados:
            st.success(f"Detecté {len(elementos_importados)} elementos.")
            preview_df = pd.DataFrame([
                {
                    "Elemento": e.nombre,
                    "phi": e.phi,
                    "Cant. elementos": e.cantidad_elementos,
                    "Repeticiones": e.cantidad_repeticiones,
                    "Medida (m)": e.medida,
                }
                for e in elementos_importados
            ])
            st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)
            if len(elementos_importados) > 10:
                st.caption(f"Mostrando 10 de {len(elementos_importados)} filas.")

            col_imp1, col_imp2 = st.columns([1, 4])
            with col_imp1:
                if st.button("Cargar tabla", type="primary", key="confirmar_import"):
                    st.session_state["proyecto_df"] = preview_df.copy()
                    st.session_state["df_version"] = st.session_state.get("df_version", 0) + 1
                    st.rerun()

# -------------------- Tabla editable --------------------

st.subheader("Planilla de armaduras")
st.caption("Cargá una fila por elemento. Podés agregar/eliminar filas con los íconos de la tabla.")

_DF_DEFAULT = pd.DataFrame(
    [{"Elemento": "", "phi": 8, "Cant. elementos": 1, "Repeticiones": 1, "Medida (m)": 0.0}],
)

# DataFrame inicial: viene de la importación si la hubo, si no, default
_df_inicial = st.session_state.get("proyecto_df", _DF_DEFAULT)
_df_version = st.session_state.get("df_version", 0)

df_editado = st.data_editor(
    _df_inicial,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=False,
    column_config={
        "Elemento": st.column_config.TextColumn(
            "Elemento",
            help="Nombre del elemento estructural (PLATEA, BASE 1, VF, tronco C5, etc.)",
            required=False,
        ),
        "phi": st.column_config.NumberColumn(
            "φ (mm)",
            help="Diámetro de la barra en milímetros",
            min_value=1, max_value=40, step=1, default=8,
        ),
        "Cant. elementos": st.column_config.NumberColumn(
            "Cant. elementos",
            help="Cantidad de piezas en este elemento",
            min_value=0, step=1, default=1,
        ),
        "Repeticiones": st.column_config.NumberColumn(
            "Repeticiones",
            help="Cuántas veces se repite el elemento en la obra",
            min_value=1, step=1, default=1,
        ),
        "Medida (m)": st.column_config.NumberColumn(
            "Medida (m)",
            help="Largo de cada pieza, en metros",
            min_value=0.0, step=0.01, format="%.2f",
        ),
    },
    key=f"data_editor_elementos_v{_df_version}",
)


# -------------------- Helper de validación --------------------

def _extraer_elementos(df, largo: float) -> tuple[list[Element], list[str]]:
    elementos_extr: list[Element] = []
    errores_extr: list[str] = []
    for n, (_, row) in enumerate(df.iterrows(), start=1):
        nombre = str(row.get("Elemento") or "").strip()
        try:
            phi = int(row.get("phi") or 0)
            cant = int(row.get("Cant. elementos") or 0)
            rep = int(row.get("Repeticiones") or 1)
            medida = float(row.get("Medida (m)") or 0.0)
        except (ValueError, TypeError):
            errores_extr.append(f"Fila {n}: valores numéricos inválidos.")
            continue
        if not nombre and cant == 0 and medida == 0.0:
            continue
        if not nombre:
            errores_extr.append(f"Fila {n}: falta nombre del elemento.")
            continue
        if phi <= 0:
            errores_extr.append(f"Fila {n}: φ debe ser mayor a 0.")
            continue
        if cant <= 0:
            errores_extr.append(f"Fila {n}: cantidad de elementos debe ser ≥ 1.")
            continue
        if medida <= 0:
            errores_extr.append(f"Fila {n}: medida debe ser > 0.")
            continue
        if medida > largo:
            errores_extr.append(
                f"Fila {n}: la pieza de {medida}m supera el largo de barra ({largo}m)."
            )
            continue
        elementos_extr.append(Element(
            nombre=nombre,
            phi=phi,
            cantidad_elementos=cant,
            cantidad_repeticiones=rep,
            medida=medida,
        ))
    return elementos_extr, errores_extr


# -------------------- Acciones: Calcular + Guardar --------------------

col_calc, col_guardar, _ = st.columns([1, 1, 4])
with col_calc:
    calcular = st.button("Calcular", type="primary", use_container_width=True)
with col_guardar:
    guardar = st.button("Guardar proyecto", use_container_width=True)

if guardar:
    elementos_g, errores_g = _extraer_elementos(df_editado, largo_barra)
    if errores_g:
        for e in errores_g:
            st.error(e)
    elif not elementos_g:
        st.warning("Cargá al menos un elemento válido antes de guardar.")
    else:
        try:
            project_id = db.guardar_proyecto(
                project_id=st.session_state.get("project_id"),
                nombre=nombre_proyecto,
                largo_barra=largo_barra,
                elementos=elementos_g,
            )
            st.session_state["project_id"] = project_id
            st.success(f"Proyecto «{nombre_proyecto}» guardado.")
        except Exception as ex:
            st.error(f"No pude guardar: {ex}")

if calcular:
    elementos, errores = _extraer_elementos(df_editado, largo_barra)

    if errores:
        for e in errores:
            st.error(e)
    elif not elementos:
        st.warning("Cargá al menos un elemento válido antes de calcular.")
    else:
        with st.spinner("Optimizando…"):
            try:
                plan = optimize(elementos, largo_barra=largo_barra, timeout_s=30.0)
                ingenuo_por_phi = metodo_ingenuo(elementos, largo_barra=largo_barra)
            except ValueError as ex:
                st.error(str(ex))
                st.stop()
        st.session_state["ultimo_plan"] = plan
        st.session_state["ultimo_ingenuo"] = ingenuo_por_phi
        st.session_state["ultimo_largo"] = largo_barra
        st.session_state["ultimo_nombre"] = nombre_proyecto
        st.session_state["ultimo_elementos"] = elementos


# -------------------- Render resultado --------------------

plan = st.session_state.get("ultimo_plan")
ingenuo = st.session_state.get("ultimo_ingenuo", {})

if plan is not None:
    st.divider()
    st.header("Resultado")

    # Resumen por phi
    st.subheader("Resumen por diámetro")
    rows = []
    total_opt = 0
    total_ing = 0
    for phi, barras in sorted(plan.barras_por_phi.items()):
        n_opt = len(barras)
        n_ing = ingenuo.get(phi, n_opt)
        ahorro = n_ing - n_opt
        rows.append({
            "φ (mm)": phi,
            "Método ingenuo": n_ing,
            "Optimizado": n_opt,
            "Ahorro (barras)": ahorro,
            "Ahorro (m)": round(ahorro * st.session_state["ultimo_largo"], 2),
        })
        total_opt += n_opt
        total_ing += n_ing
    df_resumen = pd.DataFrame(rows)
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total barras optimizadas", total_opt)
    c2.metric("Total ingenuo", total_ing)
    c3.metric("Ahorro vs. ingenuo", f"{total_ing - total_opt} barras",
              delta=f"{round((total_ing - total_opt) * st.session_state['ultimo_largo'], 1)} m")

    st.caption(f"Método: {plan.metodo_usado} · Desperdicio total: {round(plan.desperdicio_total_m, 2)} m")

    # Descarga del Excel
    elementos_guardados = st.session_state.get("ultimo_elementos", [])
    if elementos_guardados:
        nombre_archivo = (
            (st.session_state.get("ultimo_nombre") or "proyecto")
            .strip()
            .replace(" ", "_")
            .replace("/", "-")
            or "proyecto"
        )
        bytes_xlsx = generar_excel(
            nombre_proyecto=st.session_state.get("ultimo_nombre", "Proyecto"),
            elementos=elementos_guardados,
            plan=plan,
            largo_barra=st.session_state["ultimo_largo"],
            ingenuo_por_phi=ingenuo,
        )
        st.download_button(
            label="Descargar Excel",
            data=bytes_xlsx,
            file_name=f"{nombre_archivo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

    # Plan de corte
    st.subheader("Plan de corte")
    st.caption("Por cada barra física, qué piezas hay que cortar y cuánto sobra.")

    for phi in sorted(plan.barras_por_phi.keys()):
        barras = plan.barras_por_phi[phi]
        with st.expander(f"φ {phi} mm — {len(barras)} barras", expanded=False):
            corte_rows = []
            for idx, b in enumerate(barras, start=1):
                # Agrupar piezas iguales para mostrar como "3×3.20 + 1×2.40"
                from collections import Counter
                medidas = [round(m, 2) for _, m in b.piezas]
                cnt = Counter(medidas)
                texto = " + ".join(
                    f"{n}×{m:.2f}" for m, n in sorted(cnt.items(), reverse=True)
                )
                corte_rows.append({
                    "Barra #": idx,
                    "Piezas": texto,
                    "Sobrante (m)": round(b.sobrante, 2),
                })
            st.dataframe(pd.DataFrame(corte_rows), use_container_width=True, hide_index=True)
