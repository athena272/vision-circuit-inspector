"""Testes das pecas puras da comparacao por registro (comparison.registered)."""

from __future__ import annotations

import numpy as np

from circuit_inspector.comparison.registered import (
    _Cluster,
    _build_differences,
    _clusters,
    _color_label,
    _map_box,
    _nearest,
)


class TestColorLabel:
    def test_red(self) -> None:
        assert _color_label(2) == "componente vermelho"
        assert _color_label(175) == "componente vermelho"

    def test_blue(self) -> None:
        assert _color_label(110) == "componente azul"

    def test_green(self) -> None:
        assert _color_label(60) == "componente verde"


class TestClusters:
    def test_finds_blobs_above_min_area(self) -> None:
        mask = np.zeros((100, 200), np.uint8)
        mask[10:40, 10:60] = 255  # blob grande
        mask[80:83, 150:153] = 255  # blob minusculo (descartado)
        hue = np.full((100, 200), 110, np.uint8)
        clusters = _clusters(mask, hue, min_area=200)
        assert len(clusters) == 1
        assert clusters[0].label == "componente azul"
        x0, y0, x1, y1 = clusters[0].bbox
        assert (x0, y0) == (10, 10)


class TestMapBox:
    def test_identity_adds_padding(self) -> None:
        box = _map_box((50, 60, 90, 100), np.eye(3), padding=10)
        assert box == (40, 50, 100, 110)


class TestBuildDifferences:
    def _cluster(self, cx: float, cy: float, label: str, area: int = 500) -> _Cluster:
        return _Cluster(area=area, centroid=(cx, cy), bbox=(int(cx) - 10, int(cy) - 10, int(cx) + 10, int(cy) + 10), label=label)

    def test_pairs_nearby_same_color_as_mismatch(self) -> None:
        ref = [self._cluster(100, 100, "componente azul")]
        test = [self._cluster(140, 100, "componente azul")]
        diffs = _build_differences(ref, test, np.eye(3), pair_max_distance=1000)
        assert len(diffs) == 1
        assert diffs[0].kind == "mismatched"
        assert diffs[0].expected_box is not None and diffs[0].actual_box is not None

    def test_unpaired_become_missing_and_extra(self) -> None:
        ref = [self._cluster(100, 100, "componente azul")]
        test = [self._cluster(900, 900, "componente vermelho")]
        diffs = _build_differences(ref, test, np.eye(3), pair_max_distance=100)
        kinds = sorted(d.kind for d in diffs)
        assert kinds == ["extra", "missing"]

    def test_sorted_by_salience(self) -> None:
        ref = [self._cluster(100, 100, "componente azul", area=300)]
        test = [
            self._cluster(120, 100, "componente azul", area=300),
            self._cluster(800, 800, "componente vermelho", area=9000),
        ]
        diffs = _build_differences(ref, test, np.eye(3), pair_max_distance=100)
        # mismatched (salience base 1000+) deve vir antes do extra grande.
        assert diffs[0].kind == "mismatched"


class TestNearest:
    def test_prefers_same_label_then_distance(self) -> None:
        target = _Cluster(500, (100, 100), (90, 90, 110, 110), "componente azul")
        candidates = [
            _Cluster(500, (130, 100), (120, 90, 140, 110), "componente vermelho"),
            _Cluster(500, (160, 100), (150, 90, 170, 110), "componente azul"),
        ]
        # mesmo rotulo (indice 1) preferido apesar de mais distante
        assert _nearest(target, candidates, set(), max_distance=1000) == 1

    def test_respects_max_distance(self) -> None:
        target = _Cluster(500, (100, 100), (90, 90, 110, 110), "componente azul")
        candidates = [_Cluster(500, (800, 800), (790, 790, 810, 810), "componente azul")]
        assert _nearest(target, candidates, set(), max_distance=100) is None
