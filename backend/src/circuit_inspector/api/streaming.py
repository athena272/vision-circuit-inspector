"""Streaming SSE da comparacao."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import numpy as np

from ..comparison.registered_audit import (
    TOTAL_STEPS,
    PipelineStep,
    RegisteredAudit,
    iter_registered_audit,
)
from .mappers import pipeline_step_to_dto, to_compare_response


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _eta_ms(completed_steps: int, elapsed_ms: int) -> int | None:
    if completed_steps <= 0:
        return None
    avg = elapsed_ms / completed_steps
    return int(avg * (TOTAL_STEPS - completed_steps))


def build_step_event(step: PipelineStep, elapsed_ms: int) -> dict:
    return {
        "type": "step",
        "step": step.id,
        "total": TOTAL_STEPS,
        "title": step.title,
        "description": step.description,
        "percent": int(step.id / TOTAL_STEPS * 100),
        "elapsed_ms": elapsed_ms,
        "eta_ms": _eta_ms(step.id, elapsed_ms),
        "image": step.image_data_url,
    }


def build_complete_event(
    audit: RegisteredAudit,
    test_width: int,
    test_height: int,
    single_error: bool,
) -> dict:
    result = to_compare_response(
        audit.result,
        test_width,
        test_height,
        single_error=single_error,
        audit=audit,
    )
    return {
        "type": "complete",
        "percent": 100,
        "result": result.model_dump(),
        "audit": [pipeline_step_to_dto(s).model_dump() for s in audit.steps],
    }


async def stream_compare_events(
    reference_bgr: np.ndarray,
    test_bgr: np.ndarray,
    single_error: bool,
) -> AsyncIterator[str]:
    """Gera eventos SSE conforme cada etapa do pipeline e conclui com o resultado."""
    start = time.perf_counter()
    try:
        for item in iter_registered_audit(reference_bgr, test_bgr):
            if isinstance(item, PipelineStep):
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                yield _sse_event(build_step_event(item, elapsed_ms))
            elif isinstance(item, RegisteredAudit):
                height, width = test_bgr.shape[:2]
                yield _sse_event(build_complete_event(item, width, height, single_error))
    except Exception as exc:
        yield _sse_event({"type": "error", "message": str(exc)})
