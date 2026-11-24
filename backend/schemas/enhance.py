"""Pydantic v2 request and response schemas locked to the API contract."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class EnhanceParams(BaseModel):
    """Spatial-domain image enhancement parameters shared by preview and batch APIs."""

    denoise_mode: Literal["none", "median", "average", "morph_open_close"] = "none"
    kernel_size: Literal[3, 5, 7] = 3

    brightness_mode: Literal["none", "gamma", "log", "contrast_stretch"] = "gamma"
    gamma: float = Field(default=1.0, ge=0.2, le=4.0)
    auto_gamma: bool = False
    log_c: float = Field(default=1.0, ge=0.5, le=2.0)
    negative: bool = False

    stretch_r1: int = Field(default=30, ge=0, le=255)
    stretch_s1: int = Field(default=10, ge=0, le=255)
    stretch_r2: int = Field(default=225, ge=0, le=255)
    stretch_s2: int = Field(default=245, ge=0, le=255)

    contrast_mode: Literal["none", "hist_eq", "clahe"] = "none"
    clahe_clip_limit: float = Field(default=2.0, ge=1.0, le=8.0)

    sharpen_mode: Literal["none", "laplacian_4", "laplacian_8"] = "none"
    sharpen_alpha: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_stretch_bounds(self) -> "EnhanceParams":
        """Ensure contrast stretching control points satisfy r1 < r2."""
        if self.stretch_r1 >= self.stretch_r2:
            raise ValueError("stretch_r1 must be strictly less than stretch_r2")
        return self


class PreviewResponse(BaseModel):
    """Response payload for POST /api/preview."""

    processed_image: str
    hist_before: list[int]
    hist_after: list[int]
    applied_gamma: float | None
    processing_time_ms: float


class BatchCreateResponse(BaseModel):
    """Response payload for POST /api/batch-process."""

    job_id: str
    total: int
    status: Literal["queued", "processing", "done", "failed"]


class BatchStatusResponse(BaseModel):
    """Response payload for GET /api/batch-status/{job_id}."""

    job_id: str
    processed: int
    total: int
    status: Literal["queued", "processing", "done", "failed"]
    failed_files: list[str] = Field(default_factory=list)
    error: str | None = None
