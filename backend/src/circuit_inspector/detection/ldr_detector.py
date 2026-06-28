"""Deteccao de LDR (foto-resistor).

O LDR aparece como um disco metalico acinzentado (baixa saturacao), compacto e
aproximadamente circular. Os terminais sao aproximados pelos cantos inferiores
do bounding box.
"""

from __future__ import annotations

import numpy as np

from ..config import ColorProfiles, ComponentDetectionConfig
from ..models import Component, ComponentKind, Terminal
from .base import (
    ComponentDetector,
    bbox_bottom_terminals,
    color_mask,
    compact_contours,
)


class LdrDetector(ComponentDetector):
    """Detecta LDRs pelo corpo cinza compacto."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        mask = color_mask(image_bgr, self._colors.ldr_body)
        contours = compact_contours(
            mask,
            self._config.ldr_min_area,
            self._config.ldr_max_area,
            self._config.ldr_min_circularity,
        )
        components: list[Component] = []
        for contour in contours:
            start, end = bbox_bottom_terminals(contour)
            components.append(
                Component(
                    kind=ComponentKind.LDR,
                    label="ldr",
                    terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                )
            )
        return components
