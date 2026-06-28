"""Testes do comparador de placements."""

from __future__ import annotations

from circuit_inspector.comparison.comparator import compare_placements
from circuit_inspector.models import (
    Component,
    ComponentKind,
    DifferenceKind,
    Hole,
    Placement,
    Point,
    Terminal,
)


def _component(kind: ComponentKind, label: str, holes: list[Hole]) -> Component:
    terminals = tuple(Terminal(pixel=Point(0, 0), hole=h) for h in holes)
    return Component(kind=kind, label=label, terminals=terminals)


def _resistor(holes: list[Hole]) -> Component:
    return _component(ComponentKind.RESISTOR, "resistor", holes)


def test_identical_placements_have_no_differences() -> None:
    ref = Placement((_resistor([Hole(8, row="c"), Hole(10, row="c")]),))
    test = Placement((_resistor([Hole(10, row="c"), Hole(8, row="c")]),))

    result = compare_placements(ref, test)

    assert result.is_match is True
    assert len(result.matched) == 1


def test_detects_mismatched_terminals() -> None:
    ref = Placement((_resistor([Hole(8, row="c"), Hole(10, row="c")]),))
    test = Placement((_resistor([Hole(8, row="c"), Hole(11, row="c")]),))

    result = compare_placements(ref, test)

    assert result.is_match is False
    assert len(result.mismatched) == 1
    diff = result.mismatched[0]
    assert diff.kind == DifferenceKind.MISMATCHED
    assert diff.reference is not None and diff.test is not None
    assert "c10" in diff.detail and "c11" in diff.detail


def test_detects_missing_component() -> None:
    ref = Placement((_resistor([Hole(8, row="c"), Hole(10, row="c")]),))
    test = Placement(())

    result = compare_placements(ref, test)

    assert len(result.missing) == 1
    assert result.missing[0].kind == DifferenceKind.MISSING


def test_detects_extra_component() -> None:
    ref = Placement(())
    test = Placement((_resistor([Hole(8, row="c"), Hole(10, row="c")]),))

    result = compare_placements(ref, test)

    assert len(result.extra) == 1
    assert result.extra[0].kind == DifferenceKind.EXTRA


def test_matches_components_by_label() -> None:
    # Mesmos furos, mas cores diferentes -> nao casam (missing + extra).
    ref = Placement(
        (_component(ComponentKind.WIRE, "wire:red", [Hole(1, row="a"), Hole(2, row="a")]),)
    )
    test = Placement(
        (_component(ComponentKind.WIRE, "wire:black", [Hole(1, row="a"), Hole(2, row="a")]),)
    )

    result = compare_placements(ref, test)

    assert len(result.missing) == 1
    assert len(result.extra) == 1


def test_led_colors_are_distinct_components() -> None:
    # Mesmo furo, mas LED de cor diferente -> troca de cor e divergencia.
    holes = [Hole(50, row="e"), Hole(51, row="e")]
    ref = Placement((_component(ComponentKind.LED, "led:blue", holes),))
    test = Placement((_component(ComponentKind.LED, "led:red", holes),))

    result = compare_placements(ref, test)

    assert result.is_match is False
    assert len(result.missing) == 1  # led:blue ausente
    assert len(result.extra) == 1  # led:red sobrando


def test_greedy_match_picks_highest_overlap() -> None:
    # Dois resistores no gabarito; um deles movido no aluno.
    ref = Placement(
        (
            _resistor([Hole(1, row="c"), Hole(3, row="c")]),
            _resistor([Hole(8, row="c"), Hole(10, row="c")]),
        )
    )
    test = Placement(
        (
            _resistor([Hole(8, row="c"), Hole(10, row="c")]),  # igual ao 2o
            _resistor([Hole(1, row="c"), Hole(4, row="c")]),  # movido (era 1-3)
        )
    )

    result = compare_placements(ref, test)

    assert len(result.matched) == 1  # o resistor 8-10 casa exatamente
    assert len(result.mismatched) == 1  # o resistor 1-3 -> 1-4
