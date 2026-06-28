"""Mapeamento geometrico entre pixels e furos da protoboard.

A ideia central e separar duas responsabilidades:

- `CanonicalLayout`: conhece a geometria *logica* do board, ou seja, a posicao
  de cada furo em um sistema de coordenadas canonico (em unidades de "passo de
  furo"). E pura e totalmente testavel, sem depender de imagens.

- `BoardGrid`: combina o layout canonico com uma homografia que leva as
  coordenadas canonicas para pixels de uma imagem especifica. Expoe
  `hole_to_pixel` (furo -> pixel) e `nearest_hole` (pixel -> furo).

Como as duas imagens (gabarito e aluno) sao mapeadas para o *mesmo* layout
canonico, um furo `(coluna, linha)` identifica o mesmo ponto fisico nas duas,
permitindo a comparacao.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import RAIL_NEGATIVE, RAIL_POSITIVE, BoardLayout
from ..models import Hole, Point


@dataclass(frozen=True)
class CanonicalLayout:
    """Posiciona cada furo logico em coordenadas canonicas (u, v).

    `u` cresce com a coluna; `v` cresce de cima para baixo. As distancias sao
    expressas em multiplos do passo da malha (1.0 = um furo). Os parametros de
    folga (`center_gap`, `rail_gap`, `rail_separation`) sao configuraveis para
    permitir calibrar a geometria conforme o board real.

    Premissa de escopo: modela-se a trilha de alimentacao *superior* (uma faixa
    com as linhas '+' e '-'), que e a usada nos circuitos de exemplo.
    """

    board: BoardLayout = BoardLayout()
    center_gap: float = 1.0  # folga do canal central (entre linhas 'e' e 'f')
    rail_gap: float = 2.0  # folga entre a trilha e a linha 'j'
    rail_separation: float = 1.0  # distancia entre as linhas '-' e '+'

    def column_to_u(self, column: int) -> float:
        return float(column - self.board.min_column)

    def row_to_v(self, row: str) -> float:
        top = self.board.top_rows  # ('j','i','h','g','f')
        bottom = self.board.bottom_rows  # ('e','d','c','b','a')
        if row in top:
            return float(top.index(row))
        if row in bottom:
            return float(len(top) + self.center_gap + bottom.index(row))
        raise ValueError(f"Linha desconhecida: {row!r}")

    def rail_to_v(self, rail: str) -> float:
        # Trilha superior fica acima da linha 'j' (v=0), portanto v negativo.
        if rail == self.board.rail_negative:
            return -(self.rail_gap + self.rail_separation)
        if rail == self.board.rail_positive:
            return -self.rail_gap
        raise ValueError(f"Trilha desconhecida: {rail!r}")

    def hole_to_canonical(self, hole: Hole) -> tuple[float, float]:
        u = self.column_to_u(hole.column)
        v = self.rail_to_v(hole.rail) if hole.is_rail else self.row_to_v(hole.row)  # type: ignore[arg-type]
        return (u, v)

    def all_holes(self) -> list[Hole]:
        """Enumera todos os furos modelados (area central + trilha superior)."""
        holes: list[Hole] = []
        columns = range(self.board.min_column, self.board.max_column + 1)
        for column in columns:
            for row in self.board.rows:
                holes.append(Hole(column=column, row=row))
            holes.append(Hole(column=column, rail=RAIL_POSITIVE))
            holes.append(Hole(column=column, rail=RAIL_NEGATIVE))
        return holes


def _apply_homography(h: np.ndarray, u: float, v: float) -> Point:
    vec = h @ np.array([u, v, 1.0], dtype=np.float64)
    w = vec[2]
    if abs(w) < 1e-12:
        raise ValueError("Homografia degenerada ao projetar ponto.")
    return Point(x=float(vec[0] / w), y=float(vec[1] / w))


class BoardGrid:
    """Mapeia furos para pixels (e vice-versa) em uma imagem especifica."""

    def __init__(self, layout: CanonicalLayout, homography: np.ndarray) -> None:
        if homography.shape != (3, 3):
            raise ValueError("A homografia deve ser uma matriz 3x3.")
        self._layout = layout
        self._homography = np.asarray(homography, dtype=np.float64)
        # Pre-calcula o pixel de cada furo para acelerar `nearest_hole`.
        self._holes: list[Hole] = layout.all_holes()
        self._hole_pixels: list[Point] = [
            self.hole_to_pixel(hole) for hole in self._holes
        ]

    @property
    def layout(self) -> CanonicalLayout:
        return self._layout

    @property
    def homography(self) -> np.ndarray:
        return self._homography.copy()

    def hole_to_pixel(self, hole: Hole) -> Point:
        u, v = self._layout.hole_to_canonical(hole)
        return _apply_homography(self._homography, u, v)

    def nearest_hole(self, pixel: Point, snap_radius: float) -> Hole | None:
        """Retorna o furo mais proximo de `pixel`, ou None se estiver alem de
        `snap_radius`."""
        best_hole: Hole | None = None
        best_distance = float("inf")
        for hole, hole_pixel in zip(self._holes, self._hole_pixels):
            distance = pixel.distance_to(hole_pixel)
            if distance < best_distance:
                best_distance = distance
                best_hole = hole
        if best_hole is None or best_distance > snap_radius:
            return None
        return best_hole


def grid_from_reference_points(
    correspondences: list[tuple[Hole, Point]],
    layout: CanonicalLayout | None = None,
) -> BoardGrid:
    """Constroi um `BoardGrid` a partir de furos de referencia conhecidos.

    Recebe pares (furo, pixel) e estima a homografia canonico -> pixel. Usado
    tanto na calibracao assistida (4 cantos marcados manualmente) quanto nos
    testes. Requer ao menos 4 correspondencias nao colineares.
    """
    import cv2

    if len(correspondences) < 4:
        raise ValueError("Sao necessarias ao menos 4 correspondencias.")

    layout = layout or CanonicalLayout()
    src = np.array(
        [layout.hole_to_canonical(hole) for hole, _ in correspondences],
        dtype=np.float64,
    )
    dst = np.array(
        [[point.x, point.y] for _, point in correspondences],
        dtype=np.float64,
    )
    homography, _ = cv2.findHomography(src, dst, method=0)
    if homography is None:
        raise ValueError("Nao foi possivel estimar a homografia (pontos degenerados?).")
    return BoardGrid(layout=layout, homography=homography)
