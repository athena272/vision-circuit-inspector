"""Interface comum e utilitarios de visao para os detectores de componente.

Cada detector implementa `ComponentDetector` (padrao Strategy). As funcoes
auxiliares concentram operacoes de OpenCV reutilizadas pelos detectores
(mascara por cor, contornos, geometria de blobs), evitando duplicacao (DRY).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import cv2
import numpy as np

from ..config import HsvRange
from ..models import Component, Point


class ComponentDetector(ABC):
    """Detecta componentes de um tipo especifico em uma imagem BGR.

    Retorna componentes com terminais em coordenadas de pixel; o mapeamento
    para furos e responsabilidade de uma etapa posterior (separacao de
    responsabilidades).
    """

    @abstractmethod
    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        """Detecta e retorna os componentes encontrados."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Utilitarios de segmentacao e geometria
# ---------------------------------------------------------------------------


def color_mask(image_bgr: np.ndarray, hsv_range: HsvRange) -> np.ndarray:
    """Gera uma mascara binaria para a faixa HSV (tratando wrap do vermelho)."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv, np.array(hsv_range.lower), np.array(hsv_range.upper)
    )
    if hsv_range.is_split:
        mask2 = cv2.inRange(
            hsv,
            np.array(hsv_range.extra_lower),
            np.array(hsv_range.extra_upper),
        )
        mask = cv2.bitwise_or(mask, mask2)
    # Fecha pequenos buracos e remove ruido.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def find_contours(mask: np.ndarray, min_area: float) -> list[np.ndarray]:
    """Retorna contornos externos com area >= `min_area`."""
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return [c for c in contours if cv2.contourArea(c) >= min_area]


def aspect_ratio(contour: np.ndarray) -> float:
    """Razao lado_maior/lado_menor do retangulo de area minima."""
    (_, (w, h), _) = cv2.minAreaRect(contour)
    if min(w, h) < 1e-6:
        return float("inf")
    return float(max(w, h) / min(w, h))


def circularity(contour: np.ndarray) -> float:
    """Circularidade 4*pi*area/perimetro^2 (1.0 = circulo perfeito)."""
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    if perimeter < 1e-6:
        return 0.0
    return float(4.0 * np.pi * area / (perimeter * perimeter))


def centroid(contour: np.ndarray) -> Point:
    moments = cv2.moments(contour)
    if abs(moments["m00"]) < 1e-6:
        pts = contour.reshape(-1, 2).mean(axis=0)
        return Point(float(pts[0]), float(pts[1]))
    return Point(
        x=float(moments["m10"] / moments["m00"]),
        y=float(moments["m01"] / moments["m00"]),
    )


def principal_axis_endpoints(contour: np.ndarray) -> tuple[Point, Point]:
    """Endpoints de um blob alongado, ao longo do seu eixo principal (PCA)."""
    pts = contour.reshape(-1, 2).astype(np.float64)
    mean = pts.mean(axis=0)
    centered = pts - mean
    cov = np.cov(centered, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    direction = eigvecs[:, int(np.argmax(eigvals))]
    projections = centered @ direction
    p_min = pts[int(np.argmin(projections))]
    p_max = pts[int(np.argmax(projections))]
    return Point(float(p_min[0]), float(p_min[1])), Point(
        float(p_max[0]), float(p_max[1])
    )


def elongated_contours(
    mask: np.ndarray, min_area: float, min_aspect: float
) -> list[np.ndarray]:
    """Contornos com area >= `min_area` e formato alongado (>= `min_aspect`)."""
    return [
        c
        for c in find_contours(mask, min_area)
        if aspect_ratio(c) >= min_aspect
    ]


def compact_contours(
    mask: np.ndarray,
    min_area: float,
    max_area: float,
    min_circularity: float,
) -> list[np.ndarray]:
    """Contornos compactos (aproximadamente circulares) dentro da faixa de area."""
    result: list[np.ndarray] = []
    for c in find_contours(mask, min_area):
        if cv2.contourArea(c) > max_area:
            continue
        if circularity(c) < min_circularity:
            continue
        result.append(c)
    return result


def bbox_bottom_terminals(contour: np.ndarray) -> tuple[Point, Point]:
    """Aproxima os dois terminais (pernas) pelos cantos inferiores do bbox.

    Adequado para componentes compactos com pernas que descem (LED, LDR) em
    fotos top-down.
    """
    x, y, w, h = cv2.boundingRect(contour)
    bottom = y + h
    return Point(float(x), float(bottom)), Point(float(x + w), float(bottom))
