"""Testes das pecas puras da comparacao por registro (comparison.registered)."""

from __future__ import annotations

import numpy as np

from circuit_inspector.comparison.registered import (
    Cluster,
    build_differences,
    clusters_from_mask,
    color_bbox_on_image,
    color_label,
    filter_differences_by_salience,
    map_box,
    merge_nearby_clusters,
    refine_cluster_bbox,
    refine_clusters,
    refine_difference_boxes,
    _is_gutter_artifact,
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

    def test_resistor(self) -> None:
        assert color_label(95) == "componente resistor"
        assert color_label(104) == "componente resistor"

    def test_blue(self) -> None:
        assert color_label(105) == "componente azul"
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
        assert diffs[0].kind == "extra"
        assert diffs[0].label == "componente vermelho"


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

    def test_prefers_higher_salience_over_kind(self) -> None:
        result = RegisteredResult(
            differences=(
                RegisteredDifference("mismatched", "a", "", None, None, 500.0),
                RegisteredDifference("extra", "b", "", None, None, 2000.0),
            ),
            matched_count=2,
        )
        reduced = reduce_registered_to_single(result)
        assert reduced.differences[0].kind == "extra"


class TestRefineClusters:
    def test_detects_gutter_artifact(self) -> None:
        assert _is_gutter_artifact((0, 0, 900, 30)) is True
        assert _is_gutter_artifact((0, 0, 40, 80)) is False

    def test_tightens_bbox_to_diff_pixels(self) -> None:
        mask = np.zeros((120, 120), np.uint8)
        mask[50:55, 70:74] = 255
        cluster = Cluster(
            area=20,
            centroid=(72.0, 52.5),
            bbox=(60, 40, 90, 70),
            label="componente laranja",
        )
        image = np.zeros((120, 120, 3), np.uint8)
        bbox = refine_cluster_bbox(cluster, mask, image)
        assert bbox == (70, 50, 74, 55)

    def test_drops_gutter_without_wire_color(self) -> None:
        mask = np.zeros((80, 1000), np.uint8)
        mask[40:45, 10:990] = 255
        cluster = Cluster(
            area=5000,
            centroid=(500.0, 42.5),
            bbox=(10, 40, 990, 45),
            label="componente laranja",
        )
        image = np.zeros((80, 1000, 3), np.uint8)
        refined = refine_clusters([cluster], mask, image)
        assert refined == []


class TestColorBboxOnImage:
    def test_finds_nearest_color_blob_with_hint(self) -> None:
        image = np.zeros((200, 300, 3), np.uint8)
        image[35:55, 180:280] = (0, 140, 255)
        image[120:128, 20:60] = (0, 140, 255)
        bbox = color_bbox_on_image(
            image,
            "componente laranja",
            hint_box=(200, 30, 220, 60),
        )
        assert bbox is not None
        assert bbox[0] <= 180
        assert bbox[2] >= 280

    def test_refines_extra_difference_to_student_color_bbox(self) -> None:
        student = np.zeros((200, 300, 3), np.uint8)
        student[120:132, 20:90] = (0, 140, 255)
        reference = np.zeros((200, 300, 3), np.uint8)
        diff = RegisteredDifference(
            kind="extra",
            label="componente laranja",
            detail="",
            expected_box=None,
            actual_box=(190, 35, 210, 55),
            salience=100.0,
        )
        refined = refine_difference_boxes(diff, student, reference)
        assert refined.actual_box is not None
        assert refined.actual_box[2] - refined.actual_box[0] > 40

