"""Deteccao de jumpers (fios) por cor.

Um jumper e um blob colorido e alongado. Para cada cor configurada, segmenta-se
a imagem, filtram-se blobs alongados o suficiente e extraem-se os dois terminais
ao longo do eixo principal.
"""

from __future__ import annotations

import numpy as np

from ..config import ColorProfiles, ComponentDetectionConfig
from ..models import Component, ComponentKind, Terminal
from .base import (
    ComponentDetector,
    color_mask,
    elongated_contours,
    principal_axis_endpoints,
)


class WireDetector(ComponentDetector):
    """Detecta jumpers para cada cor em `ColorProfiles.wire_colors()`."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        components: list[Component] = []
        for color_name, hsv_range in self._colors.wire_colors().items():
            mask = color_mask(image_bgr, hsv_range)
            contours = elongated_contours(
                mask,
                self._config.min_wire_area,
                self._config.min_wire_aspect,
            )
            for contour in contours:
                start, end = principal_axis_endpoints(contour)
                components.append(
                    Component(
                        kind=ComponentKind.WIRE,
                        label=f"wire:{color_name}",
                        terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                    )
                )
        return components
