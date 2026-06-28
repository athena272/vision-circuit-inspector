"""Construcao do `BoardGrid` a partir de uma imagem.

Dois caminhos sao oferecidos:

1. Calibracao assistida (`build_grid_from_calibration`): o usuario fornece
   correspondencias furo->pixel conhecidas (por exemplo, 4 cantos marcados a
   mao). E o caminho robusto e recomendado, especialmente quando ha trilhas de
   alimentacao envolvidas.

2. Estimativa automatica (`estimate_grid`): detecta a malha de furos, localiza
   o canal central e ajusta uma homografia para a area central. E "best-effort"
   e funciona bem em fotos top-down padronizadas; rails nao sao mapeados neste
   modo (use calibracao para precisao com trilhas).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import HoleDetectionConfig
from ..models import Hole, Point
from .grid_mapper import BoardGrid, CanonicalLayout, grid_from_reference_points
from .hole_detector import detect_holes


class GridEstimationError(RuntimeError):
    """Levantado quando a estimativa automatica da malha falha."""


@dataclass(frozen=True)
class GridCalibration:
    """Correspondencias furo->pixel para calibracao assistida."""

    correspondences: tuple[tuple[Hole, Point], ...]


def build_grid_from_calibration(
    calibration: GridCalibration,
    layout: CanonicalLayout | None = None,
) -> BoardGrid:
    """Constroi um `BoardGrid` a partir de correspondencias conhecidas."""
    return grid_from_reference_points(
        list(calibration.correspondences), layout=layout
    )


def _cluster_1d(values: list[float], tolerance: float) -> list[float]:
    """Agrupa valores 1D proximos e retorna os centros dos grupos ordenados."""
    if not values:
        return []
    ordered = sorted(values)
    clusters: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - clusters[-1][-1] <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [float(np.mean(cluster)) for cluster in clusters]


def _median_neighbor_pitch(sorted_centers: list[float]) -> float:
    if len(sorted_centers) < 2:
        raise GridEstimationError("Nao ha pontos suficientes para estimar o passo.")
    diffs = np.diff(sorted_centers)
    return float(np.median(diffs))


def estimate_grid(
    image_bgr: np.ndarray,
    layout: CanonicalLayout | None = None,
    hole_config: HoleDetectionConfig | None = None,
) -> BoardGrid:
    """Estima um `BoardGrid` automaticamente a partir da imagem.

    Estrategia (para fotos top-down, eixos aproximadamente alinhados):
    1. Detecta os furos.
    2. Agrupa coordenadas X em colunas e Y em linhas.
    3. Localiza o canal central (o maior salto vertical entre linhas) para
       separar as linhas superiores (j..f) das inferiores (e..a).
    4. Ajusta uma homografia usando os centros de furo como referencia.

    Raises:
        GridEstimationError: se a malha nao puder ser estimada de forma confiavel.
    """
    layout = layout or CanonicalLayout()
    holes = detect_holes(image_bgr, hole_config)
    if len(holes) < 20:
        raise GridEstimationError(
            f"Furos insuficientes para estimar a malha (detectados {len(holes)})."
        )

    xs = [h.x for h in holes]
    ys = [h.y for h in holes]
    # Estima o passo a partir do vizinho mais proximo na direcao mais densa.
    approx_pitch = _estimate_pitch(xs, ys)
    tol = approx_pitch * 0.4

    column_centers = _cluster_1d(xs, tol)
    row_centers = _cluster_1d(ys, tol)
    if len(column_centers) < 4 or len(row_centers) < 4:
        raise GridEstimationError(
            "Colunas/linhas insuficientes apos agrupamento "
            f"(colunas={len(column_centers)}, linhas={len(row_centers)})."
        )

    top_rows, bottom_rows = _split_rows_by_center_channel(row_centers, layout)
    correspondences = _build_correspondences(
        column_centers, top_rows, bottom_rows, layout
    )
    return grid_from_reference_points(correspondences, layout=layout)


def _estimate_pitch(xs: list[float], ys: list[float]) -> float:
    pitch_candidates: list[float] = []
    for centers in (sorted(xs), sorted(ys)):
        clustered = _cluster_1d(centers, tolerance=3.0)
        if len(clustered) >= 2:
            pitch_candidates.append(_median_neighbor_pitch(clustered))
    if not pitch_candidates:
        raise GridEstimationError("Nao foi possivel estimar o passo da malha.")
    # O menor passo plausivel corresponde ao espacamento real entre furos.
    return min(pitch_candidates)


def _split_rows_by_center_channel(
    row_centers: list[float],
    layout: CanonicalLayout,
) -> tuple[list[float], list[float]]:
    """Separa as linhas em superiores e inferiores pelo canal central.

    O canal central produz o maior salto vertical entre linhas consecutivas.
    """
    if len(row_centers) < 2:
        raise GridEstimationError("Linhas insuficientes para localizar o canal central.")
    diffs = np.diff(row_centers)
    split_index = int(np.argmax(diffs)) + 1
    top = row_centers[:split_index]
    bottom = row_centers[split_index:]
    # Limita a no maximo 5 linhas por grupo (j..f e e..a), mantendo as mais
    # proximas do canal central, que sao as mais confiaveis.
    max_top = len(layout.board.top_rows)
    max_bottom = len(layout.board.bottom_rows)
    top = top[-max_top:]
    bottom = bottom[:max_bottom]
    return top, bottom


def _build_correspondences(
    column_centers: list[float],
    top_row_centers: list[float],
    bottom_row_centers: list[float],
    layout: CanonicalLayout,
) -> list[tuple[Hole, Point]]:
    """Monta pares (furo, pixel) a partir dos centros de coluna/linha."""
    correspondences: list[tuple[Hole, Point]] = []
    board = layout.board
    # As linhas superiores detectadas (de cima p/ baixo) mapeiam para j..f.
    top_labels = board.top_rows[-len(top_row_centers):]
    bottom_labels = board.bottom_rows[: len(bottom_row_centers)]

    for col_index, x in enumerate(column_centers):
        column = board.min_column + col_index
        if column > board.max_column:
            break
        for y, row in zip(top_row_centers, top_labels):
            correspondences.append((Hole(column=column, row=row), Point(x, y)))
        for y, row in zip(bottom_row_centers, bottom_labels):
            correspondences.append((Hole(column=column, row=row), Point(x, y)))

    if len(correspondences) < 4:
        raise GridEstimationError("Correspondencias insuficientes para a homografia.")
    return correspondences
