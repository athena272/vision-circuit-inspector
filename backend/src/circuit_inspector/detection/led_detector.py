"""Deteccao de LED (multi-cor).

O LED aparece como um domo colorido (azul ou vermelho), compacto e
aproximadamente circular. Cada cor configurada vira um componente com label
proprio (`led:blue`, `led:red`), de modo que uma troca de cor seja tratada como
uma divergencia. Os terminais (pernas) sao aproximados pelos cantos inferiores
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


class LedDetector(ComponentDetector):
    """Detecta LEDs pelo domo azul compacto."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        components: list[Component] = []
        for color_name, hsv_range in self._colors.led_colors().items():
            mask = color_mask(image_bgr, hsv_range)
            contours = compact_contours(
                mask,
                self._config.led_min_area,
                self._config.led_max_area,
                self._config.led_min_circularity,
            )
            for contour in contours:
                start, end = bbox_bottom_terminals(contour)
                components.append(
                    Component(
                        kind=ComponentKind.LED,
                        label=f"led:{color_name}",
                        terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                    )
                )
        return components
