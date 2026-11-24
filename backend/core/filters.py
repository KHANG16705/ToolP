"""Spatial denoising filters, morphological open-close, and Laplacian sharpening."""

import cv2
import numpy as np

from config import MAX_PIXEL_VALUE
from schemas.enhance import EnhanceParams

KERNEL_LAP_4: np.ndarray = np.array(
    [
        [0, 1, 0],
        [1, -4, 1],
        [0, 1, 0],
    ],
    dtype=np.float32,
)

KERNEL_LAP_8: np.ndarray = np.array(
    [
        [1, 1, 1],
        [1, -8, 1],
        [1, 1, 1],
    ],
    dtype=np.float32,
)


def apply_average_filter(v_channel: np.ndarray, kernel_size: int) -> np.ndarray:
    """Apply k x k box averaging filter with replicate border padding."""
    weight = 1.0 / float(kernel_size * kernel_size)
    kernel = np.full((kernel_size, kernel_size), weight, dtype=np.float32)
    filtered = cv2.filter2D(
        v_channel.astype(np.float32),
        ddepth=cv2.CV_32F,
        kernel=kernel,
        borderType=cv2.BORDER_REPLICATE,
    )
    return np.clip(filtered, 0.0, MAX_PIXEL_VALUE).astype(np.uint8)


def apply_median_filter(v_channel: np.ndarray, kernel_size: int) -> np.ndarray:
    """Apply k x k median filter via OpenCV for fast salt-and-pepper noise removal."""
    return cv2.medianBlur(v_channel, int(kernel_size))


def apply_morph_open_close(v_channel: np.ndarray, kernel_size: int) -> np.ndarray:
    """Apply Opening followed by Closing with a square k x k structuring element."""
    structuring_element = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    opened = cv2.morphologyEx(
        v_channel,
        cv2.MORPH_OPEN,
        structuring_element,
        borderType=cv2.BORDER_REPLICATE,
    )
    return cv2.morphologyEx(
        opened,
        cv2.MORPH_CLOSE,
        structuring_element,
        borderType=cv2.BORDER_REPLICATE,
    )


def apply_denoising(v_channel: np.ndarray, params: EnhanceParams) -> np.ndarray:
    """Execute Step 2 spatial denoising before sharpening."""
    if params.denoise_mode == "average":
        return apply_average_filter(v_channel, params.kernel_size)
    if params.denoise_mode == "median":
        return apply_median_filter(v_channel, params.kernel_size)
    if params.denoise_mode == "morph_open_close":
        return apply_morph_open_close(v_channel, params.kernel_size)
    return v_channel


def apply_laplacian_sharpening(
    v_channel: np.ndarray,
    sharpen_mode: str,
    alpha: float,
) -> np.ndarray:
    """Execute Step 4 sharpening: g(x, y) = f(x, y) - alpha * Laplacian(f)."""
    if sharpen_mode == "none" or alpha <= 0.0:
        return v_channel

    kernel = KERNEL_LAP_4 if sharpen_mode == "laplacian_4" else KERNEL_LAP_8
    v_float = v_channel.astype(np.float32)
    laplacian = cv2.filter2D(
        v_float,
        ddepth=cv2.CV_32F,
        kernel=kernel,
        borderType=cv2.BORDER_REPLICATE,
    )
    sharpened = v_float - (float(alpha) * laplacian)
    return np.clip(sharpened, 0.0, MAX_PIXEL_VALUE).astype(np.uint8)
