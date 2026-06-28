"""Testes da selecao da divergencia mais saliente."""

from __future__ import annotations

from circuit_inspector.comparison.selection import (
    most_salient_difference,
    reduce_to_single,
)
from circuit_inspector.models import (
    ComparisonResult,
    Component,
    ComponentDifference,
    ComponentKind,
    DifferenceKind,
    Hole,
    Point,
    Terminal,
)


def _component(label: str, holes: list[Hole]) -> Component:
    terminals = tuple(Terminal(pixel=Point(0, 0), hole=h) for h in holes)
    return Component(kind=ComponentKind.RESISTOR, label=label, terminals=terminals)


def _mismatch(ref_holes: list[Hole], test_holes: list[Hole]) -> ComponentDifference:
    return ComponentDifference(
        kind=DifferenceKind.MISMATCHED,
        detail="x",
        reference=_component("resistor", ref_holes),
        test=_component("resistor", test_holes),
    )


def test_returns_none_when_no_differences() -> None:
    assert most_salient_difference(ComparisonResult()) is None
    assert reduce_to_single(ComparisonResult()).is_match is True


def test_mismatch_preferred_over_missing() -> None:
    missing = ComponentDifference(DifferenceKind.MISSING, "m", reference=_component("ldr", [Hole(1, row="a"), Hole(2, row="a")]))
    mismatch = _mismatch([Hole(5, row="c"), Hole(6, row="c")], [Hole(5, row="c"), Hole(7, row="c")])
    result = ComparisonResult(differences=(missing, mismatch))

    assert most_salient_difference(result) is mismatch


def test_larger_displacement_wins_among_mismatches() -> None:
    small = _mismatch([Hole(5, row="c"), Hole(6, row="c")], [Hole(5, row="c"), Hole(7, row="c")])
    large = _mismatch([Hole(5, row="c"), Hole(6, row="c")], [Hole(20, row="c"), Hole(21, row="c")])
    result = ComparisonResult(differences=(small, large))

    assert most_salient_difference(result) is large


def test_reduce_to_single_keeps_one_difference_and_matched() -> None:
    missing = ComponentDifference(DifferenceKind.MISSING, "m", reference=_component("ldr", [Hole(1, row="a"), Hole(2, row="a")]))
    mismatch = _mismatch([Hole(5, row="c"), Hole(6, row="c")], [Hole(5, row="c"), Hole(7, row="c")])
    result = ComparisonResult(matched=(), differences=(missing, mismatch))

    reduced = reduce_to_single(result)

    assert len(reduced.differences) == 1
    assert reduced.differences[0] is mismatch
