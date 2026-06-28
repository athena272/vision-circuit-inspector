"""Testes da anotacao visual."""

from __future__ import annotations

import numpy as np

from circuit_inspector.models import (
    ComparisonResult,
    Component,
    ComponentDifference,
    ComponentKind,
    DifferenceKind,
    Hole,
    Terminal,
)
from circuit_inspector.visualization.annotator import (
    COLOR_WRONG,
    annotate_differences,
)

from tests.fixtures.synthetic_board import build_board, default_circuit


def _component(grid, holes: list[Hole]) -> Component:
    terminals = tuple(
        Terminal(pixel=grid.hole_to_pixel(h), hole=h) for h in holes
    )
    return Component(kind=ComponentKind.RESISTOR, label="resistor", terminals=terminals)


def test_annotation_preserves_shape_and_marks_mismatch() -> None:
    board = build_board(default_circuit())
    reference = _component(board.grid, [Hole(8, row="c"), Hole(10, row="c")])
    test = _component(board.grid, [Hole(8, row="c"), Hole(11, row="c")])
    result = ComparisonResult(
        matched=(),
        differences=(
            ComponentDifference(
                kind=DifferenceKind.MISMATCHED,
                detail="resistor moveu",
                reference=reference,
                test=test,
            ),
        ),
    )

    annotated = annotate_differences(board.image, board.grid, result)

    assert annotated.shape == board.image.shape
    # Deve haver pixels vermelhos (caixa de erro) que nao existiam antes.
    wrong = np.array(COLOR_WRONG, dtype=np.uint8)
    assert np.any(np.all(annotated == wrong, axis=2))


def test_annotation_of_clean_result_is_unchanged() -> None:
    board = build_board(default_circuit())
    annotated = annotate_differences(board.image, board.grid, ComparisonResult())
    assert np.array_equal(annotated, board.image)
