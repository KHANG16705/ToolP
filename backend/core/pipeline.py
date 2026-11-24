"""Coordinator for the standard 5-step spatial-domain DIP enhancement pipeline."""

from dataclasses import dataclass
import numpy as np

from core.color_space import hsv_channels_to_rgb, rgb_to_hsv_channels
from core.filters import apply_denoising, apply_laplacian_sharpening
from core.histogram import apply_contrast_enhancement, compute_histogram
from core.point_ops import apply_point_operations
from schemas.enhance import EnhanceParams


@dataclass(frozen=True)
class PipelineResult:
    """Structured output returned by the 5-step enhancement pipeline."""

    processed_rgb: np.ndarray
    hist_before: list[int]
    hist_after: list[int]
    applied_gamma: float | None


def enhance_image(image_rgb: np.ndarray, params: EnhanceParams) -> PipelineResult:
    """Run the 5-step DIP pipeline on the Value (V) channel of an RGB uint8 image."""
    # Step 1: RGB -> HSV and capture baseline histogram of V channel
    h_channel, s_channel, v_channel = rgb_to_hsv_channels(image_rgb)
    hist_before = compute_histogram(v_channel)

    # Step 2: Denoising before sharpening to avoid amplifying noise
    v_denoised = apply_denoising(v_channel, params)

    # Step 3A: Point operations (brightness_mode -> optional negative)
    v_point, applied_gamma = apply_point_operations(v_denoised, params)

    # Step 3B: Histogram equalization / CLAHE
    v_contrast = apply_contrast_enhancement(v_point, params)

    # Step 4: Laplacian sharpening
    v_final = apply_laplacian_sharpening(
        v_contrast,
        sharpen_mode=params.sharpen_mode,
        alpha=params.sharpen_alpha,
    )

    # Step 5: Compute output histogram and merge HSV -> RGB
    hist_after = compute_histogram(v_final)
    processed_rgb = hsv_channels_to_rgb(h_channel, s_channel, v_final)

    return PipelineResult(
        processed_rgb=processed_rgb,
        hist_before=hist_before,
        hist_after=hist_after,
        applied_gamma=applied_gamma,
    )
