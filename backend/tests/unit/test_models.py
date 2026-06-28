"""Testes do modelo de dominio."""

from __future__ import annotations

import math

import pytest

from circuit_inspector.models import (
    ComparisonResult,
    Component,
    ComponentDifference,
    ComponentKind,
    ComponentMatch,
    DifferenceKind,
    Hole,
    Placement,
    Point,
    Terminal,
)


def _wire(label: str, holes: list[Hole]) -> Component:
    terminals = tuple(Terminal(pixel=Point(0, 0), hole=h) for h in holes)
    return Component(kind=ComponentKind.WIRE, label=label, terminals=terminals)


class TestPoint:
    def test_distance(self) -> None:
        assert Point(0, 0).distance_to(Point(3, 4)) == pytest.approx(5.0)

    def test_as_int_tuple_rounds(self) -> None:
        assert Point(1.6, 2.4).as_int_tuple() == (2, 2)


class TestHole:
    def test_main_area_label(self) -> None:
        assert Hole(column=50, row="e").label == "e50"

    def test_rail_label(self) -> None:
        assert Hole(column=50, rail="+").label == "+50"
        assert Hole(column=50, rail="+").is_rail is True

    def test_requires_exactly_one_of_row_or_rail(self) -> None:
        with pytest.raises(ValueError):
            Hole(column=1)
        with pytest.raises(ValueError):
            Hole(column=1, row="a", rail="+")

    def test_is_hashable_and_comparable(self) -> None:
        assert Hole(1, row="a") == Hole(1, row="a")
        assert len({Hole(1, row="a"), Hole(1, row="a")}) == 1


class TestTerminalAndComponent:
    def test_terminal_mapping(self) -> None:
        terminal = Terminal(pixel=Point(10, 20))
        assert terminal.is_mapped is False
        mapped = terminal.with_hole(Hole(5, row="c"))
        assert mapped.is_mapped is True
        assert mapped.pixel == Point(10, 20)
        assert terminal.is_mapped is False  # imutabilidade preservada

    def test_component_hole_set_ignores_order(self) -> None:
        a = _wire("wire:red", [Hole(1, row="a"), Hole(2, row="a")])
        b = _wire("wire:red", [Hole(2, row="a"), Hole(1, row="a")])
        assert a.hole_set == b.hole_set

    def test_component_is_mapped(self) -> None:
        unmapped = Component(
            kind=ComponentKind.WIRE,
            label="wire:red",
            terminals=(Terminal(Point(0, 0)), Terminal(Point(1, 1))),
        )
        assert unmapped.is_mapped is False


class TestPlacement:
    def test_by_kind(self) -> None:
        wire = _wire("wire:red", [Hole(1, row="a"), Hole(2, row="a")])
        led = Component(
            kind=ComponentKind.LED,
            label="led:blue",
            terminals=(Terminal(Point(0, 0)), Terminal(Point(1, 1))),
        )
        placement = Placement(components=(wire, led))
        assert placement.by_kind(ComponentKind.WIRE) == (wire,)
        assert placement.by_kind(ComponentKind.LED) == (led,)


class TestComparisonResult:
    def test_empty_result_is_match(self) -> None:
        assert ComparisonResult().is_match is True

    def test_difference_partitioning(self) -> None:
        result = ComparisonResult(
            matched=(),
            differences=(
                ComponentDifference(DifferenceKind.MISMATCHED, "x"),
                ComponentDifference(DifferenceKind.MISSING, "y"),
                ComponentDifference(DifferenceKind.EXTRA, "z"),
                ComponentDifference(DifferenceKind.MISMATCHED, "w"),
            ),
        )
        assert result.is_match is False
        assert len(result.mismatched) == 2
        assert len(result.missing) == 1
        assert len(result.extra) == 1
