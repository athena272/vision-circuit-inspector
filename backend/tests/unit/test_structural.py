"""Testes da comparacao estrutural por ocupacao de furo."""

from __future__ import annotations

from circuit_inspector.comparison.structural import (
    _adjacent,
    _cluster,
    _format_holes,
    _infer_label,
    compare_structural,
    compute_occupancy,
)
from circuit_inspector.models import ComponentKind, DifferenceKind, Hole

from tests.fixtures.synthetic_board import ComponentSpec, build_board


class TestPureHelpers:
    def test_adjacent_same_row(self) -> None:
        assert _adjacent(Hole(5, row="c"), Hole(6, row="c"))
        assert not _adjacent(Hole(5, row="c"), Hole(7, row="c"))

    def test_adjacent_same_column(self) -> None:
        assert _adjacent(Hole(5, row="c"), Hole(5, row="d"))  # linhas consecutivas
        assert not _adjacent(Hole(5, row="c"), Hole(5, row="a"))  # nao consecutivas

    def test_adjacent_diagonal_is_false(self) -> None:
        assert not _adjacent(Hole(5, row="c"), Hole(6, row="d"))

    def test_cluster_groups_connected_holes(self) -> None:
        holes = {Hole(5, row="c"), Hole(6, row="c"), Hole(9, row="c")}
        clusters = _cluster(holes)
        assert len(clusters) == 2
        sizes = sorted(len(c) for c in clusters)
        assert sizes == [1, 2]

    def test_format_holes_is_sorted(self) -> None:
        text = _format_holes(frozenset({Hole(6, row="c"), Hole(5, row="c")}))
        assert text == "{c5, c6}"

    def test_infer_label_blue_elongated_is_resistor(self) -> None:
        cluster = frozenset({Hole(5, row="c"), Hole(6, row="c"), Hole(7, row="c")})
        # matiz azul (~110) com geometria alongada
        from circuit_inspector.comparison.structural import _HoleSample

        samples = {h: _HoleSample(h, saturation=200, hue=110) for h in cluster}
        kind, label = _infer_label(cluster, samples)
        assert kind == ComponentKind.RESISTOR
        assert label == "resistor"


class TestCompareStructural:
    def _board(self, resistor_cols: tuple[int, int]):
        # Jumper fixo (cobre bem os furos) + resistor em posicao variavel.
        specs = [
            ComponentSpec(ComponentKind.WIRE, "wire:red", Hole(2, row="a"), Hole(4, row="a")),
            ComponentSpec(
                ComponentKind.RESISTOR, "resistor",
                Hole(resistor_cols[0], row="c"), Hole(resistor_cols[1], row="c"),
            ),
        ]
        return build_board(specs)

    def test_identical_boards_match(self) -> None:
        ref = self._board((8, 10))
        test = self._board((8, 10))
        result = compare_structural(ref.image, test.image, ref.grid, test.grid)
        assert result.is_match

    def test_moved_resistor_is_detected(self) -> None:
        ref = self._board((8, 10))
        test = self._board((4, 6))
        result = compare_structural(ref.image, test.image, ref.grid, test.grid)
        assert not result.is_match
        # O LED, parado, conta como correspondente.
        assert len(result.matched) >= 1
        # A diferenca mais forte deve mencionar o resistor.
        details = " ".join(d.detail for d in result.differences)
        assert "resistor" in details

    def test_moved_resistor_pairs_as_mismatch(self) -> None:
        ref = self._board((8, 10))
        test = self._board((4, 6))
        result = compare_structural(ref.image, test.image, ref.grid, test.grid)
        kinds = {d.kind for d in result.differences}
        # Mesmo rotulo (resistor) perdido e ganho -> pareados como MISMATCHED.
        assert DifferenceKind.MISMATCHED in kinds

    def test_compute_occupancy_marks_component_holes(self) -> None:
        board = self._board((8, 10))
        occ = compute_occupancy(board.image, board.grid)
        # furos do resistor tem saturacao bem acima do fundo
        s_res = occ[Hole(9, row="c")].saturation
        s_empty = occ[Hole(1, row="a")].saturation
        assert s_res > s_empty + 40
