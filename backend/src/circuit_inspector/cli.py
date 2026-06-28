"""Interface de linha de comando do Circuit Inspector.

Uso:
    circuit-inspector GABARITO ALUNO [-o SAIDA.png]

Compara duas fotos de protoboard, imprime um relatorio das divergencias e salva
a imagem do aluno anotada com os destaques.

Codigos de saida:
    0 - circuitos equivalentes
    1 - divergencias encontradas
    2 - erro (ex.: imagem invalida, malha nao detectada)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .board.calibration_io import CalibrationFormatError, load_calibration
from .board.rectifier import GridCalibration, GridEstimationError
from .board.registration import RegistrationError
from .comparison.report import format_registered_report, format_report
from .io.image_loader import ImageLoadError, save_bgr
from .pipeline import inspect, inspect_registered, inspect_structural

_EXIT_OK = 0
_EXIT_DIFFERENCES = 1
_EXIT_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="circuit-inspector",
        description="Compara um circuito de protoboard (aluno) com o gabarito.",
    )
    parser.add_argument("reference", type=Path, help="Imagem do gabarito.")
    parser.add_argument("test", type=Path, help="Imagem do circuito do aluno.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("inspection.out.png"),
        help="Caminho da imagem anotada de saida (default: inspection.out.png).",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        help="JSON de calibracao aplicado a AMBAS as imagens (calibracao assistida).",
    )
    parser.add_argument(
        "--reference-calibration",
        type=Path,
        help="JSON de calibracao especifico do gabarito.",
    )
    parser.add_argument(
        "--test-calibration",
        type=Path,
        help="JSON de calibracao especifico do circuito do aluno.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Mostra todas as divergencias (padrao: apenas o erro principal).",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--grid",
        action="store_true",
        help=(
            "Modo estrutural por ocupacao de furo, usando calibracao da malha "
            "(requer --calibration/--*-calibration)."
        ),
    )
    mode.add_argument(
        "--typed",
        action="store_true",
        help="Modo de deteccao por tipo (cor/forma). Requer malha (calibracao).",
    )
    return parser


def _load_calibration(
    path: Path | None, fallback: Path | None
) -> GridCalibration | None:
    chosen = path or fallback
    return load_calibration(chosen) if chosen is not None else None


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI. Retorna o codigo de saida."""
    args = _build_parser().parse_args(argv)
    single_error = not args.all

    try:
        if args.grid or args.typed:
            is_match, report, annotated = _run_grid_modes(args, single_error)
        else:
            is_match, report, annotated = _run_registered(args, single_error)
    except ImageLoadError as exc:
        print(f"Erro ao carregar imagem: {exc}", file=sys.stderr)
        return _EXIT_ERROR
    except CalibrationFormatError as exc:
        print(f"Erro na calibracao: {exc}", file=sys.stderr)
        return _EXIT_ERROR
    except RegistrationError as exc:
        print(
            f"Erro ao alinhar as fotos automaticamente: {exc}\n"
            "Dica: garanta que ambas mostram a mesma protoboard, de forma nitida "
            "e com enquadramento parecido; ou use --grid com calibracao.",
            file=sys.stderr,
        )
        return _EXIT_ERROR
    except GridEstimationError as exc:
        print(
            f"Erro ao detectar a malha da protoboard: {exc}\n"
            "Dica: use calibracao assistida (--calibration) ou garanta foto "
            "top-down com a protoboard inteira e bem iluminada.",
            file=sys.stderr,
        )
        return _EXIT_ERROR

    print(report)
    save_bgr(args.output, annotated)
    print(f"\nImagem anotada salva em: {args.output}")
    return _EXIT_OK if is_match else _EXIT_DIFFERENCES


def _run_registered(args: argparse.Namespace, single_error: bool):
    inspection = inspect_registered(args.reference, args.test, single_error=single_error)
    report = format_registered_report(inspection.result, single_error=single_error)
    return inspection.result.is_match, report, inspection.annotated_test_image


def _run_grid_modes(args: argparse.Namespace, single_error: bool):
    reference_calibration = _load_calibration(
        args.reference_calibration, args.calibration
    )
    test_calibration = _load_calibration(args.test_calibration, args.calibration)
    run = inspect if args.typed else inspect_structural
    result = run(
        args.reference,
        args.test,
        reference_calibration=reference_calibration,
        test_calibration=test_calibration,
        single_error=single_error,
    )
    report = format_report(result.comparison, single_error=single_error)
    return result.comparison.is_match, report, result.annotated_test_image


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
