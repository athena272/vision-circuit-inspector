"""Testes das pecas puras da comparacao por registro (comparison.registered)."""

from __future__ import annotations

import numpy as np

from circuit_inspector.comparison.registered import (
    Cluster,
    build_differences,
    clusters_from_mask,
    color_label,
    filter_differences_by_salience,
    map_box,
    merge_nearby_clusters,
    _nearest,
)
from circuit_inspector.comparison.selection import reduce_registered_to_single
from circuit_inspector.comparison.registered import (
    RegisteredDifference,
    RegisteredResult,
)


class TestColorLabel:
    def test_red(self) -> None:
        assert color_label(2) == "componente vermelho"
        assert color_label(175) == "componente vermelho"

    def test_blue(self) -> None:
        assert color_label(110) == "componente azul"

    def test_green(self) -> None:
        assert color_label(60) == "componente verde"


class TestClusters:
    def test_finds_blobs_above_min_area(self) -> None:
        mask = np.zeros((100, 200), np.uint8)
        mask[10:40, 10:60] = 255
        mask[80:83, 150:153] = 255
        hue = np.full((100, 200), 110, np.uint8)
        found = clusters_from_mask(mask, hue, min_area=200)
        assert len(found) == 1
        assert found[0].label == "componente azul"
        x0, y0, x1, y1 = found[0].bbox
        assert (x0, y0) == (10, 10)


class TestMapBox:
    def test_identity_adds_padding(self) -> None:
        box = map_box((50, 60, 90, 100), np.eye(3), padding=10)
        assert box == (40, 50, 100, 110)


class TestBuildDifferences:
    def _cluster(self, cx: float, cy: float, label: str, area: int = 500) -> Cluster:
        return Cluster(
            area=area,
            centroid=(cx, cy),
            bbox=(int(cx) - 10, int(cy) - 10, int(cx) + 10, int(cy) + 10),
            label=label,
        )

    def test_pairs_nearby_same_color_as_mismatch(self) -> None:
        ref = [self._cluster(100, 100, "componente azul")]
        test = [self._cluster(140, 100, "componente azul")]
        diffs = build_differences(ref, test, np.eye(3), pair_max_dist=1000)
        assert len(diffs) == 1
        assert diffs[0].kind == "mismatched"

    def test_unpaired_become_missing_and_extra(self) -> None:
        ref = [self._cluster(100, 100, "componente azul")]
        test = [self._cluster(900, 900, "componente vermelho")]
        diffs = build_differences(ref, test, np.eye(3), pair_max_dist=100)
        kinds = sorted(d.kind for d in diffs)
        assert kinds == ["extra", "missing"]

    def test_sorted_by_salience(self) -> None:
        ref = [self._cluster(100, 100, "componente azul", area=300)]
        test = [
            self._cluster(120, 100, "componente azul", area=300),
            self._cluster(800, 800, "componente vermelho", area=9000),
        ]
        diffs = build_differences(ref, test, np.eye(3), pair_max_dist=100)
        assert diffs[0].kind == "mismatched"


class TestNearest:
    def test_prefers_same_label_then_distance(self) -> None:
        target = Cluster(500, (100, 100), (90, 90, 110, 110), "componente azul")
        candidates = [
            Cluster(400, (200, 100), (190, 90, 210, 110), "componente vermelho"),
            Cluster(300, (130, 100), (120, 90, 140, 110), "componente azul"),
        ]
        assert _nearest(target, candidates, set(), max_distance=200) == 1


class TestFilterDifferences:
    def test_drops_weak_missing_extra(self) -> None:
        diffs = [
            RegisteredDifference("mismatched", "a", "", None, None, 1000.0),
            RegisteredDifference("missing", "b", "", None, None, 50.0),
            RegisteredDifference("extra", "c", "", None, None, 30.0),
        ]
        filtered = filter_differences_by_salience(diffs, min_ratio=0.20)
        assert len(filtered) == 1
        assert filtered[0].kind == "mismatched"


class TestReduceRegistered:
    def test_keeps_top_difference(self) -> None:
        result = RegisteredResult(
            differences=(
                RegisteredDifference("mismatched", "a", "", None, None, 500.0),
                RegisteredDifference("extra", "b", "", None, None, 100.0),
            ),
            matched_count=2,
        )
        reduced = reduce_registered_to_single(result)
        assert len(reduced.differences) == 1
        assert reduced.differences[0].kind == "mismatched"
