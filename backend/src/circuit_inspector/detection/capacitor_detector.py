"""Deteccao de capacitor eletrolitico.

Aparece como um corpo escuro, cilindrico e arredondado (visto de cima, um disco
escuro com topo prateado). E separado do push button (tambem escuro) pela
combinacao de area maior e circularidade alta (redondo, nao quadrado), e do fio
preto pelo formato compacto (nao alongado).

Nota de escopo: representado por 2 terminais (aproximados pelos cantos
inferiores do bounding box); a polaridade nao e inferida.
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


class CapacitorDetector(ComponentDetector):
    """Detecta capacitores eletroliticos pelo corpo escuro e redondo."""

    def __init__(
        self,
        colors: ColorProfiles | None = None,
        config: ComponentDetectionConfig | None = None,
    ) -> None:
        self._colors = colors or ColorProfiles()
        self._config = config or ComponentDetectionConfig()

    def detect(self, image_bgr: np.ndarray) -> list[Component]:
        mask = color_mask(image_bgr, self._colors.dark_body)
        contours = compact_contours(
            mask,
            self._config.capacitor_min_area,
            self._config.capacitor_max_area,
            self._config.capacitor_min_circularity,
        )
        components: list[Component] = []
        for contour in contours:
            start, end = bbox_bottom_terminals(contour)
            components.append(
                Component(
                    kind=ComponentKind.CAPACITOR,
                    label="capacitor",
                    terminals=(Terminal(pixel=start), Terminal(pixel=end)),
                )
            )
        return components
