"""Testes da conversao dominio -> DTO da API (funcoes puras)."""

from __future__ import annotations

from circuit_inspector.api.mappers import difference_to_dto, to_compare_response
from circuit_inspector.comparison.registered import (
    RegisteredDifference,
    RegisteredResult,
)


def _difference(**overrides) -> RegisteredDifference:
    base = dict(
        kind="mismatched",
        label="componente azul",
        detail="componente azul: mudou de posicao.",
        expected_box=(10, 20, 30, 40),
        actual_box=(50, 60, 70, 80),
        salience=123.0,
    )
    base.update(overrides)
    return RegisteredDifference(**base)


def test_difference_to_dto_preserves_fields() -> None:
    dto = difference_to_dto(_difference())

    assert dto.kind == "mismatched"
    assert dto.label == "componente azul"
    assert dto.expected_box == (10, 20, 30, 40)
    assert dto.actual_box == (50, 60, 70, 80)
    assert dto.salience == 123.0


def test_difference_to_dto_keeps_optional_boxes_none() -> None:
    dto = difference_to_dto(_difference(kind="missing", actual_box=None))

    assert dto.actual_box is None
    assert dto.expected_box == (10, 20, 30, 40)


def test_to_compare_response_maps_result_and_dimensions() -> None:
    result = RegisteredResult(differences=(_difference(),), matched_count=4)

    response = to_compare_response(result, test_width=640, test_height=480)

    assert response.is_match is False
    assert response.matched_count == 4
    assert response.test_width == 640
    assert response.test_height == 480
    assert len(response.differences) == 1
    assert response.differences[0].kind == "mismatched"
    assert response.primary_difference is not None
    assert response.single_error_mode is True


def test_to_compare_response_all_mode_returns_everything() -> None:
    result = RegisteredResult(
        differences=(
            _difference(salience=500.0),
            _difference(kind="extra", label="b", salience=50.0),
        ),
        matched_count=1,
    )
    response = to_compare_response(result, 100, 100, single_error=False)
    assert len(response.differences) == 2
    assert response.single_error_mode is False


def test_to_compare_response_is_match_when_no_differences() -> None:
    result = RegisteredResult(differences=(), matched_count=2)

    response = to_compare_response(result, test_width=100, test_height=100)

    assert response.is_match is True
    assert response.differences == []
