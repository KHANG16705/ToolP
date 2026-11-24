"""Centralized configuration constants for the Batch Photo Enhancer backend."""

from pathlib import Path
import os

BASE_DIR: Path = Path(__file__).resolve().parent
TEMP_DIR: Path = BASE_DIR / "temp_jobs"

MAX_WORKERS: int = max(1, min(os.cpu_count() or 2, 8))
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})
CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_BATCH_FILES: int = 50
MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024

GRAY_LEVELS: int = 256
MAX_PIXEL_VALUE: float = 255.0
PREVIEW_JPEG_QUALITY: int = 90
OUTPUT_JPEG_QUALITY: int = 95
OUTPUT_WEBP_QUALITY: int = 95

AUTO_GAMMA_MIN: float = 0.25
AUTO_GAMMA_MAX: float = 3.5
AUTO_GAMMA_MEAN_MIN: float = 1.0
AUTO_GAMMA_MEAN_MAX: float = 254.0

CLAHE_TILE_GRID_SIZE: tuple[int, int] = (8, 8)

JOB_TTL_SECONDS: int = 30 * 60
ZIP_FILENAME: str = "enhanced_photos.zip"
