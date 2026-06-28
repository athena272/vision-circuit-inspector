"""Carregamento e salvamento de imagens.

Encapsula o acesso ao disco via OpenCV para isolar o resto do pipeline de
detalhes de I/O e oferecer mensagens de erro claras.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageLoadError(RuntimeError):
    """Levantado quando uma imagem nao pode ser lida do disco."""


def load_bgr(path: str | Path) -> np.ndarray:
    """Carrega uma imagem como matriz BGR (formato nativo do OpenCV).

    Raises:
        ImageLoadError: se o arquivo nao existir ou nao puder ser decodificado.
    """
    image_path = Path(path)
    if not image_path.exists():
        raise ImageLoadError(f"Imagem nao encontrada: {image_path}")

    # cv2.imread nao lida bem com caminhos non-ASCII no Windows; usamos imdecode.
    data = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ImageLoadError(f"Falha ao decodificar a imagem: {image_path}")
    return image


def decode_bgr(data: bytes) -> np.ndarray:
    """Decodifica bytes de uma imagem (ex.: upload HTTP) em matriz BGR.

    Util para fontes que nao estao no disco, mantendo a mesma semantica de erro
    de `load_bgr`.

    Raises:
        ImageLoadError: se os bytes estiverem vazios ou nao puderem ser decodificados.
    """
    if not data:
        raise ImageLoadError("Conteudo de imagem vazio.")

    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ImageLoadError("Falha ao decodificar a imagem enviada.")
    return image


def save_bgr(path: str | Path, image: np.ndarray) -> None:
    """Salva uma imagem BGR no disco, criando diretorios se necessario."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = out_path.suffix or ".png"
    ok, buffer = cv2.imencode(suffix, image)
    if not ok:
        raise ImageLoadError(f"Falha ao codificar a imagem para: {out_path}")
    buffer.tofile(str(out_path))
