"""Validacao do par real certa/errada com reducao de ruido."""

from __future__ import annotations

from pathlib import Path

import pytest

from circuit_inspector.comparison.registered import compare_registered
from circuit_inspector.comparison.selection import reduce_registered_to_single
from circuit_inspector.io.image_loader import load_bgr

ASSETS = Path(__file__).resolve().parents[2] / "assets"


@pytest.mark.integration
def test_real_pair_reports_single_primary_difference() -> None:
    """O par certa/errada deve gerar poucas divergencias apos filtros; uma principal."""
    reference = ASSETS / "sample_certa_1.png"
    test = ASSETS / "sample_errada_1.png"
    if not reference.exists() or not test.exists():
        pytest.skip("Imagens sample_certa_1 / sample_errada_1 nao disponiveis.")

    result = compare_registered(load_bgr(reference), load_bgr(test))
    single = reduce_registered_to_single(result)

    assert len(result.differences) <= 5, (
        f"Esperado <= 5 divergencias apos filtros, obteve {len(result.differences)}"
    )
    assert len(single.differences) == 1
    assert single.differences[0].kind == "mismatched"
