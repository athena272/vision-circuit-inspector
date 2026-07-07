"""Comparacao por registro automatico (zero clique, sem malha canonica).

Alinha a foto do aluno sobre a do gabarito (`board.registration`) e compara a
*ocupacao* (saturacao) pixel a pixel no frame ja alinhado. As regioes que mudam
de ocupacao sao as diferencas; sao pareadas (gabarito x aluno) como componente
que se moveu e anotadas de volta na foto original do aluno.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..board.registration import (
    RegistrationConfig,
    estimate_registration,
    reference_validity_mask,
    warp_to_reference,
)
from ..config import DEFAULT_CONFIG, OccupancyConfig

Box = tuple[int, int, int, int]  # (x0, y0, x1, y1)
_BOX_PADDING = 10

REGISTERED_KIND_PRIORITY = {"mismatched": 2, "missing": 1, "extra": 1}


@dataclass(frozen=True)
class RegisteredDifference:
    """Uma diferenca localizada, ja em coordenadas da foto do aluno."""

    kind: str  # 'mismatched' | 'missing' | 'extra'
    label: str
    detail: str
    expected_box: Box | None
    actual_box: Box | None
    salience: float


@dataclass(frozen=True)
class RegisteredResult:
    differences: tuple[RegisteredDifference, ...]
    matched_count: int

    @property
    def is_match(self) -> bool:
        return len(self.differences) == 0


@dataclass(frozen=True)
class Cluster:
    """Uma regiao alterada (diff) no frame do gabarito."""

    area: int
    centroid: tuple[float, float]
    bbox: Box
    label: str


@dataclass(frozen=True)
class RegisteredPipelineState:
    """Estado intermediario do pipeline registrado (para auditoria e testes)."""

    reference_bgr: np.ndarray
    test_bgr: np.ndarray
    test_aligned: np.ndarray
    valid: np.ndarray
    sat_ref_blur: np.ndarray
    sat_test_blur: np.ndarray
    fg_ref: np.ndarray
    fg_test: np.ndarray
    hue_ref: np.ndarray
    hue_test: np.ndarray
    only_ref: np.ndarray
    only_test: np.ndarray
    ref_clusters: tuple[Cluster, ...]
    test_clusters: tuple[Cluster, ...]
    homography: np.ndarray
    homography_inv: np.ndarray
    raw_differences: tuple[RegisteredDifference, ...]
    result: RegisteredResult


def min_area_for_image(width: int, height: int) -> int:
    return max(250, int(0.00025 * width * height))


def foreground(
    image_bgr: np.ndarray, valid: np.ndarray, config: OccupancyConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mascara de ocupacao, canal de matiz e saturacao suavizada (filtro da media)."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    sat_blur = cv2.GaussianBlur(hsv[:, :, 1], (0, 0), 2)
    background = float(np.median(sat_blur[valid > 0])) if np.any(valid) else 0.0
    fg = (sat_blur > background + config.occupied_delta).astype(np.uint8) * 255
    fg = cv2.bitwise_and(fg, valid)
    return fg, hsv[:, :, 0], sat_blur


def color_label(hue: float) -> str:
    if hue <= 12 or hue >= 168:
        return "componente vermelho"
    if 13 <= hue <= 24:
        return "componente laranja"
    if 36 <= hue <= 85:
        return "componente verde"
    if 86 <= hue <= 135:
        return "componente azul"
    return "componente"


def clusters_from_mask(mask: np.ndarray, hue: np.ndarray, min_area: int) -> list[Cluster]:
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    found: list[Cluster] = []
    for i in range(1, count):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        bw = int(stats[i, cv2.CC_STAT_WIDTH])
        bh = int(stats[i, cv2.CC_STAT_HEIGHT])
        region_hue = float(np.median(hue[labels == i]))
        found.append(
            Cluster(
                area=area,
                centroid=(float(centroids[i][0]), float(centroids[i][1])),
                bbox=(x, y, x + bw, y + bh),
                label=color_label(region_hue),
            )
        )
    return found


def merge_nearby_clusters(items: list[Cluster], max_distance: int) -> list[Cluster]:
    """Funde blobs vizinhos da mesma cor para reduzir fragmentacao por alinhamento."""
    if max_distance <= 0 or len(items) < 2:
        return items

    merged: list[Cluster] = []
    used = [False] * len(items)
    for i, cluster in enumerate(items):
        if used[i]:
            continue
        group = [cluster]
        used[i] = True
        for j in range(i + 1, len(items)):
            if used[j]:
                continue
            other = items[j]
            if cluster.label != other.label:
                continue
            if _distance(cluster.centroid, other.centroid) > max_distance:
                continue
            group.append(other)
            used[j] = True
        merged.append(_merge_cluster_group(group))
    return merged


def diff_masks(
    fg_ref: np.ndarray,
    fg_test: np.ndarray,
    kernel_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    only_ref = cv2.morphologyEx(
        cv2.subtract(fg_ref, cv2.dilate(fg_test, kernel)), cv2.MORPH_OPEN, kernel
    )
    only_test = cv2.morphologyEx(
        cv2.subtract(fg_test, cv2.dilate(fg_ref, kernel)), cv2.MORPH_OPEN, kernel
    )
    return only_ref, only_test


def pair_max_distance(width: int, height: int, frac: float) -> float:
    return frac * float(np.hypot(width, height))


def build_differences(
    ref_clusters: list[Cluster],
    test_clusters: list[Cluster],
    homography_inv: np.ndarray,
    pair_max_dist: float,
) -> list[RegisteredDifference]:
    ref_sorted = sorted(ref_clusters, key=lambda c: c.area, reverse=True)
    test_sorted = sorted(test_clusters, key=lambda c: c.area, reverse=True)
    used: set[int] = set()
    diffs: list[RegisteredDifference] = []

    for rc in ref_sorted:
        best = _nearest(rc, test_sorted, used, pair_max_dist)
        if best is not None:
            used.add(best)
            tc = test_sorted[best]
            label = rc.label if rc.label != "componente" else tc.label
            diffs.append(
                RegisteredDifference(
                    kind="mismatched",
                    label=label,
                    detail=f"{label}: mudou de posicao (verde = gabarito, vermelho = aluno).",
                    expected_box=map_box(rc.bbox, homography_inv),
                    actual_box=map_box(tc.bbox, homography_inv),
                    salience=float(rc.area + tc.area) + _distance(rc.centroid, tc.centroid),
                )
            )
        else:
            diffs.append(
                RegisteredDifference(
                    kind="missing",
                    label=rc.label,
                    detail=f"{rc.label}: presente no gabarito, ausente no aluno.",
                    expected_box=map_box(rc.bbox, homography_inv),
                    actual_box=None,
                    salience=float(rc.area),
                )
            )

    for i, tc in enumerate(test_sorted):
        if i in used:
            continue
        diffs.append(
            RegisteredDifference(
                kind="extra",
                label=tc.label,
                detail=f"{tc.label}: presente no aluno, ausente no gabarito.",
                expected_box=None,
                actual_box=map_box(tc.bbox, homography_inv),
                salience=float(tc.area),
            )
        )

    diffs.sort(
        key=lambda d: (REGISTERED_KIND_PRIORITY[d.kind], d.salience), reverse=True
    )
    return diffs


def filter_differences_by_salience(
    differences: list[RegisteredDifference],
    min_ratio: float,
) -> list[RegisteredDifference]:
    """Descarta missing/extra fracos em relacao ao cluster mais saliente."""
    if not differences or min_ratio <= 0:
        return differences
    top_salience = max(d.salience for d in differences)
    if top_salience <= 0:
        return differences
    threshold = top_salience * min_ratio
    kept: list[RegisteredDifference] = []
    for diff in differences:
        if diff.kind == "mismatched":
            kept.append(diff)
        elif diff.salience >= threshold:
            kept.append(diff)
    kept.sort(
        key=lambda d: (REGISTERED_KIND_PRIORITY[d.kind], d.salience), reverse=True
    )
    return kept


def map_box(box: Box, homography_inv: np.ndarray, padding: int = _BOX_PADDING) -> Box:
    x0, y0, x1, y1 = box
    corners = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1, 1, 2)
    mapped = cv2.perspectiveTransform(corners, homography_inv).reshape(-1, 2)
    xs, ys = mapped[:, 0], mapped[:, 1]
    return (
        int(xs.min()) - padding,
        int(ys.min()) - padding,
        int(xs.max()) + padding,
        int(ys.max()) + padding,
    )


def run_registered_pipeline(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    registration_config: RegistrationConfig = RegistrationConfig(),
    occupancy_config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> RegisteredPipelineState:
    """Executa o pipeline registrado e devolve estado intermediario + resultado."""
    homography = estimate_registration(reference_bgr, test_bgr, registration_config)
    height, width = reference_bgr.shape[:2]
    test_aligned = warp_to_reference(test_bgr, homography, (width, height))
    valid = reference_validity_mask(test_bgr.shape, homography, (width, height))

    fg_ref, hue_ref, sat_ref_blur = foreground(reference_bgr, valid, occupancy_config)
    fg_test, hue_test, sat_test_blur = foreground(test_aligned, valid, occupancy_config)

    only_ref, only_test = diff_masks(
        fg_ref, fg_test, occupancy_config.alignment_dilate_kernel
    )

    min_area = min_area_for_image(width, height)
    ref_clusters = merge_nearby_clusters(
        clusters_from_mask(only_ref, hue_ref, min_area),
        occupancy_config.merge_cluster_distance_px,
    )
    test_clusters = merge_nearby_clusters(
        clusters_from_mask(only_test, hue_test, min_area),
        occupancy_config.merge_cluster_distance_px,
    )

    matched_count = _count_components(cv2.bitwise_and(fg_ref, fg_test), min_area)
    homography_inv = np.linalg.inv(homography)
    max_pair_dist = pair_max_distance(
        width, height, occupancy_config.pair_max_distance_frac
    )
    raw = build_differences(ref_clusters, test_clusters, homography_inv, max_pair_dist)
    filtered = filter_differences_by_salience(raw, occupancy_config.min_salience_ratio)
    result = RegisteredResult(differences=tuple(filtered), matched_count=matched_count)

    return RegisteredPipelineState(
        reference_bgr=reference_bgr,
        test_bgr=test_bgr,
        test_aligned=test_aligned,
        valid=valid,
        sat_ref_blur=sat_ref_blur,
        sat_test_blur=sat_test_blur,
        fg_ref=fg_ref,
        fg_test=fg_test,
        hue_ref=hue_ref,
        hue_test=hue_test,
        only_ref=only_ref,
        only_test=only_test,
        ref_clusters=tuple(ref_clusters),
        test_clusters=tuple(test_clusters),
        homography=homography,
        homography_inv=homography_inv,
        raw_differences=tuple(raw),
        result=result,
    )


def compare_registered(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    registration_config: RegistrationConfig = RegistrationConfig(),
    occupancy_config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> RegisteredResult:
    """Compara gabarito e aluno por registro automatico + diferenca de ocupacao."""
    return run_registered_pipeline(
        reference_bgr, test_bgr, registration_config, occupancy_config
    ).result


def _count_components(foreground_mask: np.ndarray, min_area: int) -> int:
    count, _, stats, _ = cv2.connectedComponentsWithStats(foreground_mask, 8)
    return sum(1 for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= min_area)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _merge_cluster_group(group: list[Cluster]) -> Cluster:
    xs0 = [c.bbox[0] for c in group]
    ys0 = [c.bbox[1] for c in group]
    xs1 = [c.bbox[2] for c in group]
    ys1 = [c.bbox[3] for c in group]
    cx = sum(c.centroid[0] for c in group) / len(group)
    cy = sum(c.centroid[1] for c in group) / len(group)
    return Cluster(
        area=sum(c.area for c in group),
        centroid=(cx, cy),
        bbox=(min(xs0), min(ys0), max(xs1), max(ys1)),
        label=group[0].label,
    )


def _nearest(
    comp: Cluster, candidates: list[Cluster], used: set[int], max_distance: float
) -> int | None:
    best, best_key = None, None
    for i, other in enumerate(candidates):
        if i in used:
            continue
        distance = _distance(comp.centroid, other.centroid)
        if distance > max_distance:
            continue
        key = (other.label != comp.label, distance)
        if best_key is None or key < best_key:
            best_key, best = key, i
    return best
