"""Testes de escala de caixas apos downscale de processamento."""

from __future__ import annotations

from circuit_inspector.comparison.box_scale import scale_registered_result
from circuit_inspector.comparison.registered import RegisteredDifference, RegisteredResult


def test_scales_boxes_to_original_resolution() -> None:
    result = RegisteredResult(
        differences=(
            RegisteredDifference(
                kind="extra",
                label="componente laranja",
                detail="",
                expected_box=None,
                actual_box=(100, 200, 120, 220),
                salience=500.0,
            ),
        ),
        matched_count=1,
    )
    scaled = scale_registered_result(result, 2.0, 2.0)
    assert scaled.differences[0].actual_box == (200, 400, 240, 440)
