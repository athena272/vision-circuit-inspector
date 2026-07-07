"""Validacao dos pares reais certa/errada com reducao de ruido."""

from __future__ import annotations

from pathlib import Path

import pytest

from circuit_inspector.comparison.registered import compare_registered
from circuit_inspector.comparison.selection import reduce_registered_to_single
from circuit_inspector.io.image_loader import load_bgr

ASSETS = Path(__file__).resolve().parents[2] / "assets"

PAIR_KIND_EXPECTATIONS: dict[int, str] = {
    5: "missing",
}

PAIR_EXPECTATIONS: dict[int, str] = {
    1: "componente azul",
    2: "componente laranja",
    3: "componente resistor",
    4: "componente resistor",
    5: "componente resistor",
    6: "componente laranja",
    7: "componente azul",
    8: "componente azul",
    9: "componente vermelho",
    10: "componente azul",
}


def _pair_paths(n: int) -> tuple[Path, Path]:
    ref_png = ASSETS / f"sample_certa_{n}.png"
    ref_jpg = ASSETS / f"sample_certa_{n}.jpg"
    test_png = ASSETS / f"sample_errada_{n}.png"
    test_jpg = ASSETS / f"sample_errada_{n}.jpg"
    reference = ref_png if ref_png.exists() else ref_jpg
    test = test_png if test_png.exists() else test_jpg
    return reference, test


@pytest.mark.integration
@pytest.mark.parametrize("n,expected_label", sorted(PAIR_EXPECTATIONS.items()))
def test_real_pair_primary_difference(n: int, expected_label: str) -> None:
    """Cada par certa/errada deve reportar a divergencia principal esperada."""
    reference, test = _pair_paths(n)
    if not reference.exists() or not test.exists():
        pytest.skip(f"Imagens sample_certa_{n} / sample_errada_{n} nao disponiveis.")

    result = compare_registered(load_bgr(reference), load_bgr(test))
    single = reduce_registered_to_single(result)

    if n == 1:
        assert len(result.differences) <= 5, (
            f"Esperado <= 5 divergencias apos filtros, obteve {len(result.differences)}"
        )

    assert len(single.differences) == 1, (
        f"Par {n}: esperado 1 divergencia principal, obteve {len(single.differences)}"
    )
    assert single.differences[0].label == expected_label, (
        f"Par {n}: esperado {expected_label!r}, obteve {single.differences[0].label!r}"
    )
    if n in PAIR_KIND_EXPECTATIONS:
        expected_kind = PAIR_KIND_EXPECTATIONS[n]
        assert single.differences[0].kind == expected_kind, (
            f"Par {n}: esperado tipo {expected_kind!r}, obteve {single.differences[0].kind!r}"
        )
