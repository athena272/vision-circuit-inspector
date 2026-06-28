"""Deteccao da malha de furos da protoboard.

Usa um blob detector do OpenCV para localizar os furos (pequenos pontos
escuros, aproximadamente quadrados/circulares, dispostos numa malha regular).
O resultado e uma lista de centros em pixels, consumida pelo `rectifier` para
estimar a geometria do board.

Esta etapa e sensivel a iluminacao/foco; por isso os parametros vivem em
`HoleDetectionConfig` e ha um visualizador de debug para inspecao.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..config import HoleDetectionConfig
from ..models import Point


def detect_holes(
    image_bgr: np.ndarray,
    config: HoleDetectionConfig | None = None,
) -> list[Point]:
    """Detecta os centros dos furos da protoboard.

    Args:
        image_bgr: imagem no formato BGR.
        config: parametros do detector (usa o default se omitido).

    Returns:
        Lista de centros (em pixels) dos furos detectados.
    """
    config = config or HoleDetectionConfig()
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Equaliza o contraste local para tolerar iluminacao irregular.
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    params = cv2.SimpleBlobDetector_Params()
    params.filterByColor = True
    params.blobColor = 0  # furos sao escuros
    params.filterByArea = True
    params.minArea = config.min_area
    params.maxArea = config.max_area
    params.filterByCircularity = True
    params.minCircularity = config.min_circularity
    params.filterByInertia = True
    params.minInertiaRatio = config.min_inertia_ratio
    params.filterByConvexity = False

    detector = cv2.SimpleBlobDetector_create(params)
    keypoints = detector.detect(gray)
    return [Point(x=float(kp.pt[0]), y=float(kp.pt[1])) for kp in keypoints]


def draw_holes(image_bgr: np.ndarray, holes: list[Point]) -> np.ndarray:
    """Desenha os furos detectados sobre uma copia da imagem (debug)."""
    canvas = image_bgr.copy()
    for hole in holes:
        cv2.circle(canvas, hole.as_int_tuple(), 4, (0, 255, 0), 1, cv2.LINE_AA)
    return canvas
