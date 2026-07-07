"""Aplicacao FastAPI da inspecao de circuitos."""

from __future__ import annotations

import os

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ..board.registration import RegistrationError
from ..comparison.registered_audit import compare_registered_with_audit
from ..io.image_loader import ImageLoadError, decode_bgr
from .mappers import to_compare_response
from .schemas import CompareResponse, HealthResponse
from .streaming import stream_compare_events

_DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
_MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def _allowed_origins() -> list[str]:
    raw = os.getenv("CIRCUIT_INSPECTOR_CORS_ORIGINS")
    if not raw:
        return list(_DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


async def _read_image(upload: UploadFile, field: str):
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
    app = FastAPI(
        title="Circuit Inspector API",
        version="0.2.0",
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
        all: bool = Query(False, description="Retorna todas as divergencias (debug)."),
        include_audit: bool = Query(False, description="Inclui imagens das 6 etapas."),
    ) -> CompareResponse:
        reference_bgr = await _read_image(reference, "reference")
        test_bgr = await _read_image(test, "test")

        try:
            audit = compare_registered_with_audit(reference_bgr, test_bgr)
        except RegistrationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Nao foi possivel alinhar as duas fotos. Garanta enquadramentos "
                    f"semelhantes do mesmo circuito. ({exc})"
                ),
            ) from exc

        height, width = test_bgr.shape[:2]
        return to_compare_response(
            audit.result,
            width,
            height,
            single_error=not all,
            audit=audit if include_audit else None,
        )

    @app.post("/api/compare/stream", tags=["inspection"])
    async def compare_stream(
        reference: UploadFile = File(description="Foto do gabarito."),
        test: UploadFile = File(description="Foto do circuito do aluno."),
        all: bool = Query(False, description="Retorna todas as divergencias (debug)."),
    ) -> StreamingResponse:
        reference_bgr = await _read_image(reference, "reference")
        test_bgr = await _read_image(test, "test")

        async def event_generator():
            try:
                async for event in stream_compare_events(
                    reference_bgr, test_bgr, single_error=not all
                ):
                    yield event
            except RegistrationError as exc:
                from .streaming import _sse_event

                yield _sse_event(
                    {
                        "type": "error",
                        "message": (
                            "Nao foi possivel alinhar as duas fotos. "
                            f"({exc})"
                        ),
                    }
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    host = os.getenv("CIRCUIT_INSPECTOR_HOST", "127.0.0.1")
    port = int(os.getenv("CIRCUIT_INSPECTOR_PORT", "8000"))
    uvicorn.run("circuit_inspector.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
