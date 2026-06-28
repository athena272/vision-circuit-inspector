"""Testes do mapeamento de componentes para furos."""

from __future__ import annotations

from circuit_inspector.config import MatchingConfig
from circuit_inspector.detection.registry import DetectorRegistry
from circuit_inspector.mapping import map_components_to_holes
from circuit_inspector.models import Component, ComponentKind, Hole, Point, Terminal

from tests.fixtures.synthetic_board import build_board, default_circuit


def test_maps_detected_components_to_expected_holes() -> None:
    board = build_board(default_circuit())
    components = DetectorRegistry.default().detect_all(board.image)

    placement = map_components_to_holes(components, board.grid)

    # Resistor: deve ocupar os furos c8 e c10 (independente da ordem).
    resistors = placement.by_kind(ComponentKind.RESISTOR)
    assert len(resistors) == 1
    labels = {h.label for h in resistors[0].hole_set}
    assert labels == {"c8", "c10"}


def test_drops_components_with_unmappable_terminals() -> None:
    board = build_board(default_circuit())
    far = Component(
        kind=ComponentKind.WIRE,
        label="wire:red",
        terminals=(Terminal(Point(-500, -500)), Terminal(Point(-600, -600))),
    )
    placement = map_components_to_holes([far], board.grid, MatchingConfig())
    assert placement.components == ()


def test_deduplicates_components_in_same_holes() -> None:
    board = build_board(default_circuit())
    p1 = board.grid.hole_to_pixel(Hole(8, row="c"))
    p2 = board.grid.hole_to_pixel(Hole(10, row="c"))
    dup_a = Component(
        kind=ComponentKind.RESISTOR,
        label="resistor",
        terminals=(Terminal(p1), Terminal(p2)),
    )
    dup_b = Component(
        kind=ComponentKind.RESISTOR,
        label="resistor",
        terminals=(Terminal(p2), Terminal(p1)),
    )
    placement = map_components_to_holes([dup_a, dup_b], board.grid)
    assert len(placement.components) == 1


def test_drops_degenerate_component_same_hole() -> None:
    board = build_board(default_circuit())
    # Dois terminais no mesmo ponto -> mesmo furo -> descartado.
    p = board.grid.hole_to_pixel(default_circuit()[0].hole_a)
    degenerate = Component(
        kind=ComponentKind.WIRE,
        label="wire:red",
        terminals=(Terminal(p), Terminal(p)),
    )
    placement = map_components_to_holes([degenerate], board.grid)
    assert placement.components == ()
