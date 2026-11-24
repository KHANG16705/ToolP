"""Color space conversions (RGB <-> HSV) and Unicode-safe image I/O."""

import base64
from pathlib import Path
import cv2
import numpy as np

from config import OUTPUT_JPEG_QUALITY, OUTPUT_WEBP_QUALITY, PREVIEW_JPEG_QUALITY


def decode_image_bytes_to_rgb(raw_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes into an RGB uint8 NumPy array (H x W x 3)."""
    if not raw_bytes:
        raise ValueError("Empty image payload")

    buffer = np.frombuffer(raw_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError("Unable to decode image bytes")

    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def encode_rgb_to_jpeg_base64(
    image_rgb: np.ndarray,
    quality: int = PREVIEW_JPEG_QUALITY,
) -> str:
    """Encode an RGB uint8 image into a base64 JPEG data URL."""
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, encoded = cv2.imencode(".jpg", image_bgr, encode_params)
    if not success:
        raise ValueError("Failed to encode preview JPEG")

    b64_data = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64_data}"


def read_image_file_rgb(file_path: Path) -> np.ndarray:
    """Read an image file from disk into RGB uint8 safely with Unicode paths."""
    raw_bytes = file_path.read_bytes()
    return decode_image_bytes_to_rgb(raw_bytes)


def write_image_file_rgb(file_path: Path, image_rgb: np.ndarray) -> None:
    """Write an RGB uint8 image to disk preserving the target file extension."""
    ext = file_path.suffix.lower() or ".jpg"
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

    encode_params: list[int] = []
    if ext in {".jpg", ".jpeg"}:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), OUTPUT_JPEG_QUALITY]
    elif ext == ".webp":
        encode_params = [int(cv2.IMWRITE_WEBP_QUALITY), OUTPUT_WEBP_QUALITY]

    success, encoded = cv2.imencode(ext, image_bgr, encode_params)
    if not success:
        raise ValueError(f"Failed to encode image with extension {ext}")

    file_path.write_bytes(encoded.tobytes())


def rgb_to_hsv_channels(image_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert RGB uint8 image to HSV and return separated (H, S, V) uint8 channels."""
    image_hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    h_channel, s_channel, v_channel = cv2.split(image_hsv)
    return h_channel, s_channel, v_channel


def hsv_channels_to_rgb(
    h_channel: np.ndarray,
    s_channel: np.ndarray,
    v_channel: np.ndarray,
) -> np.ndarray:
    """Merge (H, S, V) uint8 channels and convert back to RGB uint8."""
    image_hsv = cv2.merge([h_channel, s_channel, v_channel])
    return cv2.cvtColor(image_hsv, cv2.COLOR_HSV2RGB)
