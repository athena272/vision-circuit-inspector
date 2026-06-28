"""Camada HTTP (FastAPI) que expoe a inspecao de circuitos.

Mantida fina e desacoplada do nucleo de visao: os endpoints apenas decodificam
as imagens, delegam ao pipeline e serializam o resultado via `schemas`/`mappers`.
"""

from .app import create_app

__all__ = ["create_app"]
