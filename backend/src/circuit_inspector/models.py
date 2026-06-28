"""Modelo de dominio do Circuit Inspector.

Tipos imutaveis e fortemente tipados que representam o circuito em cada estagio
do pipeline:

- `Point`         : coordenada em pixels.
- `Hole`          : furo logico da protoboard (coluna/linha ou trilha).
- `Terminal`      : extremidade de um componente (pixel + furo mapeado).
- `Component`     : componente detectado com seus terminais.
- `Placement`     : conjunto de componentes de uma imagem.
- `ComparisonResult` e auxiliares: resultado da comparacao gabarito x aluno.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class ComponentKind(str, Enum):
    """Tipos de componente reconhecidos pelo sistema."""

    WIRE = "wire"
    LED = "led"
    LDR = "ldr"
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    POTENTIOMETER = "potentiometer"
    BUTTON = "button"


@dataclass(frozen=True)
class Point:
    """Coordenada em pixels (origem no canto superior esquerdo)."""

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_int_tuple(self) -> tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))


@dataclass(frozen=True, order=True)
class Hole:
    """Furo logico da protoboard.

    Um furo pertence a area central (definido por `column` + `row` em 'a'..'j')
    ou a uma trilha de alimentacao (definido por `column` + `rail` em '+'/'-').
    Exatamente um entre `row` e `rail` deve estar preenchido.
    """

    column: int
    row: str | None = None
    rail: str | None = None

    def __post_init__(self) -> None:
        has_row = self.row is not None
        has_rail = self.rail is not None
        if has_row == has_rail:
            raise ValueError(
                "Hole exige exatamente um entre 'row' e 'rail' "
                f"(row={self.row!r}, rail={self.rail!r})."
            )

    @property
    def is_rail(self) -> bool:
        return self.rail is not None

    @property
    def label(self) -> str:
        marker = self.rail if self.is_rail else self.row
        return f"{marker}{self.column}"


@dataclass(frozen=True)
class Terminal:
    """Extremidade de um componente.

    `pixel` e sempre conhecido (vem da deteccao). `hole` so e preenchido apos o
    mapeamento geometrico; antes disso permanece `None`.
    """

    pixel: Point
    hole: Hole | None = None

    @property
    def is_mapped(self) -> bool:
        return self.hole is not None

    def with_hole(self, hole: Hole) -> "Terminal":
        """Retorna uma copia com o furo mapeado preenchido."""
        return Terminal(pixel=self.pixel, hole=hole)


@dataclass(frozen=True)
class Component:
    """Componente detectado com seus terminais.

    `label` e um identificador legivel e estavel usado para casar componentes
    entre as duas imagens (ex.: 'wire:red', 'led:blue', 'resistor', 'ldr').
    """

    kind: ComponentKind
    label: str
    terminals: tuple[Terminal, ...]

    @property
    def is_mapped(self) -> bool:
        return all(t.is_mapped for t in self.terminals)

    @property
    def holes(self) -> tuple[Hole, ...]:
        return tuple(t.hole for t in self.terminals if t.hole is not None)

    @property
    def hole_set(self) -> frozenset[Hole]:
        """Conjunto de furos, independente da ordem dos terminais.

        Usado na comparacao: um componente esta no lugar certo se ocupa o mesmo
        conjunto de furos, nao importando qual terminal foi detectado primeiro.
        """
        return frozenset(self.holes)


@dataclass(frozen=True)
class Placement:
    """Conjunto de componentes detectados em uma imagem."""

    components: tuple[Component, ...] = ()

    def by_kind(self, kind: ComponentKind) -> tuple[Component, ...]:
        return tuple(c for c in self.components if c.kind == kind)


class DifferenceKind(str, Enum):
    """Natureza de uma divergencia entre gabarito e aluno."""

    MISMATCHED = "mismatched"  # mesmo componente, terminais diferentes
    MISSING = "missing"  # presente no gabarito, ausente no aluno
    EXTRA = "extra"  # presente no aluno, ausente no gabarito


@dataclass(frozen=True)
class ComponentMatch:
    """Par de componentes correspondentes que estao no mesmo lugar."""

    reference: Component
    test: Component


@dataclass(frozen=True)
class ComponentDifference:
    """Uma divergencia entre os dois circuitos.

    Para `MISMATCHED`, ambos `reference` e `test` estao preenchidos.
    Para `MISSING`, apenas `reference`; para `EXTRA`, apenas `test`.
    """

    kind: DifferenceKind
    detail: str
    reference: Component | None = None
    test: Component | None = None


@dataclass(frozen=True)
class ComparisonResult:
    """Resultado da comparacao entre o gabarito e o circuito do aluno."""

    matched: tuple[ComponentMatch, ...] = ()
    differences: tuple[ComponentDifference, ...] = field(default_factory=tuple)

    @property
    def is_match(self) -> bool:
        """True quando nao ha nenhuma divergencia."""
        return len(self.differences) == 0

    def _of_kind(self, kind: DifferenceKind) -> tuple[ComponentDifference, ...]:
        return tuple(d for d in self.differences if d.kind == kind)

    @property
    def mismatched(self) -> tuple[ComponentDifference, ...]:
        return self._of_kind(DifferenceKind.MISMATCHED)

    @property
    def missing(self) -> tuple[ComponentDifference, ...]:
        return self._of_kind(DifferenceKind.MISSING)

    @property
    def extra(self) -> tuple[ComponentDifference, ...]:
        return self._of_kind(DifferenceKind.EXTRA)
