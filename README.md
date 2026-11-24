# BATCH PHOTO ENHANCER — MASTER SPEC & AI AGENT README

> **Mục đích tài liệu:** Đây là tài liệu đặc tả kiến trúc gốc (**Single Source of Truth**) dành cho **AI Coding Agents** (Cursor, Windsurf, Claude Code, GitHub Copilot) và đội ngũ lập trình viên. Mọi mã nguồn ở `backend/` và `frontend/` **BẮT BUỘC** tuân thủ tuyệt đối hợp đồng API, cấu trúc thư mục và quy tắc Clean Code dưới đây.

---

## 1. TỔNG QUAN DỰ ÁN

**Batch Photo Enhancer** là ứng dụng web phục chế và nâng cấp chất lượng ảnh hàng loạt, sử dụng các thuật toán **Xử lý ảnh số trong miền không gian (Spatial Domain Digital Image Processing)** làm lõi Backend.

* **Chế độ Live Preview:** Người dùng tải lên 1 hoặc nhiều ảnh, chọn 1 ảnh mẫu (được resize xuống tối đa `800px` ở phía Client) để tinh chỉnh thanh trượt thông số và xem ngay kết quả Trước/Sau (**Before-After Slider**) cùng biểu đồ **Histogram** (256 mức xám) trong `< 200ms`.
* **Chế độ Batch Processing:** Áp dụng bộ thông số đã chốt lên toàn bộ ảnh độ phân giải gốc bằng tiến trình ngầm đa nhân CPU (`ProcessPoolExecutor`), theo dõi tiến độ theo thời gian thực và tải về 1 file `.zip` duy nhất.

---

## 2. QUY TẮC CODE SẠCH & CẤU TRÚC KHOA HỌC (MANDATORY CLEAN CODE RULES)

AI Agent **BẮT BUỘC** tuân thủ các nguyên tắc sau khi sinh mã nguồn cho cả Backend và Frontend:

1. **Phân tách trách nhiệm rõ ràng (Separation of Concerns):**
   * Tuyệt đối **KHÔNG** viết dồn toàn bộ logic vào một file duy nhất (`main.py` hoặc `App.jsx`).
   * Mỗi module/file chỉ đảm nhiệm 1 vai trò duy nhất (thuật toán thuần tách riêng khỏi pipeline, pipeline tách riêng khỏi API router, UI tách thành các component nhỏ tái sử dụng).
2. **Hàm ngắn gọn, đơn nhiệm (Single Responsibility):**
   * Mỗi hàm tối đa ~30–40 dòng, chỉ làm đúng một việc, đầu vào và đầu ra rõ ràng.
   * Đặt tên biến, tên hàm tiếng Anh tự mô tả ngữ nghĩa (ví dụ: `apply_gamma_correction`, `compute_normalized_histogram`, không dùng tên vô nghĩa như `func1`, `tmp`, `x2`).
3. **Kiểu dữ liệu tường minh (Strict Typing):**
   * **Backend (Python):** Dùng đầy đủ Type Hints (`np.ndarray`, `dict[str, Any]`, `Literal[...]`) và **Pydantic v2** cho mọi request/response schema.
   * **Frontend (React):** Khai báo rõ cấu trúc props/state, gom toàn bộ hằng số mặc định và cấu hình API vào một nơi tập trung (`constants.js` và `services/api.js`).
4. **Không Magic Numbers & Không lặp code (DRY):**
   * Mọi ngưỡng mặc định (ví dụ: `PREVIEW_MAX_WIDTH = 800`, `DEBOUNCE_MS = 280`, `GRAY_LEVELS = 256`) phải khai báo thành hằng số ở đầu module.
5. **Code sạch, dễ đọc, dễ bảo trì:**
   * Chỉ thêm docstring ngắn gọn mô tả công thức/mục đích ở đầu hàm thuật toán; tránh comment thừa giải thích từng dòng code hiển nhiên.
   * Xử lý lỗi đầy đủ (try/except có thông báo lỗi thân thiện bằng HTTP status code chuẩn `400`, `404`, `422`, `500`).

---

## 3. CẤU TRÚC THƯ MỤC MONOREPO CHUẨN

```text
batch-photo-enhancer/
├── README.md                          # Tài liệu này (Master Spec & API Contract)
├── HANDOFF_TV1_TV2.md                 # Hướng dẫn bàn giao & chạy thử cho TV1, TV2
├── run_backend.bat                    # Script click đúp chạy Backend (Windows, 1 worker)
├── run_frontend.bat                   # Script click đúp chạy Frontend (Windows)
├── skills/
│   ├── SKILL_BACKEND_DIP.md           # Hướng dẫn chi tiết công thức & code Backend
│   └── SKILL_FRONTEND_REACT.md        # Hướng dẫn chi tiết UI & tích hợp Frontend
├── backend/
│   ├── main.py                        # Khởi tạo FastAPI, CORS, GET /health, đăng ký routers
│   ├── config.py                      # Hằng số cấu hình (TEMP_DIR, MAX_WORKERS, giới hạn 50 ảnh/15MB)
│   ├── requirements.txt               # Danh sách thư viện Python (dùng opencv-python-headless)
│   ├── schemas/
│   │   └── enhance.py                 # Pydantic models (EnhanceParams, PreviewResponse, BatchStatus)
│   ├── core/
│   │   ├── color_space.py             # Chuyển đổi RGB <-> HSV, tách/ghép kênh Value (V)
│   │   ├── point_ops.py               # Brightness (Gamma/Auto-Gamma, Log, Contrast Stretch) -> Negative
│   │   ├── histogram.py               # Tính Histogram, Histogram Equalization (NumPy), CLAHE
│   │   ├── filters.py                 # Averaging, Median (cv2.medianBlur), Opening/Closing, Laplacian 4 & 8
│   │   └── pipeline.py                # Điều phối chuỗi xử lý 5 bước chuẩn
│   ├── services/
│   │   └── batch_service.py           # Quản lý Job, ProcessPoolExecutor, ZIP (giữ đuôi, _1/_2, failed_files)
│   ├── api/
│   │   └── routes.py                  # Định nghĩa 4 REST API Endpoints
│   └── tests/
│       └── test_dip_and_api.py        # Bộ test tự động kiểm tra toán học DIP, API & đa tiến trình
└── frontend/
    ├── .env                           # VITE_API_URL=http://127.0.0.1:8000
    ├── .env.example
    ├── package.json                   # React + Vite + Tailwind + Axios + Recharts + Lucide
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                    # Layout chính điều phối trạng thái
        ├── constants/
        │   └── defaultParams.js       # Giá trị mặc định cho EnhanceParams & giới hạn upload
        ├── services/
        │   └── api.js                 # Axios client + hàm gọi API chuẩn Contract
        ├── utils/
        │   └── imageResize.js         # Resize ảnh mẫu xuống max 800px trên Canvas
        └── components/
            ├── UploadDropzone.jsx     # Kéo-thả nhiều ảnh & danh sách ảnh đã chọn
            ├── ControlPanel.jsx       # Thanh trượt & nút chọn thuật toán (4 bước UI)
            ├── BeforeAfterSlider.jsx  # Thanh gạt so sánh ảnh Trước / Sau
            ├── HistogramChart.jsx     # Biểu đồ 256 mức xám (Recharts — Trước & Sau)
            └── BatchProgressModal.jsx # Thanh tiến độ xử lý hàng loạt, cảnh báo failed_files & tải ZIP
```

### Quy ước phân công & Git Flow (Nhóm 3 người)
* **Nhánh chính:** `main` (chứa nền tảng đã kiểm thử) và 3 nhánh công việc:
  * `feat/backend-core` — **Lead:** Toàn bộ `backend/` + tích hợp hệ thống.
  * `feat/frontend-ui` — **TV1:** Toàn bộ 5 component UI + `App.jsx` trong `frontend/src/`.
  * `docs/dataset-report` — **TV2:** Bộ ảnh kiểm thử (Dataset), QA trên Swagger/UI và Báo cáo.

---

## 4. HỢP ĐỒNG API (API CONTRACT — KHÓA CỨNG FE & BE)

**Base URL (Local):** `http://127.0.0.1:8000`

### 4.1. Cấu trúc đối tượng `EnhanceParams` (JSON Schema)
Dùng chung cho cả `/api/preview` và `/api/batch-process` (gửi dưới dạng chuỗi JSON trong trường `params` của `multipart/form-data`):

```json
{
  "denoise_mode": "none",
  "kernel_size": 3,
  "brightness_mode": "gamma",
  "gamma": 1.0,
  "auto_gamma": false,
  "log_c": 1.0,
  "negative": false,
  "stretch_r1": 30,
  "stretch_s1": 10,
  "stretch_r2": 225,
  "stretch_s2": 245,
  "contrast_mode": "none",
  "clahe_clip_limit": 2.0,
  "sharpen_mode": "none",
  "sharpen_alpha": 0.5
}
```

**Bảng ràng buộc giá trị hợp lệ (Validation Rules):**

| Tên trường | Kiểu | Giá trị hợp lệ | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| `denoise_mode` | `string` | `"none"`, `"median"`, `"average"`, `"morph_open_close"` | Chế độ khử nhiễu (Bước 2) |
| `kernel_size` | `int` | `3`, `5`, `7` (bắt buộc số lẻ) | Kích thước cửa sổ lọc / phần tử cấu trúc |
| `brightness_mode` | `string` | `"none"`, `"gamma"`, `"log"`, `"contrast_stretch"` | Chế độ biến đổi điểm ảnh (Bước 3A) |
| `gamma` | `float` | `0.2` đến `4.0` (mặc định `1.0`) | Hệ số mũ Gamma (`< 1` sáng lên, `> 1` tối đi) |
| `auto_gamma` | `bool` | `true` / `false` | Tự động tính Gamma theo độ sáng trung bình ảnh |
| `log_c` | `float` | `0.5` đến `2.0` (mặc định `1.0`) | Hệ số khuếch đại cho biến đổi Logarit |
| `negative` | `bool` | `true` / `false` | Bật/tắt biến đổi âm bản (`s = 255 - r`). **Thứ tự thực thi:** chạy `brightness_mode` trước $\rightarrow$ nếu `negative == true` tính `255 - V` $\rightarrow$ sang `contrast_mode` |
| `stretch_r1`, `stretch_s1` | `int` | `0` đến `255` (`r1 < r2`) | Điểm mốc thấp `(r1, s1)` cho Contrast Stretching |
| `stretch_r2`, `stretch_s2` | `int` | `0` đến `255` (`r1 < r2`) | Điểm mốc cao `(r2, s2)` cho Contrast Stretching |
| `contrast_mode` | `string` | `"none"`, `"hist_eq"`, `"clahe"` | Cân bằng Histogram toàn cục hoặc CLAHE cục bộ (Bước 3B) |
| `clahe_clip_limit` | `float` | `1.0` đến `8.0` (mặc định `2.0`) | Giới hạn cắt trần tương phản của CLAHE |
| `sharpen_mode` | `string` | `"none"`, `"laplacian_4"`, `"laplacian_8"` | Làm sắc nét Laplacian 4-láng giềng hoặc 8-láng giềng (Bước 4) |
| `sharpen_alpha` | `float` | `0.0` đến `1.0` (mặc định `0.5`) | Cường độ sắc nét (`1.0` = công thức gốc giáo trình) |

---

### 4.2. Chi tiết Các API Endpoints (4 Core + 1 Health Check)

**Quy định chung về Upload (cả FE & BE):**
* **Định dạng ảnh chấp nhận (MIME Types):** `image/jpeg`, `image/png`, `image/webp` (trả `400 Bad Request` nếu sai định dạng).
* **Giới hạn Server:** Tối đa **50 ảnh/batch**, tối đa **15MB/ảnh**.
* **Đóng gói Batch ZIP:** Giữ nguyên đuôi ảnh gốc (`.jpg`/`.jpeg`/`.png`/`.webp`); nếu trùng tên file tự thêm hậu tố `_1`, `_2`; nếu có ảnh hỏng/không giải mã được sẽ bỏ qua ảnh đó và ghi vào `failed_files` thay vì làm fail cả batch.

#### 0) `GET /health`
* **Response (`200 OK`, `application/json`):**
```json
{
  "status": "ok"
}
```

#### 1) `POST /api/preview`
* **Content-Type:** `multipart/form-data`
* **Form Fields:**
  * `file`: 1 file ảnh mẫu (`image/jpeg`, `image/png`, `image/webp`, tối đa `15MB`).
  * `params`: Chuỗi JSON tuân theo schema `EnhanceParams`.
* **Response (`200 OK`, `application/json`):**
```json
{
  "processed_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "hist_before": [12, 34, 56, "... (đủ 256 số nguyên)"],
  "hist_after": [0, 15, 42, "... (đủ 256 số nguyên)"],
  "applied_gamma": 0.65,
  "processing_time_ms": 42.5
}
```
*(Lưu ý: `applied_gamma` có kiểu `float | None` — trả số thực khi `brightness_mode == "gamma"`, trả `null` ở các mode khác.)*

#### 2) `POST /api/batch-process`
* **Content-Type:** `multipart/form-data`
* **Form Fields:**
  * `files`: Danh sách từ 1 đến 50 file ảnh gốc (`image/jpeg`, `image/png`, `image/webp`, mỗi file tối đa `15MB`, gửi lặp key `files`).
  * `params`: Chuỗi JSON tuân theo schema `EnhanceParams`.
* **Response (`202 Accepted`, `application/json`):**
```json
{
  "job_id": "7f3c9a12-8b4e-4d91-a210-9c4f1e2b3d4a",
  "total": 25,
  "status": "queued"
}
```

#### 3) `GET /api/batch-status/{job_id}`
* **Response (`200 OK`, `application/json`):**
```json
{
  "job_id": "7f3c9a12-8b4e-4d91-a210-9c4f1e2b3d4a",
  "processed": 15,
  "total": 25,
  "status": "processing",
  "failed_files": [],
  "error": null
}
```
*(Các giá trị `status`: `"queued"`, `"processing"`, `"done"`, `"failed"`. Mảng `failed_files` liệt kê tên các ảnh hỏng bị bỏ qua trong batch.)*

#### 4) `GET /api/batch-download/{job_id}`
* **Response (`200 OK`):** `application/zip` với header `Content-Disposition: attachment; filename="enhanced_photos.zip"`.
* Nếu job chưa xong hoặc không tồn tại: trả `404 Not Found` hoặc `400 Bad Request`.

---

## 5. HƯỚNG DẪN CHẠY & DEBUG NHANH

> **Chạy nhanh trên Windows:** Có thể click đúp trực tiếp `run_backend.bat` và `run_frontend.bat` ở thư mục gốc dự án.

### Chạy Backend (Bắt buộc chạy đúng 1 worker do `JOBS` lưu trên RAM)
```bash
cd backend
# Windows (khuyến nghị dùng py launcher):
py -m venv venv
venv\Scripts\activate
# macOS / Linux:
# python3 -m venv venv && source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000 --workers 1
```
* Kiểm tra sức khỏe server tại: `http://127.0.0.1:8000/health`
* Kiểm tra Swagger UI tại: `http://127.0.0.1:8000/docs`

### Chạy Frontend
```bash
cd frontend
npm install
npm run dev
```
* Mở trình duyệt tại: `http://127.0.0.1:5173` (hoặc `http://localhost:5173`)

### Checklist Debug nhanh khi gặp lỗi
* **Lỗi CORS trên trình duyệt:** Kiểm tra `allow_origins` trong `backend/main.py` đã bao gồm `http://localhost:5173` và `http://127.0.0.1:5173` chưa.
* **Lỗi `422 Unprocessable Entity`:** Mở DevTools -> tab Network -> Payload để kiểm tra key `params` đã được `JSON.stringify()` đúng tên trường như mục 4.1 chưa.
* **Ảnh bị ám màu xanh/đỏ bất thường:** Kiểm tra lại thứ tự chuyển đổi BGR <-> RGB của OpenCV trong `backend/core/color_space.py`.
