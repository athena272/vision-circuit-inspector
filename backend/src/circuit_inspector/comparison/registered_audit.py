"""Auditoria visual do pipeline registrado (6 etapas do diagrama de blocos)."""

from __future__ import annotations

import gc
import time
from collections.abc import Iterator
from dataclasses import dataclass

import cv2
import numpy as np

from ..board.registration import RegistrationConfig
from ..config import DEFAULT_CONFIG, OccupancyConfig
from ..io.image_loader import encode_png_base64
from .registered import (
    Cluster,
    RegisteredDifference,
    RegisteredResult,
    run_registered_pipeline,
)

TOTAL_STEPS = 6
_AUDIT_PREVIEW_MAX_SIDE = 720


@dataclass(frozen=True)
class PipelineStep:
    id: int
    title: str
    description: str
    image_data_url: str
    duration_ms: int


@dataclass(frozen=True)
class RegisteredAudit:
    steps: tuple[PipelineStep, ...]
    result: RegisteredResult
    all_differences: tuple[RegisteredDifference, ...]


def iter_registered_audit(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    registration_config: RegistrationConfig = RegistrationConfig(),
    occupancy_config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> Iterator[PipelineStep | RegisteredAudit]:
    """Gera cada etapa conforme concluida e, por ultimo, o audit completo."""
    steps: list[PipelineStep] = []
    start = time.perf_counter()

    def make_step(step_id: int, title: str, description: str, image: np.ndarray) -> PipelineStep:
        return PipelineStep(
            id=step_id,
            title=title,
            description=description,
            image_data_url=encode_png_base64(image),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )

    step1 = make_step(
        1,
        "Imagem",
        (
            "Recebemos as duas fotos: gabarito (esquerda) e circuito do aluno "
            "(direita). A partir daqui o sistema compara o mesmo circuito."
        ),
        _compose_input_pair(reference_bgr, test_bgr),
    )
    steps.append(step1)
    yield step1

    state = run_registered_pipeline(
        reference_bgr, test_bgr, registration_config, occupancy_config
    )
    preview = _preview_factor(state.reference_bgr.shape[:2], _AUDIT_PREVIEW_MAX_SIDE)

    for step_id, title, description, image in (
        (
            2,
            "Alinhamento",
            (
                "Alinhamos a foto do aluno sobre o gabarito (SIFT + homografia). "
                "Assim, cada pixel representa o mesmo ponto fisico nas duas fotos."
            ),
            _compose_alignment(
                _preview_bgr(state.reference_bgr, preview),
                _preview_bgr(state.test_aligned, preview),
            ),
        ),
        (
            3,
            "Subtracao",
            (
                "Subtraimos as mascaras de ocupacao: vermelho = sumiu no aluno, "
                "verde = apareceu no aluno. Sao os candidatos a divergencia."
            ),
            _compose_subtraction(
                _preview_mask(state.only_ref, preview),
                _preview_mask(state.only_test, preview),
            ),
        ),
        (
            4,
            "Filtro da media",
            (
                "Suavizamos o canal de saturacao (filtro gaussiano) para reduzir "
                "ruido da camera e destacar componentes coloridos sobre o fundo."
            ),
            _compose_mean_filter(
                _preview_mask(state.sat_ref_blur, preview),
                _preview_mask(state.sat_test_blur, preview),
            ),
        ),
        (
            5,
            "Binarizacao",
            (
                "Convertemos saturacao e corpos escuros (botao/capacitor) em mascaras "
                "binarias: branco = regiao ocupada, preto = fundo ou furo vazio."
            ),
            _compose_binarization(
                _preview_mask(state.fg_ref, preview),
                _preview_mask(state.fg_test, preview),
                _preview_mask(state.dark_fg_ref, preview),
                _preview_mask(state.dark_fg_test, preview),
            ),
        ),
        (
            6,
            "Extracao de caracteristicas",
            (
                "Agrupamos as regioes alteradas em clusters e rotulamos pela cor "
                "dominante. O par mais saliente vira a divergencia principal."
            ),
            _compose_features(
                _preview_bgr(state.test_aligned, preview),
                _preview_clusters(state.ref_clusters, preview),
                _preview_clusters(state.test_clusters, preview),
            ),
        ),
    ):
        step = make_step(step_id, title, description, image)
        steps.append(step)
        yield step

    pipeline_result = state.result
    del state
    gc.collect()

    audit = RegisteredAudit(
        steps=tuple(steps),
        result=pipeline_result,
        all_differences=tuple(pipeline_result.differences),
    )
    yield audit


def compare_registered_with_audit(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    registration_config: RegistrationConfig = RegistrationConfig(),
    occupancy_config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> RegisteredAudit:
    """Executa o pipeline e retorna o audit completo (sem streaming)."""
    audit: RegisteredAudit | None = None
    for item in iter_registered_audit(
        reference_bgr, test_bgr, registration_config, occupancy_config
    ):
        if isinstance(item, RegisteredAudit):
            audit = item
    assert audit is not None
    return audit


def _compose_input_pair(reference_bgr: np.ndarray, test_bgr: np.ndarray) -> np.ndarray:
    ref = _resize_to_height(reference_bgr, 480)
    test = _resize_to_height(test_bgr, 480)
    gap = np.full((ref.shape[0], 8, 3), 200, np.uint8)
    return np.hstack([ref, gap, test])


def _compose_alignment(reference_bgr: np.ndarray, aligned_bgr: np.ndarray) -> np.ndarray:
    return cv2.addWeighted(reference_bgr, 0.5, aligned_bgr, 0.5, 0)


def _compose_subtraction(only_ref: np.ndarray, only_test: np.ndarray) -> np.ndarray:
    h, w = only_ref.shape[:2]
    canvas = np.zeros((h, w, 3), np.uint8)
    canvas[only_ref > 0] = (0, 0, 255)
    canvas[only_test > 0] = (0, 255, 0)
    both = cv2.bitwise_and(only_ref, only_test)
    canvas[both > 0] = (0, 255, 255)
    return canvas


def _compose_mean_filter(sat_ref: np.ndarray, sat_test: np.ndarray) -> np.ndarray:
    ref_vis = cv2.applyColorMap(sat_ref, cv2.COLORMAP_VIRIDIS)
    test_vis = cv2.applyColorMap(sat_test, cv2.COLORMAP_VIRIDIS)
    gap = np.full((sat_ref.shape[0], 8, 3), 200, np.uint8)
    return np.hstack([ref_vis, gap, test_vis])


def _compose_binarization(
    fg_ref: np.ndarray,
    fg_test: np.ndarray,
    dark_ref: np.ndarray | None = None,
    dark_test: np.ndarray | None = None,
) -> np.ndarray:
    ref_bgr = cv2.cvtColor(fg_ref, cv2.COLOR_GRAY2BGR)
    test_bgr = cv2.cvtColor(fg_test, cv2.COLOR_GRAY2BGR)
    if dark_ref is not None and np.any(dark_ref):
        ref_bgr[dark_ref > 0] = (180, 80, 40)
    if dark_test is not None and np.any(dark_test):
        test_bgr[dark_test > 0] = (180, 80, 40)
    gap = np.full((fg_ref.shape[0], 8, 3), 200, np.uint8)
    return np.hstack([ref_bgr, gap, test_bgr])


def _compose_features(
    base_bgr: np.ndarray,
    ref_clusters: tuple[Cluster, ...],
    test_clusters: tuple[Cluster, ...],
) -> np.ndarray:
    canvas = base_bgr.copy()
    for cluster in ref_clusters:
        x0, y0, x1, y1 = cluster.bbox
        cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 200, 0), 2)
        cv2.putText(
            canvas,
            cluster.label[:12],
            (x0, max(12, y0 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 200, 0),
            1,
            cv2.LINE_AA,
        )
    for cluster in test_clusters:
        x0, y0, x1, y1 = cluster.bbox
        cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 0, 220), 2)
    return canvas


def _resize_to_height(image: np.ndarray, target_h: int) -> np.ndarray:
    h, w = image.shape[:2]
    if h <= target_h:
        return image
    scale = target_h / h
    return cv2.resize(image, (int(w * scale), target_h), interpolation=cv2.INTER_AREA)


def _preview_factor(shape: tuple[int, int], max_side: int) -> float:
    height, width = shape
    longest = max(height, width)
    if longest <= max_side:
        return 1.0
    return max_side / longest


def _preview_bgr(image: np.ndarray, factor: float) -> np.ndarray:
    if factor >= 1.0:
        return image
    height, width = image.shape[:2]
    new_w = max(1, int(width * factor))
    new_h = max(1, int(height * factor))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _preview_mask(mask: np.ndarray, factor: float) -> np.ndarray:
    if factor >= 1.0:
        return mask
    height, width = mask.shape[:2]
    new_w = max(1, int(width * factor))
    new_h = max(1, int(height * factor))
    return cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)


def _preview_clusters(clusters: tuple[Cluster, ...], factor: float) -> tuple[Cluster, ...]:
    if factor >= 1.0:
        return clusters
    scaled: list[Cluster] = []
    for cluster in clusters:
        x0, y0, x1, y1 = cluster.bbox
        cx, cy = cluster.centroid
        scaled.append(
            Cluster(
                area=cluster.area,
                centroid=(cx * factor, cy * factor),
                bbox=(
                    int(x0 * factor),
                    int(y0 * factor),
                    int(x1 * factor),
                    int(y1 * factor),
                ),
                label=cluster.label,
            )
        )
    return tuple(scaled)
