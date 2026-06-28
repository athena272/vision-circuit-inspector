"""Deteccao de potenciometro.

Aparece como um corpo metalico acinzentado (knob) bem maior que os demais
componentes. Compartilha a faixa de cor com o LDR, mas e separado dele pela area
muito maior.

Nota de escopo: representado por 2 terminais (aproximados pelos cantos
inferiores do bounding box); o potenciometro real tem 3 pinos.
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


class PotentiometerDetector(ComponentDetector):
    """Detecta potenciometros pelo corpo metalico grande."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        mask = color_mask(image_bgr, self._colors.metallic)
        contours = compact_contours(
            mask,
            self._config.potentiometer_min_area,
            self._config.potentiometer_max_area,
            self._config.potentiometer_min_circularity,
        )
        components: list[Component] = []
        for contour in contours:
            start, end = bbox_bottom_terminals(contour)
            components.append(
                Component(
                    kind=ComponentKind.POTENTIOMETER,
                    label="potentiometer",
                    terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                )
            )
        return components
