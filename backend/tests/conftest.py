"""Fixtures compartilhadas entre os testes."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"


@pytest.fixture(scope="session")
def assets_dir() -> Path:
    """Diretorio com as imagens de exemplo."""
    return ASSETS_DIR
