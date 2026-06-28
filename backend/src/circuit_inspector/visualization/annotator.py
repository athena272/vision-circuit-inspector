"""Anotacao visual do resultado da comparacao.

Desenha sobre a imagem do aluno:
- caixa vermelha onde um componente esta no lugar errado ou sobrando;
- caixa verde na posicao esperada (gabarito) para divergencias de posicao e
  componentes faltando;
- uma linha ligando a posicao errada a esperada, nos casos de troca de furo.

Como ambas as imagens sao mapeadas para o mesmo frame canonico, a posicao
esperada (furos do gabarito) e projetada na imagem do aluno via `BoardGrid`.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..board.grid_mapper import BoardGrid
from ..comparison.registered import RegisteredDifference, RegisteredResult
from ..models import ComparisonResult, Component, Point

COLOR_WRONG = (0, 0, 255)  # vermelho (BGR)
COLOR_EXPECTED = (0, 170, 0)  # verde
COLOR_LINK = (0, 140, 255)  # laranja
_BOX_PADDING = 16


def _actual_points(component: Component) -> list[Point]:
    return [t.pixel for t in component.terminals]


def _expected_points(component: Component, grid: BoardGrid) -> list[Point]:
    return [grid.hole_to_pixel(hole) for hole in component.hole_set]


def _bounding_box(points: list[Point], padding: int) -> tuple[int, int, int, int]:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return (
        int(min(xs)) - padding,
        int(min(ys)) - padding,
        int(max(xs)) + padding,
        int(max(ys)) + padding,
    )


def _centroid(points: list[Point]) -> tuple[int, int]:
    n = len(points)
    return (int(sum(p.x for p in points) / n), int(sum(p.y for p in points) / n))


def _draw_box(
    image: np.ndarray,
    points: list[Point],
    color: tuple[int, int, int],
    label: str,
    label_below: bool = False,
) -> None:
    x0, y0, x1, y1 = _bounding_box(points, _BOX_PADDING)
    cv2.rectangle(image, (x0, y0), (x1, y1), color, 2, cv2.LINE_AA)
    text_y = (y1 + 16) if label_below else max(12, y0 - 6)
    cv2.putText(
        image, label, (x0, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA
    )


def annotate_differences(
    image_bgr: np.ndarray,
    grid: BoardGrid,
    result: ComparisonResult,
) -> np.ndarray:
    """Retorna uma copia da imagem do aluno com as divergencias destacadas."""
    canvas = image_bgr.copy()

    for diff in result.mismatched:
        assert diff.reference is not None and diff.test is not None
        actual = _actual_points(diff.test)
        expected = _expected_points(diff.reference, grid)
        _draw_box(canvas, actual, COLOR_WRONG, f"{diff.test.label} (errado)")
        _draw_box(canvas, expected, COLOR_EXPECTED, "esperado", label_below=True)
        cv2.line(
            canvas, _centroid(actual), _centroid(expected), COLOR_LINK, 1, cv2.LINE_AA
        )

    for diff in result.missing:
        assert diff.reference is not None
        expected = _expected_points(diff.reference, grid)
        _draw_box(canvas, expected, COLOR_EXPECTED, f"{diff.reference.label} (faltando)")

    for diff in result.extra:
        assert diff.test is not None
        actual = _actual_points(diff.test)
        _draw_box(canvas, actual, COLOR_WRONG, f"{diff.test.label} (sobrando)")

    return canvas


def _draw_rect(
    image: np.ndarray,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    label: str,
    label_below: bool = False,
) -> tuple[int, int]:
    x0, y0, x1, y1 = box
    cv2.rectangle(image, (x0, y0), (x1, y1), color, 2, cv2.LINE_AA)
    text_y = (y1 + 16) if label_below else max(12, y0 - 6)
    cv2.putText(
        image, label, (x0, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA
    )
    return ((x0 + x1) // 2, (y0 + y1) // 2)


def annotate_registered(
    image_bgr: np.ndarray,
    result: RegisteredResult,
    single_error: bool = True,
) -> np.ndarray:
    """Anota a foto do aluno com as diferencas do modo de registro automatico."""
    canvas = image_bgr.copy()
    diffs = result.differences[:1] if single_error else result.differences
    for diff in diffs:
        _annotate_one(canvas, diff)
    return canvas


def _annotate_one(canvas: np.ndarray, diff: RegisteredDifference) -> None:
    actual_center = expected_center = None
    if diff.actual_box is not None:
        suffix = "errado" if diff.kind == "mismatched" else "sobrando"
        actual_center = _draw_rect(
            canvas, diff.actual_box, COLOR_WRONG, f"{diff.label} ({suffix})"
        )
    if diff.expected_box is not None:
        label = "esperado" if diff.kind == "mismatched" else f"{diff.label} (faltando)"
        expected_center = _draw_rect(
            canvas, diff.expected_box, COLOR_EXPECTED, label, label_below=True
        )
    if actual_center is not None and expected_center is not None:
        cv2.line(canvas, actual_center, expected_center, COLOR_LINK, 1, cv2.LINE_AA)
