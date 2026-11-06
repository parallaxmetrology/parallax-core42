"""Clean patch-level implementation of the frozen Parallax 42-axis panel.

The numerical definitions are preserved from the verified v4.1 kernel. Notebook
configuration, batch sampling, reference-dependent deviation scoring, classification,
and survival analysis are deliberately outside this module.
"""

from __future__ import annotations

import hashlib
import math
import traceback
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, distance_transform_edt, gaussian_filter
from scipy.optimize import minimize_scalar
from scipy.spatial import ConvexHull
from scipy.spatial.distance import jensenshannon
from skimage import feature, measure
from skimage.filters import threshold_local
from skimage.morphology import closing, disk, opening, remove_small_objects

from .schema import AXES, OUTPUT_COLUMNS, SCHEMA_ID


HPE = np.array([
    [0.38971, 0.68898, -0.07868],
    [-0.22981, 1.18340, 0.04641],
    [0.00000, 0.00000, 1.00000],
])

HE_STAIN_MATRIX = np.array([
    [0.644211, 0.716556, 0.266844],
    [0.092789, 0.954111, 0.283111],
    [0.000000, 0.000000, 1.000000],
])


@dataclass(frozen=True)
class ExtractorConfig:
    """Numerical configuration frozen for the Core 42 v1.0 schema."""

    resize_long_edge_px: int = 512
    void_threshold: float = 0.18
    dog_center_sigma: float = 1.0
    dog_surround_sigma: float = 3.0
    dog_surround_weight: float = 0.65
    peripheral_band_fraction: float = 0.15
    blob_min_sigma: float = 6.0
    blob_max_sigma: float = 20.0
    blob_threshold: float = 0.05
    degenerate_void_ratio: float = 0.97

    @property
    def g4_scales(self) -> tuple[int, int, int]:
        return 1, 8, 32


FROZEN_CONFIG = ExtractorConfig()


def _norm01(values: np.ndarray) -> np.ndarray:
    minimum, maximum = values.min(), values.max()
    return (values - minimum) / (maximum - minimum + 1e-8)


def _degamma(values: np.ndarray) -> np.ndarray:
    return np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )


def _lab_l(linear_rgb: np.ndarray) -> np.ndarray:
    transform = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ])
    shape = linear_rgb.shape
    xyz = linear_rgb.reshape(-1, 3) @ transform.T
    xyz /= np.array([0.95047, 1.00000, 1.08883])

    def f(values: np.ndarray) -> np.ndarray:
        return np.where(values > 0.008856, values ** (1 / 3), 7.787 * values + 16 / 116)

    fy = f(xyz[:, 1])
    lightness = np.where(xyz[:, 1] > 0.008856, 116 * fy - 16, 903.3 * xyz[:, 1])
    return (lightness / 100.0).clip(0, 1).reshape(shape[:2])


def _lms(linear_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = (linear_rgb.reshape(-1, 3) @ HPE.T).clip(0).reshape(linear_rgb.shape)
    return values[:, :, 0], values[:, :, 1], values[:, :, 2]


def _deconvolve_he(srgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    optical_density = -np.log10(srgb.clip(1e-6, 1.0))
    stains = np.linalg.pinv(HE_STAIN_MATRIX) @ optical_density.reshape(-1, 3).T
    hematoxylin = stains[0].reshape(srgb.shape[:2]).clip(0)
    eosin = stains[1].reshape(srgb.shape[:2]).clip(0)
    return _norm01(hematoxylin), _norm01(eosin)


def _dog(field: np.ndarray, cfg: ExtractorConfig) -> np.ndarray:
    return np.maximum(
        0,
        gaussian_filter(field, cfg.dog_center_sigma)
        - cfg.dog_surround_weight * gaussian_filter(field, cfg.dog_surround_sigma),
    )


def _gradients(field: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gx = np.gradient(field, axis=1)
    gy = np.gradient(field, axis=0)
    return gx, gy, np.sqrt(gx**2 + gy**2)


def _centroid(field: np.ndarray) -> tuple[float, float]:
    normalized = _norm01(field)
    total = normalized.sum()
    if total < 1e-8:
        return 0.0, 0.0
    height, width = normalized.shape
    x = np.arange(width, dtype=np.float32)
    y = np.arange(height, dtype=np.float32)
    cx = (normalized.sum(axis=0) @ x) / total
    cy = (normalized.sum(axis=1) @ y) / total
    return float((cx - (width - 1) / 2) / width), float((cy - (height - 1) / 2) / height)


def _void_ratio(field: np.ndarray, cfg: ExtractorConfig) -> float:
    return float((_norm01(field) < cfg.void_threshold).sum() / field.size)


def _cohesion(field: np.ndarray) -> float:
    normalized = _norm01(field)
    total = normalized.sum()
    if total < 1e-8:
        return 0.0
    threshold = np.percentile(normalized, 75)
    return float(normalized[normalized >= threshold].sum() / total)


def _sdi(field: np.ndarray, cfg: ExtractorConfig) -> float:
    normalized = _norm01(field)
    height, width = normalized.shape
    active = normalized >= cfg.void_threshold
    if active.sum() < 2:
        return 0.0
    y, x = np.where(active)
    distances = np.sqrt((x - x.mean()) ** 2 + (y - y.mean()) ** 2)
    return float(distances.mean() / np.sqrt(width**2 + height**2))


def _rho(field: np.ndarray, cfg: ExtractorConfig) -> float:
    active = _norm01(field) >= cfg.void_threshold
    area = active.sum()
    if area < 3:
        return 0.0
    y, x = np.where(active)
    points = np.column_stack([x, y])
    if len(points) > 1500:
        points = points[np.linspace(0, len(points) - 1, 1500, dtype=int)]
    try:
        hull_area = ConvexHull(points).volume
        return 0.0 if hull_area < 1 else float(min(150, 100 * area / hull_area))
    except Exception:
        return 0.0


def _peripheral_fraction(field: np.ndarray, cfg: ExtractorConfig) -> float:
    normalized = _norm01(field)
    height, width = normalized.shape
    total = normalized.sum()
    if total < 1e-8:
        return 0.0
    bh, bw = int(height * cfg.peripheral_band_fraction), int(width * cfg.peripheral_band_fraction)
    edge = np.zeros((height, width), dtype=bool)
    edge[:bh, :] = True
    edge[height - bh :, :] = True
    edge[:, :bw] = True
    edge[:, width - bw :] = True
    return float(normalized[edge].sum() / total)


def _orientation_coherence(field: np.ndarray, gx: np.ndarray, gy: np.ndarray, cfg: ExtractorConfig) -> float:
    active = _norm01(field) >= cfg.void_threshold
    if active.sum() < 2:
        return 0.0
    magnitude = np.sqrt(gx[active] ** 2 + gy[active] ** 2) + 1e-8
    angles = (np.arctan2(gy[active], gx[active]) + np.pi) % (2 * np.pi)
    histogram, _ = np.histogram(angles, bins=8, range=(0, 2 * np.pi), weights=magnitude)
    probabilities = histogram / (histogram.sum() + 1e-8)
    entropy = -np.sum(probabilities[probabilities > 0] * np.log2(probabilities[probabilities > 0]))
    return float(1 - entropy / np.log2(8))


def _structural_thickness(field: np.ndarray, cfg: ExtractorConfig) -> float:
    normalized = _norm01(field)
    height, width = normalized.shape
    active = normalized >= cfg.void_threshold
    if active.sum() < 2:
        return 0.0
    distance = distance_transform_edt(active)
    return float(2 * distance[active].mean() / min(width, height))


def _kernel(field: np.ndarray, gx: np.ndarray, gy: np.ndarray, cfg: ExtractorConfig) -> dict[str, float]:
    dx, dy = _centroid(field)
    return {
        "dx": dx,
        "dy": dy,
        "rv": _void_ratio(field, cfg),
        "mu": _cohesion(field),
        "sdi": _sdi(field, cfg),
        "rho": _rho(field, cfg),
        "xp": _peripheral_fraction(field, cfg),
        "theta": _orientation_coherence(field, gx, gy, cfg),
        "ds": _structural_thickness(field, cfg),
    }


def _build_masks(srgb: np.ndarray, cfg: ExtractorConfig) -> tuple[list[dict], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    linear = _degamma(srgb)
    lightness = _lab_l(linear)
    l_cone, m_cone, s_cone = _lms(linear)
    hematoxylin, eosin = _deconvolve_he(srgb)
    ln, mn, sn = _norm01(l_cone), _norm01(m_cone), _norm01(s_cone)
    gx, gy, baseline = _gradients(lightness)
    baseline = _norm01(baseline)
    lm_field = _norm01(np.maximum(0, l_cone - m_cone))
    yb_field = _norm01(np.maximum(0, l_cone + m_cone - 2 * s_cone))
    lm_dog = _norm01(_dog(lm_field, cfg))
    confirmed = _norm01(baseline * lm_dog)
    cone_max = _norm01(np.maximum(np.maximum(_dog(ln, cfg), _dog(mn, cfg)), _dog(sn, cfg)))
    blind_spot = _norm01(lm_dog * (baseline < cfg.void_threshold).astype(np.float32))
    active = baseline[baseline > cfg.void_threshold]
    if active.size > 100:
        low = float(np.percentile(active, 30))
        high = float(np.percentile(active, 70))
    else:
        low = float(np.percentile(baseline, 70))
        high = float(np.percentile(baseline, 90))
    high = max(high, low * 1.5, low + 1e-3)
    canny = feature.canny(lightness, sigma=1.0, low_threshold=low, high_threshold=high)
    gap = _norm01(((baseline > cfg.void_threshold) & ~canny).astype(np.float32))
    masks = [
        {"short": "Baseline", "field": baseline, "group": "vtl"},
        {"short": "L cone", "field": _norm01(_dog(ln, cfg)), "group": "cone"},
        {"short": "M cone", "field": _norm01(_dog(mn, cfg)), "group": "cone"},
        {"short": "S cone", "field": _norm01(_dog(sn, cfg)), "group": "cone"},
        {"short": "L-M", "field": lm_dog, "group": "opponent"},
        {"short": "L+M-2S", "field": _norm01(_dog(yb_field, cfg)), "group": "opponent"},
        {"short": "Protanopia", "field": _norm01(_dog((mn + sn) / 2, cfg)), "group": "deficiency"},
        {"short": "Deuteranopia", "field": _norm01(_dog((ln + sn) / 2, cfg)), "group": "deficiency"},
        {"short": "Tritanopia", "field": _norm01(_dog((ln + mn) / 2, cfg)), "group": "deficiency"},
        {"short": "H-channel", "field": _norm01(_dog(hematoxylin, cfg)), "group": "he"},
        {"short": "E-channel", "field": _norm01(_dog(eosin, cfg)), "group": "he"},
        {"short": "Confirmed", "field": confirmed, "group": "combined"},
        {"short": "Cone max", "field": cone_max, "group": "combined"},
        {"short": "Blind spot", "field": blind_spot, "group": "combined"},
        {"short": "Canny", "field": _norm01(canny.astype(np.float32)), "group": "edge"},
        {"short": "Gap", "field": gap, "group": "edge"},
    ]
    return masks, gx, gy, baseline, lightness, hematoxylin, gap


def _coherence(masks: list[dict], cfg: ExtractorConfig) -> dict[str, object]:
    independent_groups = {"vtl", "cone", "opponent", "deficiency", "he"}
    independent = [
        mask for mask in masks
        if mask["group"] in independent_groups and mask.get("rv", 1.0) < cfg.degenerate_void_ratio
    ]
    degenerate = [mask["short"] for mask in masks if mask.get("rv", 0.0) >= cfg.degenerate_void_ratio]
    if len(independent) >= 2:
        coordinates = np.array([[mask["dx"], mask["dy"]] for mask in independent])
        distances = [
            np.linalg.norm(coordinates[i] - coordinates[j])
            for i in range(len(independent)) for j in range(i + 1, len(independent))
        ]
        omega = float(np.mean(distances))
    else:
        omega = float("nan")
    values = {mask["short"]: mask for mask in masks}
    confirmed_rv = values["Confirmed"]["rv"]
    cone_rv = values["Cone max"]["rv"]
    baseline_rv = values["Baseline"]["rv"]
    blind_rv = values["Blind spot"]["rv"]
    return {
        "omega": omega,
        "gamma": float(confirmed_rv - cone_rv),
        "delta_r": float(confirmed_rv - baseline_rv),
        "beta": float(1 - blind_rv),
        "degenerate": degenerate,
        "n_valid": len(independent),
    }


def _g1(lightness: np.ndarray) -> tuple[float, float]:
    height, width = lightness.shape
    x = np.arange(width, dtype=np.float32)
    y = np.arange(height, dtype=np.float32)
    points = []
    for sigma in [2, 4, 8, 16, 32]:
        blurred = gaussian_filter(lightness, sigma)
        total = blurred.sum()
        if total < 1e-8:
            points.append([0.5, 0.5])
        else:
            points.append([
                (blurred.sum(axis=0) @ x) / total / width,
                (blurred.sum(axis=1) @ y) / total / height,
            ])
    differences = np.diff(np.asarray(points), axis=0)
    path_length = float(np.sqrt((differences**2).sum(axis=1)).sum())
    vectors = differences / (np.sqrt((differences**2).sum(axis=1, keepdims=True)) + 1e-8)
    angles = [np.arccos(np.clip(vectors[i] @ vectors[i + 1], -1, 1)) for i in range(len(vectors) - 1)]
    return path_length, float(np.mean(angles)) if angles else 0.0


def _g2(lightness: np.ndarray) -> tuple[float, int, int, float, float]:
    height, width = lightness.shape
    blurred = gaussian_filter(lightness, 3.0)
    block_size = max(31, (min(height, width) // 10) | 1)
    threshold = threshold_local(blurred, block_size, offset=-0.02)
    voids = opening(~(blurred > threshold), disk(2))
    voids = closing(voids, disk(3))
    minimum_size = max(64, height * width // 500)
    # max_size=N removes components with size <=N, reproducing the historical
    # min_size threshold (which removed components with size <minimum_size).
    voids = remove_small_objects(voids, max_size=minimum_size - 1)
    regions = measure.regionprops(measure.label(voids))
    ratios = [r.axis_major_length / r.axis_minor_length for r in regions if r.axis_minor_length > 0]
    areas = [r.area for r in regions]
    count = len(regions)
    return (
        float(voids.mean()),
        count,
        min(128, count),
        float(np.mean(ratios)) if ratios else 1.0,
        float(max(areas) / (height * width)) if areas else 0.0,
    )


def _g3(lightness: np.ndarray) -> tuple[float, float]:
    gray = (lightness * 255).astype(np.uint8)
    low = float(np.percentile(gray, 85)) / 255.0
    high = float(np.percentile(gray, 97)) / 255.0
    edges = feature.canny(lightness, sigma=1.0, low_threshold=low, high_threshold=high)
    variances, densities = [], []
    for contour in measure.find_contours(edges.astype(float), 0.5):
        if len(contour) < 5:
            continue
        differences = np.diff(contour, axis=0)
        tangents = differences / (np.sqrt((differences**2).sum(axis=1, keepdims=True)) + 1e-8)
        angles = [np.arccos(np.clip(tangents[i] @ tangents[i + 1], -1, 1)) for i in range(len(tangents) - 1)]
        if angles:
            variances.append(float(np.var(angles)))
            signs = np.sign(np.asarray(angles) - np.mean(angles))
            densities.append(int(np.sum(np.diff(signs) != 0)) / (len(contour) + 1e-8))
    return (
        float(np.mean(variances)) if variances else 0.0,
        float(np.mean(densities)) if densities else 0.0,
    )


def _orientation_entropy(blurred: np.ndarray | None, gx_base: np.ndarray, gy_base: np.ndarray) -> float:
    if blurred is None:
        gx, gy = gx_base, gy_base
    else:
        gx, gy = np.gradient(blurred, axis=1), np.gradient(blurred, axis=0)
    magnitude = np.sqrt(gx**2 + gy**2)
    angles = (np.arctan2(gy, gx) + np.pi) % (2 * np.pi)
    histogram, _ = np.histogram(angles.ravel(), bins=36, range=(0, 2 * np.pi), weights=magnitude.ravel())
    probabilities = histogram / (histogram.sum() + 1e-8)
    entropy = -np.sum(probabilities[probabilities > 0] * np.log2(probabilities[probabilities > 0]))
    return float(entropy / np.log2(36) * 5.0)


def _g4(lightness: np.ndarray, gx: np.ndarray, gy: np.ndarray, cfg: ExtractorConfig) -> tuple[list[float], float]:
    entropies = [
        _orientation_entropy(None if sigma <= 1 else gaussian_filter(lightness, sigma), gx, gy)
        for sigma in cfg.g4_scales
    ]
    span = np.log(cfg.g4_scales[-1]) - np.log(cfg.g4_scales[0])
    return entropies, float((entropies[-1] - entropies[0]) / (span if span > 0 else 1.0))


def _sci(lightness: np.ndarray, gx: np.ndarray, gy: np.ndarray) -> float:
    height, width = lightness.shape
    magnitude = np.sqrt(gx**2 + gy**2)
    quadrants = [
        (slice(None, height // 2), slice(None, width // 2)),
        (slice(None, height // 2), slice(width // 2, None)),
        (slice(height // 2, None), slice(None, width // 2)),
        (slice(height // 2, None), slice(width // 2, None)),
    ]
    regional = 1 / (1 + np.var([magnitude[q].mean() for q in quadrants]) * 1000)
    angles = (np.arctan2(gy, gx) + np.pi) % (2 * np.pi)
    histogram, _ = np.histogram(angles.ravel(), bins=18, range=(0, 2 * np.pi), weights=magnitude.ravel())
    probabilities = histogram / (histogram.sum() + 1e-8)
    entropy = -np.sum(probabilities[probabilities > 0] * np.log2(probabilities[probabilities > 0]))
    alignment = 1 - entropy / np.log2(18)
    edge_scales = []
    for sigma in [1, 2, 4]:
        blurred = gaussian_filter(lightness, sigma)
        gx_scale, gy_scale = np.gradient(blurred, axis=1), np.gradient(blurred, axis=0)
        edge_scales.append(np.sqrt(gx_scale**2 + gy_scale**2).mean())
    scale_consistency = 1 / (1 + np.var(edge_scales) * 100)
    flattened = lightness.ravel() - lightness.mean()
    sample = flattened[: min(1000, len(flattened))]
    autocorrelation = np.correlate(sample, sample, mode="full")
    autocorrelation /= autocorrelation.max() + 1e-8
    rhythm = float(np.mean(np.abs(autocorrelation)) * 2)
    return float(np.clip((0.30 * regional + 0.30 * alignment + 0.25 * scale_consistency + 0.15 * rhythm) * 5.0, 0, 5))


def _standardized(value: float, mean: float, std: float) -> float:
    return float(np.clip((value - mean) / (std + 1e-8), -3.5, 3.5))


def _vcli(g1_len: float, g1_curv: float, g2_v: float, g2_chi: int, g2_ar: float, g2_cut: float, g3_kvar: float, g3_infl: float, g4: list[float], g4_slope: float, sci: float) -> float:
    z1 = _standardized(g1_len, 0.05, 0.04) + 0.5 * _standardized(g1_curv, 0.3, 0.25)
    z2 = (
        _standardized(g2_v, 0.3, 0.2)
        + 0.75 * _standardized(np.log(1 + g2_cut), 0.5, 0.4)
        + 0.5 * _standardized(g2_ar, 2.0, 1.5)
        + 0.5 * _standardized(-min(128, abs(g2_chi)), -30, 20)
    )
    z3 = _standardized(np.log(1 + g3_kvar), 0.3, 0.3) + _standardized(g3_infl, 0.2, 0.2)
    z4 = 0.5 * _standardized(g4[0], 2.5, 1.0) + 0.5 * _standardized(-g4_slope, 0.10, 0.15)
    raw = 0.25 * z1 + 0.20 * z2 + 0.27 * z3 + 0.20 * z4 + 0.08 * (sci / 5.0)
    return float(np.clip(2.5 + raw * 2.5 / 3.5, 0, 5))


def _radial_profile(field: np.ndarray, center: tuple[float, float], bins: int = 60) -> np.ndarray:
    height, width = field.shape
    cx, cy = center
    y, x = np.mgrid[0:height, 0:width]
    radius = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    maximum = np.sqrt(max(cx, width - 1 - cx) ** 2 + max(cy, height - 1 - cy) ** 2) + 1e-8
    normalized_radius = radius / maximum
    histogram = np.zeros(bins)
    edges = np.linspace(0, 1, bins + 1)
    for index in range(bins):
        mask = (normalized_radius >= edges[index]) & (normalized_radius < edges[index + 1])
        histogram[index] = field[mask].sum()
    return histogram / (histogram.sum() + 1e-8)


def _fit_radial(profile: np.ndarray) -> float:
    radius = np.linspace(0, 1, len(profile))

    def loss(alpha: float) -> float:
        expected = np.exp(-alpha * radius)
        expected /= expected.sum() + 1e-8
        return float(np.mean((expected - profile) ** 2))

    alpha = minimize_scalar(loss, bounds=(0.1, 200.0), method="bounded").x
    expected = np.exp(-alpha * radius)
    expected = (expected + 1e-12) / (expected + 1e-12).sum()
    observed = (profile + 1e-12) / (profile + 1e-12).sum()
    return float(1 - jensenshannon(observed, expected))


def _radial_compliance(field: np.ndarray) -> tuple[float, float, float]:
    normalized = _norm01(field)
    height, width = normalized.shape
    frame_center = ((width - 1) / 2, (height - 1) / 2)
    frame_score = _fit_radial(_radial_profile(normalized, frame_center))
    dx, dy = _centroid(normalized)
    structure_center = (dx * width + (width - 1) / 2, dy * height + (height - 1) / 2)
    structure_score = _fit_radial(_radial_profile(normalized, structure_center))
    return frame_score, structure_score, float(structure_score - frame_score)


def _blob(hematoxylin: np.ndarray, cfg: ExtractorConfig) -> tuple[float, float, float]:
    blobs = feature.blob_dog(
        hematoxylin,
        min_sigma=cfg.blob_min_sigma,
        max_sigma=cfg.blob_max_sigma,
        sigma_ratio=1.6,
        threshold=cfg.blob_threshold,
    )
    count = len(blobs)
    if count == 0:
        return 0.0, 0.0, 0.0
    radii = blobs[:, 2] * np.sqrt(2)
    area_units = hematoxylin.size / 10000.0
    return (
        float(count / area_units),
        float(radii.mean()),
        float(radii.std() / (radii.mean() + 1e-8)) if count > 1 else 0.0,
    )


def _prepare_rgb(rgb: np.ndarray, cfg: ExtractorConfig) -> tuple[np.ndarray, tuple[int, int], tuple[int, int]]:
    array = np.asarray(rgb)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected HxWx3 RGB input, got {array.shape}")
    if array.dtype != np.uint8:
        if np.issubdtype(array.dtype, np.floating) and array.min() >= 0 and array.max() <= 1:
            array = np.rint(array * 255.0).astype(np.uint8)
        else:
            array = np.clip(array, 0, 255).astype(np.uint8)
    original_height, original_width = array.shape[:2]
    scale = min(1.0, cfg.resize_long_edge_px / max(original_width, original_height))
    measured_width, measured_height = int(original_width * scale), int(original_height * scale)
    if scale < 1.0:
        array = np.asarray(Image.fromarray(array).resize((measured_width, measured_height), Image.Resampling.LANCZOS))
    return array, (original_width, original_height), (measured_width, measured_height)


def measure_rgb(rgb: np.ndarray, source_id: str = "", config: ExtractorConfig | None = None) -> dict[str, object]:
    """Measure one RGB patch and return metadata followed by the frozen 42 axes."""
    cfg = config or FROZEN_CONFIG
    if cfg != FROZEN_CONFIG:
        raise ValueError("Core 42 v1.0 constants are frozen; create a new schema for altered parameters")
    result: dict[str, object] = {
        "schema_id": SCHEMA_ID,
        "source_id": source_id,
        "status": "ok",
        "warning": "",
        "image_hash": "",
        "original_width_px": 0,
        "original_height_px": 0,
        "measured_width_px": 0,
        "measured_height_px": 0,
        "resize_long_edge_px": cfg.resize_long_edge_px,
        "confirmed_empty": False,
        "g4_scale_collapse": False,
        "degenerate_masks": "",
        "n_valid_masks": 0,
    }
    result.update({axis: float("nan") for axis in AXES})
    try:
        prepared, original, measured = _prepare_rgb(rgb, cfg)
        result.update({
            "original_width_px": original[0],
            "original_height_px": original[1],
            "measured_width_px": measured[0],
            "measured_height_px": measured[1],
            "image_hash": hashlib.md5(prepared.tobytes()).hexdigest()[:12],
        })
        srgb = prepared.astype(np.float32) / 255.0
        masks, gx, gy, baseline, lightness, hematoxylin, gap = _build_masks(srgb, cfg)
        for mask in masks:
            mask["dx"], mask["dy"] = _centroid(mask["field"])
            mask["rv"] = _void_ratio(mask["field"], cfg)
            mask["mu"] = _cohesion(mask["field"])
        confirmed = next(mask["field"] for mask in masks if mask["short"] == "Confirmed")
        if confirmed.sum() < 1e-4 * confirmed.size:
            result["confirmed_empty"] = True
            result["warning"] = "confirmed_empty"
            confirmed_kernel = {key: float("nan") for key in ["rv", "mu", "sdi", "rho", "xp", "theta", "ds"]}
        else:
            confirmed_kernel = _kernel(confirmed, gx, gy, cfg)
        baseline_kernel = _kernel(baseline, gx, gy, cfg)
        coherence = _coherence(masks, cfg)
        result["degenerate_masks"] = " ".join(coherence["degenerate"])
        result["n_valid_masks"] = coherence["n_valid"]
        g1_len, g1_curv = _g1(lightness)
        g2_v, g2_n, g2_chi, g2_ar, g2_cut = _g2(lightness)
        g3_kvar, g3_infl = _g3(lightness)
        g4_values, g4_slope = _g4(lightness, gx, gy, cfg)
        if cfg.g4_scales[2] == cfg.g4_scales[1]:
            result["g4_scale_collapse"] = True
            result["warning"] = (str(result["warning"]) + "; g4_scale_collapse").strip("; ")
        sci = _sci(lightness, gx, gy)
        vcli = _vcli(g1_len, g1_curv, g2_v, g2_chi, g2_ar, g2_cut, g3_kvar, g3_infl, g4_values, g4_slope, sci)
        rc_f, rc_s, drc = _radial_compliance(confirmed)
        try:
            blob_density, blob_size_mean, blob_size_cv = _blob(hematoxylin, cfg)
        except Exception as exc:
            blob_density = blob_size_mean = blob_size_cv = float("nan")
            result["warning"] = (str(result["warning"]) + f"; blob_error:{type(exc).__name__}").strip("; ")
        gap_rv = _void_ratio(gap, cfg)
        values = {
            "gap_rv": gap_rv,
            "gap_theta": _orientation_coherence(gap, gx, gy, cfg),
            "gap_delta_vs_baseline": gap_rv - baseline_kernel["rv"],
            "gap_ds": _structural_thickness(gap, cfg),
            "blob_density": blob_density,
            "blob_size_mean": blob_size_mean,
            "blob_size_cv": blob_size_cv,
            **{f"k_{key}": confirmed_kernel[key] for key in ["rv", "mu", "sdi", "rho", "xp", "theta", "ds"]},
            **{f"b_{key}": baseline_kernel[key] for key in ["rv", "mu", "sdi", "rho", "xp", "theta", "ds"]},
            "omega": coherence["omega"],
            "gamma": coherence["gamma"],
            "delta_r": coherence["delta_r"],
            "beta": coherence["beta"],
            "g1_len": g1_len,
            "g1_curv": g1_curv,
            "g2_V": g2_v,
            "g2_n": g2_n,
            "g2_AR": g2_ar,
            "g2_cut": g2_cut,
            "g3_kvar": g3_kvar,
            "g3_infl": g3_infl,
            "g4_s1": g4_values[0],
            "g4_s8": g4_values[1],
            "g4_s32": g4_values[2],
            "g4_slope": g4_slope,
            "sci": sci,
            "vcli_g": vcli,
            "rc_f": rc_f,
            "rc_s": rc_s,
            "drc": drc,
        }
        if tuple(values) != AXES:
            raise RuntimeError("Internal output order does not match frozen schema")
        result.update(values)
    except Exception:
        result["status"] = "error"
        result["warning"] = traceback.format_exc()[-500:]
    return {column: result[column] for column in OUTPUT_COLUMNS}


def measure_path(path: str | Path, source_id: str | None = None, config: ExtractorConfig | None = None) -> dict[str, object]:
    """Load and measure one image path."""
    image_path = Path(path)
    rgb = np.asarray(Image.open(image_path).convert("RGB"))
    return measure_rgb(rgb, source_id=image_path.name if source_id is None else source_id, config=config)
