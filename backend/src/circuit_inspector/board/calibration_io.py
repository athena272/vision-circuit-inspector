"""Leitura/escrita de calibracao da malha (GridCalibration) em JSON.

Permite informar, uma vez por board, alguns furos de referencia conhecidos
(>= 4) com seus pixels, para o caminho de calibracao assistida -- mais
confiavel que a estimativa automatica quando a foto inclui varias secoes de
protoboard.

Formato JSON:
{
  "correspondences": [
    {"hole": {"column": 50, "row": "j"}, "pixel": {"x": 410, "y": 200}},
    {"hole": {"column": 60, "rail": "+"}, "pixel": {"x": 770, "y": 120}}
  ]
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Hole, Point
from .rectifier import GridCalibration


class CalibrationFormatError(ValueError):
    """Levantado quando o JSON de calibracao e invalido."""


def _parse_hole(data: dict[str, Any]) -> Hole:
    if "column" not in data:
        raise CalibrationFormatError("Furo sem 'column'.")
    return Hole(
        column=int(data["column"]),
        row=data.get("row"),
        rail=data.get("rail"),
    )


def _parse_point(data: dict[str, Any]) -> Point:
    try:
        return Point(x=float(data["x"]), y=float(data["y"]))
    except (KeyError, TypeError) as exc:
        raise CalibrationFormatError(f"Pixel invalido: {data!r}") from exc


def parse_calibration(payload: dict[str, Any]) -> GridCalibration:
    """Constroi um GridCalibration a partir do dicionario ja carregado."""
    items = payload.get("correspondences")
    if not isinstance(items, list) or len(items) < 4:
        raise CalibrationFormatError(
            "A calibracao exige ao menos 4 correspondencias em 'correspondences'."
        )
    correspondences = tuple(
        (_parse_hole(item["hole"]), _parse_point(item["pixel"])) for item in items
    )
    return GridCalibration(correspondences=correspondences)


def load_calibration(path: str | Path) -> GridCalibration:
    """Carrega uma calibracao de um arquivo JSON."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CalibrationFormatError(f"JSON invalido em {path}: {exc}") from exc
    return parse_calibration(payload)


def save_calibration(path: str | Path, calibration: GridCalibration) -> None:
    """Salva uma calibracao em JSON (util para o picker interativo/manual)."""
    payload = {
        "correspondences": [
            {
                "hole": _hole_to_dict(hole),
                "pixel": {"x": point.x, "y": point.y},
            }
            for hole, point in calibration.correspondences
        ]
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _hole_to_dict(hole: Hole) -> dict[str, Any]:
    data: dict[str, Any] = {"column": hole.column}
    if hole.is_rail:
        data["rail"] = hole.rail
    else:
        data["row"] = hole.row
    return data
