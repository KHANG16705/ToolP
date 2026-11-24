"""Automated verification tests for DIP formulas, API contract, and Windows multiprocessing."""

import io
import json
import time
import zipfile
import cv2
import numpy as np
from fastapi.testclient import TestClient

from config import TEMP_DIR
from core.filters import apply_laplacian_sharpening, apply_median_filter, apply_morph_open_close
from core.histogram import apply_histogram_equalization, compute_histogram
from core.pipeline import enhance_image
from core.point_ops import apply_point_operations
from main import app
from schemas.enhance import EnhanceParams

client = TestClient(app)


def _encode_test_image(image_rgb: np.ndarray, ext: str = ".jpg") -> bytes:
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(ext, image_bgr)
    assert ok
    return buf.tobytes()


def test_point_ops_order_and_applied_gamma() -> None:
    """Verify brightness_mode runs before negative and applied_gamma is float | None."""
    v = np.full((64, 64), 40, dtype=np.uint8)

    params_auto = EnhanceParams(brightness_mode="gamma", auto_gamma=True, negative=False)
    v_bright, applied = apply_point_operations(v, params_auto)
    assert applied is not None and applied < 1.0
    assert float(np.mean(v_bright)) > 110.0

    params_gamma_neg = EnhanceParams(brightness_mode="gamma", gamma=0.5, negative=True)
    v_neg, applied_neg = apply_point_operations(v, params_gamma_neg)
    expected_before_neg, _ = apply_point_operations(
        v, EnhanceParams(brightness_mode="gamma", gamma=0.5, negative=False)
    )
    assert applied_neg == 0.5
    assert np.array_equal(v_neg, 255 - expected_before_neg)

    params_log = EnhanceParams(brightness_mode="log", log_c=1.2)
    _, applied_log = apply_point_operations(v, params_log)
    assert applied_log is None


def test_histogram_equalization_and_laplacian_no_overflow() -> None:
    """Verify pure-NumPy histogram equalization and uint8 overflow safety in Laplacian."""
    low_contrast = np.tile(np.arange(100, 140, dtype=np.uint8), (40, 1))
    eq = apply_histogram_equalization(low_contrast)
    hist_before = compute_histogram(low_contrast)
    hist_after = compute_histogram(eq)

    assert len(hist_before) == 256 and len(hist_after) == 256
    assert sum(hist_before) == low_contrast.size
    assert sum(hist_after) == eq.size
    assert int(eq.max()) - int(eq.min()) > int(low_contrast.max()) - int(low_contrast.min())

    step_edge = np.zeros((32, 32), dtype=np.uint8)
    step_edge[:, 16:] = 255
    sharp_4 = apply_laplacian_sharpening(step_edge, "laplacian_4", 1.0)
    sharp_8 = apply_laplacian_sharpening(step_edge, "laplacian_8", 1.0)
    assert sharp_4.dtype == np.uint8 and sharp_8.dtype == np.uint8
    assert int(sharp_4[:, 0].max()) == 0 and int(sharp_4[:, -1].min()) == 255
    assert int(sharp_8[:, 0].max()) == 0 and int(sharp_8[:, -1].min()) == 255


def test_denoising_removes_salt_and_pepper() -> None:
    """Verify median and morph_open_close clean impulse noise cleanly."""
    clean = np.full((32, 32), 120, dtype=np.uint8)
    noisy = clean.copy()
    noisy[10, 10] = 255
    noisy[20, 20] = 0

    med = apply_median_filter(noisy, 3)
    morph = apply_morph_open_close(noisy, 3)
    assert med[10, 10] == 120 and med[20, 20] == 120
    assert morph[10, 10] == 120 and morph[20, 20] == 120


def test_preview_endpoint_contract_and_validation() -> None:
    """Verify POST /api/preview returns locked schema and enforces 400/422 errors."""
    img = np.zeros((120, 160, 3), dtype=np.uint8)
    img[:, :, 0] = 60
    img[:, :, 1] = 120
    img[:, :, 2] = 180
    payload = _encode_test_image(img, ".webp")

    params = EnhanceParams(
        denoise_mode="median",
        kernel_size=3,
        brightness_mode="gamma",
        auto_gamma=True,
        contrast_mode="clahe",
        clahe_clip_limit=2.5,
        sharpen_mode="laplacian_4",
        sharpen_alpha=0.6,
    )
    resp = client.post(
        "/api/preview",
        files={"file": ("sample.webp", payload, "image/webp")},
        data={"params": params.model_dump_json()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed_image"].startswith("data:image/jpeg;base64,")
    assert len(body["hist_before"]) == 256
    assert len(body["hist_after"]) == 256
    assert isinstance(body["applied_gamma"], float)
    assert body["processing_time_ms"] < 200.0

    # Invalid MIME -> 400
    bad_mime = client.post(
        "/api/preview",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"params": params.model_dump_json()},
    )
    assert bad_mime.status_code == 400

    # Invalid stretch_r1 >= stretch_r2 -> 422
    bad_params = params.model_dump()
    bad_params["stretch_r1"] = 200
    bad_params["stretch_r2"] = 100
    invalid_resp = client.post(
        "/api/preview",
        files={"file": ("sample.webp", payload, "image/webp")},
        data={"params": json.dumps(bad_params)},
    )
    assert invalid_resp.status_code == 422


def test_batch_multiprocessing_dedupe_fault_tolerance_and_cleanup() -> None:
    """Verify batch ZIP preserves extensions, deduplicates _1, skips corrupt file, and cleans up."""
    img_a = np.full((80, 80, 3), 90, dtype=np.uint8)
    img_b = np.full((80, 80, 3), 150, dtype=np.uint8)

    jpg_bytes = _encode_test_image(img_a, ".jpg")
    png_bytes = _encode_test_image(img_b, ".png")
    params_json = EnhanceParams(brightness_mode="contrast_stretch", contrast_mode="hist_eq").model_dump_json()

    create_resp = client.post(
        "/api/batch-process",
        files=[
            ("files", ("photo.jpg", jpg_bytes, "image/jpeg")),
            ("files", ("photo.jpg", jpg_bytes, "image/jpeg")),
            ("files", ("sample.png", png_bytes, "image/png")),
            ("files", ("broken.jpg", b"not-a-valid-jpeg", "image/jpeg")),
        ],
        data={"params": params_json},
    )
    assert create_resp.status_code == 202
    job_id = create_resp.json()["job_id"]
    assert create_resp.json()["total"] == 4

    status_body = None
    for _ in range(80):
        status_resp = client.get(f"/api/batch-status/{job_id}")
        assert status_resp.status_code == 200
        status_body = status_resp.json()
        if status_body["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)

    assert status_body is not None
    assert status_body["status"] == "done"
    assert status_body["processed"] == 4
    assert status_body["failed_files"] == ["broken.jpg"]

    dl_resp = client.get(f"/api/batch-download/{job_id}")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(dl_resp.content)) as zf:
        names = sorted(zf.namelist())
        assert names == ["photo.jpg", "photo_1.jpg", "sample.png"]
        for name in names:
            decoded = cv2.imdecode(np.frombuffer(zf.read(name), dtype=np.uint8), cv2.IMREAD_COLOR)
            assert decoded is not None and decoded.shape[:2] == (80, 80)

    # Temp directory cleaned up by FileResponse BackgroundTask
    assert not (TEMP_DIR / job_id).exists()

    # Unknown job -> 404
    assert client.get("/api/batch-status/does-not-exist").status_code == 404


def test_batch_rejects_over_50_files() -> None:
    """Verify server enforces the 50-image batch limit."""
    img = np.full((16, 16, 3), 100, dtype=np.uint8)
    jpg_bytes = _encode_test_image(img, ".jpg")
    files = [("files", (f"img_{i}.jpg", jpg_bytes, "image/jpeg")) for i in range(51)]
    resp = client.post(
        "/api/batch-process",
        files=files,
        data={"params": EnhanceParams().model_dump_json()},
    )
    assert resp.status_code == 400
