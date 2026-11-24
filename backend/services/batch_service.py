"""Multiprocessing batch image enhancement service, ZIP packaging, and temp cleanup."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import shutil
import threading
import time
from typing import Any
import uuid
import zipfile

from config import (
    ALLOWED_EXTENSIONS,
    CONTENT_TYPE_TO_EXT,
    JOB_TTL_SECONDS,
    MAX_WORKERS,
    TEMP_DIR,
    ZIP_FILENAME,
)
from core.color_space import read_image_file_rgb, write_image_file_rgb
from core.pipeline import enhance_image
from schemas.enhance import EnhanceParams

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def process_single_file_task(
    input_path_str: str,
    output_path_str: str,
    params_dict: dict[str, Any],
) -> tuple[str, bool, str | None]:
    """Top-level Windows spawn-safe worker that enhances one image from disk to disk."""
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)
    try:
        params = EnhanceParams.model_validate(params_dict)
        image_rgb = read_image_file_rgb(input_path)
        result = enhance_image(image_rgb, params)
        write_image_file_rgb(output_path, result.processed_rgb)
        return (input_path.name, True, None)
    except Exception as exc:  # noqa: BLE001
        return (input_path.name, False, str(exc))


def build_unique_filename(
    raw_filename: str | None,
    content_type: str | None,
    used_names: set[str],
) -> str:
    """Sanitize filename, preserve valid extension, and append _1/_2 on duplicates."""
    safe_name = Path(raw_filename or "image").name
    stem = Path(safe_name).stem or "image"
    ext = Path(safe_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        ext = CONTENT_TYPE_TO_EXT.get(content_type or "", ".jpg")

    candidate = f"{stem}{ext}"
    counter = 1
    while candidate.lower() in used_names:
        candidate = f"{stem}_{counter}{ext}"
        counter += 1

    used_names.add(candidate.lower())
    return candidate


def cleanup_job_files(job_id: str) -> None:
    """Delete a job's temporary directory and mark its zip_path as cleaned."""
    job_dir = TEMP_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            job["zip_path"] = None


def cleanup_expired_jobs() -> None:
    """Remove temporary directories and records for jobs older than JOB_TTL_SECONDS."""
    now = time.time()
    expired_ids: list[str] = []

    with JOBS_LOCK:
        for job_id, job in list(JOBS.items()):
            if now - float(job.get("created_at", now)) > JOB_TTL_SECONDS:
                expired_ids.append(job_id)

    for job_id in expired_ids:
        job_dir = TEMP_DIR / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        with JOBS_LOCK:
            JOBS.pop(job_id, None)


def _package_zip(output_dir: Path, zip_path: Path) -> int:
    """Compress all enhanced images in output_dir into a single ZIP archive."""
    files = sorted(p for p in output_dir.iterdir() if p.is_file())
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=file_path.name)
    return len(files)


def _run_batch_job(
    job_id: str,
    file_pairs: list[tuple[Path, Path]],
    output_dir: Path,
    zip_path: Path,
    params_dict: dict[str, Any],
) -> None:
    """Execute batch tasks across a process pool and update shared job state."""
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]["status"] = "processing"

    failed_files: list[str] = []
    worker_count = max(1, min(MAX_WORKERS, len(file_pairs)))

    try:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    process_single_file_task,
                    str(in_path),
                    str(out_path),
                    params_dict,
                )
                for in_path, out_path in file_pairs
            ]

            for future in as_completed(futures):
                filename, succeeded, _err = future.result()
                with JOBS_LOCK:
                    job = JOBS.get(job_id)
                    if job is None:
                        continue
                    job["processed"] += 1
                    if not succeeded:
                        failed_files.append(filename)
                        job["failed_files"] = list(failed_files)

        packaged_count = _package_zip(output_dir, zip_path)
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                job["failed_files"] = list(failed_files)
                if packaged_count == 0:
                    job["status"] = "failed"
                    job["error"] = "All images failed to decode or process."
                    job["zip_path"] = None
                else:
                    job["status"] = "done"
                    job["zip_path"] = str(zip_path)
    except Exception as exc:  # noqa: BLE001
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                job["status"] = "failed"
                job["error"] = f"Batch processing error: {exc}"
                job["zip_path"] = None


def create_batch_job(
    uploaded_items: list[tuple[str, str | None, bytes]],
    params: EnhanceParams,
) -> dict[str, Any]:
    """Persist uploaded images to temp_jobs/{job_id}/input and launch background worker."""
    cleanup_expired_jobs()

    job_id = str(uuid.uuid4())
    job_dir = TEMP_DIR / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    file_pairs: list[tuple[Path, Path]] = []

    for raw_name, content_type, raw_bytes in uploaded_items:
        unique_name = build_unique_filename(raw_name, content_type, used_names)
        in_path = input_dir / unique_name
        out_path = output_dir / unique_name
        in_path.write_bytes(raw_bytes)
        file_pairs.append((in_path, out_path))

    zip_path = job_dir / ZIP_FILENAME
    job_record: dict[str, Any] = {
        "job_id": job_id,
        "processed": 0,
        "total": len(file_pairs),
        "status": "queued",
        "failed_files": [],
        "zip_path": None,
        "error": None,
        "created_at": time.time(),
    }

    with JOBS_LOCK:
        JOBS[job_id] = job_record

    worker_thread = threading.Thread(
        target=_run_batch_job,
        args=(job_id, file_pairs, output_dir, zip_path, params.model_dump()),
        daemon=True,
    )
    worker_thread.start()

    return {
        "job_id": job_id,
        "total": len(file_pairs),
        "status": "queued",
    }


def get_batch_job(job_id: str) -> dict[str, Any] | None:
    """Return a snapshot copy of a batch job's status dictionary, or None."""
    cleanup_expired_jobs()
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return None
        return {
            **job,
            "failed_files": list(job.get("failed_files", [])),
        }
