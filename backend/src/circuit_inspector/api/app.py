"""Aplicacao FastAPI da inspecao de circuitos.

Expoe o modo de registro automatico (zero clique) como uma API HTTP. Os
endpoints sao finos: validam a entrada, delegam ao pipeline e serializam a
saida. Toda a logica de visao continua no nucleo (`circuit_inspector.*`).
"""

from __future__ import annotations

import os

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from ..board.registration import RegistrationError
from ..io.image_loader import ImageLoadError, decode_bgr
from ..pipeline import inspect_registered_images
from .mappers import to_compare_response
from .schemas import CompareResponse, HealthResponse

# Origens liberadas no CORS. Em dev, o Vite roda em 5173; sobrescrevivel por env
# (lista separada por virgula) para outros ambientes.
_DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
_MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB por imagem.


def _allowed_origins() -> list[str]:
    raw = os.getenv("CIRCUIT_INSPECTOR_CORS_ORIGINS")
    if not raw:
        return list(_DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


async def _read_image(upload: UploadFile, field: str):
    """Le e decodifica um upload em matriz BGR, validando tipo e tamanho."""
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O campo '{field}' deve ser uma imagem.",
        )

    data = await upload.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Imagem '{field}' excede o limite de 15 MB.",
        )

    try:
        return decode_bgr(data)
    except ImageLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Imagem '{field}' invalida: {exc}",
        ) from exc


def create_app() -> FastAPI:
    """Cria e configura a aplicacao FastAPI."""
    app = FastAPI(
        title="Circuit Inspector API",
        version="0.1.0",
        summary="Comparacao por visao computacional de circuitos em protoboard.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/compare", response_model=CompareResponse, tags=["inspection"])
    async def compare(
        reference: UploadFile = File(description="Foto do gabarito."),
        test: UploadFile = File(description="Foto do circuito do aluno."),
    ) -> CompareResponse:
        reference_bgr = await _read_image(reference, "reference")
        test_bgr = await _read_image(test, "test")

        try:
            inspection = inspect_registered_images(reference_bgr, test_bgr)
        except RegistrationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Nao foi possivel alinhar as duas fotos. Garanta enquadramentos "
                    f"semelhantes do mesmo circuito. ({exc})"
                ),
            ) from exc

        height, width = test_bgr.shape[:2]
        return to_compare_response(inspection.result, width, height)

    return app


app = create_app()


def run() -> None:
    """Sobe o servidor de desenvolvimento (entry point `circuit-inspector-api`)."""
    import uvicorn

    host = os.getenv("CIRCUIT_INSPECTOR_HOST", "127.0.0.1")
    port = int(os.getenv("CIRCUIT_INSPECTOR_PORT", "8000"))
    uvicorn.run("circuit_inspector.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
