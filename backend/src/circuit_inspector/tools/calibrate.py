"""Calibrador interativo da malha da protoboard.

Gera o JSON de calibracao (correspondencias furo->pixel) que o pipeline usa no
modo de calibracao assistida. O usuario clica, na imagem, nos furos de
referencia (tipicamente os 4 cantos da secao principal) e o arquivo e salvo.

Uso:
    python -m circuit_inspector.tools.calibrate FOTO.png saida.json \
        --holes 45:j 60:j 45:a 60:a

`--holes` lista os furos a clicar, na ordem. Cada furo e "coluna:linha"
(ex.: 45:j) ou "coluna:trilha" (ex.: 60:+). Apos os cliques, uma janela mostra
a malha estimada sobre a imagem para conferencia.

A logica pura (parse e montagem da calibracao) e testavel; a coleta de cliques
depende de interface grafica (OpenCV highgui) e nao e coberta por testes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..board.calibration_io import save_calibration
from ..board.rectifier import GridCalibration
from ..models import Hole, Point


def parse_hole_spec(spec: str) -> Hole:
    """Converte "coluna:linha" ou "coluna:trilha" em um Hole.

    Exemplos: "45:j" -> Hole(45, row='j'); "60:+" -> Hole(60, rail='+').
    """
    if ":" not in spec:
        raise ValueError(f"Furo invalido (use coluna:linha): {spec!r}")
    column_text, marker = spec.split(":", 1)
    try:
        column = int(column_text)
    except ValueError as exc:
        raise ValueError(f"Coluna invalida em {spec!r}") from exc

    marker = marker.strip()
    if marker in ("+", "-"):
        return Hole(column=column, rail=marker)
    if len(marker) == 1 and marker.isalpha():
        return Hole(column=column, row=marker.lower())
    raise ValueError(f"Linha/trilha invalida em {spec!r}")


def build_calibration(holes: list[Hole], points: list[Point]) -> GridCalibration:
    """Monta uma GridCalibration validando o pareamento furo<->pixel."""
    if len(holes) != len(points):
        raise ValueError("Numero de furos e de pontos clicados nao confere.")
    if len(holes) < 4:
        raise ValueError("Sao necessarios ao menos 4 furos de referencia.")
    return GridCalibration(correspondences=tuple(zip(holes, points)))


def _collect_points(image_path: Path, holes: list[Hole]) -> list[Point]:  # pragma: no cover - GUI
    """Abre a imagem e coleta um clique por furo, na ordem informada.

    Teclas: ESC cancela, `u`/Backspace desfaz o ultimo clique, `r` reinicia.
    Os marcadores sao redesenhados a cada frame, de modo que desfazer e limpo.
    """
    import cv2

    from ..io.image_loader import load_bgr

    base = load_bgr(image_path)
    points: list[Point] = []
    window = "Calibracao - clique nos furos (ESC cancela | u desfaz | r reinicia)"

    def on_mouse(event: int, x: int, y: int, flags: int, _: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < len(holes):
            points.append(Point(float(x), float(y)))

    def render() -> "object":
        frame = base.copy()
        for index, point in enumerate(points):
            center = point.as_int_tuple()
            cv2.circle(frame, center, 6, (0, 0, 255), -1)
            cv2.putText(
                frame, holes[index].label, (center[0] + 8, center[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA,
            )
        return frame

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)
    while len(points) < len(holes):
        cv2.imshow(window, render())
        print(f"Clique no furo: {holes[len(points)].label}   ", end="\r", flush=True)
        key = cv2.waitKey(20) & 0xFF
        if key == 27:  # ESC
            cv2.destroyAllWindows()
            raise KeyboardInterrupt("Calibracao cancelada pelo usuario.")
        if key in (ord("u"), 8) and points:  # 'u' ou Backspace
            points.pop()
        elif key == ord("r"):
            points.clear()
    cv2.destroyAllWindows()
    return points


def _show_overlay(image_path: Path, calibration: GridCalibration) -> None:  # pragma: no cover - GUI
    """Mostra a malha estimada sobre a imagem, para conferencia visual."""
    import cv2

    from ..board.debug import draw_grid
    from ..board.rectifier import build_grid_from_calibration
    from ..io.image_loader import load_bgr

    grid = build_grid_from_calibration(calibration)
    overlay = draw_grid(load_bgr(image_path), grid)
    window = "Conferencia da malha (tecla qualquer para fechar)"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.imshow(window, overlay)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="circuit-inspector-calibrate",
        description="Gera um JSON de calibracao clicando nos furos de referencia.",
    )
    parser.add_argument("image", type=Path, help="Foto da protoboard.")
    parser.add_argument("output", type=Path, help="Arquivo JSON de saida.")
    parser.add_argument(
        "--holes",
        nargs="+",
        default=["45:j", "60:j", "45:a", "60:a"],
        help="Furos a clicar, na ordem (ex.: 45:j 60:j 45:a 60:a).",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Nao mostrar a malha de conferencia ao final.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - GUI
    args = _build_parser().parse_args(argv)
    try:
        holes = [parse_hole_spec(spec) for spec in args.holes]
        points = _collect_points(args.image, holes)
        calibration = build_calibration(holes, points)
    except (ValueError, KeyboardInterrupt) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2

    save_calibration(args.output, calibration)
    print(f"\nCalibracao salva em: {args.output}")
    if not args.no_overlay:
        _show_overlay(args.image, calibration)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
