"""Formatacao textual do resultado da comparacao."""

from __future__ import annotations

from ..models import ComparisonResult
from .registered import RegisteredResult
from .selection import most_salient_difference


def format_report(result: ComparisonResult, single_error: bool = False) -> str:
    """Gera um relatorio legivel do resultado da comparacao.

    Com `single_error=True`, foca na divergencia mais saliente (caso de "um erro
    por placa"), mantendo a saida enxuta.
    """
    if result.is_match:
        return (
            "OK: o circuito do aluno corresponde ao gabarito.\n"
            f"Componentes conferidos: {len(result.matched)}"
        )

    if single_error:
        top = most_salient_difference(result)
        assert top is not None  # ha divergencias pois nao e match
        lines = [
            "ERRO ENCONTRADO:",
            f"  - [{top.kind.value}] {top.detail}",
        ]
        extra = len(result.differences) - 1
        if extra > 0:
            lines.append(
                f"\n({extra} outra(s) diferenca(s) ignorada(s); use --all para ver todas.)"
            )
        return "\n".join(lines)

    lines = [
        "DIVERGENCIAS ENCONTRADAS:",
        f"  Componentes corretos : {len(result.matched)}",
        f"  Em furo errado       : {len(result.mismatched)}",
        f"  Faltando             : {len(result.missing)}",
        f"  Sobrando             : {len(result.extra)}",
        "",
    ]
    for diff in result.differences:
        lines.append(f"  - [{diff.kind.value}] {diff.detail}")
    return "\n".join(lines)


def format_registered_report(result: RegisteredResult, single_error: bool = False) -> str:
    """Relatorio do modo de registro automatico (zero clique)."""
    if result.is_match:
        return (
            "OK: o circuito do aluno corresponde ao gabarito.\n"
            f"Regioes conferidas: {result.matched_count}"
        )

    if single_error:
        top = result.differences[0]
        lines = ["ERRO ENCONTRADO:", f"  - [{top.kind}] {top.detail}"]
        extra = len(result.differences) - 1
        if extra > 0:
            lines.append(
                f"\n({extra} outra(s) diferenca(s) ignorada(s); use --all para ver todas.)"
            )
        return "\n".join(lines)

    lines = [
        "DIVERGENCIAS ENCONTRADAS:",
        f"  Regioes corretas : {result.matched_count}",
        f"  Diferencas       : {len(result.differences)}",
        "",
    ]
    for diff in result.differences:
        lines.append(f"  - [{diff.kind}] {diff.detail}")
    return "\n".join(lines)
