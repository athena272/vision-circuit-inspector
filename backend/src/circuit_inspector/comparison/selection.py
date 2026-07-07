"""Selecao da divergencia mais relevante.

Os circuitos do problema tem, por construcao, no maximo um erro por placa.
Quando a deteccao gera divergencias espurias, este modulo reduz o resultado a
divergencia mais saliente, deixando a saida limpa e focada.

Criterio de salience (maior = mais relevante):
1. Tipo: um componente em furo errado (MISMATCHED) e mais informativo que um
   simplesmente faltando/sobrando (que costuma vir de falha de deteccao).
2. Magnitude: para MISMATCHED, o quanto o componente se deslocou (em furos).
"""

from __future__ import annotations

import math

from ..models import (
    ComparisonResult,
    Component,
    ComponentDifference,
    DifferenceKind,
    Hole,
)
from .registered import RegisteredDifference, RegisteredResult

# j (topo) .. a (base) -> 0..9; usado apenas para ranquear deslocamento.
_ROW_INDEX = {row: index for index, row in enumerate("jihgfedcba")}
_RAIL_Y = {"+": -2.0, "-": -3.0}

_KIND_PRIORITY = {
    DifferenceKind.MISMATCHED: 2,
    DifferenceKind.MISSING: 1,
    DifferenceKind.EXTRA: 1,
}


def _hole_xy(hole: Hole) -> tuple[float, float]:
    if hole.is_rail:
        return (float(hole.column), _RAIL_Y[hole.rail])  # type: ignore[index]
    return (float(hole.column), float(_ROW_INDEX.get(hole.row or "", 0)))


def _centroid(component: Component) -> tuple[float, float]:
    points = [_hole_xy(h) for h in component.hole_set]
    if not points:
        return (0.0, 0.0)
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def _displacement(diff: ComponentDifference) -> float:
    if diff.reference is None or diff.test is None:
        return 0.0
    rx, ry = _centroid(diff.reference)
    tx, ty = _centroid(diff.test)
    return math.hypot(rx - tx, ry - ty)


def difference_salience(diff: ComponentDifference) -> tuple[int, float]:
    """Pontua uma divergencia para ordenacao (maior = mais relevante)."""
    return (_KIND_PRIORITY[diff.kind], _displacement(diff))


def most_salient_difference(
    result: ComparisonResult,
) -> ComponentDifference | None:
    """Retorna a divergencia mais relevante, ou None se nao houver."""
    if not result.differences:
        return None
    return max(result.differences, key=difference_salience)


def reduce_to_single(result: ComparisonResult) -> ComparisonResult:
    """Reduz o resultado a sua divergencia mais saliente (preserva `matched`)."""
    top = most_salient_difference(result)
    differences = () if top is None else (top,)
    return ComparisonResult(matched=result.matched, differences=differences)


_REGISTERED_KIND_PRIORITY = {"mismatched": 2, "missing": 1, "extra": 1}


def registered_difference_salience(diff: RegisteredDifference) -> tuple[int, float]:
    """Pontua uma divergencia registrada para ordenacao (maior = mais relevante)."""
    return (_REGISTERED_KIND_PRIORITY[diff.kind], diff.salience)


def most_salient_registered_difference(
    result: RegisteredResult,
) -> RegisteredDifference | None:
    """Retorna a divergencia registrada mais relevante, ou None."""
    if not result.differences:
        return None
    return max(result.differences, key=registered_difference_salience)


def reduce_registered_to_single(result: RegisteredResult) -> RegisteredResult:
    """Reduz o resultado registrado a sua divergencia mais saliente."""
    top = most_salient_registered_difference(result)
    differences = () if top is None else (top,)
    return RegisteredResult(
        differences=differences, matched_count=result.matched_count
    )
