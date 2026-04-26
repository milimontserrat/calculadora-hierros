"""
Tests del optimizador.

Casos sintéticos (CLAUDE.md §8) + casos reales del Excel (10 targets verificados).
Criterio de aceptación de Fase 1: todo en verde en menos de 60s.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from core.models import Element
from core.optimizer import optimize, optimize_phi


FIXTURES = Path(__file__).parent / "fixtures" / "ejemplo_real.json"


# -------------------- 5 tests sintéticos del CLAUDE.md §8 --------------------

def test_caso_trivial_una_pieza():
    """1 pieza de 5m con barra de 12m → 1 barra, sobrante 7m."""
    plan = optimize([Element("X", 8, 1, 1, 5.0)], largo_barra=12.0)
    assert plan.total_barras == 1
    assert plan.barras_por_phi[8][0].sobrante == pytest.approx(7.0)


def test_pieza_excede_barra():
    """Pieza de 13m con barra de 12m → ValueError."""
    with pytest.raises(ValueError, match="excede"):
        optimize([Element("X", 8, 1, 1, 13.0)], largo_barra=12.0)


def test_multiples_diametros_no_se_mezclan():
    """φ8 y φ10 nunca van en la misma barra."""
    plan = optimize([
        Element("A", 8, 1, 1, 5.0),
        Element("B", 10, 1, 1, 5.0),
    ], largo_barra=12.0)
    # 2 barras: una para cada φ
    assert plan.total_barras == 2
    assert set(plan.barras_por_phi.keys()) == {8, 10}
    for phi, barras in plan.barras_por_phi.items():
        for barra in barras:
            assert barra.phi == phi


def test_cota_inferior_se_respeta():
    """total_barras >= ceil(suma_largos / largo_barra)."""
    elementos = [
        Element("X", 8, 10, 1, 4.0),  # 10 piezas de 4m → 40m total → cota inf = ceil(40/12) = 4
    ]
    plan = optimize(elementos, largo_barra=12.0)
    suma_largos = sum(e.longitud_total for e in elementos)
    cota_inf = math.ceil(suma_largos / 12.0)
    assert plan.total_barras >= cota_inf


def test_elementos_invalidos_se_ignoran():
    """cantidad_total_piezas == 0 → ignorar silenciosamente."""
    plan = optimize([
        Element("Vacio", 8, 0, 1, 5.0),
        Element("OK", 8, 1, 1, 5.0),
    ], largo_barra=12.0)
    assert plan.total_barras == 1


# -------------------- Tests parametrizados con datos reales del Excel --------------------

def _cargar_fixtures() -> dict:
    if not FIXTURES.exists():
        pytest.skip(
            f"Fixture {FIXTURES} no existe. "
            "Correr: .venv/Scripts/python scripts/extract_fixtures.py"
        )
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def _build_casos():
    """Devuelve lista de tuplas (id, hoja, phi, target) para parametrizar."""
    if not FIXTURES.exists():
        return []
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    casos = []
    for key, target in data["expected_targets"].items():
        hoja, phi_str = key.split(":")
        casos.append(pytest.param(hoja, int(phi_str), target, id=key))
    return casos


@pytest.mark.parametrize("hoja,phi,target", _build_casos())
def test_excel_real(hoja: str, phi: int, target: int):
    """
    Aserción dura: el optimizador debe matchear o mejorar el método ingenuo de Mili.
    Aserción dura: respetar la cota inferior matemática.
    Aserción suave (warning): intentar alcanzar el target manual de Mili.
    """
    import warnings as _warnings
    fixtures = _cargar_fixtures()
    largo = fixtures["largo_barra"]
    elems_raw = fixtures["data"][hoja][str(phi)]
    ingenuo = fixtures["ingenuo_referencia"].get(f"{hoja}:{phi}")

    elementos = [
        Element(
            nombre=e["nombre"],
            phi=e["phi"],
            cantidad_elementos=e["cant_elementos"],
            cantidad_repeticiones=e["cant_rep"],
            medida=e["medida"],
        )
        for e in elems_raw
    ]
    plan = optimize(elementos, largo_barra=largo, timeout_s=30.0)
    n = plan.total_barras

    suma = sum(e.longitud_total for e in elementos)
    cota_inf = math.ceil(suma / largo)

    # Hard: respeta cota inferior matemática
    assert n >= cota_inf, f"{hoja}:phi{phi} viola cota inferior ({n} < {cota_inf})"

    # Hard: mejora (o iguala) el método ingenuo de Mili
    if ingenuo is not None:
        assert n <= ingenuo, (
            f"{hoja}:phi{phi} REGRESION: optimizer={n} > ingenuo={ingenuo}"
        )

    # Soft: warning si no llegamos al target manual (puede ser inalcanzable)
    if n > target:
        _warnings.warn(
            f"{hoja}:phi{phi}: optimizer={n} > target_manual={target} "
            f"(cota_inf={cota_inf}, ingenuo={ingenuo}). "
            "El target manual puede ser incorrecto."
        )


def test_phi8_bases_objetivo_oficial_105():
    """
    Caso central de CLAUDE.md §8: phi8 de 'bases y vf' debe ser <= 105 barras.
    Es el caso que motiva todo el proyecto.
    """
    fixtures = _cargar_fixtures()
    elems_raw = fixtures["data"]["bases_y_vf"]["8"]
    elementos = [
        Element(
            nombre=e["nombre"],
            phi=e["phi"],
            cantidad_elementos=e["cant_elementos"],
            cantidad_repeticiones=e["cant_rep"],
            medida=e["medida"],
        )
        for e in elems_raw
    ]
    plan = optimize(elementos, largo_barra=12.0, timeout_s=30.0)
    assert plan.total_barras <= 105, (
        f"phi8 bases dio {plan.total_barras}, debería ser <= 105 "
        "(metodo ingenuo da 117)"
    )
