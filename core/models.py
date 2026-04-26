from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Element:
    nombre: str
    phi: int
    cantidad_elementos: int
    cantidad_repeticiones: int
    medida: float

    @property
    def cantidad_total_piezas(self) -> int:
        return self.cantidad_elementos * self.cantidad_repeticiones

    @property
    def longitud_total(self) -> float:
        return self.cantidad_total_piezas * self.medida

    def es_valido(self) -> bool:
        return self.cantidad_total_piezas > 0 and self.medida > 0


@dataclass
class Project:
    id: str | None
    nombre: str
    largo_barra: float
    elementos: list[Element]
    created_at: datetime
    updated_at: datetime


@dataclass
class BarUsage:
    """Cómo se usa una barra individual: qué piezas se cortan de ella."""

    phi: int
    piezas: list[tuple[str, float]]
    sobrante: float


@dataclass
class CutPlan:
    """Resultado del optimizador para un proyecto entero."""

    barras_por_phi: dict[int, list[BarUsage]] = field(default_factory=dict)
    total_barras: int = 0
    desperdicio_total_m: float = 0.0
    metodo_usado: str = ""
