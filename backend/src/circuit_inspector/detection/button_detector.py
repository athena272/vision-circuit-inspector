"""Deteccao de push button (chave tatil).

Aparece como um corpo escuro aproximadamente quadrado. E separado do capacitor
(tambem escuro) pela circularidade menor (quadrado, nao circulo) e do fio preto
pelo formato compacto (aspecto proximo de 1).

Nota de escopo: representado por 2 terminais (aproximados pelos cantos
inferiores do bounding box); a chave real tem 4 pinos.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..config import ColorProfiles, ComponentDetectionConfig
from ..models import Component, ComponentKind, Terminal
from .base import (
    ComponentDetector,
    aspect_ratio,
    bbox_bottom_terminals,
    circularity,
    color_mask,
    find_contours,
)


class ButtonDetector(ComponentDetector):
    """Detecta push buttons pelo corpo escuro e quadrado."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        cfg = self._config
        mask = color_mask(image_bgr, self._colors.dark_body)
        components: list[Component] = []
        for contour in find_contours(mask, cfg.button_min_area):
            area = cv2.contourArea(contour)
            if area > cfg.button_max_area:
                continue
            circ = circularity(contour)
            if not (cfg.button_min_circularity <= circ <= cfg.button_max_circularity):
                continue
            if aspect_ratio(contour) > cfg.button_max_aspect:
                continue
            start, end = bbox_bottom_terminals(contour)
            components.append(
                Component(
                    kind=ComponentKind.BUTTON,
                    label="button",
                    terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                )
            )
        return components
