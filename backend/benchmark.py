"""Reproducible, full-resolution quality and local performance benchmarks.

Run from the project root with backend/venv/Scripts/python.exe backend/benchmark.py.
This module calls the production pipeline and batch worker without modifying them.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from importlib.metadata import version
from itertools import repeat
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
import time
from typing import Any

import cv2
import numpy as np

from config import ALLOWED_EXTENSIONS, MAX_PIXEL_VALUE, MAX_WORKERS, PREVIEW_JPEG_QUALITY
from core.color_space import (
    decode_image_bytes_to_rgb,
    encode_rgb_to_jpeg_base64,
    hsv_channels_to_rgb,
    read_image_file_rgb,
    rgb_to_hsv_channels,
)
from core.pipeline import enhance_image
from schemas.enhance import EnhanceParams
from services.batch_service import process_single_file_task

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BATCH_SIZE = 25
RANDOM_SEED = 42
NOISE_FRACTION = 0.05
PREVIEW_MAX_DIMENSION = 800
PREVIEW_TARGET_MS = 200.0
PREVIEW_REPEATS = 10
BATCH_REPEATS = 3
WARMUP_REPEATS = 1
SSIM_WINDOW = 7
METRIC_STRIP_ROWS = 256
MILLISECONDS_PER_SECOND = 1000.0
LOCAL_TIMEZONE = timezone(timedelta(hours=7), name="Asia/Saigon")
ENHANCEMENT_GROUPS = ("thieu_sang", "scan_cu")
JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ImageCase:
    path: Path
    relative_path: str
    group: str
    width: int
    height: int
    sha256: str

    def as_dict(self) -> JsonObject:
        return {
            "path": self.relative_path, "group": self.group,
            "width": self.width, "height": self.height,
            "dtype": "uint8", "color_space": "RGB", "sha256": self.sha256,
        }


def _timestamp() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _checksum(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _metadata(args: argparse.Namespace) -> JsonObject:
    libraries = ("numpy", "opencv-python-headless", "scikit-image", "scipy",
                 "fastapi", "starlette", "pydantic", "httpx")
    return {
        "schema_version": 1, "started_at": _timestamp(), "timezone": "Asia/Saigon (UTC+07:00)",
        "seed": args.seed, "python_version": platform.python_version(),
        "python_executable": str(Path(os.sys.executable)), "platform": platform.platform(),
        "cpu": {"processor": platform.processor(), "logical_count": os.cpu_count(),
                "architecture": platform.machine()},
        "configured_max_workers": MAX_WORKERS, "opencv_threads_per_process": cv2.getNumThreads(),
        "process_start_method": "spawn", "library_versions": {name: version(name) for name in libraries},
        "project_root": str(PROJECT_ROOT), "statistical_std_ddof": 0,
        "thread_environment": {name: os.environ.get(name) for name in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OPENCV_FOR_THREADS_NUM",
        )},
        "run_configuration": {
            "input": str(args.input), "output": str(args.output),
            "preview_repeats": args.preview_repeats, "batch_repeats": args.batch_repeats,
            "warmups_per_preview_image": args.warmup,
        },
        "non_finite_policy": "JSON null with an adjacent *_status field; identical-image PSNR has explicit positive_infinity_identical status.",
        "timing_note": "Preview and batch timing scopes are recorded in their sections; verification and final JSON writing are not workload timings.",
    }


def _record_error(errors: list[JsonObject], stage: str, path: str, exc: Any) -> None:
    errors.append({"stage": stage, "path": path, "message": str(exc)})


def _stats(values: list[float]) -> JsonObject:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=np.float64)
    if not finite.size:
        return {"sample_count": 0, "mean": None, "std": None,
                "median": None, "p95": None, "min": None, "max": None}
    return {
        "sample_count": int(finite.size), "mean": float(finite.mean()),
        "std": float(finite.std(ddof=0)), "median": float(np.median(finite)),
        "p95": float(np.percentile(finite, 95)),
        "min": float(finite.min()), "max": float(finite.max()),
    }


def _discover_dataset(input_dir: Path, errors: list[JsonObject]) -> tuple[list[ImageCase], JsonObject]:
    paths = sorted(
        (path for path in input_dir.rglob("*")
         if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS),
        key=lambda path: path.relative_to(input_dir).as_posix(),
    )
    cases: list[ImageCase] = []
    if not input_dir.is_dir():
        _record_error(errors, "dataset", str(input_dir), "Input directory does not exist")
    for path in paths:
        relative = path.relative_to(input_dir)
        try:
            image = read_image_file_rgb(path)
            height, width = image.shape[:2]
            group = relative.parts[0] if len(relative.parts) > 1 else "ungrouped"
            cases.append(ImageCase(path, relative.as_posix(), group, width, height, _checksum(path)))
        except Exception as exc:
            _record_error(errors, "dataset", relative.as_posix(), exc)
    return cases, {
        "input_directory": str(input_dir), "expected_batch_size": EXPECTED_BATCH_SIZE,
        "discovered_count": len(paths), "successful_count": len(cases),
        "skipped_count": len(paths) - len(cases),
        "groups": dict(sorted(Counter(case.group for case in cases).items())),
        "images": [case.as_dict() for case in cases],
    }


def _isolated_params(**changes: Any) -> EnhanceParams:
    values: JsonObject = {
        "denoise_mode": "none", "brightness_mode": "none", "auto_gamma": False,
        "contrast_mode": "none", "sharpen_mode": "none", "negative": False,
    }
    values.update(changes)
    return EnhanceParams.model_validate(values)


def _performance_params() -> EnhanceParams:
    return EnhanceParams(
        denoise_mode="median", kernel_size=3, brightness_mode="gamma", auto_gamma=True,
        contrast_mode="clahe", clahe_clip_limit=2.0,
        sharpen_mode="laplacian_4", sharpen_alpha=0.5, negative=False,
    )


def _add_noise(image: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, JsonObject]:
    h_channel, s_channel, original_v = rgb_to_hsv_channels(image)
    noisy_v = original_v.copy()
    count = int(math.floor(original_v.size * NOISE_FRACTION + 0.5))
    positions = rng.choice(original_v.size, size=count, replace=False)
    salt_count = count // 2
    noisy_v.flat[positions[:salt_count]] = int(MAX_PIXEL_VALUE)
    noisy_v.flat[positions[salt_count:]] = 0
    noisy_rgb = hsv_channels_to_rgb(h_channel, s_channel, noisy_v)
    return noisy_rgb, {
        "selected_pixel_count": count, "salt_pixel_count": salt_count,
        "pepper_pixel_count": count - salt_count,
        "selected_fraction": count / original_v.size,
        "actually_changed_pixel_count": int(np.count_nonzero(noisy_v != original_v)),
        "noise_v_sha256": hashlib.sha256(noisy_v.tobytes()).hexdigest(),
    }


def _strip_ssim(reference: np.ndarray, candidate: np.ndarray) -> float:
    """Compute skimage's default 7x7 SSIM with exact halos, bounding peak memory."""
    # Lazy import keeps benchmark-only SciPy/skimage startup out of spawned workers.
    from skimage.metrics import structural_similarity

    height, width = reference.shape
    if min(height, width) < SSIM_WINDOW:
        raise ValueError(f"SSIM requires both dimensions >= {SSIM_WINDOW}")
    radius = SSIM_WINDOW // 2
    weighted_sum = 0.0
    total_centers = 0
    for start in range(radius, height - radius, METRIC_STRIP_ROWS):
        stop = min(start + METRIC_STRIP_ROWS, height - radius)
        rows = slice(start - radius, stop + radius)
        score = structural_similarity(
            reference[rows], candidate[rows], data_range=MAX_PIXEL_VALUE,
            win_size=SSIM_WINDOW, gaussian_weights=False, use_sample_covariance=True,
        )
        centers = (stop - start) * (width - 2 * radius)
        weighted_sum += float(score) * centers
        total_centers += centers
    return weighted_sum / total_centers


def _quality_metrics(reference: np.ndarray, candidate: np.ndarray) -> JsonObject:
    if reference.shape != candidate.shape or reference.ndim != 2:
        raise ValueError("Quality metrics require equally sized, two-dimensional V channels")
    squared_error = 0.0
    for start in range(0, reference.shape[0], METRIC_STRIP_ROWS):
        rows = slice(start, start + METRIC_STRIP_ROWS)
        difference = reference[rows].astype(np.float64) - candidate[rows].astype(np.float64)
        squared_error += float(np.sum(difference * difference, dtype=np.float64))
    mse = squared_error / reference.size
    psnr = None if mse == 0.0 else float(10.0 * math.log10(MAX_PIXEL_VALUE**2 / mse))
    return {
        "psnr_db": psnr,
        "psnr_status": "positive_infinity_identical" if mse == 0.0 else "finite",
        "ssim": _strip_ssim(reference, candidate), "mse": mse,
    }


def _quality_summary(metrics: list[JsonObject]) -> JsonObject:
    return {
        "image_count": len(metrics),
        "psnr_db": _stats([row["psnr_db"] for row in metrics if row["psnr_db"] is not None]),
        "ssim": _stats([row["ssim"] for row in metrics]),
        "infinite_psnr_count": sum(row["psnr_status"] == "positive_infinity_identical" for row in metrics),
    }


def _denoise_case(case: ImageCase, rng: np.random.Generator,
                  configs: dict[str, EnhanceParams]) -> JsonObject:
    image = read_image_file_rgb(case.path)
    reference_v = rgb_to_hsv_channels(image)[2]
    noisy_image, noise_info = _add_noise(image, rng)
    baseline = _quality_metrics(reference_v, rgb_to_hsv_channels(noisy_image)[2])
    results = {}
    for name, params in configs.items():
        result = enhance_image(noisy_image, params)
        results[name] = _quality_metrics(reference_v, rgb_to_hsv_channels(result.processed_rgb)[2])
    return {"path": case.relative_path, "group": case.group, "noise": noise_info,
            "baseline": baseline, "results": results}


def _run_denoising(cases: list[ImageCase], seed: int, errors: list[JsonObject]) -> JsonObject:
    configs = {
        f"{method}_{kernel}x{kernel}": _isolated_params(denoise_mode=method, kernel_size=kernel)
        for method in ("average", "median", "morph_open_close") for kernel in (3, 5)
    }
    rng = np.random.default_rng(seed)
    rows = []
    for index, case in enumerate(cases, start=1):
        print(f"[denoising {index}/{len(cases)}] {case.relative_path}", flush=True)
        try:
            rows.append(_denoise_case(case, rng, configs))
        except Exception as exc:
            _record_error(errors, "denoising", case.relative_path, exc)
    summary = {name: _quality_summary([row["results"][name] for row in rows]) for name in configs}
    return {
        "channel": "HSV V", "data_range": int(MAX_PIXEL_VALUE),
        "noise_fraction": NOISE_FRACTION, "seed": seed,
        "reference_note": "Synthetic added-noise recovery; source images are not assumed clean ground truth.",
        "noise_note": "5% distinct selected V positions; some may already equal the assigned 0/255 value.",
        "ssim_settings": {"window_size": SSIM_WINDOW, "gaussian_weights": False,
                          "use_sample_covariance": True, "strip_rows": METRIC_STRIP_ROWS},
        "aggregation": "Unweighted arithmetic statistics across images; infinite PSNR excluded and counted separately.",
        "configs": {name: params.model_dump() for name, params in configs.items()},
        "images": rows, "baseline_summary": _quality_summary([row["baseline"] for row in rows]),
        "summary": summary, "successful_count": len(rows), "failed_count": len(cases) - len(rows),
    }


def _v_stats(image: np.ndarray) -> JsonObject:
    v_channel = rgb_to_hsv_channels(image)[2]
    return {"mean_v": float(np.mean(v_channel)), "std_v": float(np.std(v_channel, ddof=0))}


def _enhancement_case(case: ImageCase, configs: dict[str, EnhanceParams]) -> JsonObject:
    image = read_image_file_rgb(case.path)
    before = _v_stats(image)
    results = {}
    for name, params in configs.items():
        result = enhance_image(image, params)
        after = _v_stats(result.processed_rgb)
        results[name] = {
            "after": after, "delta_mean_v": after["mean_v"] - before["mean_v"],
            "delta_std_v": after["std_v"] - before["std_v"], "applied_gamma": result.applied_gamma,
        }
    return {"path": case.relative_path, "group": case.group, "before": before, "results": results}


def _enhancement_summary(rows: list[JsonObject], methods: list[str]) -> JsonObject:
    summary: JsonObject = {}
    for group in ENHANCEMENT_GROUPS:
        selected = [row for row in rows if row["group"] == group]
        summary[group] = {}
        for method in methods:
            entry: JsonObject = {"image_count": len(selected)}
            for metric in ("mean_v", "std_v"):
                entry[f"before_{metric}_across_images"] = _stats([row["before"][metric] for row in selected])
                entry[f"after_{metric}_across_images"] = _stats([row["results"][method]["after"][metric] for row in selected])
                entry[f"delta_{metric}_across_images"] = _stats([row["results"][method][f"delta_{metric}"] for row in selected])
            summary[group][method] = entry
    return summary


def _run_enhancement(cases: list[ImageCase], errors: list[JsonObject]) -> JsonObject:
    configs = {
        "auto_gamma": _isolated_params(brightness_mode="gamma", auto_gamma=True),
        "hist_eq": _isolated_params(contrast_mode="hist_eq"),
        "clahe": _isolated_params(contrast_mode="clahe", clahe_clip_limit=2.0),
    }
    selected = [case for case in cases if case.group in ENHANCEMENT_GROUPS]
    rows = []
    for case in selected:
        print(f"[enhancement] {case.relative_path}", flush=True)
        try:
            rows.append(_enhancement_case(case, configs))
        except Exception as exc:
            _record_error(errors, "enhancement", case.relative_path, exc)
    for group in ENHANCEMENT_GROUPS:
        if not any(case.group == group for case in selected):
            _record_error(errors, "enhancement", group, "Required image group is missing")
    return {
        "groups": list(ENHANCEMENT_GROUPS), "channel": "HSV V", "range": [0, int(MAX_PIXEL_VALUE)],
        "std_ddof": 0, "aggregation_note": "std_v is spatial pixel spread within one image; *_across_images.std is spread between images.",
        "interpretation": "An increase in Mean V or Std V alone does not establish better visual quality. mo_nhe is not treated as low contrast.",
        "configs": {name: params.model_dump() for name, params in configs.items()},
        "images": rows, "summary": _enhancement_summary(rows, list(configs)),
        "successful_count": len(rows), "failed_count": len(selected) - len(rows),
    }


def _prepare_preview(image: np.ndarray) -> tuple[np.ndarray, bytes]:
    height, width = image.shape[:2]
    scale = min(1.0, PREVIEW_MAX_DIMENSION / max(height, width))
    target_width = max(1, math.floor(width * scale + 0.5))
    target_height = max(1, math.floor(height * scale + 0.5))
    if (target_height, target_width) != (height, width):
        image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)
    data_url = encode_rgb_to_jpeg_base64(image, quality=PREVIEW_JPEG_QUALITY)
    payload = base64.b64decode(data_url.split(",", 1)[1])
    return decode_image_bytes_to_rgb(payload), payload


def _measure_preview(client: Any, image: np.ndarray, payload: bytes,
                     params: EnhanceParams, params_json: str) -> JsonObject:
    started = time.perf_counter()
    result = enhance_image(image, params)
    encoded = encode_rgb_to_jpeg_base64(result.processed_rgb)
    processing_ms = (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
    started = time.perf_counter()
    response = client.post(
        "/api/preview", files={"file": ("preview.jpg", payload, "image/jpeg")},
        data={"params": params_json},
    )
    response_ms = (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
    response.raise_for_status()
    body = response.json()
    if body["processed_image"] != encoded or len(body["hist_after"]) != 256:
        raise ValueError("Direct pipeline and Preview API results differ")
    return {"preview_processing_ms": processing_ms, "preview_response_ms": response_ms,
            "api_reported_processing_ms": float(body["processing_time_ms"])}


def _preview_summary(samples: list[JsonObject]) -> JsonObject:
    summary = {}
    for metric in ("preview_processing_ms", "preview_response_ms", "api_reported_processing_ms"):
        stats = _stats([sample[metric] for sample in samples])
        stats["mean_under_target"] = stats["mean"] < PREVIEW_TARGET_MS if samples else None
        stats["p95_under_target"] = stats["p95"] < PREVIEW_TARGET_MS if samples else None
        summary[metric] = stats
    return summary


def _preview_case(client: Any, case: ImageCase, params: EnhanceParams,
                  repeats: int, warmup: int) -> JsonObject:
    image, payload = _prepare_preview(read_image_file_rgb(case.path))
    params_json = params.model_dump_json()
    for _ in range(warmup):
        _measure_preview(client, image, payload, params, params_json)
    samples = [_measure_preview(client, image, payload, params, params_json) for _ in range(repeats)]
    return {
        "path": case.relative_path, "group": case.group,
        "original_width": case.width, "original_height": case.height,
        "preview_width": image.shape[1], "preview_height": image.shape[0],
        "jpeg_bytes": len(payload), "samples": samples, "summary": _preview_summary(samples),
    }


def _run_preview(cases: list[ImageCase], params: EnhanceParams, repeats: int,
                 warmup: int, errors: list[JsonObject]) -> JsonObject:
    from fastapi.testclient import TestClient
    from main import app

    rows = []
    with TestClient(app) as client:
        for index, case in enumerate(cases, start=1):
            print(f"[preview {index}/{len(cases)}] {case.relative_path}", flush=True)
            try:
                rows.append(_preview_case(client, case, params, repeats, warmup))
            except Exception as exc:
                _record_error(errors, "preview", case.relative_path, exc)
    return {
        "max_dimension_px": PREVIEW_MAX_DIMENSION, "jpeg_quality": PREVIEW_JPEG_QUALITY,
        "resize_note": "Same aspect-ratio/no-upscale/positive-rounding rule as frontend; OpenCV INTER_AREA is not bit-identical to browser Canvas resampling.",
        "repeats_per_image": repeats, "excluded_warmups_per_image": warmup,
        "target_ms": PREVIEW_TARGET_MS, "params": params.model_dump(),
        "timing_scope": {
            "preview_processing_ms": "enhance_image including histograms + encode_rgb_to_jpeg_base64; excludes decode, resize and input JPEG preparation.",
            "preview_response_ms": "Local TestClient POST, including multipart, decode, validation, pipeline, output encoding and response serialization; excludes network, browser and client response.json().",
            "api_reported_processing_ms": "processing_time_ms returned by the same API call, rounded by the existing route to 0.01 ms.",
        },
        "images": rows, "summary": _preview_summary([sample for row in rows for sample in row["samples"]]),
        "successful_count": len(rows), "failed_count": len(cases) - len(rows),
    }


def _execute_batch(tasks: list[tuple[str, str]], params_dict: JsonObject,
                   mode: str, workers: int) -> tuple[list[tuple[str, bool, str | None]], float]:
    started = time.perf_counter()
    if mode == "parallel":
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as executor:
            outcomes = list(executor.map(
                process_single_file_task, [task[0] for task in tasks],
                [task[1] for task in tasks], repeat(params_dict),
            ))
    else:
        outcomes = [process_single_file_task(source, target, params_dict) for source, target in tasks]
    return outcomes, time.perf_counter() - started


def _verify_outputs(cases: list[ImageCase], paths: list[Path],
                    reference_paths: list[Path] | None) -> list[JsonObject]:
    verification = []
    for index, (case, path) in enumerate(zip(cases, paths, strict=True)):
        try:
            digest = _checksum(path)
            if reference_paths is None:
                shape = read_image_file_rgb(path).shape
                matches = shape == (case.height, case.width, 3)
                method = "reference_output_dimensions"
            else:
                reference = reference_paths[index]
                matches = digest == _checksum(reference)
                method = "identical_encoded_sha256"
                if not matches:
                    matches = bool(np.array_equal(read_image_file_rgb(path), read_image_file_rgb(reference)))
                    method = "decoded_pixel_equality"
            verification.append({"path": case.relative_path, "equivalent": matches,
                                 "method": method, "output_sha256": digest})
        except Exception as exc:
            verification.append({"path": case.relative_path, "equivalent": False, "error": str(exc)})
    return verification


def _batch_once(cases: list[ImageCase], root: Path, round_index: int, mode: str,
                params: EnhanceParams, workers: int, reference: list[Path] | None,
                errors: list[JsonObject]) -> tuple[JsonObject, list[Path]]:
    output_dir = root / f"round_{round_index + 1}_{mode}"
    output_dir.mkdir()
    paths = [output_dir / f"{index:03d}_{case.path.name}" for index, case in enumerate(cases)]
    tasks = [(str(case.path), str(path)) for case, path in zip(cases, paths, strict=True)]
    outcomes, elapsed = _execute_batch(tasks, params.model_dump(), mode, workers)
    verification = _verify_outputs(cases, paths, reference)
    for case, outcome, checked in zip(cases, outcomes, verification, strict=True):
        if not outcome[1] or not checked["equivalent"]:
            _record_error(errors, "batch", case.relative_path, outcome[2] or checked.get("error", "Output mismatch"))
    succeeded = sum(outcome[1] for outcome in outcomes)
    return {
        "round": round_index + 1, "mode": mode, "elapsed_s": elapsed,
        "images_per_second": succeeded / elapsed, "attempted_count": len(tasks),
        "successful_count": succeeded, "failed_count": len(tasks) - succeeded,
        "outputs_equivalent": all(row["equivalent"] for row in verification),
        "verified_count": sum(row["equivalent"] for row in verification), "verification": verification,
    }, paths


def _batch_summary(runs: list[JsonObject], repeats: int) -> JsonObject:
    summary = {}
    for mode in ("sequential", "parallel"):
        selected = [run for run in runs if run["mode"] == mode]
        stats = _stats([run["elapsed_s"] for run in selected])
        total_elapsed = sum(run["elapsed_s"] for run in selected)
        summary[mode] = {"elapsed_s": stats, "images_per_second":
                         sum(run["successful_count"] for run in selected) / total_elapsed if total_elapsed else None}
    valid = len(runs) == repeats * 2 and all(
        run["successful_count"] == EXPECTED_BATCH_SIZE and run["outputs_equivalent"] for run in runs
    )
    summary["speedup"] = (
        summary["sequential"]["elapsed_s"]["mean"] / summary["parallel"]["elapsed_s"]["mean"]
        if valid else None
    )
    summary["comparison_valid"] = valid
    summary["speedup_interpretation"] = "sequential_mean / parallel_mean; values below 1 mean parallel is slower"
    return summary


def _run_batch(cases: list[ImageCase], params: EnhanceParams, repeats: int,
               temp_parent: Path, errors: list[JsonObject]) -> JsonObject:
    workers = max(1, min(MAX_WORKERS, len(cases)))
    result: JsonObject = {
        "batch_size": len(cases), "expected_batch_size": EXPECTED_BATCH_SIZE,
        "worker_count": workers, "repeats_per_mode": repeats, "params": params.model_dump(),
        "source_paths": [case.relative_path for case in cases], "runs": [],
        "timing_scope": "Full-resolution disk read/decode -> production pipeline -> encode/write. Parallel includes pool startup/shutdown and task IPC. Excludes output-directory setup, verification, upload, polling and ZIP.",
        "cache_note": "Alternating mode order between rounds; OS file caches are not flushed. No batch pool warm-up; every parallel run creates a fresh spawn pool.",
    }
    if len(cases) != EXPECTED_BATCH_SIZE:
        _record_error(errors, "batch", "", f"Expected exactly {EXPECTED_BATCH_SIZE} unique valid images, found {len(cases)}; batch skipped")
        result["status"] = "skipped_wrong_image_count"
        result["summary"] = _batch_summary([], repeats)
        return result
    with TemporaryDirectory(prefix="benchmark_", dir=temp_parent) as temp_name:
        reference = None
        for round_index in range(repeats):
            order = ("sequential", "parallel") if round_index % 2 == 0 else ("parallel", "sequential")
            for mode in order:
                print(f"[batch {round_index + 1}/{repeats}] {mode}, {len(cases)} images, workers={workers}", flush=True)
                try:
                    row, paths = _batch_once(cases, Path(temp_name), round_index, mode, params, workers, reference, errors)
                    result["runs"].append(row)
                    if reference is None:
                        reference = paths
                    print(f"  {row['elapsed_s']:.3f} s; successful={row['successful_count']}; equivalent={row['outputs_equivalent']}", flush=True)
                except Exception as exc:
                    _record_error(errors, "batch", f"round_{round_index + 1}/{mode}", exc)
    result["summary"] = _batch_summary(result["runs"], repeats)
    result["status"] = "complete" if result["summary"]["comparison_valid"] else "incomplete"
    return result


def _verify_sources(cases: list[ImageCase], errors: list[JsonObject]) -> bool:
    unchanged = True
    for case in cases:
        try:
            if _checksum(case.path) != case.sha256:
                raise ValueError("Source SHA-256 changed during the benchmark")
        except Exception as exc:
            unchanged = False
            _record_error(errors, "source_integrity", case.relative_path, exc)
    return unchanged


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            scalar = item.item() if isinstance(item, np.generic) else item
            cleaned[key] = _json_safe(scalar)
            if isinstance(scalar, float) and not math.isfinite(scalar):
                cleaned[f"{key}_status"] = "nan" if math.isnan(scalar) else (
                    "positive_infinity" if scalar > 0 else "negative_infinity"
                )
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _check_report(report: JsonObject) -> None:
    required = {"metadata", "dataset", "denoising", "enhancement", "preview", "batch", "errors"}
    if not required.issubset(report):
        raise ValueError("Benchmark JSON is missing required sections")
    if report["metadata"]["status"] != "complete":
        return
    count = report["dataset"]["successful_count"]
    if count != EXPECTED_BATCH_SIZE or report["dataset"]["discovered_count"] != count:
        raise ValueError("Complete benchmark requires exactly 25 discovered and decoded images")
    if report["denoising"]["successful_count"] != count or report["preview"]["successful_count"] != count:
        raise ValueError("Not all images completed quality and Preview benchmarks")
    if len(report["denoising"]["configs"]) != 6 or not report["batch"]["summary"]["comparison_valid"]:
        raise ValueError("Missing denoising configuration or invalid batch comparison")
    expected_samples = count * report["preview"]["repeats_per_image"]
    if report["preview"]["summary"]["preview_response_ms"]["sample_count"] != expected_samples:
        raise ValueError("Unexpected number of Preview measurements")


def _write_report(output: Path, report: JsonObject) -> None:
    cleaned = _json_safe(report)
    _check_report(cleaned)
    output.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    loaded = json.loads(output.read_text(encoding="utf-8"))
    _check_report(loaded)
    if loaded != cleaned:
        raise ValueError("JSON round-trip verification failed")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "sample_images")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "docs" / "benchmark_results.json")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--preview-repeats", type=int, default=PREVIEW_REPEATS)
    parser.add_argument("--batch-repeats", type=int, default=BATCH_REPEATS)
    parser.add_argument("--warmup", type=int, default=WARMUP_REPEATS)
    args = parser.parse_args()
    if args.seed < 0 or args.preview_repeats < PREVIEW_REPEATS or args.batch_repeats < BATCH_REPEATS or args.warmup < 1:
        parser.error("Require seed >= 0, preview-repeats >= 10, batch-repeats >= 3 and warmup >= 1")
    args.input = args.input.resolve()
    args.output = args.output.resolve()
    if args.output.is_relative_to(args.input):
        parser.error("Output must be outside the source image directory")
    return args


def main() -> int:
    args = _parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    errors: list[JsonObject] = []
    report: JsonObject = {"metadata": _metadata(args), "errors": errors}
    cases, report["dataset"] = _discover_dataset(args.input, errors)
    print(f"Decoded {len(cases)} / {report['dataset']['discovered_count']} images", flush=True)
    params = _performance_params()
    started = time.perf_counter()
    report["denoising"] = _run_denoising(cases, args.seed, errors)
    report["enhancement"] = _run_enhancement(cases, errors)
    report["preview"] = _run_preview(cases, params, args.preview_repeats, args.warmup, errors)
    report["batch"] = _run_batch(cases, params, args.batch_repeats, args.output.parent, errors)
    report["dataset"]["source_files_unchanged"] = _verify_sources(cases, errors)
    report["metadata"].update({
        "finished_at": _timestamp(), "total_experiment_elapsed_s": time.perf_counter() - started,
        "actual_worker_count": report["batch"]["worker_count"],
        "status": "complete" if not errors else "completed_with_errors",
    })
    _write_report(args.output, report)
    print(f"Results: {args.output}; errors={len(errors)}", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
