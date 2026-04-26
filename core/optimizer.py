"""
Optimizador 1D Cutting Stock para barras de hierro.

Estrategia:
  1. Validar (pieza > barra → ValueError).
  2. Early-exit si todo entra en una sola barra.
  3. Trabajar en milímetros enteros para evitar imprecisión float.
  4. Agrupar piezas iguales (clave para que el caso de 1368 piezas sea viable).
  5. Correr CP-SAT con FFD como hint inicial. Si timeout, devolver FFD.
"""

from __future__ import annotations

import logging
import math
import time
from collections import Counter, defaultdict
from typing import Iterable

from ortools.sat.python import cp_model

from core.models import BarUsage, CutPlan, Element

log = logging.getLogger(__name__)

# Conversión metros → milímetros enteros (3 decimales son más que suficientes para hierro)
MM = 1000


def _to_mm(x: float) -> int:
    return int(round(x * MM))


def _from_mm(x: int) -> float:
    return x / MM


# -------------------- FFD (First Fit Decreasing) --------------------

def ffd(piezas_mm: list[int], largo_mm: int) -> list[list[int]]:
    """First Fit Decreasing. Devuelve lista de barras, cada barra es lista de piezas."""
    barras: list[list[int]] = []
    sobrantes: list[int] = []  # capacidad restante de cada barra
    for p in sorted(piezas_mm, reverse=True):
        colocada = False
        for j, sob in enumerate(sobrantes):
            if p <= sob:
                barras[j].append(p)
                sobrantes[j] -= p
                colocada = True
                break
        if not colocada:
            barras.append([p])
            sobrantes.append(largo_mm - p)
    return barras


# -------------------- CP-SAT agrupado --------------------

def cp_sat_optimo(
    piezas_mm: list[int],
    largo_mm: int,
    cota_inferior: int,
    cota_superior: int,
    timeout_s: float,
) -> list[list[int]] | None:
    """
    Modelo CP-SAT con variables agrupadas por medida (no pieza-por-pieza).

    Variables:
      x[m][j] ∈ ℤ≥0  cuántas piezas de medida m van a la barra j
      y[j]    ∈ {0,1} barra j en uso

    Restricciones:
      Σ_j x[m][j] = cantidad[m]                 ∀ m
      Σ_m m·x[m][j] ≤ L · y[j]                  ∀ j
      y[j] ≥ y[j+1]                             (simetría)

    Objetivo: min Σ y[j].

    Devuelve lista de barras (cada barra como lista de piezas en mm) o None si no encontró solución.
    """
    counts = Counter(piezas_mm)  # {medida_mm: cantidad}
    medidas = sorted(counts.keys(), reverse=True)
    J = cota_superior  # cantidad máxima de barras a considerar

    model = cp_model.CpModel()

    x = {}
    for m in medidas:
        for j in range(J):
            x[(m, j)] = model.NewIntVar(0, counts[m], f"x_{m}_{j}")
    y = [model.NewBoolVar(f"y_{j}") for j in range(J)]

    # Cada medida usa exactamente cantidad[m] piezas
    for m in medidas:
        model.Add(sum(x[(m, j)] for j in range(J)) == counts[m])

    # Capacidad por barra
    for j in range(J):
        model.Add(sum(m * x[(m, j)] for m in medidas) <= largo_mm * y[j])

    # Simetría: barras se usan en orden
    for j in range(J - 1):
        model.Add(y[j] >= y[j + 1])

    # Cota inferior dura
    model.Add(sum(y) >= cota_inferior)

    model.Minimize(sum(y))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_s
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    barras: list[list[int]] = []
    for j in range(J):
        if solver.Value(y[j]) == 0:
            continue
        contenido: list[int] = []
        for m in medidas:
            n = solver.Value(x[(m, j)])
            contenido.extend([m] * n)
        if contenido:
            barras.append(contenido)
    return barras


# -------------------- API pública --------------------

def optimize_phi(
    piezas_m: list[float],
    nombres: list[str],
    largo_barra: float,
    phi: int,
    timeout_s: float = 30.0,
) -> list[BarUsage]:
    """
    Optimiza un único φ. piezas_m y nombres son listas paralelas (mismo length).
    Devuelve lista de BarUsage.
    """
    if len(piezas_m) != len(nombres):
        raise ValueError("piezas_m y nombres deben tener mismo largo")
    if not piezas_m:
        return []

    largo_mm = _to_mm(largo_barra)

    # Validación
    for nombre, p in zip(nombres, piezas_m):
        if _to_mm(p) > largo_mm:
            raise ValueError(
                f"Pieza '{nombre}' de {p}m (φ{phi}) excede el largo de barra de {largo_barra}m"
            )

    piezas_mm = [_to_mm(p) for p in piezas_m]
    nombres_por_medida: dict[int, list[str]] = defaultdict(list)
    for nombre, mm in zip(nombres, piezas_mm):
        nombres_por_medida[mm].append(nombre)

    # Early-exit: todo en una barra
    if sum(piezas_mm) <= largo_mm:
        sobrante = largo_mm - sum(piezas_mm)
        return [BarUsage(
            phi=phi,
            piezas=[(nombres[i], piezas_m[i]) for i in range(len(piezas_m))],
            sobrante=_from_mm(sobrante),
        )]

    cota_inf = math.ceil(sum(piezas_mm) / largo_mm)

    # FFD primero (rápido, da cota superior)
    t0 = time.perf_counter()
    barras_ffd = ffd(piezas_mm, largo_mm)
    cota_sup = len(barras_ffd)
    t_ffd = time.perf_counter() - t0
    log.info(f"φ{phi}: FFD={cota_sup} barras (cota_inf={cota_inf}) en {t_ffd*1000:.1f}ms")

    # Si FFD ya iguala la cota inferior, óptimo encontrado
    if cota_sup == cota_inf:
        log.info(f"φ{phi}: FFD óptimo (= cota inferior)")
        return _barras_a_usage(barras_ffd, largo_mm, phi, nombres_por_medida)

    # CP-SAT con FFD como cota superior
    t0 = time.perf_counter()
    barras_cp = cp_sat_optimo(
        piezas_mm=piezas_mm,
        largo_mm=largo_mm,
        cota_inferior=cota_inf,
        cota_superior=cota_sup,
        timeout_s=timeout_s,
    )
    t_cp = time.perf_counter() - t0

    if barras_cp is not None and len(barras_cp) <= cota_sup:
        log.info(f"φ{phi}: CP-SAT={len(barras_cp)} barras en {t_cp*1000:.1f}ms")
        return _barras_a_usage(barras_cp, largo_mm, phi, nombres_por_medida)

    log.warning(f"φ{phi}: CP-SAT sin mejora, usando FFD")
    return _barras_a_usage(barras_ffd, largo_mm, phi, nombres_por_medida)


def _barras_a_usage(
    barras: list[list[int]],
    largo_mm: int,
    phi: int,
    nombres_por_medida: dict[int, list[str]],
) -> list[BarUsage]:
    """
    Convierte la lista de barras (en mm) a BarUsage, asignando nombres de elementos
    a cada pieza desde el pool nombres_por_medida (que se va consumiendo).
    """
    pool = {m: list(ns) for m, ns in nombres_por_medida.items()}
    out: list[BarUsage] = []
    for contenido in barras:
        piezas: list[tuple[str, float]] = []
        for mm in contenido:
            nombre = pool[mm].pop() if pool[mm] else "?"
            piezas.append((nombre, _from_mm(mm)))
        sobrante = largo_mm - sum(contenido)
        out.append(BarUsage(phi=phi, piezas=piezas, sobrante=_from_mm(sobrante)))
    return out


def metodo_ingenuo(elementos: Iterable[Element], largo_barra: float = 12.0) -> dict[int, int]:
    """
    Replica el cálculo manual que hace Mili en Excel:
      cant_x_barra = floor(largo_barra / medida)
      barras_por_elemento = ceil(cantidad_total_piezas / cant_x_barra)
      total_phi = suma sobre todos los elementos del mismo phi

    Devuelve dict[phi -> total_barras_ingenuo].
    """
    totales: dict[int, int] = defaultdict(int)
    for e in elementos:
        if not e.es_valido():
            continue
        if e.medida > largo_barra:
            continue  # se valida en optimize_phi
        cant_x_barra = int(largo_barra // e.medida)
        if cant_x_barra == 0:
            continue
        totales[e.phi] += math.ceil(e.cantidad_total_piezas / cant_x_barra)
    return dict(totales)


def optimize(
    elementos: Iterable[Element],
    largo_barra: float = 12.0,
    timeout_s: float = 30.0,
) -> CutPlan:
    """
    Optimiza un proyecto entero. Resuelve por separado para cada φ y agrega los resultados.
    """
    elementos = [e for e in elementos if e.es_valido()]

    # Agrupar por φ
    por_phi: dict[int, tuple[list[float], list[str]]] = defaultdict(lambda: ([], []))
    for e in elementos:
        for _ in range(e.cantidad_total_piezas):
            por_phi[e.phi][0].append(e.medida)
            por_phi[e.phi][1].append(e.nombre)

    barras_por_phi: dict[int, list[BarUsage]] = {}
    metodos: list[str] = []

    for phi in sorted(por_phi.keys()):
        piezas, nombres = por_phi[phi]
        usage_list = optimize_phi(
            piezas_m=piezas,
            nombres=nombres,
            largo_barra=largo_barra,
            phi=phi,
            timeout_s=timeout_s,
        )
        barras_por_phi[phi] = usage_list

    total_barras = sum(len(v) for v in barras_por_phi.values())
    desperdicio = sum(b.sobrante for v in barras_por_phi.values() for b in v)

    return CutPlan(
        barras_por_phi=barras_por_phi,
        total_barras=total_barras,
        desperdicio_total_m=desperdicio,
        metodo_usado="OR-Tools CP-SAT + FFD",
    )
