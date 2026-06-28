"""Testes do registro automatico por features (board.registration)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from circuit_inspector.board.registration import (
    RegistrationConfig,
    RegistrationError,
    estimate_registration,
)


def _textured_image(seed: int = 0, size: int = 400) -> np.ndarray:
    """Imagem com textura rica (nao repetitiva) para o SIFT encontrar features."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size, 3), 230, np.uint8)
    for _ in range(120):
        center = (int(rng.integers(0, size)), int(rng.integers(0, size)))
        color = tuple(int(c) for c in rng.integers(0, 255, size=3))
        if rng.random() < 0.5:
            cv2.circle(img, center, int(rng.integers(4, 18)), color, -1)
        else:
            pt2 = (int(rng.integers(0, size)), int(rng.integers(0, size)))
            cv2.line(img, center, pt2, color, int(rng.integers(1, 4)))
    return img


def _known_homography(size: int) -> np.ndarray:
    src = np.float32([[0, 0], [size, 0], [size, size], [0, size]])
    dst = np.float32([[12, 8], [size - 6, 14], [size - 18, size - 10], [10, size - 20]])
    return cv2.getPerspectiveTransform(src, dst)


class TestEstimateRegistration:
    def test_recovers_known_homography(self) -> None:
        size = 400
        reference = _textured_image(seed=1, size=size)
        H_known = _known_homography(size)
        test = cv2.warpPerspective(reference, H_known, (size, size))

        estimated = estimate_registration(reference, test)

        # estimated leva test -> reference; aplicado aos pontos do test (H_known @ p)
        # deve recuperar os pontos originais p.
        pts = np.float32([[50, 60], [300, 80], [120, 350], [350, 350]]).reshape(-1, 1, 2)
        in_test = cv2.perspectiveTransform(pts, H_known)
        recovered = cv2.perspectiveTransform(in_test, estimated)
        error = np.linalg.norm(recovered.reshape(-1, 2) - pts.reshape(-1, 2), axis=1)
        assert float(error.max()) < 3.0

    def test_raises_when_no_features(self) -> None:
        blank_a = np.full((200, 200, 3), 128, np.uint8)
        blank_b = np.full((200, 200, 3), 128, np.uint8)
        with pytest.raises(RegistrationError):
            estimate_registration(blank_a, blank_b, RegistrationConfig(min_inliers=25))
