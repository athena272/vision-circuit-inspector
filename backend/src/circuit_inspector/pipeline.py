"""Orquestracao do pipeline de inspecao ponta a ponta.

Junta as etapas (retificacao/malha, deteccao, mapeamento, comparacao e
anotacao) em uma API simples: dada uma imagem de gabarito e uma de aluno,
produz o resultado da comparacao e a imagem anotada.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .board.grid_mapper import BoardGrid, CanonicalLayout
from .board.rectifier import GridCalibration, build_grid_from_calibration, estimate_grid
from .board.registration import RegistrationConfig
from .comparison.comparator import compare_placements
from .comparison.registered import RegisteredResult, compare_registered
from .comparison.selection import reduce_to_single
from .comparison.structural import compare_structural
from .config import DEFAULT_CONFIG, InspectorConfig
from .detection.registry import DetectorRegistry
from .io.image_loader import load_bgr
from .mapping import map_components_to_holes
from .models import ComparisonResult, Placement
from .visualization.annotator import annotate_differences, annotate_registered


@dataclass(frozen=True)
class InspectionResult:
    """Resultado completo de uma inspecao."""

    comparison: ComparisonResult
    annotated_test_image: np.ndarray
    reference_placement: Placement
    test_placement: Placement


def build_grid(
    image_bgr: np.ndarray,
    config: InspectorConfig = DEFAULT_CONFIG,
    calibration: GridCalibration | None = None,
) -> BoardGrid:
    """Constroi o `BoardGrid` da imagem (calibracao assistida ou automatica)."""
    layout = CanonicalLayout(board=config.board)
    if calibration is not None:
        return build_grid_from_calibration(calibration, layout)
    return estimate_grid(image_bgr, layout, config.holes)


def inspect_images(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    config: InspectorConfig = DEFAULT_CONFIG,
    reference_calibration: GridCalibration | None = None,
    test_calibration: GridCalibration | None = None,
    single_error: bool = True,
) -> InspectionResult:
    """Executa o pipeline sobre duas imagens ja carregadas (BGR).

    `single_error=True` (padrao) anota apenas a divergencia mais saliente -
    adequado ao caso de "um erro por placa" e mantem a imagem limpa. O campo
    `comparison` sempre carrega o resultado completo.
    """
    registry = DetectorRegistry.default(config)

    reference_grid = build_grid(reference_bgr, config, reference_calibration)
    test_grid = build_grid(test_bgr, config, test_calibration)

    reference_placement = map_components_to_holes(
        registry.detect_all(reference_bgr), reference_grid, config.matching
    )
    test_placement = map_components_to_holes(
        registry.detect_all(test_bgr), test_grid, config.matching
    )

    comparison = compare_placements(reference_placement, test_placement)
    annotated_result = reduce_to_single(comparison) if single_error else comparison
    annotated = annotate_differences(test_bgr, test_grid, annotated_result)

    return InspectionResult(
        comparison=comparison,
        annotated_test_image=annotated,
        reference_placement=reference_placement,
        test_placement=test_placement,
    )


def inspect(
    reference_path: str | Path,
    test_path: str | Path,
    config: InspectorConfig = DEFAULT_CONFIG,
    reference_calibration: GridCalibration | None = None,
    test_calibration: GridCalibration | None = None,
    single_error: bool = True,
) -> InspectionResult:
    """Carrega as imagens dos caminhos informados e executa o pipeline."""
    return inspect_images(
        load_bgr(reference_path),
        load_bgr(test_path),
        config=config,
        reference_calibration=reference_calibration,
        test_calibration=test_calibration,
        single_error=single_error,
    )


def inspect_structural_images(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    config: InspectorConfig = DEFAULT_CONFIG,
    reference_calibration: GridCalibration | None = None,
    test_calibration: GridCalibration | None = None,
    single_error: bool = True,
) -> InspectionResult:
    """Pipeline estrutural (tipo-agnostico) sobre duas imagens ja carregadas.

    Em vez de classificar tipos de componente (fragil em fotos reais), compara a
    *ocupacao* de cada furo entre gabarito e aluno. Recomendado para fotos reais.
    """
    reference_grid = build_grid(reference_bgr, config, reference_calibration)
    test_grid = build_grid(test_bgr, config, test_calibration)

    comparison = compare_structural(
        reference_bgr, test_bgr, reference_grid, test_grid, config.occupancy
    )
    annotated_result = reduce_to_single(comparison) if single_error else comparison
    annotated = annotate_differences(test_bgr, test_grid, annotated_result)

    return InspectionResult(
        comparison=comparison,
        annotated_test_image=annotated,
        reference_placement=Placement(),
        test_placement=Placement(),
    )


def inspect_structural(
    reference_path: str | Path,
    test_path: str | Path,
    config: InspectorConfig = DEFAULT_CONFIG,
    reference_calibration: GridCalibration | None = None,
    test_calibration: GridCalibration | None = None,
    single_error: bool = True,
) -> InspectionResult:
    """Carrega as imagens e executa o pipeline estrutural (ocupacao de furo)."""
    return inspect_structural_images(
        load_bgr(reference_path),
        load_bgr(test_path),
        config=config,
        reference_calibration=reference_calibration,
        test_calibration=test_calibration,
        single_error=single_error,
    )


@dataclass(frozen=True)
class RegisteredInspection:
    """Resultado do modo de registro automatico (sem malha canonica)."""

    result: RegisteredResult
    annotated_test_image: np.ndarray


def inspect_registered_images(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    config: InspectorConfig = DEFAULT_CONFIG,
    registration_config: RegistrationConfig = RegistrationConfig(),
    single_error: bool = True,
) -> RegisteredInspection:
    """Pipeline por registro automatico: alinha aluno->gabarito e compara ocupacao.

    Nao requer calibracao nem malha; e o modo recomendado para fotos reais.
    """
    result = compare_registered(
        reference_bgr, test_bgr, registration_config, config.occupancy
    )
    annotated = annotate_registered(test_bgr, result, single_error)
    return RegisteredInspection(result=result, annotated_test_image=annotated)


def inspect_registered(
    reference_path: str | Path,
    test_path: str | Path,
    config: InspectorConfig = DEFAULT_CONFIG,
    registration_config: RegistrationConfig = RegistrationConfig(),
    single_error: bool = True,
) -> RegisteredInspection:
    """Carrega as imagens e executa o pipeline por registro automatico."""
    return inspect_registered_images(
        load_bgr(reference_path),
        load_bgr(test_path),
        config=config,
        registration_config=registration_config,
        single_error=single_error,
    )
