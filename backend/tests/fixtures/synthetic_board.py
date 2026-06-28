"""Gerador de protoboard sintetica para testes deterministicos.

Desenha uma protoboard simplificada (fundo claro, malha de furos escuros e
componentes coloridos) a partir de uma especificacao de alto nivel, com cores
compativeis com os perfis HSV de `ColorProfiles`. Retorna a imagem, o
`BoardGrid` verdadeiro e o `Placement` verdadeiro (ground truth), permitindo
validar deteccao, mapeamento e comparacao sem depender de fotos reais.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from circuit_inspector.board.grid_mapper import BoardGrid, CanonicalLayout
from circuit_inspector.config import BoardLayout
from circuit_inspector.models import (
    Component,
    ComponentKind,
    Hole,
    Placement,
    Terminal,
)

BACKGROUND_BGR = (210, 210, 210)
HOLE_BGR = (30, 30, 30)
WIRE_BGR = {
    "red": (0, 0, 255),
    "orange": (0, 140, 255),
    "green": (0, 180, 0),
    "black": (20, 20, 20),
}
LED_BGR = {"blue": (255, 0, 0), "red": (0, 0, 255)}
LDR_BGR = (150, 150, 150)
RESISTOR_BGR = (200, 200, 0)
CAPACITOR_BGR = (30, 30, 30)
POTENTIOMETER_BGR = (150, 150, 150)
BUTTON_BGR = (30, 30, 30)


@dataclass(frozen=True)
class ComponentSpec:
    """Especificacao de um componente a desenhar (dois furos)."""

    kind: ComponentKind
    label: str
    hole_a: Hole
    hole_b: Hole


@dataclass(frozen=True)
class SyntheticBoard:
    image: np.ndarray
    grid: BoardGrid
    placement: Placement


def _affine_homography(scale: float, tx: float, ty: float) -> np.ndarray:
    return np.array(
        [[scale, 0.0, tx], [0.0, scale, ty], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def _px(grid: BoardGrid, hole: Hole) -> tuple[int, int]:
    return grid.hole_to_pixel(hole).as_int_tuple()


def build_board(
    specs: list[ComponentSpec],
    layout: CanonicalLayout | None = None,
    pitch: float = 28.0,
    margin: float = 45.0,
) -> SyntheticBoard:
    """Constroi uma protoboard sintetica com os componentes informados."""
    layout = layout or CanonicalLayout(board=BoardLayout(min_column=1, max_column=12))

    # Extensao vertical canonica (inclui as trilhas, para reservar espaco).
    min_v = layout.rail_to_v(layout.board.rail_negative)
    max_v = layout.row_to_v(layout.board.bottom_rows[-1])
    max_u = layout.column_to_u(layout.board.max_column)

    tx = margin - 0.0 * pitch
    ty = margin - min_v * pitch
    width = int(margin * 2 + max_u * pitch)
    height = int(margin * 2 + (max_v - min_v) * pitch)

    grid = BoardGrid(layout, _affine_homography(pitch, tx, ty))

    image = np.full((height, width, 3), BACKGROUND_BGR, dtype=np.uint8)
    _draw_holes(image, grid, layout, pitch)

    components: list[Component] = []
    for spec in specs:
        _draw_component(image, grid, spec, pitch)
        components.append(_spec_to_component(grid, spec))

    return SyntheticBoard(image=image, grid=grid, placement=Placement(tuple(components)))


def _draw_holes(
    image: np.ndarray,
    grid: BoardGrid,
    layout: CanonicalLayout,
    pitch: float,
) -> None:
    """Desenha apenas os furos da area central (entrada do estimador automatico)."""
    half = max(2, int(pitch * 0.12))
    for column in range(layout.board.min_column, layout.board.max_column + 1):
        for row in layout.board.rows:
            x, y = _px(grid, Hole(column=column, row=row))
            cv2.rectangle(
                image, (x - half, y - half), (x + half, y + half), HOLE_BGR, -1
            )


def _draw_component(
    image: np.ndarray,
    grid: BoardGrid,
    spec: ComponentSpec,
    pitch: float,
) -> None:
    pa = _px(grid, spec.hole_a)
    pb = _px(grid, spec.hole_b)
    if spec.kind == ComponentKind.WIRE:
        color = WIRE_BGR[spec.label.split(":")[1]]
        cv2.line(image, pa, pb, color, int(pitch * 0.32))
    elif spec.kind == ComponentKind.RESISTOR:
        cv2.line(image, pa, pb, RESISTOR_BGR, int(pitch * 0.45))
    elif spec.kind == ComponentKind.LED:
        _draw_compact(image, pa, pb, LED_BGR[spec.label.split(":")[1]])
    elif spec.kind == ComponentKind.LDR:
        _draw_compact(image, pa, pb, LDR_BGR)
    elif spec.kind == ComponentKind.CAPACITOR:
        _draw_compact(image, pa, pb, CAPACITOR_BGR)
    elif spec.kind == ComponentKind.POTENTIOMETER:
        _draw_compact(image, pa, pb, POTENTIOMETER_BGR)
    elif spec.kind == ComponentKind.BUTTON:
        _draw_square(image, pa, pb, BUTTON_BGR)
    else:  # pragma: no cover - defensivo
        raise ValueError(f"Tipo nao suportado no gerador: {spec.kind}")


def _draw_compact(
    image: np.ndarray,
    pa: tuple[int, int],
    pb: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    """Desenha um corpo circular cujos cantos inferiores do bbox caem nos furos."""
    cx = (pa[0] + pb[0]) // 2
    radius = max(10, abs(pb[0] - pa[0]) // 2)
    center_y = pa[1] - radius
    cv2.circle(image, (cx, center_y), radius, color, -1)


def _draw_square(
    image: np.ndarray,
    pa: tuple[int, int],
    pb: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    """Desenha um corpo quadrado cujos cantos inferiores caem nos furos."""
    cx = (pa[0] + pb[0]) // 2
    half = max(10, abs(pb[0] - pa[0]) // 2)
    bottom = pa[1]
    cv2.rectangle(
        image, (cx - half, bottom - 2 * half), (cx + half, bottom), color, -1
    )


def _spec_to_component(grid: BoardGrid, spec: ComponentSpec) -> Component:
    return Component(
        kind=spec.kind,
        label=spec.label,
        terminals=(
            Terminal(pixel=grid.hole_to_pixel(spec.hole_a), hole=spec.hole_a),
            Terminal(pixel=grid.hole_to_pixel(spec.hole_b), hole=spec.hole_b),
        ),
    )


def full_circuit_layout() -> CanonicalLayout:
    """Layout maior, com espaco para todos os tipos de componente."""
    return CanonicalLayout(board=BoardLayout(min_column=1, max_column=24))


def full_circuit() -> list[ComponentSpec]:
    """Circuito com um exemplar de cada tipo de componente suportado.

    Os componentes sao espacados para evitar sobreposicao entre blobs de mesma
    cor (escuros: fio preto/capacitor/botao; cinzas: LDR/potenciometro).
    Use com `full_circuit_layout()`.
    """
    return [
        ComponentSpec(ComponentKind.WIRE, "wire:red", Hole(2, row="j"), Hole(2, rail="+")),
        ComponentSpec(ComponentKind.WIRE, "wire:black", Hole(23, row="j"), Hole(23, rail="-")),
        ComponentSpec(ComponentKind.WIRE, "wire:green", Hole(1, row="a"), Hole(3, row="a")),
        ComponentSpec(ComponentKind.WIRE, "wire:orange", Hole(6, row="a"), Hole(9, row="a")),
        ComponentSpec(ComponentKind.LED, "led:blue", Hole(5, row="c"), Hole(6, row="c")),
        ComponentSpec(ComponentKind.LED, "led:red", Hole(8, row="c"), Hole(9, row="c")),
        ComponentSpec(ComponentKind.LDR, "ldr", Hole(11, row="c"), Hole(12, row="c")),
        ComponentSpec(ComponentKind.RESISTOR, "resistor", Hole(14, row="c"), Hole(16, row="c")),
        ComponentSpec(ComponentKind.CAPACITOR, "capacitor", Hole(18, row="c"), Hole(20, row="c")),
        ComponentSpec(ComponentKind.BUTTON, "button", Hole(22, row="e"), Hole(23, row="e")),
        ComponentSpec(
            ComponentKind.POTENTIOMETER, "potentiometer", Hole(13, row="h"), Hole(17, row="h")
        ),
    ]


def default_circuit() -> list[ComponentSpec]:
    """Um circuito simples de referencia usado em varios testes."""
    return [
        ComponentSpec(
            ComponentKind.WIRE, "wire:red",
            Hole(2, row="j"), Hole(2, rail="+"),
        ),
        ComponentSpec(
            ComponentKind.WIRE, "wire:black",
            Hole(10, row="j"), Hole(10, rail="-"),
        ),
        ComponentSpec(
            ComponentKind.WIRE, "wire:orange",
            Hole(4, row="a"), Hole(7, row="a"),
        ),
        ComponentSpec(
            ComponentKind.LED, "led:blue",
            Hole(2, row="e"), Hole(3, row="e"),
        ),
        ComponentSpec(
            ComponentKind.RESISTOR, "resistor",
            Hole(8, row="c"), Hole(10, row="c"),
        ),
    ]
