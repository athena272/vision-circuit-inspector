"""Visualizacao de debug das etapas do board.

Util para inspecionar/ajustar a deteccao da malha e o mapeamento de furos
quando se trabalha com imagens reais.
"""

from __future__ import annotations

import cv2
import numpy as np

from .grid_mapper import BoardGrid


def draw_grid(image_bgr: np.ndarray, grid: BoardGrid) -> np.ndarray:
    """Sobrepoe os furos previstos pelo `BoardGrid` na imagem."""
    canvas = image_bgr.copy()
    for hole in grid.layout.all_holes():
        pixel = grid.hole_to_pixel(hole)
        x, y = pixel.as_int_tuple()
        if 0 <= x < canvas.shape[1] and 0 <= y < canvas.shape[0]:
            color = (0, 0, 255) if hole.is_rail else (0, 200, 0)
            cv2.circle(canvas, (x, y), 3, color, 1, cv2.LINE_AA)
    return canvas
