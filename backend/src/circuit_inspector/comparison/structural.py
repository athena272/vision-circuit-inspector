"""Comparacao estrutural por ocupacao de furo (tipo-agnostica).

Em fotos reais, classificar o *tipo* de cada componente por cor/forma e fragil
(ex.: resistor de corpo azul ~ LED azul; LDR cinza ~ fundo bege). Para o caso
"um erro por placa", o que importa e descobrir *onde* a ocupacao mudou entre o
gabarito e o aluno - independentemente do tipo.

Estrategia:
1. Para cada furo da area central, mede-se a *saturacao* (HSV) num patch ao
   redor. Componentes coloridos elevam a saturacao acima do fundo; furos vazios
   ficam proximos do fundo. Limiares sao adaptativos (relativos a saturacao
   mediana do board), o que da robustez a iluminacao/camera.
2. Compara-se furo a furo: ocupado no gabarito e vazio no aluno => "perdido";
   vazio no gabarito e ocupado no aluno => "ganho".
3. Agrupam-se furos adjacentes; cada agrupamento e uma regiao que mudou.
4. Pareiam-se regioes perdidas/ganhas de mesmo rotulo (componente que se moveu).

O resultado e um `ComparisonResult` padrao, reaproveitando relatorio, selecao do
erro principal e anotacao.

Limitacao: detecta mudancas de componentes *coloridos* (resistor, LED, jumpers).
Corpos de baixa saturacao (LDR cinza, fio preto) nao sao cobertos por este modo.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np

from ..board.grid_mapper import BoardGrid
from ..config import DEFAULT_CONFIG, OccupancyConfig
from ..models import (
    ComparisonResult,
    Component,
    ComponentDifference,
    ComponentKind,
    ComponentMatch,
    DifferenceKind,
    Hole,
    Terminal,
)


@dataclass(frozen=True)
class _HoleSample:
    hole: Hole
    saturation: float
    hue: float


def _local_pitch(grid: BoardGrid, hole: Hole) -> float:
    """Distancia em pixels ate o furo vizinho de coluna (escala local da malha)."""
    p = grid.hole_to_pixel(hole)
    neighbor = grid.hole_to_pixel(Hole(column=hole.column + 1, row=hole.row, rail=hole.rail))
    pitch = p.distance_to(neighbor)
    return pitch if pitch > 1e-3 else 1.0


def _sample(hsv: np.ndarray, grid: BoardGrid, hole: Hole, radius: int) -> _HoleSample | None:
    p = grid.hole_to_pixel(hole)
    x, y = int(round(p.x)), int(round(p.y))
    h, w = hsv.shape[:2]
    if not (radius <= x < w - radius and radius <= y < h - radius):
        return None
    patch = hsv[y - radius : y + radius, x - radius : x + radius].reshape(-1, 3)
    return _HoleSample(
        hole=hole,
        saturation=float(np.median(patch[:, 1])),
        hue=float(np.median(patch[:, 0])),
    )


def compute_occupancy(
    image_bgr: np.ndarray,
    grid: BoardGrid,
    config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> dict[Hole, _HoleSample]:
    """Amostra saturacao/matiz de cada furo da area central visivel na imagem."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    layout = grid.layout
    samples: dict[Hole, _HoleSample] = {}
    for column in range(layout.board.min_column, layout.board.max_column + 1):
        for row in layout.board.rows:
            hole = Hole(column=column, row=row)
            radius = max(4, int(_local_pitch(grid, hole) * config.patch_radius_frac))
            sample = _sample(hsv, grid, hole, radius)
            if sample is not None:
                samples[hole] = sample
    return samples


def _background_saturation(samples: dict[Hole, _HoleSample]) -> float:
    if not samples:
        return 0.0
    return float(np.median([s.saturation for s in samples.values()]))


_ROW_ORDER = "jihgfedcba"
_ROW_INDEX = {row: i for i, row in enumerate(_ROW_ORDER)}


def _adjacent(a: Hole, b: Hole) -> bool:
    if a.row is None or b.row is None:
        return False
    if a.column == b.column:
        return abs(_ROW_INDEX[a.row] - _ROW_INDEX[b.row]) == 1
    if a.row == b.row:
        return abs(a.column - b.column) == 1
    return False


def _cluster(holes: set[Hole]) -> list[frozenset[Hole]]:
    """Agrupa furos adjacentes (4-vizinhanca na malha logica)."""
    remaining = set(holes)
    clusters: list[frozenset[Hole]] = []
    while remaining:
        seed = remaining.pop()
        group = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for other in list(remaining):
                if _adjacent(current, other):
                    remaining.discard(other)
                    group.add(other)
                    queue.append(other)
        clusters.append(frozenset(group))
    return clusters


def _cluster_strength(
    cluster: frozenset[Hole],
    ref: dict[Hole, _HoleSample],
    test: dict[Hole, _HoleSample],
) -> float:
    total = 0.0
    for hole in cluster:
        sr = ref[hole].saturation if hole in ref else 0.0
        st = test[hole].saturation if hole in test else 0.0
        total += abs(sr - st)
    return total


def _infer_label(
    cluster: frozenset[Hole], samples: dict[Hole, _HoleSample]
) -> tuple[ComponentKind, str]:
    """Heuristica de rotulo a partir do matiz dominante e da geometria."""
    hues = [samples[h].hue for h in cluster if h in samples]
    hue = float(np.median(hues)) if hues else 0.0
    columns = {h.column for h in cluster}
    rows = {h.row for h in cluster if h.row is not None}
    col_span = max(columns) - min(columns) + 1
    elongated = len(rows) == 1 and col_span >= 2

    if hue <= 10 or hue >= 170:
        return (ComponentKind.WIRE, "wire:red") if not _compact(rows, col_span) else (ComponentKind.LED, "led:red")
    if 11 <= hue <= 22:
        return (ComponentKind.WIRE, "wire:orange")
    if 36 <= hue <= 85:
        return (ComponentKind.WIRE, "wire:green")
    if 86 <= hue <= 135:
        if elongated:
            return (ComponentKind.RESISTOR, "resistor")
        return (ComponentKind.LED, "led:blue")
    return (ComponentKind.RESISTOR, "componente")


def _compact(rows: set[str], col_span: int) -> bool:
    return len(rows) >= 2 and col_span <= 2


def _component(cluster: frozenset[Hole], grid: BoardGrid, kind: ComponentKind, label: str) -> Component:
    terminals = tuple(
        Terminal(pixel=grid.hole_to_pixel(hole), hole=hole)
        for hole in sorted(cluster)
    )
    return Component(kind=kind, label=label, terminals=terminals)


def _format_holes(holes: frozenset[Hole]) -> str:
    return "{" + ", ".join(h.label for h in sorted(holes)) + "}"


def compare_structural(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    reference_grid: BoardGrid,
    test_grid: BoardGrid,
    config: OccupancyConfig = DEFAULT_CONFIG.occupancy,
) -> ComparisonResult:
    """Compara dois circuitos por ocupacao de furo e retorna as diferencas."""
    ref = compute_occupancy(reference_bgr, reference_grid, config)
    test = compute_occupancy(test_bgr, test_grid, config)

    ref_bg = _background_saturation(ref)
    test_bg = _background_saturation(test)
    occ_ref = ref_bg + config.occupied_delta
    empty_ref = ref_bg + config.empty_delta
    occ_test = test_bg + config.occupied_delta
    empty_test = test_bg + config.empty_delta

    common = ref.keys() & test.keys()
    lost: set[Hole] = set()
    gained: set[Hole] = set()
    matched_holes: set[Hole] = set()
    for hole in common:
        sr = ref[hole].saturation
        st = test[hole].saturation
        if sr >= occ_ref and st <= empty_test:
            lost.add(hole)
        elif st >= occ_test and sr <= empty_ref:
            gained.add(hole)
        elif sr >= occ_ref and st >= occ_test:
            matched_holes.add(hole)

    lost_clusters = [
        c for c in _cluster(lost)
        if _cluster_strength(c, ref, test) >= config.min_cluster_strength
    ]
    gained_clusters = [
        c for c in _cluster(gained)
        if _cluster_strength(c, ref, test) >= config.min_cluster_strength
    ]

    differences = _build_differences(
        lost_clusters, gained_clusters, ref, test, reference_grid, test_grid
    )
    matched = tuple(
        ComponentMatch(
            reference=_component(c, reference_grid, ComponentKind.RESISTOR, "componente"),
            test=_component(c, test_grid, ComponentKind.RESISTOR, "componente"),
        )
        for c in _cluster(matched_holes)
    )
    return ComparisonResult(matched=matched, differences=tuple(differences))


def _build_differences(
    lost_clusters: list[frozenset[Hole]],
    gained_clusters: list[frozenset[Hole]],
    ref: dict[Hole, _HoleSample],
    test: dict[Hole, _HoleSample],
    reference_grid: BoardGrid,
    test_grid: BoardGrid,
) -> list[ComponentDifference]:
    """Pareia regioes perdidas/ganhas (mesmo rotulo) e monta as diferencas,
    ordenadas da mais forte para a mais fraca."""
    lost_info = [
        (c, *_infer_label(c, ref), _cluster_strength(c, ref, test)) for c in lost_clusters
    ]
    gained_info = [
        (c, *_infer_label(c, test), _cluster_strength(c, ref, test)) for c in gained_clusters
    ]
    lost_info.sort(key=lambda t: t[3], reverse=True)
    gained_info.sort(key=lambda t: t[3], reverse=True)

    used_gained: set[int] = set()
    diffs: list[tuple[float, ComponentDifference]] = []

    for lc, lkind, llabel, lstrength in lost_info:
        pair_index = next(
            (
                i
                for i, (_, _, glabel, _) in enumerate(gained_info)
                if i not in used_gained and glabel == llabel
            ),
            None,
        )
        if pair_index is not None:
            gc, gkind, glabel, gstrength = gained_info[pair_index]
            used_gained.add(pair_index)
            diff = ComponentDifference(
                kind=DifferenceKind.MISMATCHED,
                detail=f"{llabel}: esperado em {_format_holes(lc)}, encontrado em {_format_holes(gc)}.",
                reference=_component(lc, reference_grid, lkind, llabel),
                test=_component(gc, test_grid, gkind, glabel),
            )
            diffs.append((lstrength + gstrength, diff))
        else:
            diff = ComponentDifference(
                kind=DifferenceKind.MISSING,
                detail=f"{llabel}: presente no gabarito em {_format_holes(lc)}, ausente no aluno.",
                reference=_component(lc, reference_grid, lkind, llabel),
            )
            diffs.append((lstrength, diff))

    for i, (gc, gkind, glabel, gstrength) in enumerate(gained_info):
        if i in used_gained:
            continue
        diff = ComponentDifference(
            kind=DifferenceKind.EXTRA,
            detail=f"{glabel}: presente no aluno em {_format_holes(gc)}, ausente no gabarito.",
            test=_component(gc, test_grid, gkind, glabel),
        )
        diffs.append((gstrength, diff))

    diffs.sort(key=lambda t: t[0], reverse=True)
    return [d for _, d in diffs]
