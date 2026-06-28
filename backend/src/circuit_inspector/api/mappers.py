"""Conversao do dominio para os DTOs da API.

Funcoes puras, sem dependencia de I/O ou framework, faceis de testar isoladamente.
"""

from __future__ import annotations

from ..comparison.registered import RegisteredDifference, RegisteredResult
from .schemas import CompareResponse, DifferenceDTO


def difference_to_dto(difference: RegisteredDifference) -> DifferenceDTO:
    """Mapeia uma `RegisteredDifference` do dominio para o DTO publico."""
    return DifferenceDTO(
        kind=difference.kind,
        label=difference.label,
        detail=difference.detail,
        expected_box=difference.expected_box,
        actual_box=difference.actual_box,
        salience=difference.salience,
    )


def to_compare_response(
    result: RegisteredResult, test_width: int, test_height: int
) -> CompareResponse:
    """Monta a resposta da API a partir do resultado do pipeline registrado."""
    return CompareResponse(
        is_match=result.is_match,
        matched_count=result.matched_count,
        test_width=test_width,
        test_height=test_height,
        differences=[difference_to_dto(d) for d in result.differences],
    )
