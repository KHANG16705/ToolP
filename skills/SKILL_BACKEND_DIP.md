# AI SKILL: BACKEND DIGITAL IMAGE PROCESSING (FASTAPI + NUMPY + OPENCV)

> **Vai trò của AI Agent:** Bạn là Senior Python & Computer Vision Engineer. Khi sinh mã nguồn cho thư mục `backend/`, bạn phải cài đặt **chính xác 100% các công thức toán học trong giáo trình Xử lý ảnh số**, tách biệt rõ giữa **Công thức chuẩn giáo trình (tự cài đặt bằng NumPy)** và **Mở rộng thực tế**, đồng thời đảm bảo mã nguồn sạch, có cấu trúc khoa học và tối ưu hiệu năng.

---

## 1. QUY TẮC KIẾN TRÚC & CLEAN CODE BẮT BUỘC

1. **Cấu trúc module chặt chẽ:**
   * `core/color_space.py`: Đọc/ghi byte ảnh, chuyển đổi `RGB <-> HSV`.
   * `core/point_ops.py`: Các toán tử xử lý điểm ảnh `s = T(r)`.
   * `core/histogram.py`: Tính lược đồ xám, Cân bằng Histogram (NumPy thuần) và CLAHE.
   * `core/filters.py`: Lọc không gian (Averaging, Median), Hình thái học (Opening/Closing) và làm sắc nét Laplacian.
   * `core/pipeline.py`: Hàm duy nhất `enhance_image(image_rgb: np.ndarray, params: EnhanceParams)` điều phối đúng thứ tự 5 bước.
   * `services/batch_service.py`: Xử lý đa luồng, quản lý trạng thái job và nén ZIP.
   * `api/routes.py`: Chỉ làm nhiệm vụ nhận request, validate qua Pydantic và gọi `core`/`services`. Tuyệt đối không viết code xử lý ảnh trong file route.
2. **Vectorization với NumPy:**
   * Ưu tiên dùng phép toán mảng NumPy (`np.power`, `np.log1p`, `np.bincount`, `np.cumsum`, `np.lib.stride_tricks.sliding_window_view`) thay vì vòng lặp `for` lồng nhau theo từng pixel để đảm bảo tốc độ Preview `< 200ms`.
3. **An toàn kiểu dữ liệu ảnh (Tránh lỗi tràn số `uint8`):**
   * Mọi phép tính số thực (Gamma, Log, Contrast Stretching, Laplacian) **BẮT BUỘC** ép kiểu sang `np.float32` hoặc `np.float64` trước khi tính, sau đó mới `np.clip(img, 0, 255).astype(np.uint8)`.
4. **Chuẩn hóa hệ màu OpenCV:**
   * Quy ước xuyên suốt trong `core/`: Mọi hàm xử lý ảnh màu nhận đầu vào là **RGB** (`uint8`, shape `H x W x 3`). Khi dùng `cv2.imdecode` (mặc định trả về BGR), phải chuyển ngay `cv2.cvtColor(img, cv2.COLOR_BGR2RGB)` ở cửa vào và chuyển lại BGR trước khi `cv2.imencode`.

---

## 2. ĐẶC TẢ CÔNG THỨC TOÁN HỌC CHUẨN GIÁO TRÌNH (CORE PIPELINE 5 BƯỚC)

### Bước 1: Chuyển đổi không gian màu (`core/color_space.py`) — [Chuẩn giáo trình Chương 2]
* Chuyển ảnh đầu vào từ **RGB sang HSV** (`cv2.COLOR_RGB2HSV`).
* Tách 3 kênh `H, S, V = cv2.split(hsv)`.
* **Lưu lại mảng Histogram trước xử lý** từ kênh `V` gốc (`hist_before`).
* Toàn bộ Bước 2, 3, 4 chỉ thao tác trên kênh cường độ sáng `V` (ảnh xám 8-bit, mức xám `L = 256`, miền `[0, 255]`) để bảo toàn màu sắc gốc của ảnh.

---

### Bước 2: Khử nhiễu (`core/filters.py`) — [Chuẩn giáo trình Chương 3 & Chương 6]
Thực hiện **TRƯỚC** bước làm sắc nét để tránh khuếch đại nhiễu. Áp dụng **Replicate / Edge Padding** (lặp lại giá trị biên ảnh theo đúng quy ước bài tập giáo trình).

1. **Bộ lọc trung bình (`denoise_mode == "average"`):**
   * Phương trình lọc không gian 2D tổng quát:
     `g(x, y) = sum_{s=-a}^{a} sum_{t=-b}^{b} w(s, t) * f(x + s, y + t)`
   * Với mặt nạ `k x k` (`k = kernel_size`, ví dụ `3x3`), mọi trọng số `w(s, t) = 1 / (k * k)`.
   * Tác dụng: Tương đương lọc thông thấp, làm mịn nhiễu Gaussian (lưu ý: hơi làm mờ cạnh).

2. **Bộ lọc trung vị (`denoise_mode == "median"`):**
   * Bộ lọc phi tuyến chuyên trị nhiễu muối tiêu (Salt & Pepper).
   * Với tập `K = k * k` pixel láng giềng đã sắp xếp tăng dần `A = {a_1 <= a_2 <= ... <= a_K}`:
     * Vì `k` luôn là số lẻ (`3, 5, 7`) nên `K` lẻ: `median(A) = a_{(K+1)/2}` (chỉ số 0-based là `K // 2`).
   * Cài đặt bằng `sliding_window_view` + `np.median` hoặc `cv2.medianBlur(v, kernel_size)` cho ảnh lớn.

3. **Khử nhiễu Salt & Pepper bằng Hình thái học (`denoise_mode == "morph_open_close"`):**
   * Chuẩn giáo trình Chương 6 (Slide 60–61):
     * **Phép Mở (Opening):** `f o s = (f ⊖ s) ⊕ s` — loại bỏ đốm trắng (nhiễu salt).
     * **Phép Đóng (Closing):** `f • s = (f ⊕ s) ⊖ s` — loại bỏ đốm đen (nhiễu pepper).
     * **Kết hợp:** Áp dụng Opening trước, sau đó áp dụng Closing với phần tử cấu trúc (Structuring Element) hình vuông kích thước `kernel_size x kernel_size`:
       `result = closing(opening(V, se), se)` (dùng `cv2.morphologyEx` với `MORPH_OPEN` rồi `MORPH_CLOSE`).

---

### Bước 3A: Biến đổi điểm ảnh (`core/point_ops.py`) — [Chuẩn giáo trình Chương 3]
Mô hình tổng quát: `s = T(r)` với `r` là mức xám đầu vào tại `(x, y)` và `s` là mức xám đầu ra.

1. **Biến đổi hàm mũ / Hiệu chỉnh Gamma (`brightness_mode == "gamma"`):**
   * Chuẩn hóa mức xám về đoạn `[0, 1]`: `r_norm = V.astype(np.float32) / 255.0`.
   * Công thức giáo trình: `s_norm = c * (r_norm ** gamma)` (với `c = 1.0`).
   * **Mở rộng thực tế — Auto-Gamma (`auto_gamma == True`):**
     * Tính mức sáng trung bình `mean_v = float(np.mean(V))` (chặn biên an toàn `np.clip(mean_v, 1.0, 254.0)`).
     * Tính `gamma = np.log(0.5) / np.log(mean_v / 255.0)` và kẹp trong khoảng `[0.25, 3.5]`.
     * Trả giá trị `applied_gamma` này trong response của `/api/preview` để UI hiển thị.
   * Quy đổi lại 8-bit: `V = np.clip(s_norm * 255.0, 0, 255).astype(np.uint8)`.

2. **Biến đổi Logarit (`brightness_mode == "log"`):**
   * Công thức giáo trình: `s = c * log(1 + r)`.
   * Với ảnh 8-bit `r ∈ [0, 255]`, hệ số chuẩn hóa để giữ dải `[0, 255]` là `c_base = 255.0 / np.log(1.0 + 255.0)`.
   * Tính: `s = (log_c * c_base) * np.log1p(V.astype(np.float32))`, sau đó `np.clip(s, 0, 255).astype(np.uint8)`.

3. **Kéo dãn độ tương phản — Contrast Stretching (`brightness_mode == "contrast_stretch"`):**
   * Hàm tuyến tính từng đoạn đi qua `(0, 0) -> (r1, s1) -> (r2, s2) -> (255, 255)`:
     * Nếu `0 <= r <= r1`: `s = (s1 / max(r1, 1)) * r`
     * Nếu `r1 < r <= r2`: `s = s1 + ((s2 - s1) / max(r2 - r1, 1)) * (r - r1)`
     * Nếu `r2 < r <= 255`: `s = s2 + ((255 - s2) / max(255 - r2, 1)) * (r - r2)`
   * Nên tạo bảng tra cứu **LUT (Look-Up Table)** 256 phần tử bằng NumPy để ánh xạ tức thời `V = lut[V]`.

4. **Biến đổi âm bản (`negative == True`):**
   * Công thức giáo trình: `s = (L - 1) - r = 255 - r`.

---

### Bước 3B: Xử lý lược đồ xám (`core/histogram.py`) — [Chuẩn giáo trình Chương 3 + Mở rộng]

1. **Tính lược đồ xám (Histogram):**
   * Đếm số lượng pixel `n_k` cho từng mức xám `k ∈ [0, 255]` bằng `np.bincount(V.ravel(), minlength=256)`.
   * Xác suất mức xám: `p(r_k) = n_k / n` (với `n = H * W`).

2. **Cân bằng lược đồ xám (`contrast_mode == "hist_eq"`) — BẮT BUỘC tự cài bằng NumPy theo công thức giáo trình:**
   * Công thức giáo trình:
     `s_k = T(r_k) = (L - 1) * sum_{j=0}^{k} (n_j / n)` với `L = 256`, `k = 0, 1, ..., 255`.
   * Cài đặt sạch bằng NumPy:
     ```python
     counts = np.bincount(v_channel.ravel(), minlength=256)
     pdf = counts / float(v_channel.size)
     cdf = np.cumsum(pdf)
     lut = np.round(255.0 * cdf).astype(np.uint8)
     return lut[v_channel]
     ```

3. **Mở rộng thực tế — CLAHE (`contrast_mode == "clahe"`):**
   * Dùng `cv2.createCLAHE(clipLimit=params.clahe_clip_limit, tileGridSize=(8, 8)).apply(v_channel)` để cân bằng tương phản cục bộ, tránh cháy sáng nền trơn.

---

### Bước 4: Làm sắc nét bằng Toán tử Laplacian (`core/filters.py`) — [Chuẩn giáo trình Chương 3]
* **Nguyên lý giáo trình:**
  * Đạo hàm bậc 2 (Laplacian): `∇²f = ∂²f/∂x² + ∂²f/∂y²`.
  * Tăng cường sắc nét: `g(x, y) = f(x, y) - α * ∇²f` (khi `α = 1.0`, khớp chính xác 100% công thức `g = f - ∇²f` trong giáo trình).
* **Hai mặt nạ `∇²` chuẩn giáo trình:**
  * `laplacian_4` (4-láng giềng, tâm `-4`):
    ```python
    KERNEL_LAP_4 = np.array([[0,  1, 0],
                             [1, -4, 1],
                             [0,  1, 0]], dtype=np.float32)
    ```
    *(Khi `α = 1.0`, tương đương mặt nạ gộp 1 bước có tâm `5` và 4 cạnh `-1`)*
  * `laplacian_8` (Biến thể 8-láng giềng, tâm `-8`):
    ```python
    KERNEL_LAP_8 = np.array([[1,  1, 1],
                             [1, -8, 1],
                             [1,  1, 1]], dtype=np.float32)
    ```
    *(Khi `α = 1.0`, tương đương mặt nạ gộp 1 bước có tâm `9` và 8 lân cận `-1`)*
* **Cài đặt an toàn không tràn số:**
  ```python
  v_float = v_channel.astype(np.float32)
  lap = cv2.filter2D(v_float, ddepth=cv2.CV_32F, kernel=kernel, borderType=cv2.BORDER_REPLICATE)
  sharpened = v_float - (alpha * lap)
  return np.clip(sharpened, 0, 255).astype(np.uint8)
  ```

---

### Bước 5: Ghép kênh & Xuất ảnh (`core/pipeline.py`)
* Tính mảng `hist_after` (256 phần tử `list[int]`) từ kênh `V` cuối cùng.
* Ghép `hsv_out = cv2.merge([H, S, V_out])` và chuyển ngược về RGB (`cv2.COLOR_HSV2RGB`).

---

## 3. XỬ LÝ HÀNG LOẠT ĐA LUỒNG & NÉN ZIP (`services/batch_service.py`)

* **Tương thích Windows (Rất quan trọng):** Khi dùng `concurrent.futures.ProcessPoolExecutor` trên Windows (`spawn` method), hàm worker `process_single_file_task(input_path, output_path, params_dict)` **PHẢI là top-level function** (định nghĩa ở mức module, không lồng bên trong class hoặc route) để có thể `pickle` được.
* **Quản lý Job:**
  * Lưu trạng thái trong dictionary toàn cục `JOBS: dict[str, dict]` có trường `processed`, `total`, `status`, `zip_path`, `error`.
  * Lưu ảnh upload tạm vào `temp_jobs/{job_id}/input/`, ảnh kết quả vào `temp_jobs/{job_id}/output/`, sau đó nén bằng `zipfile.ZipFile` thành `temp_jobs/{job_id}/enhanced_photos.zip`.
* **Dọn dẹp tài nguyên:** Sau khi tải ZIP thành công hoặc khi job quá 30 phút, có hàm dọn thư mục tạm để tránh đầy ổ cứng.

---

## 4. CẤU HÌNH FASTAPI & CORS (`main.py`)

* Mở `CORSMiddleware` cho `["http://localhost:5173", "http://127.0.0.1:5173"]`.
* Kiểm tra định dạng file đầu vào (chỉ nhận `image/jpeg`, `image/png`, `image/webp`; trả `400 Bad Request` nếu sai định dạng).
* Trả về lỗi JSON rõ ràng khi `params` không hợp lệ (`422`) hoặc `job_id` không tồn tại (`404`).
