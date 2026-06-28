"""Testes da estimativa automatica da malha (rectifier)."""

from __future__ import annotations

import numpy as np
import pytest

from circuit_inspector.board.rectifier import (
    GridEstimationError,
    estimate_grid,
)
from circuit_inspector.models import Hole

from tests.fixtures.synthetic_board import build_board, default_circuit


def test_estimate_grid_recovers_known_holes() -> None:
    board = build_board(default_circuit())

    grid = estimate_grid(board.image)

    # Para varios furos da area central, o pixel verdadeiro deve mapear de volta
    # para o mesmo furo via nearest_hole.
    for hole in [Hole(1, row="j"), Hole(6, row="f"), Hole(3, row="e"), Hole(12, row="a")]:
        truth_pixel = board.grid.hole_to_pixel(hole)
        assert grid.nearest_hole(truth_pixel, snap_radius=16.0) == hole


def test_estimate_grid_raises_on_blank_image() -> None:
    blank = np.full((300, 300, 3), 210, dtype=np.uint8)
    with pytest.raises(GridEstimationError):
        estimate_grid(blank)
