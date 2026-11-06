"""Explicit optional preprocessing for Parallax Core 42.

Normalization is intentionally separate from measurement. The extractor never fits
a stain target implicitly. A caller must provide a recorded target matrix and target
concentrations, or fit a new target and preserve it as part of that study's protocol.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class FixedMacenkoNormalizer:
    """Mean-centred covariance implementation used by the verified recent studies."""

    def __init__(self, alpha: float = 1.0, beta: float = 0.15) -> None:
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.stain_matrix_target: np.ndarray | None = None
        self.maxC_target: np.ndarray | None = None

    @staticmethod
    def _od(image: np.ndarray) -> np.ndarray:
        return -np.log(np.clip(image.astype(np.float64) / 255.0, 1e-6, 1.0))

    def _get_stain_matrix(self, image: np.ndarray) -> np.ndarray:
        optical_density = self._od(image).reshape(-1, 3)
        tissue = optical_density[np.all(optical_density > self.beta, axis=1)]
        if len(tissue) < 10:
            raise ValueError("Too few tissue pixels for fixed Macenko normalization")
        covariance = np.cov(tissue.T)
        _, eigenvectors = np.linalg.eigh(covariance)
        plane = eigenvectors[:, 1:3]
        projected = tissue @ plane
        angles = np.arctan2(projected[:, 1], projected[:, 0])
        low = plane @ np.array([
            np.cos(np.percentile(angles, self.alpha)),
            np.sin(np.percentile(angles, self.alpha)),
        ])
        high = plane @ np.array([
            np.cos(np.percentile(angles, 100.0 - self.alpha)),
            np.sin(np.percentile(angles, 100.0 - self.alpha)),
        ])
        first, second = (low, high) if low[0] > high[0] else (high, low)
        stains = np.array([first, second], dtype=np.float64)
        stains /= np.linalg.norm(stains, axis=1, keepdims=True)
        return stains * np.sign(stains[:, :1])

    def fit(self, target: np.ndarray) -> "FixedMacenkoNormalizer":
        target = _validate_rgb(target)
        self.stain_matrix_target = self._get_stain_matrix(target)
        optical_density = self._od(target).reshape(-1, 3)
        concentrations = np.linalg.lstsq(
            self.stain_matrix_target.T,
            optical_density.T,
            rcond=None,
        )[0]
        self.maxC_target = np.percentile(concentrations, 99, axis=1)
        return self

    def set_target(self, stain_matrix: np.ndarray, max_concentrations: np.ndarray) -> None:
        stains = np.asarray(stain_matrix, dtype=np.float64)
        maximum = np.asarray(max_concentrations, dtype=np.float64)
        if stains.shape != (2, 3) or maximum.shape != (2,):
            raise ValueError("Expected a 2x3 stain matrix and two target concentrations")
        if not np.isfinite(stains).all() or not np.isfinite(maximum).all():
            raise ValueError("Normalizer target contains non-finite values")
        self.stain_matrix_target = stains.copy()
        self.maxC_target = maximum.copy()

    def transform(self, image: np.ndarray) -> np.ndarray:
        image = _validate_rgb(image)
        if self.stain_matrix_target is None or self.maxC_target is None:
            raise RuntimeError("Set or fit a target before normalization")
        source_stains = self._get_stain_matrix(image)
        optical_density = self._od(image).reshape(-1, 3)
        concentrations = np.linalg.lstsq(source_stains.T, optical_density.T, rcond=None)[0]
        source_maximum = np.percentile(concentrations, 99, axis=1)
        concentrations *= (self.maxC_target / (source_maximum + 1e-8))[:, None]
        reconstructed = self.stain_matrix_target.T @ concentrations
        normalized = np.clip(np.exp(-reconstructed.T), 0.0, 1.0)
        return (normalized.reshape(image.shape) * 255.0).astype(np.uint8)


def _validate_rgb(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected HxWx3 RGB input, got {array.shape}")
    if array.dtype != np.uint8:
        if np.issubdtype(array.dtype, np.floating) and array.min() >= 0 and array.max() <= 1:
            array = np.rint(array * 255.0).astype(np.uint8)
        else:
            array = np.clip(array, 0, 255).astype(np.uint8)
    return array


def load_target(path: str | Path) -> FixedMacenkoNormalizer:
    """Load a recorded fixed-Macenko target from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    normalizer = FixedMacenkoNormalizer(
        alpha=float(payload.get("alpha", 1.0)),
        beta=float(payload.get("beta", 0.15)),
    )
    normalizer.set_target(payload["stain_matrix_target"], payload["maxC_target"])
    return normalizer
