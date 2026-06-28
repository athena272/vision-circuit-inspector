"""Testes dos helpers puros do calibrador interativo."""

from __future__ import annotations

import pytest

from circuit_inspector.tools.calibrate import build_calibration, parse_hole_spec
from circuit_inspector.models import Hole, Point


class TestParseHoleSpec:
    def test_row_spec(self) -> None:
        assert parse_hole_spec("45:j") == Hole(column=45, row="j")

    def test_rail_spec(self) -> None:
        assert parse_hole_spec("60:+") == Hole(column=60, rail="+")
        assert parse_hole_spec("60:-") == Hole(column=60, rail="-")

    def test_uppercase_row_is_normalized(self) -> None:
        assert parse_hole_spec("50:E") == Hole(column=50, row="e")

    @pytest.mark.parametrize("spec", ["45", "x:j", "45:jj", "45:9"])
    def test_invalid_specs_raise(self, spec: str) -> None:
        with pytest.raises(ValueError):
            parse_hole_spec(spec)


class TestBuildCalibration:
    def test_builds_from_matched_lists(self) -> None:
        holes = [Hole(45, row="j"), Hole(60, row="j"), Hole(45, row="a"), Hole(60, row="a")]
        points = [Point(0, 0), Point(10, 0), Point(0, 10), Point(10, 10)]
        calib = build_calibration(holes, points)
        assert len(calib.correspondences) == 4
        assert calib.correspondences[0] == (holes[0], points[0])

    def test_mismatched_lengths_raise(self) -> None:
        with pytest.raises(ValueError):
            build_calibration([Hole(1, row="a")], [Point(0, 0), Point(1, 1)])

    def test_requires_at_least_four(self) -> None:
        holes = [Hole(1, row="a"), Hole(2, row="a"), Hole(3, row="a")]
        points = [Point(0, 0), Point(1, 0), Point(2, 0)]
        with pytest.raises(ValueError):
            build_calibration(holes, points)
