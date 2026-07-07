"""Conversao do dominio para os DTOs da API."""

from __future__ import annotations

from ..comparison.registered import RegisteredDifference, RegisteredResult
from ..comparison.registered_audit import PipelineStep, RegisteredAudit
from ..comparison.selection import reduce_registered_to_single
from .schemas import CompareResponse, DifferenceDTO, PipelineStepDTO


def difference_to_dto(difference: RegisteredDifference) -> DifferenceDTO:
    return DifferenceDTO(
        kind=difference.kind,
        label=difference.label,
        detail=difference.detail,
        expected_box=difference.expected_box,
        actual_box=difference.actual_box,
        salience=difference.salience,
    )


def pipeline_step_to_dto(step: PipelineStep) -> PipelineStepDTO:
    return PipelineStepDTO(
        id=step.id,
        title=step.title,
        description=step.description,
        image_data_url=step.image_data_url,
        duration_ms=step.duration_ms,
    )


def to_compare_response(
    result: RegisteredResult,
    test_width: int,
    test_height: int,
    *,
    single_error: bool = True,
    audit: RegisteredAudit | None = None,
) -> CompareResponse:
    """Monta a resposta da API com modo um-erro-por-placa por padrao."""
    full = result
    if audit is not None:
        full = RegisteredResult(
            differences=audit.all_differences,
            matched_count=audit.result.matched_count,
        )

    display = full if not single_error else reduce_registered_to_single(full)
    primary = display.differences[0] if display.differences else None

    return CompareResponse(
        is_match=display.is_match,
        matched_count=full.matched_count,
        test_width=test_width,
        test_height=test_height,
        single_error_mode=single_error,
        primary_difference=difference_to_dto(primary) if primary else None,
        differences=[difference_to_dto(d) for d in display.differences],
        all_differences=[difference_to_dto(d) for d in full.differences],
        audit=[pipeline_step_to_dto(s) for s in audit.steps] if audit else [],
    )
