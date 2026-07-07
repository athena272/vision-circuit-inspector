"""Contratos (DTOs) da API HTTP."""

from __future__ import annotations

from pydantic import BaseModel, Field

BoxDTO = tuple[int, int, int, int]


class DifferenceDTO(BaseModel):
    kind: str
    label: str
    detail: str
    expected_box: BoxDTO | None = None
    actual_box: BoxDTO | None = None
    salience: float


class PipelineStepDTO(BaseModel):
    id: int
    title: str
    description: str
    image_data_url: str
    duration_ms: int


class CompareResponse(BaseModel):
    is_match: bool
    matched_count: int
    test_width: int
    test_height: int
    single_error_mode: bool = True
    primary_difference: DifferenceDTO | None = None
    differences: list[DifferenceDTO] = Field(default_factory=list)
    all_differences: list[DifferenceDTO] = Field(
        default_factory=list,
        description="Todas as divergencias detectadas (antes do filtro um-erro).",
    )
    audit: list[PipelineStepDTO] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
