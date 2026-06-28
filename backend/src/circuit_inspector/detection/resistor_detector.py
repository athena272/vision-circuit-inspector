"""Deteccao de resistor.

O resistor aparece como um corpo cilindrico alongado (filme metalico
azul/verde-azulado), deitado sobre a protoboard, com as pernas dobradas em dois
furos. Os terminais sao extraidos pelos extremos do eixo principal do corpo.
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


class ResistorDetector(ComponentDetector):
    """Detecta resistores pelo corpo alongado."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        mask = color_mask(image_bgr, self._colors.resistor_body)
        contours = elongated_contours(
            mask,
            self._config.min_resistor_area,
            self._config.min_resistor_aspect,
        )
        components: list[Component] = []
        for contour in contours:
            start, end = principal_axis_endpoints(contour)
            components.append(
                Component(
                    kind=ComponentKind.RESISTOR,
                    label="resistor",
                    terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                )
            )
        return components
