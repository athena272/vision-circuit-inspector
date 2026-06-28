"""Testes de leitura/escrita da calibracao."""

from __future__ import annotations

from pathlib import Path

import pytest

from circuit_inspector.board.calibration_io import (
    CalibrationFormatError,
    load_calibration,
    parse_calibration,
    save_calibration,
)
from circuit_inspector.board.rectifier import GridCalibration
from circuit_inspector.models import Hole, Point


def _valid_payload() -> dict:
    return {
        "correspondences": [
            {"hole": {"column": 50, "row": "j"}, "pixel": {"x": 410, "y": 200}},
            {"hole": {"column": 60, "row": "j"}, "pixel": {"x": 770, "y": 200}},
            {"hole": {"column": 50, "row": "a"}, "pixel": {"x": 410, "y": 540}},
            {"hole": {"column": 60, "rail": "+"}, "pixel": {"x": 770, "y": 120}},
        ]
    }


def test_parse_valid_calibration() -> None:
    calib = parse_calibration(_valid_payload())
    assert len(calib.correspondences) == 4
    hole, point = calib.correspondences[0]
    assert hole == Hole(column=50, row="j")
    assert point == Point(410, 200)
    # Trilha preservada.
    assert calib.correspondences[3][0] == Hole(column=60, rail="+")


def test_parse_requires_at_least_four() -> None:
    with pytest.raises(CalibrationFormatError):
        parse_calibration({"correspondences": [{"hole": {"column": 1, "row": "a"}, "pixel": {"x": 0, "y": 0}}]})


def test_roundtrip_save_load(tmp_path: Path) -> None:
    calib = GridCalibration(
        correspondences=(
            (Hole(50, row="j"), Point(410, 200)),
            (Hole(60, row="j"), Point(770, 200)),
            (Hole(50, row="a"), Point(410, 540)),
            (Hole(60, row="a"), Point(770, 540)),
        )
    )
    path = tmp_path / "calib.json"
    save_calibration(path, calib)
    loaded = load_calibration(path)
    assert loaded == calib
