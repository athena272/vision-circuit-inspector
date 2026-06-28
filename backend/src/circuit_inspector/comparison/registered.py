"""Comparacao por registro automatico (zero clique, sem malha canonica).

Alinha a foto do aluno sobre a do gabarito (`board.registration`) e compara a
*ocupacao* (saturacao) pixel a pixel no frame ja alinhado. As regioes que mudam
de ocupacao sao as diferencas; sao pareadas (gabarito x aluno) como componente
que se moveu e anotadas de volta na foto original do aluno.

Nao depende de calibracao manual nem da malha logica a..j: o referencial e a
propria foto do gabarito. O rotulo e pela *cor* dominante da regiao alterada
(heuristica honesta): distinguir resistor x LED de forma confiavel exigiria
analise de forma do componente inteiro, fragil quando varios componentes
coloridos ficam proximos.

Limitacao: a ocupacao por saturacao cobre componentes *coloridos* (resistor,
LED, jumpers). Corpos de baixa saturacao (LDR cinza, fio preto) nao entram.
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


@dataclass(frozen=True)
class RegisteredDifference:
    """Uma diferenca localizada, ja em coordenadas da foto do aluno."""

    kind: str  # 'mismatched' | 'missing' | 'extra'
    label: str
    detail: str
    expected_box: Box | None  # posicao no gabarito (verde)
    actual_box: Box | None  # posicao no aluno (vermelho)
    salience: float


@dataclass(frozen=True)
class RegisteredResult:
    differences: tuple[RegisteredDifference, ...]
    matched_count: int

    @property
    def is_match(self) -> bool:
        return len(self.differences) == 0


@dataclass(frozen=True)
class _Cluster:
    """Uma regiao alterada (diff) no frame do gabarito."""

    area: int
    centroid: tuple[float, float]
    bbox: Box
    label: str


def _min_area(width: int, height: int) -> int:
    return max(250, int(0.00025 * width * height))


def _foreground(
    image_bgr: np.ndarray, valid: np.ndarray, config: OccupancyConfig
) -> tuple[np.ndarray, np.ndarray]:
    """Mascara de ocupacao por saturacao (adaptativa) e o canal de matiz."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    sat = cv2.GaussianBlur(hsv[:, :, 1], (0, 0), 2)
    background = float(np.median(sat[valid > 0])) if np.any(valid) else 0.0
    fg = (sat > background + config.occupied_delta).astype(np.uint8) * 255
    fg = cv2.bitwise_and(fg, valid)
    return fg, hsv[:, :, 0]


def _color_label(hue: float) -> str:
    if hue <= 12 or hue >= 168:
        return "componente vermelho"
    if 13 <= hue <= 24:
        return "componente laranja"
    if 36 <= hue <= 85:
        return "componente verde"
    if 86 <= hue <= 135:
        return "componente azul"
    return "componente"


def _clusters(mask: np.ndarray, hue: np.ndarray, min_area: int) -> list[_Cluster]:
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    clusters: list[_Cluster] = []
    for i in range(1, count):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        bw = int(stats[i, cv2.CC_STAT_WIDTH])
        bh = int(stats[i, cv2.CC_STAT_HEIGHT])
        region_hue = float(np.median(hue[labels == i]))
        clusters.append(
            _Cluster(
                area=area,
                centroid=(float(centroids[i][0]), float(centroids[i][1])),
                bbox=(x, y, x + bw, y + bh),
                label=_color_label(region_hue),
            )
        )
    return clusters


def _count_components(foreground: np.ndarray, min_area: int) -> int:
    count, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    return sum(1 for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= min_area)


def _map_box(box: Box, homography_inv: np.ndarray, padding: int = _BOX_PADDING) -> Box:
    """Leva uma bbox do frame do gabarito para a foto original do aluno."""
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


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _distance_cap(width: int, height: int) -> float:
    return 0.5 * float(np.hypot(width, height))


def compare_registered(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    registration_config: RegistrationConfig = RegistrationConfig(),
    occupancy_config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> RegisteredResult:
    """Compara gabarito e aluno por registro automatico + diferenca de ocupacao."""
    homography = estimate_registration(reference_bgr, test_bgr, registration_config)
    height, width = reference_bgr.shape[:2]
    test_aligned = warp_to_reference(test_bgr, homography, (width, height))
    valid = reference_validity_mask(test_bgr.shape, homography, (width, height))

    fg_ref, hue_ref = _foreground(reference_bgr, valid, occupancy_config)
    fg_test, hue_test = _foreground(test_aligned, valid, occupancy_config)

    kernel = np.ones((7, 7), np.uint8)
    only_ref = cv2.morphologyEx(cv2.subtract(fg_ref, cv2.dilate(fg_test, kernel)), cv2.MORPH_OPEN, kernel)
    only_test = cv2.morphologyEx(cv2.subtract(fg_test, cv2.dilate(fg_ref, kernel)), cv2.MORPH_OPEN, kernel)

    min_area = _min_area(width, height)
    ref_clusters = _clusters(only_ref, hue_ref, min_area)
    test_clusters = _clusters(only_test, hue_test, min_area)
    matched_count = _count_components(cv2.bitwise_and(fg_ref, fg_test), min_area)

    homography_inv = np.linalg.inv(homography)
    differences = _build_differences(
        ref_clusters, test_clusters, homography_inv, _distance_cap(width, height)
    )
    return RegisteredResult(differences=tuple(differences), matched_count=matched_count)


def _build_differences(
    ref_clusters: list[_Cluster],
    test_clusters: list[_Cluster],
    homography_inv: np.ndarray,
    pair_max_distance: float,
) -> list[RegisteredDifference]:
    ref_sorted = sorted(ref_clusters, key=lambda c: c.area, reverse=True)
    test_sorted = sorted(test_clusters, key=lambda c: c.area, reverse=True)
    used: set[int] = set()
    diffs: list[RegisteredDifference] = []

    for rc in ref_sorted:
        best = _nearest(rc, test_sorted, used, pair_max_distance)
        if best is not None:
            used.add(best)
            tc = test_sorted[best]
            label = rc.label if rc.label != "componente" else tc.label
            diffs.append(
                RegisteredDifference(
                    kind="mismatched",
                    label=label,
                    detail=f"{label}: mudou de posicao (verde = gabarito, vermelho = aluno).",
                    expected_box=_map_box(rc.bbox, homography_inv),
                    actual_box=_map_box(tc.bbox, homography_inv),
                    salience=float(rc.area + tc.area) + _distance(rc.centroid, tc.centroid),
                )
            )
        else:
            diffs.append(
                RegisteredDifference(
                    kind="missing",
                    label=rc.label,
                    detail=f"{rc.label}: presente no gabarito, ausente no aluno.",
                    expected_box=_map_box(rc.bbox, homography_inv),
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
                actual_box=_map_box(tc.bbox, homography_inv),
                salience=float(tc.area),
            )
        )

    # Uma troca de posicao (mismatched) e mais informativa que faltando/sobrando
    # (que costumam ser artefatos); por isso o tipo domina a magnitude.
    diffs.sort(key=lambda d: (_KIND_PRIORITY[d.kind], d.salience), reverse=True)
    return diffs


_KIND_PRIORITY = {"mismatched": 2, "missing": 1, "extra": 1}


def _nearest(
    comp: _Cluster, candidates: list[_Cluster], used: set[int], max_distance: float
) -> int | None:
    """Indice do candidato nao usado mais proximo (preferindo mesma cor)."""
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
