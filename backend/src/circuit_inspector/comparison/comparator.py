"""Comparacao entre o circuito gabarito e o do aluno.

Os componentes sao casados por `label` (tipo + cor, ex.: 'wire:red'). Dentro de
cada label, o casamento e guloso pelo maior numero de furos em comum. A partir
do casamento sao geradas as divergencias:

- MISMATCHED: componente presente nos dois, mas em furos diferentes.
- MISSING   : presente no gabarito e ausente no aluno.
- EXTRA     : presente no aluno e ausente no gabarito.
"""

from __future__ import annotations

from collections import defaultdict

from ..models import (
    ComparisonResult,
    Component,
    ComponentDifference,
    ComponentMatch,
    DifferenceKind,
    Placement,
)


def _group_by_label(placement: Placement) -> dict[str, list[Component]]:
    groups: dict[str, list[Component]] = defaultdict(list)
    for component in placement.components:
        groups[component.label].append(component)
    return groups


def _holes_text(component: Component) -> str:
    return "{" + ", ".join(sorted(h.label for h in component.hole_set)) + "}"


def _overlap(a: Component, b: Component) -> int:
    return len(a.hole_set & b.hole_set)


def _best_match_index(reference: Component, candidates: list[Component]) -> int | None:
    """Indice do candidato com maior sobreposicao de furos (None se vazio)."""
    if not candidates:
        return None
    scores = [(_overlap(reference, c), -i) for i, c in enumerate(candidates)]
    best_score, neg_index = max(scores)
    return -neg_index


def compare_placements(
    reference: Placement,
    test: Placement,
) -> ComparisonResult:
    """Compara dois placements e retorna as correspondencias e divergencias."""
    reference_groups = _group_by_label(reference)
    test_groups = _group_by_label(test)
    all_labels = set(reference_groups) | set(test_groups)

    matched: list[ComponentMatch] = []
    differences: list[ComponentDifference] = []

    for label in sorted(all_labels):
        ref_components = list(reference_groups.get(label, []))
        remaining_test = list(test_groups.get(label, []))

        for ref in ref_components:
            index = _best_match_index(ref, remaining_test)
            if index is None:
                differences.append(
                    ComponentDifference(
                        kind=DifferenceKind.MISSING,
                        detail=f"{label}: ausente no aluno (esperado em {_holes_text(ref)}).",
                        reference=ref,
                    )
                )
                continue

            candidate = remaining_test.pop(index)
            if ref.hole_set == candidate.hole_set:
                matched.append(ComponentMatch(reference=ref, test=candidate))
            else:
                differences.append(
                    ComponentDifference(
                        kind=DifferenceKind.MISMATCHED,
                        detail=(
                            f"{label}: esperado em {_holes_text(ref)}, "
                            f"encontrado em {_holes_text(candidate)}."
                        ),
                        reference=ref,
                        test=candidate,
                    )
                )

        for leftover in remaining_test:
            differences.append(
                ComponentDifference(
                    kind=DifferenceKind.EXTRA,
                    detail=f"{label}: presente no aluno em {_holes_text(leftover)}, sem correspondente no gabarito.",
                    test=leftover,
                )
            )

    return ComparisonResult(matched=tuple(matched), differences=tuple(differences))
