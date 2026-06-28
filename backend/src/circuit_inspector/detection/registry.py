"""Registro e orquestracao dos detectores de componente.

Agrega os detectores disponiveis e executa todos sobre uma imagem. Adicionar um
novo tipo de componente significa apenas criar um `ComponentDetector` e
registra-lo aqui (principio Open/Closed) -- nada mais no pipeline muda.
"""

from __future__ import annotations

import numpy as np

from ..config import InspectorConfig
from ..models import Component
from .base import ComponentDetector
from .button_detector import ButtonDetector
from .capacitor_detector import CapacitorDetector
from .ldr_detector import LdrDetector
from .led_detector import LedDetector
from .potentiometer_detector import PotentiometerDetector
from .resistor_detector import ResistorDetector
from .wire_detector import WireDetector


class DetectorRegistry:
    """Mantem a colecao de detectores e executa a deteccao completa."""

    def __init__(self, detectors: list[ComponentDetector]) -> None:
        self._detectors = list(detectors)

    @classmethod
    def default(cls, config: InspectorConfig | None = None) -> "DetectorRegistry":
        config = config or InspectorConfig()
        colors = config.colors
        components_cfg = config.components
        return cls(
            [
                WireDetector(colors, components_cfg),
                LedDetector(colors, components_cfg),
                LdrDetector(colors, components_cfg),
                ResistorDetector(colors, components_cfg),
                CapacitorDetector(colors, components_cfg),
                PotentiometerDetector(colors, components_cfg),
                ButtonDetector(colors, components_cfg),
            ]
        )

    def detect_all(self, image_bgr: np.ndarray) -> list[Component]:
        components: list[Component] = []
        for detector in self._detectors:
            components.extend(detector.detect(image_bgr))
        return components
