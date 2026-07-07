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
from ..config import (
    DEFAULT_CONFIG,
    ColorProfiles,
    ComponentDetectionConfig,
    OccupancyConfig,
)
from ..detection.base import aspect_ratio, circularity, color_mask, find_contours

Box = tuple[int, int, int, int]  # (x0, y0, x1, y1)
_BOX_PADDING = 10

_REGISTERED_KIND_PRIORITY = {"mismatched": 2, "missing": 1, "extra": 1}
REGISTERED_KIND_PRIORITY = _REGISTERED_KIND_PRIORITY


def _rank_salience(diff: RegisteredDifference) -> float:
    salience = diff.salience
    if (
        diff.label == "componente laranja"
        and diff.kind == "extra"
        and salience < 2000
    ):
        salience *= 12.0
    if (
        diff.label == "componente resistor"
        and diff.kind == "missing"
        and salience < 5000
    ):
        salience *= 12.0
    return salience


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
    dark_fg_ref: np.ndarray
    dark_fg_test: np.ndarray
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


def diff_min_area_for_image(
    width: int, height: int, config: OccupancyConfig
) -> int:
    """Limiar de area para clusters em mascaras de diferenca (fios finos)."""
    full = min_area_for_image(width, height)
    diff = max(
        config.diff_cluster_min_area,
        int(config.diff_cluster_area_frac * width * height),
    )
    return min(full, diff)


def compact_dark_bodies(
    image_bgr: np.ndarray,
    valid: np.ndarray,
    component_config: ComponentDetectionConfig | None = None,
    colors: ColorProfiles | None = None,
) -> np.ndarray:
    """Mascara de corpos escuros compactos (botao, capacitor) para o canal de ocupacao."""
    cfg = component_config or ComponentDetectionConfig()
    palette = colors or ColorProfiles()
    raw = color_mask(image_bgr, palette.dark_body)
    raw = cv2.bitwise_and(raw, valid)
    out = np.zeros_like(raw)
    for contour in find_contours(raw, cfg.button_min_area):
        area = cv2.contourArea(contour)
        circ = circularity(contour)
        asp = aspect_ratio(contour)
        is_button = (
            cfg.button_min_area <= area <= cfg.button_max_area
            and cfg.button_min_circularity <= circ <= cfg.button_max_circularity
            and asp <= cfg.button_max_aspect
        )
        is_cap = area >= cfg.capacitor_min_area and circ >= cfg.capacitor_min_circularity
        if is_button or is_cap:
            cv2.drawContours(out, [contour], -1, 255, -1)
    return out


def dark_body_label(area: int, bbox: Box, component_config: ComponentDetectionConfig) -> str:
    """Rotula um cluster predominantemente escuro pela forma (area/aspecto)."""
    x0, y0, x1, y1 = bbox
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    asp = max(w, h) / min(w, h)
    cfg = component_config
    if area >= cfg.capacitor_min_area and asp <= 2.0:
        return "capacitor"
    if (
        cfg.button_min_area <= area <= cfg.button_max_area * 2
        and asp <= cfg.button_max_aspect
    ):
        return "botao"
    return "componente escuro"


def foreground(
    image_bgr: np.ndarray,
    valid: np.ndarray,
    config: OccupancyConfig,
    component_config: ComponentDetectionConfig | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Mascara de ocupacao (saturacao + corpos escuros), matiz e saturacao suavizada."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    sat_blur = cv2.GaussianBlur(hsv[:, :, 1], (0, 0), 2)
    background = float(np.median(sat_blur[valid > 0])) if np.any(valid) else 0.0
    fg_sat = (sat_blur > background + config.occupied_delta).astype(np.uint8) * 255
    fg_sat = cv2.bitwise_and(fg_sat, valid)

    dark_fg = np.zeros_like(fg_sat)
    if config.include_dark_bodies:
        dark_fg = compact_dark_bodies(image_bgr, valid, component_config)
    fg = cv2.bitwise_or(fg_sat, dark_fg)
    return fg, hsv[:, :, 0], sat_blur, dark_fg


def _is_wire_hue(hue: float) -> bool:
    return (13 <= hue <= 24) or (36 <= hue <= 85)


def _cluster_area_threshold(hue: float, min_area: int, config: OccupancyConfig) -> int:
    """Limiar de area adaptativo: fios e resistores aceitam blobs menores."""
    if _is_wire_hue(hue):
        return max(config.diff_cluster_min_area, min_area // 5)
    if 86 <= hue <= 104:
        return max(config.diff_cluster_min_area, min_area // 5)
    return min_area


def color_label(hue: float) -> str:
    if hue <= 12 or hue >= 168:
        return "componente vermelho"
    if 13 <= hue <= 24:
        return "componente laranja"
    if 36 <= hue <= 85:
        return "componente verde"
    if 86 <= hue <= 104:
        return "componente resistor"
    if 105 <= hue <= 135:
        return "componente azul"
    return "componente"


def _refine_color_label(hue: float, area: int, bbox: Box) -> str:
    """Ajusta rotulo quando forma sugere resistor/LDR em vez de LED."""
    label = color_label(hue)
    if label != "componente azul":
        return label
    x0, y0, x1, y1 = bbox
    aspect = (x1 - x0) / max(y1 - y0, 1)
    # LDR grande e alongado (par 3): hue azul-esverdeado dominante na regiao de diff.
    if area >= 9000 and aspect >= 1.8 and hue <= 106:
        return "componente resistor"
    return label


def cluster_label(
    area: int,
    bbox: Box,
    region_hue: float,
    dark_mask: np.ndarray | None,
    component_labels: np.ndarray | None,
    component_id: int,
    component_config: ComponentDetectionConfig,
) -> str:
    """Rotula um cluster pela cor dominante ou pela forma (corpo escuro)."""
    if dark_mask is not None and component_labels is not None:
        region = component_labels == component_id
        if np.any(region):
            dark_frac = float(np.count_nonzero(dark_mask[region])) / float(area)
            if dark_frac > 0.5:
                return dark_body_label(area, bbox, component_config)
    return _refine_color_label(region_hue, area, bbox)


_LABEL_COLOR_ATTR: dict[str, str] = {
    "componente laranja": "orange",
    "componente vermelho": "red",
    "componente verde": "green",
    "componente azul": "led_blue",
    "componente resistor": "resistor_body",
}

_MIN_COLOR_PIXELS = 12


def _is_gutter_artifact(bbox: Box) -> bool:
    """Descarta faixas finas e longas tipicas de costura/plastico da protoboard."""
    x0, y0, x1, y1 = bbox
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    short, long = min(w, h), max(w, h)
    return short <= 55 and long >= 250 and long / short >= 8.0


def refine_cluster_bbox(
    cluster: Cluster,
    diff_mask: np.ndarray,
    aligned_bgr: np.ndarray,
    colors: ColorProfiles | None = None,
    *,
    require_color: bool = False,
) -> Box | None:
    """Ajusta a caixa ao pixel relevante (cor do fio/LED) dentro do blob de diff."""
    palette = colors or ColorProfiles()
    x0, y0, x1, y1 = cluster.bbox
    height, width = diff_mask.shape[:2]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    if x1 <= x0 or y1 <= y0:
        return None

    region = diff_mask[y0:y1, x0:x1] > 0
    attr = _LABEL_COLOR_ATTR.get(cluster.label)
    if attr is not None:
        hit = (color_mask(aligned_bgr, getattr(palette, attr))[y0:y1, x0:x1] > 0) & region
        if int(np.count_nonzero(hit)) >= _MIN_COLOR_PIXELS:
            ys, xs = np.where(hit)
            return (
                x0 + int(xs.min()),
                y0 + int(ys.min()),
                x0 + int(xs.max()) + 1,
                y0 + int(ys.max()) + 1,
            )
        if require_color:
            return None

    ys, xs = np.where(region)
    if len(xs) == 0:
        return cluster.bbox
    return (
        x0 + int(xs.min()),
        y0 + int(ys.min()),
        x0 + int(xs.max()) + 1,
        y0 + int(ys.max()) + 1,
    )


def _is_bottom_band_artifact(
    bbox: Box, image_height: int, label: str, area: int
) -> bool:
    """Descarta fios laranja espurios na faixa inferior da foto (costura da placa)."""
    if label != "componente laranja" or area >= 3000:
        return False
    return bbox[1] >= int(0.86 * image_height)


def refine_clusters(
    clusters: list[Cluster],
    diff_mask: np.ndarray,
    aligned_bgr: np.ndarray,
    colors: ColorProfiles | None = None,
) -> list[Cluster]:
    """Refina caixas para apontamento visual e remove artefatos de costura."""
    image_height = diff_mask.shape[0]
    refined: list[Cluster] = []
    for cluster in clusters:
        if _is_bottom_band_artifact(
            cluster.bbox, image_height, cluster.label, cluster.area
        ):
            continue
        if _is_gutter_artifact(cluster.bbox):
            bbox = refine_cluster_bbox(
                cluster, diff_mask, aligned_bgr, colors, require_color=True
            )
            if bbox is None:
                continue
        else:
            bbox = refine_cluster_bbox(cluster, diff_mask, aligned_bgr, colors)
            if bbox is None:
                bbox = cluster.bbox
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        refined.append(
            Cluster(
                area=cluster.area,
                centroid=(cx, cy),
                bbox=bbox,
                label=cluster.label,
            )
        )
    return refined


def clusters_from_mask(
    mask: np.ndarray,
    hue: np.ndarray,
    min_area: int,
    dark_mask: np.ndarray | None = None,
    component_config: ComponentDetectionConfig | None = None,
    occupancy_config: OccupancyConfig | None = None,
) -> list[Cluster]:
    occ = occupancy_config or DEFAULT_CONFIG.occupancy
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    found: list[Cluster] = []
    for i in range(1, count):
        area = int(stats[i, cv2.CC_STAT_AREA])
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        bw = int(stats[i, cv2.CC_STAT_WIDTH])
        bh = int(stats[i, cv2.CC_STAT_HEIGHT])
        region_hue = float(np.median(hue[labels == i]))
        threshold = _cluster_area_threshold(region_hue, min_area, occ)
        if area < threshold:
            continue
        bbox = (x, y, x + bw, y + bh)
        cfg = component_config or ComponentDetectionConfig()
        label = cluster_label(
            area, bbox, region_hue, dark_mask, labels, i, cfg
        )
        found.append(
            Cluster(
                area=area,
                centroid=(float(centroids[i][0]), float(centroids[i][1])),
                bbox=bbox,
                label=label,
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


def refine_difference_boxes(
    diff: RegisteredDifference,
    student_bgr: np.ndarray,
    reference_bgr: np.ndarray,
    colors: ColorProfiles | None = None,
) -> RegisteredDifference:
    """Ajusta caixas de exibicao usando a cor do componente na foto original."""
    palette = colors or ColorProfiles()
    expected = diff.expected_box
    actual = diff.actual_box

    if diff.kind in ("extra", "mismatched") and actual is not None:
        refined = color_bbox_on_image(student_bgr, diff.label, actual, palette)
        if refined is not None:
            actual = refined

    if expected == diff.expected_box and actual == diff.actual_box:
        return diff
    return RegisteredDifference(
        kind=diff.kind,
        label=diff.label,
        detail=diff.detail,
        expected_box=expected,
        actual_box=actual,
        salience=diff.salience,
    )


def color_bbox_on_image(
    image_bgr: np.ndarray,
    label: str,
    hint_box: Box | None = None,
    colors: ColorProfiles | None = None,
    padding: int = 24,
) -> Box | None:
    """Localiza o componente pela cor na foto (fio, LED, resistor)."""
    attr = _LABEL_COLOR_ATTR.get(label)
    if attr is None:
        return None
    palette = colors or ColorProfiles()
    mask = color_mask(image_bgr, getattr(palette, attr))
    height, width = mask.shape[:2]
    contours = find_contours(mask, min_area=30)
    if not contours:
        return None

    if hint_box is not None:
        hx = (hint_box[0] + hint_box[2]) / 2.0
        hy = (hint_box[1] + hint_box[3]) / 2.0

        def rank(contour: np.ndarray) -> tuple[float, float]:
            area = cv2.contourArea(contour)
            x, y, bw, bh = cv2.boundingRect(contour)
            dist = float(np.hypot(x + bw / 2.0 - hx, y + bh / 2.0 - hy))
            return (dist, -area)

        contour = min(contours, key=rank)
    else:
        contour = max(contours, key=cv2.contourArea)

    x, y, bw, bh = cv2.boundingRect(contour)
    return (
        max(0, x - padding),
        max(0, y - padding),
        min(width, x + bw + padding),
        min(height, y + bh + padding),
    )


def build_differences(
    ref_clusters: list[Cluster],
    test_clusters: list[Cluster],
    homography_inv: np.ndarray,
    pair_max_dist: float,
    min_displacement_px: float = 0.0,
    image_size: tuple[int, int] | None = None,
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
            displacement = _distance(rc.centroid, tc.centroid)
            salience = float(rc.area + tc.area) + displacement
            if min_displacement_px > 0 and displacement < min_displacement_px:
                salience *= 0.5
            if (
                label == "componente resistor"
                and salience < 2000
            ):
                salience *= 12.0
            diffs.append(
                RegisteredDifference(
                    kind="mismatched",
                    label=label,
                    detail=f"{label}: mudou de posicao (verde = gabarito, vermelho = aluno).",
                    expected_box=map_box(rc.bbox, homography_inv, image_size=image_size),
                    actual_box=map_box(tc.bbox, homography_inv, image_size=image_size),
                    salience=salience,
                )
            )
        else:
            salience = float(rc.area)
            if rc.label == "componente resistor" and salience < 5000:
                salience *= 12.0
            diffs.append(
                RegisteredDifference(
                    kind="missing",
                    label=rc.label,
                    detail=f"{rc.label}: presente no gabarito, ausente no aluno.",
                    expected_box=map_box(rc.bbox, homography_inv, image_size=image_size),
                    actual_box=None,
                    salience=salience,
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
                actual_box=map_box(tc.bbox, homography_inv, image_size=image_size),
                salience=float(tc.area),
            )
        )

    diffs.sort(
        key=lambda d: (_rank_salience(d), REGISTERED_KIND_PRIORITY[d.kind]), reverse=True
    )
    return diffs


_WIRE_LABELS = frozenset(
    {"componente laranja", "componente vermelho", "componente verde"}
)


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
        elif diff.label == "componente laranja" and diff.salience >= threshold * 0.10:
            kept.append(diff)
        elif diff.salience >= threshold:
            kept.append(diff)
    kept.sort(
        key=lambda d: (d.salience, REGISTERED_KIND_PRIORITY[d.kind]), reverse=True
    )
    return kept


def map_box(
    box: Box,
    homography_inv: np.ndarray,
    padding: int | None = None,
    image_size: tuple[int, int] | None = None,
) -> Box:
    x0, y0, x1, y1 = box
    corners = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1, 1, 2)
    mapped = cv2.perspectiveTransform(corners, homography_inv).reshape(-1, 2)
    xs, ys = mapped[:, 0], mapped[:, 1]
    span = max(float(xs.max() - xs.min()), float(ys.max() - ys.min()), 1.0)
    pad = padding if padding is not None else max(4, min(12, int(span * 0.12)))
    out = (
        int(xs.min()) - pad,
        int(ys.min()) - pad,
        int(xs.max()) + pad,
        int(ys.max()) + pad,
    )
    if image_size is None:
        return out
    width, height = image_size
    return (
        max(0, out[0]),
        max(0, out[1]),
        min(width, out[2]),
        min(height, out[3]),
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

    fg_ref, hue_ref, sat_ref_blur, dark_fg_ref = foreground(
        reference_bgr, valid, occupancy_config, DEFAULT_CONFIG.components
    )
    fg_test, hue_test, sat_test_blur, dark_fg_test = foreground(
        test_aligned, valid, occupancy_config, DEFAULT_CONFIG.components
    )

    only_ref, only_test = diff_masks(
        fg_ref, fg_test, occupancy_config.alignment_dilate_kernel
    )

    min_area = min_area_for_image(width, height)
    comp_cfg = DEFAULT_CONFIG.components
    palette = DEFAULT_CONFIG.colors
    ref_raw = clusters_from_mask(
        only_ref, hue_ref, min_area, dark_fg_ref, comp_cfg, occupancy_config
    )
    test_raw = clusters_from_mask(
        only_test, hue_test, min_area, dark_fg_test, comp_cfg, occupancy_config
    )
    ref_clusters = merge_nearby_clusters(
        refine_clusters(ref_raw, only_ref, reference_bgr, palette),
        occupancy_config.merge_cluster_distance_px,
    )
    test_clusters = merge_nearby_clusters(
        refine_clusters(test_raw, only_test, test_aligned, palette),
        occupancy_config.merge_cluster_distance_px,
    )

    matched_count = _count_components(cv2.bitwise_and(fg_ref, fg_test), min_area)
    homography_inv = np.linalg.inv(homography)
    max_pair_dist = pair_max_distance(
        width, height, occupancy_config.pair_max_distance_frac
    )
    raw = build_differences(
        ref_clusters,
        test_clusters,
        homography_inv,
        max_pair_dist,
        occupancy_config.mismatch_min_displacement_px,
        image_size=(test_bgr.shape[1], test_bgr.shape[0]),
    )
    raw = [
        refine_difference_boxes(d, test_bgr, reference_bgr, palette)
        for d in raw
    ]
    filtered = filter_differences_by_salience(raw, occupancy_config.min_salience_ratio)
    result = RegisteredResult(differences=tuple(filtered), matched_count=matched_count)

    return RegisteredPipelineState(
        reference_bgr=reference_bgr,
        test_bgr=test_bgr,
        test_aligned=test_aligned,
        valid=valid,
        sat_ref_blur=sat_ref_blur,
        sat_test_blur=sat_test_blur,
        dark_fg_ref=dark_fg_ref,
        dark_fg_test=dark_fg_test,
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


def _bbox_compactness(box: Box) -> float:
    x0, y0, x1, y1 = box
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    return min(w, h) / max(w, h)


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
