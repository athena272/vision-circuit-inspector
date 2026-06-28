"""Testes de integracao do pipeline ponta a ponta."""

from __future__ import annotations

from pathlib import Path

import pytest

from circuit_inspector.models import ComparisonResult, ComponentKind
from circuit_inspector.pipeline import inspect, inspect_images

from tests.fixtures.synthetic_board import (
    ComponentSpec,
    build_board,
    default_circuit,
)


def test_synthetic_reference_vs_moved_component() -> None:
    """Gabarito x aluno com um unico resistor movido: deve acusar 1 divergencia."""
    reference_specs = default_circuit()
    reference = build_board(reference_specs)

    # Aluno: identico, exceto o resistor que vai de c8-c10 para c8-c11.
    wrong_specs = [
        spec
        if spec.kind != ComponentKind.RESISTOR
        else ComponentSpec(
            spec.kind, spec.label, spec.hole_a, spec.hole_a.__class__(11, row="c")
        )
        for spec in reference_specs
    ]
    wrong = build_board(wrong_specs)

    result = inspect_images(reference.image, wrong.image)

    comparison = result.comparison
    assert comparison.is_match is False
    assert len(comparison.matched) == 4  # 3 fios + 1 LED
    assert len(comparison.mismatched) == 1
    assert len(comparison.missing) == 0
    assert len(comparison.extra) == 0
    assert "resistor" in comparison.mismatched[0].detail
    # A imagem anotada preserva as dimensoes da imagem do aluno.
    assert result.annotated_test_image.shape == wrong.image.shape


def test_synthetic_identical_boards_match() -> None:
    reference = build_board(default_circuit())
    other = build_board(default_circuit())
    result = inspect_images(reference.image, other.image)
    assert result.comparison.is_match is True


@pytest.mark.integration
def test_real_images_smoke_runs_end_to_end() -> None:
    """Caracterizacao: o pipeline roda em fotos reais sem quebrar."""
    assets = Path(__file__).resolve().parents[2] / "assets"
    reference = assets / "sample_full_a.png"
    test = assets / "sample_full_b.png"
    if not reference.exists() or not test.exists():
        pytest.skip("Imagens de exemplo nao disponiveis.")

    result = inspect(reference, test)

    assert isinstance(result.comparison, ComparisonResult)
    loaded_shape = result.annotated_test_image.shape
    assert len(loaded_shape) == 3 and loaded_shape[2] == 3
