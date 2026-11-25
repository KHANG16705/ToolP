"""Checks for benchmark measurement validity and non-destructive input handling."""

import argparse
import json
from pathlib import Path

import numpy as np
import pytest
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from benchmark import (
    NOISE_FRACTION,
    SSIM_WINDOW,
    _add_noise,
    _batch_summary,
    _discover_dataset,
    _execute_batch,
    _isolated_params,
    _json_safe,
    _metadata,
    _performance_params,
    _prepare_preview,
    _quality_metrics,
    _run_batch,
    _strip_ssim,
    _verify_outputs,
)
from core.color_space import read_image_file_rgb, rgb_to_hsv_channels, write_image_file_rgb


def test_noise_is_repeatable_distinct_and_does_not_modify_input() -> None:
    image = np.full((80, 100, 3), 120, dtype=np.uint8)
    original = image.copy()
    first, info = _add_noise(image, np.random.default_rng(42))
    second, repeated = _add_noise(image, np.random.default_rng(42))
    v_channel = rgb_to_hsv_channels(first)[2]
    assert np.array_equal(image, original)
    assert np.array_equal(first, second) and info == repeated
    assert info["selected_pixel_count"] == int(image.shape[0] * image.shape[1] * NOISE_FRACTION)
    assert np.count_nonzero(v_channel == 255) == info["salt_pixel_count"] == 200
    assert np.count_nonzero(v_channel == 0) == info["pepper_pixel_count"] == 200
    assert info["actually_changed_pixel_count"] == 400


@pytest.mark.parametrize("shape", [(7, 7), (259, 19), (530, 33)])
def test_striped_metrics_match_full_image_skimage(shape: tuple[int, int]) -> None:
    rng = np.random.default_rng(7)
    reference = rng.integers(0, 256, size=shape, dtype=np.uint8)
    candidate = rng.integers(0, 256, size=shape, dtype=np.uint8)
    result = _quality_metrics(reference, candidate)
    assert result["ssim"] == pytest.approx(
        structural_similarity(reference, candidate, data_range=255, win_size=SSIM_WINDOW), abs=1e-12,
    )
    assert result["psnr_db"] == pytest.approx(peak_signal_noise_ratio(reference, candidate, data_range=255))


def test_identical_psnr_and_nonfinite_values_produce_strict_json() -> None:
    image = np.full((9, 9), 120, dtype=np.uint8)
    metrics = _quality_metrics(image, image)
    assert metrics["psnr_db"] is None and metrics["psnr_status"] == "positive_infinity_identical"
    assert metrics["ssim"] == 1.0
    cleaned = _json_safe({"metrics": metrics, "infinity": np.float64(np.inf), "nan": float("nan")})
    assert cleaned["infinity"] is None and cleaned["infinity_status"] == "positive_infinity"
    assert cleaned["nan"] is None and cleaned["nan_status"] == "nan"
    assert json.loads(json.dumps(cleaned, allow_nan=False)) == cleaned


def test_ssim_rejects_unsupported_small_images() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        _strip_ssim(np.zeros((6, 8), dtype=np.uint8), np.zeros((6, 8), dtype=np.uint8))


@pytest.mark.parametrize("shape,expected", [((123, 400), (123, 400)), ((1001, 2000), (400, 800)), ((2000, 1001), (800, 400))])
def test_preview_preserves_aspect_ratio_and_does_not_upscale(
    shape: tuple[int, int], expected: tuple[int, int],
) -> None:
    decoded, payload = _prepare_preview(np.full((*shape, 3), 100, dtype=np.uint8))
    assert decoded.shape == (*expected, 3)
    assert payload.startswith(b"\xff\xd8")


def test_dataset_reports_corrupt_files_and_missing_directory(tmp_path: Path) -> None:
    folder = tmp_path / "thieu_sang"
    folder.mkdir()
    write_image_file_rgb(folder / "ảnh.png", np.full((12, 15, 3), 50, dtype=np.uint8))
    (folder / "broken.jpg").write_bytes(b"not an image")
    (folder / "notes.txt").write_text("ignore", encoding="utf-8")
    errors = []
    cases, dataset = _discover_dataset(tmp_path, errors)
    assert len(cases) == dataset["successful_count"] == 1
    assert dataset["discovered_count"] == 2 and dataset["skipped_count"] == 1
    assert cases[0].relative_path == "thieu_sang/ảnh.png" and len(errors) == 1
    missing_errors = []
    assert _discover_dataset(tmp_path / "missing", missing_errors)[0] == []
    assert len(missing_errors) == 1


def test_incomplete_batch_cannot_claim_a_speedup(tmp_path: Path) -> None:
    errors = []
    result = _run_batch([], _performance_params(), 3, tmp_path, errors)
    assert result["status"] == "skipped_wrong_image_count"
    assert result["summary"]["speedup"] is None and errors
    assert not _batch_summary([], 3)["comparison_valid"]


def test_spawn_worker_matches_sequential_outputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    rng = np.random.default_rng(8)
    write_image_file_rgb(source / "ảnh.png", rng.integers(0, 256, (19, 21, 3), dtype=np.uint8))
    write_image_file_rgb(source / "second.webp", rng.integers(0, 256, (17, 23, 3), dtype=np.uint8))
    errors = []
    cases, _ = _discover_dataset(source, errors)
    params = _performance_params().model_dump()
    sequential = [tmp_path / f"sequential_{case.path.name}" for case in cases]
    parallel = [tmp_path / f"parallel_{case.path.name}" for case in cases]
    for mode, outputs in (("sequential", sequential), ("parallel", parallel)):
        tasks = [(str(case.path), str(output)) for case, output in zip(cases, outputs, strict=True)]
        outcomes, elapsed = _execute_batch(tasks, params, mode, workers=2)
        assert all(outcome[1] for outcome in outcomes) and elapsed > 0
    assert all(row["equivalent"] for row in _verify_outputs(cases, parallel, sequential))
    assert read_image_file_rgb(parallel[0]).shape == (cases[0].height, cases[0].width, 3)
    assert all(case.sha256 for case in cases) and not errors


def test_parameter_isolation_and_metadata(tmp_path: Path) -> None:
    isolated = _isolated_params(contrast_mode="hist_eq")
    assert isolated.denoise_mode == isolated.brightness_mode == isolated.sharpen_mode == "none"
    assert not isolated.negative and not isolated.auto_gamma
    metadata = _metadata(argparse.Namespace(
        seed=42, input=tmp_path, output=tmp_path / "results.json",
        preview_repeats=10, batch_repeats=3, warmup=1,
    ))
    assert metadata["process_start_method"] == "spawn"
    assert metadata["library_versions"]["scikit-image"]
    assert metadata["started_at"].endswith("+07:00")
