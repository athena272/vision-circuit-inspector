"""Contratos (DTOs) da API HTTP.

Modelos Pydantic que definem o formato de resposta publico, isolando o resto do
sistema das estruturas internas do dominio (`RegisteredResult` etc.).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Caixa em pixels da imagem do aluno: (x0, y0, x1, y1).
BoxDTO = tuple[int, int, int, int]


class DifferenceDTO(BaseModel):
    """Uma diferenca localizada entre gabarito e aluno."""

    kind: str = Field(description="'mismatched' | 'missing' | 'extra'.")
    label: str = Field(description="Rotulo da regiao (ex.: 'componente azul').")
    detail: str = Field(description="Descricao legivel da divergencia.")
    expected_box: BoxDTO | None = Field(
        default=None, description="Posicao no gabarito (verde), se houver."
    )
    actual_box: BoxDTO | None = Field(
        default=None, description="Posicao no aluno (vermelho), se houver."
    )
    salience: float = Field(description="Quanto maior, mais relevante a divergencia.")


class CompareResponse(BaseModel):
    """Resultado da comparacao por registro automatico."""

    is_match: bool = Field(description="True quando nenhuma divergencia foi detectada.")
    matched_count: int = Field(description="Componentes presentes em ambas as fotos.")
    test_width: int = Field(description="Largura (px) da imagem do aluno.")
    test_height: int = Field(description="Altura (px) da imagem do aluno.")
    differences: list[DifferenceDTO] = Field(
        default_factory=list,
        description="Divergencias ordenadas da mais para a menos saliente.",
    )


class HealthResponse(BaseModel):
    """Resposta do healthcheck."""

    status: str = "ok"
