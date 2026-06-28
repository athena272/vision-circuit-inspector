"""Mapeamento de componentes detectados para furos da protoboard.

Recebe componentes com terminais em pixel (saida dos detectores) e usa o
`BoardGrid` para associar cada terminal ao furo mais proximo, produzindo um
`Placement` com furos preenchidos. Componentes que nao podem ser mapeados de
forma confiavel (terminal sem furo proximo ou terminais degenerados) sao
descartados.
"""

from __future__ import annotations

import math

from .board.grid_mapper import BoardGrid
from .config import MatchingConfig
from .models import Component, Hole, Placement, Terminal


def _canonical_distance(grid: BoardGrid, a: Hole, b: Hole) -> float:
    ua, va = grid.layout.hole_to_canonical(a)
    ub, vb = grid.layout.hole_to_canonical(b)
    return math.hypot(ua - ub, va - vb)


def _map_component(
    component: Component,
    grid: BoardGrid,
    config: MatchingConfig,
) -> Component | None:
    mapped: list[Terminal] = []
    for terminal in component.terminals:
        hole = grid.nearest_hole(terminal.pixel, config.terminal_snap_radius)
        if hole is None:
            return None
        mapped.append(terminal.with_hole(hole))

    holes = [t.hole for t in mapped if t.hole is not None]
    if len(holes) < 2:
        return None
    if _canonical_distance(grid, holes[0], holes[1]) < config.min_terminal_separation:
        return None

    return Component(
        kind=component.kind,
        label=component.label,
        terminals=tuple(mapped),
    )


def _deduplicate(components: list[Component]) -> list[Component]:
    """Remove deteccoes redundantes: mesmo label ocupando o mesmo par de furos.

    Duas deteccoes que caem nos mesmos furos representam o mesmo componente
    fisico (efeito comum de reflexos/sombras gerando contornos repetidos).
    """
    seen: set[tuple[str, frozenset[Hole]]] = set()
    unique: list[Component] = []
    for component in components:
        key = (component.label, component.hole_set)
        if key in seen:
            continue
        seen.add(key)
        unique.append(component)
    return unique


def map_components_to_holes(
    components: list[Component],
    grid: BoardGrid,
    config: MatchingConfig | None = None,
) -> Placement:
    """Mapeia os terminais de cada componente para furos, retornando um Placement."""
    config = config or MatchingConfig()
    mapped = [
        result
        for component in components
        if (result := _map_component(component, grid, config)) is not None
    ]
    return Placement(components=tuple(_deduplicate(mapped)))
