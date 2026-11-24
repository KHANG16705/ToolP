"""Histogram calculation, textbook NumPy histogram equalization, and CLAHE."""

import cv2
import numpy as np

from config import CLAHE_TILE_GRID_SIZE, GRAY_LEVELS, MAX_PIXEL_VALUE
from schemas.enhance import EnhanceParams


def compute_histogram(v_channel: np.ndarray) -> list[int]:
    """Compute a 256-bin intensity histogram for an 8-bit V channel."""
    counts = np.bincount(v_channel.ravel(), minlength=GRAY_LEVELS)
    return [int(value) for value in counts[:GRAY_LEVELS]]


def apply_histogram_equalization(v_channel: np.ndarray) -> np.ndarray:
    """Apply global histogram equalization using pure NumPy: s_k = round(255 * CDF(r_k))."""
    counts = np.bincount(v_channel.ravel(), minlength=GRAY_LEVELS)
    pdf = counts / float(v_channel.size)
    cdf = np.cumsum(pdf)
    lut = np.round(MAX_PIXEL_VALUE * cdf).astype(np.uint8)
    return lut[v_channel]


def apply_clahe(v_channel: np.ndarray, clip_limit: float) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) with 8x8 tiles."""
    clahe = cv2.createCLAHE(
        clipLimit=float(clip_limit),
        tileGridSize=CLAHE_TILE_GRID_SIZE,
    )
    return clahe.apply(v_channel)


def apply_contrast_enhancement(v_channel: np.ndarray, params: EnhanceParams) -> np.ndarray:
    """Execute Step 3B contrast enhancement according to contrast_mode."""
    if params.contrast_mode == "hist_eq":
        return apply_histogram_equalization(v_channel)
    if params.contrast_mode == "clahe":
        return apply_clahe(v_channel, clip_limit=params.clahe_clip_limit)
    return v_channel
