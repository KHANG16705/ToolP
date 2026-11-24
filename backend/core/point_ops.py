"""Spatial-domain point operations s = T(r) operating on the 8-bit Value (V) channel."""

import numpy as np

from config import (
    AUTO_GAMMA_MAX,
    AUTO_GAMMA_MEAN_MAX,
    AUTO_GAMMA_MEAN_MIN,
    AUTO_GAMMA_MIN,
    GRAY_LEVELS,
    MAX_PIXEL_VALUE,
)
from schemas.enhance import EnhanceParams


def compute_auto_gamma(v_channel: np.ndarray) -> float:
    """Estimate gamma = log(0.5) / log(mean_v / 255) clamped to [0.25, 3.5]."""
    mean_v = float(np.clip(np.mean(v_channel), AUTO_GAMMA_MEAN_MIN, AUTO_GAMMA_MEAN_MAX))
    raw_gamma = float(np.log(0.5) / np.log(mean_v / MAX_PIXEL_VALUE))
    clamped = float(np.clip(raw_gamma, AUTO_GAMMA_MIN, AUTO_GAMMA_MAX))
    return round(clamped, 4)


def apply_gamma_correction(
    v_channel: np.ndarray,
    gamma: float,
    auto_gamma: bool = False,
) -> tuple[np.ndarray, float]:
    """Apply power-law transform s = (r / 255) ** gamma * 255."""
    effective_gamma = compute_auto_gamma(v_channel) if auto_gamma else round(float(gamma), 4)
    r_norm = v_channel.astype(np.float32) / MAX_PIXEL_VALUE
    s_norm = np.power(r_norm, effective_gamma)
    result = np.clip(s_norm * MAX_PIXEL_VALUE, 0.0, MAX_PIXEL_VALUE).astype(np.uint8)
    return result, effective_gamma


def apply_log_transform(v_channel: np.ndarray, log_c: float = 1.0) -> np.ndarray:
    """Apply logarithmic transform s = (log_c * c_base) * log(1 + r)."""
    c_base = MAX_PIXEL_VALUE / float(np.log(1.0 + MAX_PIXEL_VALUE))
    transformed = (float(log_c) * c_base) * np.log1p(v_channel.astype(np.float32))
    return np.clip(transformed, 0.0, MAX_PIXEL_VALUE).astype(np.uint8)


def build_contrast_stretch_lut(r1: int, s1: int, r2: int, s2: int) -> np.ndarray:
    """Build a 256-entry piecewise-linear LUT through (0,0)->(r1,s1)->(r2,s2)->(255,255)."""
    r_vals = np.arange(GRAY_LEVELS, dtype=np.float32)
    lut = np.empty(GRAY_LEVELS, dtype=np.float32)

    low_mask = r_vals <= r1
    mid_mask = (r_vals > r1) & (r_vals <= r2)
    high_mask = r_vals > r2

    lut[low_mask] = (float(s1) / max(r1, 1)) * r_vals[low_mask]
    lut[mid_mask] = float(s1) + ((float(s2 - s1) / max(r2 - r1, 1)) * (r_vals[mid_mask] - r1))
    lut[high_mask] = float(s2) + (
        (float(MAX_PIXEL_VALUE - s2) / max(int(MAX_PIXEL_VALUE) - r2, 1)) * (r_vals[high_mask] - r2)
    )
    return np.clip(np.round(lut), 0.0, MAX_PIXEL_VALUE).astype(np.uint8)


def apply_contrast_stretching(
    v_channel: np.ndarray,
    r1: int,
    s1: int,
    r2: int,
    s2: int,
) -> np.ndarray:
    """Apply piecewise-linear contrast stretching via a 256-entry LUT."""
    lut = build_contrast_stretch_lut(r1, s1, r2, s2)
    return lut[v_channel]


def apply_negative(v_channel: np.ndarray) -> np.ndarray:
    """Apply image negative transform s = 255 - r."""
    return (int(MAX_PIXEL_VALUE) - v_channel).astype(np.uint8)


def apply_point_operations(
    v_channel: np.ndarray,
    params: EnhanceParams,
) -> tuple[np.ndarray, float | None]:
    """Execute Step 3A: brightness_mode first, followed by negative if enabled."""
    applied_gamma: float | None = None
    result = v_channel

    if params.brightness_mode == "gamma":
        result, applied_gamma = apply_gamma_correction(
            result,
            gamma=params.gamma,
            auto_gamma=params.auto_gamma,
        )
    elif params.brightness_mode == "log":
        result = apply_log_transform(result, log_c=params.log_c)
    elif params.brightness_mode == "contrast_stretch":
        result = apply_contrast_stretching(
            result,
            r1=params.stretch_r1,
            s1=params.stretch_s1,
            r2=params.stretch_r2,
            s2=params.stretch_s2,
        )

    if params.negative:
        result = apply_negative(result)

    return result, applied_gamma
