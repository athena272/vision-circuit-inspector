"""Testes do mapeamento geometrico (CanonicalLayout + BoardGrid)."""

from __future__ import annotations

import numpy as np
import pytest

from circuit_inspector.board.grid_mapper import (
    BoardGrid,
    CanonicalLayout,
    grid_from_reference_points,
)
from circuit_inspector.config import BoardLayout
from circuit_inspector.models import Hole, Point


@pytest.fixture
def layout() -> CanonicalLayout:
    # Board pequeno para facilitar a verificacao manual.
    return CanonicalLayout(board=BoardLayout(min_column=1, max_column=5))


def _affine_homography(scale: float, tx: float, ty: float) -> np.ndarray:
    """Homografia puramente afim (escala + translacao)."""
    return np.array(
        [[scale, 0.0, tx], [0.0, scale, ty], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


class TestCanonicalLayout:
    def test_column_to_u_is_zero_based(self, layout: CanonicalLayout) -> None:
        assert layout.column_to_u(1) == 0.0
        assert layout.column_to_u(5) == 4.0

    def test_top_rows_increase_downward(self, layout: CanonicalLayout) -> None:
        assert layout.row_to_v("j") == 0.0
        assert layout.row_to_v("f") == 4.0

    def test_center_gap_between_e_and_f(self, layout: CanonicalLayout) -> None:
        # 'f' (ultima do topo) = 4.0; 'e' (primeira de baixo) fica abaixo com a
        # folga do canal central: len(top)=5 + center_gap=1 => 6.0.
        assert layout.row_to_v("f") == 4.0
        assert layout.row_to_v("e") == len(layout.board.top_rows) + layout.center_gap
        # A distancia f->e e maior que o passo normal entre linhas adjacentes.
        assert layout.row_to_v("e") - layout.row_to_v("f") > 1.0

    def test_rails_are_above_main_area(self, layout: CanonicalLayout) -> None:
        assert layout.rail_to_v("+") < 0
        assert layout.rail_to_v("-") < layout.rail_to_v("+")

    def test_all_holes_includes_rails(self, layout: CanonicalLayout) -> None:
        holes = layout.all_holes()
        assert any(h.is_rail for h in holes)
        assert any(not h.is_rail for h in holes)


class TestBoardGrid:
    def test_hole_to_pixel_with_affine(self, layout: CanonicalLayout) -> None:
        grid = BoardGrid(layout, _affine_homography(scale=10.0, tx=100.0, ty=50.0))
        # Hole (col=1, row='j') -> canonical (0, 0) -> pixel (100, 50).
        pixel = grid.hole_to_pixel(Hole(column=1, row="j"))
        assert pixel.x == pytest.approx(100.0)
        assert pixel.y == pytest.approx(50.0)
        # Hole (col=2, row='j') -> canonical (1, 0) -> pixel (110, 50).
        pixel2 = grid.hole_to_pixel(Hole(column=2, row="j"))
        assert pixel2.x == pytest.approx(110.0)

    def test_nearest_hole_snaps_to_closest(self, layout: CanonicalLayout) -> None:
        grid = BoardGrid(layout, _affine_homography(scale=10.0, tx=100.0, ty=50.0))
        # Proximo do furo (col=2, row='j') em (110, 50).
        nearest = grid.nearest_hole(Point(112, 52), snap_radius=15.0)
        assert nearest == Hole(column=2, row="j")

    def test_nearest_hole_returns_none_when_too_far(
        self, layout: CanonicalLayout
    ) -> None:
        grid = BoardGrid(layout, _affine_homography(scale=10.0, tx=100.0, ty=50.0))
        assert grid.nearest_hole(Point(1000, 1000), snap_radius=15.0) is None

    def test_invalid_homography_shape(self, layout: CanonicalLayout) -> None:
        with pytest.raises(ValueError):
            BoardGrid(layout, np.eye(2))


class TestGridFromReferencePoints:
    def test_roundtrip_with_four_corners(self, layout: CanonicalLayout) -> None:
        # Define uma homografia afim conhecida e gera 4 cantos a partir dela.
        h = _affine_homography(scale=20.0, tx=30.0, ty=40.0)
        truth = BoardGrid(layout, h)
        corners = [
            Hole(column=1, row="j"),
            Hole(column=5, row="j"),
            Hole(column=1, row="a"),
            Hole(column=5, row="a"),
        ]
        correspondences = [(hole, truth.hole_to_pixel(hole)) for hole in corners]

        estimated = grid_from_reference_points(correspondences, layout=layout)

        # O grid estimado deve reproduzir os pixels de furos arbitrarios.
        for hole in [Hole(3, row="c"), Hole(2, row="h"), Hole(4, row="b")]:
            expected = truth.hole_to_pixel(hole)
            actual = estimated.hole_to_pixel(hole)
            assert actual.x == pytest.approx(expected.x, abs=1e-3)
            assert actual.y == pytest.approx(expected.y, abs=1e-3)

    def test_requires_at_least_four_points(self, layout: CanonicalLayout) -> None:
        with pytest.raises(ValueError):
            grid_from_reference_points(
                [(Hole(1, row="j"), Point(0, 0))], layout=layout
            )
