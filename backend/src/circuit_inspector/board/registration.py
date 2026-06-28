"""Registro automatico foto-a-foto (alinhamento gabarito x aluno).

Em vez de calibrar a malha de cada foto manualmente, alinhamos a imagem do aluno
sobre a do gabarito estimando uma homografia por casamento de features
(SIFT, com ORB como alternativa) e RANSAC. Como a maior parte da protoboard e
identica nas duas fotos, sobram muitas correspondencias; o(s) componente(s) que
mudaram viram outliers e sao naturalmente descartados pelo RANSAC.

Vantagens sobre a calibracao manual:
- Zero cliques e sem depender da serigrafia (numeros impressos).
- Elimina a inconsistencia entre duas calibracoes manuais (a maior fonte de
  ruido), pois passa a existir um unico referencial (o do gabarito).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


class RegistrationError(RuntimeError):
    """Levantado quando nao e possivel alinhar as duas imagens de forma confiavel."""


@dataclass(frozen=True)
class RegistrationConfig:
    """Parametros do registro por features."""

    max_features: int = 5000
    ratio: float = 0.75  # teste de razao de Lowe
    ransac_reproj_threshold: float = 5.0
    min_inliers: int = 25


def _detect_and_match(
    reference_gray: np.ndarray,
    test_gray: np.ndarray,
    config: RegistrationConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Retorna pontos correspondentes (test, reference) apos o teste de razao."""
    sift = cv2.SIFT_create(nfeatures=config.max_features)
    kp_ref, des_ref = sift.detectAndCompute(reference_gray, None)
    kp_test, des_test = sift.detectAndCompute(test_gray, None)
    if des_ref is None or des_test is None or len(kp_ref) < 4 or len(kp_test) < 4:
        raise RegistrationError("Features insuficientes para o registro das imagens.")

    matcher = cv2.BFMatcher(cv2.NORM_L2)
    knn = matcher.knnMatch(des_test, des_ref, k=2)
    good = [m for m, n in knn if m.distance < config.ratio * n.distance]
    if len(good) < config.min_inliers:
        raise RegistrationError(
            f"Poucas correspondencias confiaveis ({len(good)}) para o registro."
        )

    test_pts = np.float32([kp_test[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    ref_pts = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    return test_pts, ref_pts


def estimate_registration(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    config: RegistrationConfig = RegistrationConfig(),
) -> np.ndarray:
    """Estima a homografia que leva pixels do *aluno* para o frame do *gabarito*.

    Returns:
        Matriz 3x3 `H` tal que `ponto_gabarito ~ H @ ponto_aluno`.

    Raises:
        RegistrationError: se nao houver correspondencias/inliers suficientes.
    """
    reference_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_bgr, cv2.COLOR_BGR2GRAY)

    test_pts, ref_pts = _detect_and_match(reference_gray, test_gray, config)
    homography, mask = cv2.findHomography(
        test_pts, ref_pts, cv2.RANSAC, config.ransac_reproj_threshold
    )
    if homography is None:
        raise RegistrationError("Falha ao estimar a homografia de registro.")
    inliers = int(mask.sum()) if mask is not None else 0
    if inliers < config.min_inliers:
        raise RegistrationError(
            f"Inliers insuficientes apos o RANSAC ({inliers})."
        )
    return homography


def warp_to_reference(
    test_bgr: np.ndarray,
    homography: np.ndarray,
    size: tuple[int, int],
) -> np.ndarray:
    """Deforma a imagem do aluno para o frame do gabarito (largura, altura)."""
    width, height = size
    return cv2.warpPerspective(test_bgr, homography, (width, height))


def reference_validity_mask(
    test_shape: tuple[int, int],
    homography: np.ndarray,
    size: tuple[int, int],
    erosion: int = 9,
) -> np.ndarray:
    """Mascara (no frame do gabarito) dos pixels cobertos pela foto do aluno."""
    width, height = size
    full = np.full(test_shape[:2], 255, dtype=np.uint8)
    mask = cv2.warpPerspective(full, homography, (width, height))
    if erosion > 0:
        mask = cv2.erode(mask, np.ones((erosion, erosion), np.uint8))
    return mask
