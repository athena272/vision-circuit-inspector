"""Escala caixas de diferenca quando a imagem foi reduzida antes do processamento."""

from __future__ import annotations

from ..comparison.registered import RegisteredDifference, RegisteredResult

Box = tuple[int, int, int, int]


def scale_box(box: Box | None, scale_x: float, scale_y: float) -> Box | None:
    if box is None:
        return None
    x0, y0, x1, y1 = box
    return (
        int(round(x0 * scale_x)),
        int(round(y0 * scale_y)),
        int(round(x1 * scale_x)),
        int(round(y1 * scale_y)),
    )


def scale_registered_result(
    result: RegisteredResult,
    scale_x: float,
    scale_y: float,
) -> RegisteredResult:
    """Reescala caixas do resultado para as dimensoes originais da foto do aluno."""
    if scale_x == 1.0 and scale_y == 1.0:
        return result
    scaled = tuple(
        RegisteredDifference(
            kind=d.kind,
            label=d.label,
            detail=d.detail,
            expected_box=scale_box(d.expected_box, scale_x, scale_y),
            actual_box=scale_box(d.actual_box, scale_x, scale_y),
            salience=d.salience,
        )
        for d in result.differences
    )
    return RegisteredResult(differences=scaled, matched_count=result.matched_count)
