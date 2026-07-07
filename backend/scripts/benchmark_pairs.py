"""Relatorio local do benchmark certa x errada (pares 1-10).

Uso:
    python scripts/benchmark_pairs.py
    python scripts/benchmark_pairs.py --pair 4
"""

from __future__ import annotations

import argparse
from pathlib import Path

from circuit_inspector.comparison.registered import compare_registered
from circuit_inspector.comparison.selection import reduce_registered_to_single
from circuit_inspector.io.image_loader import load_bgr

ASSETS = Path(__file__).resolve().parents[1] / "assets"

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


def run_pair(n: int) -> tuple[bool, str, str]:
    expected = PAIR_EXPECTATIONS[n]
    reference, test = _pair_paths(n)
    if not reference.exists() or not test.exists():
        return False, expected, "(imagens ausentes)"
    result = reduce_registered_to_single(
        compare_registered(load_bgr(reference), load_bgr(test))
    )
    if not result.differences:
        return False, expected, "(nenhuma divergencia)"
    got = result.differences[0].label
    return got == expected, expected, got


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark pares certa/errada")
    parser.add_argument(
        "--pair",
        type=int,
        action="append",
        dest="pairs",
        help="Numero do par (repita para varios). Padrao: 1-10.",
    )
    args = parser.parse_args()
    pairs = args.pairs or list(range(1, 11))

    ok = 0
    for n in pairs:
        if n not in PAIR_EXPECTATIONS:
            print(f"Par {n}: ignorado (fora do gabarito 1-10)")
            continue
        passed, expected, got = run_pair(n)
        status = "OK" if passed else "FAIL"
        if passed:
            ok += 1
        print(f"Par {n:2d}  {status:4s}  esperado={expected!r}  obtido={got!r}")

    total = len([p for p in pairs if p in PAIR_EXPECTATIONS])
    print(f"\n{ok}/{total} pares corretos")


if __name__ == "__main__":
    main()
