"""Testes de integracao da API HTTP via TestClient."""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from circuit_inspector.api.app import create_app

from tests.fixtures.synthetic_board import build_board, default_circuit


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def _png_bytes(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
def test_compare_identical_boards_reports_match(client: TestClient) -> None:
    board = build_board(default_circuit())
    png = _png_bytes(board.image)

    response = client.post(
        "/api/compare",
        files={
            "reference": ("ref.png", png, "image/png"),
            "test": ("test.png", png, "image/png"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_match"] is True
    assert body["differences"] == []
    assert body["test_width"] == board.image.shape[1]
    assert body["test_height"] == board.image.shape[0]


def test_compare_rejects_non_image(client: TestClient) -> None:
    response = client.post(
        "/api/compare",
        files={
            "reference": ("a.txt", b"not an image", "text/plain"),
            "test": ("b.txt", b"not an image", "text/plain"),
        },
    )

    assert response.status_code == 400


def test_compare_rejects_corrupt_image(client: TestClient) -> None:
    response = client.post(
        "/api/compare",
        files={
            "reference": ("a.png", b"\x89PNG\r\n\x1a\n garbage", "image/png"),
            "test": ("b.png", b"\x89PNG\r\n\x1a\n garbage", "image/png"),
        },
    )

    assert response.status_code == 400


def test_compare_requires_both_fields(client: TestClient) -> None:
    response = client.post(
        "/api/compare",
        files={"reference": ("ref.png", b"\x89PNG", "image/png")},
    )

    assert response.status_code == 422


def test_compare_stream_emits_steps_and_complete(client: TestClient) -> None:
    board = build_board(default_circuit())
    png = _png_bytes(board.image)

    with client.stream(
        "POST",
        "/api/compare/stream",
        files={
            "reference": ("ref.png", png, "image/png"),
            "test": ("test.png", png, "image/png"),
        },
    ) as response:
        assert response.status_code == 200
        events: list[dict] = []
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            import json

            events.append(json.loads(line.removeprefix("data: ")))

    step_events = [e for e in events if e.get("type") == "step"]
    complete = next(e for e in events if e.get("type") == "complete")
    assert len(step_events) == 6
    assert complete["percent"] == 100
    assert complete["result"]["is_match"] is True

