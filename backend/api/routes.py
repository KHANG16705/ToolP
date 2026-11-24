"""REST API endpoints adhering strictly to the Batch Photo Enhancer API contract."""

import json
from pathlib import Path
import time
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.background import BackgroundTask

from config import (
    ALLOWED_CONTENT_TYPES,
    MAX_BATCH_FILES,
    MAX_FILE_SIZE_BYTES,
    ZIP_FILENAME,
)
from core.color_space import decode_image_bytes_to_rgb, encode_rgb_to_jpeg_base64
from core.pipeline import enhance_image
from schemas.enhance import (
    BatchCreateResponse,
    BatchStatusResponse,
    EnhanceParams,
    PreviewResponse,
)
from services.batch_service import (
    cleanup_job_files,
    create_batch_job,
    get_batch_job,
)

router = APIRouter(prefix="/api", tags=["Image Enhancement"])


def _parse_enhance_params(params_json: str) -> EnhanceParams:
    """Parse and validate JSON params string against EnhanceParams schema."""
    try:
        raw_data = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid JSON in 'params': {exc.msg}",
        ) from exc

    try:
        return EnhanceParams.model_validate(raw_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=json.loads(exc.json()),
        ) from exc


async def _read_and_validate_upload(upload: UploadFile) -> tuple[str, str | None, bytes]:
    """Read an uploaded image and validate MIME type and 15MB size limit."""
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{upload.content_type}' for '{upload.filename}'. "
                "Allowed formats: image/jpeg, image/png, image/webp."
            ),
        )

    raw_bytes = await upload.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{upload.filename}' is empty.",
        )

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{upload.filename}' exceeds the {max_mb}MB per-image limit.",
        )

    return (upload.filename or "image.jpg", upload.content_type, raw_bytes)


@router.post("/preview", response_model=PreviewResponse)
async def preview_enhance(
    file: UploadFile = File(...),
    params: str = Form(...),
) -> PreviewResponse:
    """Enhance a single preview image and return base64 JPEG + 256-bin histograms."""
    enhance_params = _parse_enhance_params(params)
    _filename, _content_type, raw_bytes = await _read_and_validate_upload(file)

    try:
        image_rgb = decode_image_bytes_to_rgb(raw_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not decode uploaded image: {exc}",
        ) from exc

    start_time = time.perf_counter()
    pipeline_result = enhance_image(image_rgb, enhance_params)
    processed_data_url = encode_rgb_to_jpeg_base64(pipeline_result.processed_rgb)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return PreviewResponse(
        processed_image=processed_data_url,
        hist_before=pipeline_result.hist_before,
        hist_after=pipeline_result.hist_after,
        applied_gamma=pipeline_result.applied_gamma,
        processing_time_ms=elapsed_ms,
    )


@router.post(
    "/batch-process",
    response_model=BatchCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_process(
    files: list[UploadFile] = File(...),
    params: str = Form(...),
) -> BatchCreateResponse:
    """Enqueue up to 50 full-resolution images for parallel enhancement and ZIP export."""
    enhance_params = _parse_enhance_params(params)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image file is required.",
        )

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BATCH_FILES} images allowed per batch.",
        )

    uploaded_items: list[tuple[str, str | None, bytes]] = []
    for upload in files:
        uploaded_items.append(await _read_and_validate_upload(upload))

    job_summary = create_batch_job(uploaded_items, enhance_params)
    return BatchCreateResponse(**job_summary)


@router.get("/batch-status/{job_id}", response_model=BatchStatusResponse)
async def batch_status(job_id: str) -> BatchStatusResponse:
    """Return real-time progress and failed_files list for a batch enhancement job."""
    job = get_batch_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' not found.",
        )

    return BatchStatusResponse(
        job_id=job["job_id"],
        processed=job["processed"],
        total=job["total"],
        status=job["status"],
        failed_files=job["failed_files"],
        error=job["error"],
    )


@router.get("/batch-download/{job_id}")
async def batch_download(job_id: str) -> FileResponse:
    """Download the generated enhanced_photos.zip archive and clean up temp files."""
    job = get_batch_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' not found.",
        )

    if job["status"] != "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch job '{job_id}' is not ready for download (status: {job['status']}).",
        )

    zip_path_str = job.get("zip_path")
    if not zip_path_str or not Path(zip_path_str).is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ZIP archive for job '{job_id}' has expired or already been downloaded.",
        )

    return FileResponse(
        path=zip_path_str,
        media_type="application/zip",
        filename=ZIP_FILENAME,
        background=BackgroundTask(cleanup_job_files, job_id),
    )
