# HƯỚNG DẪN BÀN GIAO CHO TV1 & TV2 (HANDOFF GUIDE)

> **Dự án:** Batch Photo Enhancer (Spatial Domain Digital Image Processing)  
> **Repository:** `https://github.com/KHANG16705/ToolP.git`  
> **Tài liệu chuẩn:** Đọc kỹ `README.md` và file `skills/SKILL_*.md` tương ứng trước khi làm.

---

## PHẦN 1: HƯỚNG DẪN DÀNH CHO TV1 (FRONTEND UI)

### 1.1. Lấy code & chuyển sang nhánh `feat/frontend-ui`
```powershell
git clone https://github.com/KHANG16705/ToolP.git
cd ToolP
git checkout feat/frontend-ui
```
*(Nếu đã clone trước đó: `git fetch origin && git checkout feat/frontend-ui && git pull origin feat/frontend-ui`.)*

### 1.2. Khởi chạy Backend & Frontend trong 2 cú click
1. **Click đúp `run_backend.bat`** ở thư mục gốc: tự tạo `venv`, cài thư viện Python và mở FastAPI thật ở `http://127.0.0.1:8000` (đúng 1 worker).
2. **Click đúp `run_frontend.bat`** ở thư mục gốc: tự chạy `npm install` (lần đầu) và mở Vite ở `http://127.0.0.1:5173`.
3. Vào `http://127.0.0.1:5173` thấy badge xanh **`Backend API Ready (:8000)`** là sẵn sàng code!

### 1.3. Các file Contract Lead đã dựng sẵn (KHÔNG đổi tên trường / KHÔNG sửa `backend/`)
- `frontend/src/constants/defaultParams.js`:
  - `DEFAULT_ENHANCE_PARAMS` (đủ 15 trường khớp 100% Backend)
  - `ALLOWED_MIME_TYPES` (`image/jpeg`, `image/png`, `image/webp`)
  - `MAX_BATCH_FILES = 50`, `MAX_FILE_SIZE_MB = 15`, `MAX_FILE_SIZE_BYTES`
  - `PREVIEW_MAX_WIDTH = 800`, `DEBOUNCE_MS = 280`, `POLL_INTERVAL_MS = 800`
- `frontend/src/services/api.js`:
  - `previewEnhance(imageBlob, params, signal)` $\rightarrow$ `POST /api/preview`
  - `startBatchProcess(files, params)` $\rightarrow$ `POST /api/batch-process`
  - `getBatchStatus(jobId)` $\rightarrow$ `GET /api/batch-status/{job_id}`
  - `downloadBatchZip(jobId)` $\rightarrow$ `GET /api/batch-download/{job_id}` (trả `Blob`)
  - `checkBackendHealth()` $\rightarrow$ `GET /health`
- `frontend/src/utils/imageResize.js`:
  - `resizeImageForPreview(file)` $\rightarrow$ resize cạnh dài nhất `<= 800px`, xuất JPEG `0.9`.

### 1.4. Danh sách chính xác 5 Component TV1 cần xây dựng (trong `frontend/src/components/`)
Bám sát thiết kế Dark Mode Studio (`slate-950`/`slate-900`, nhấn `indigo-500`/`sky-500`) trong `skills/SKILL_FRONTEND_REACT.md`:

| # | File Component | Nhiệm vụ cốt lõi & Điểm bắt buộc |
| :-: | :--- | :--- |
| 1 | `UploadDropzone.jsx` | Kéo-thả chọn 1–50 ảnh (`image/jpeg`, `image/png`, `image/webp`, `<= 15MB`/ảnh); hiển thị danh sách ảnh; cho phép click đổi ảnh mẫu Preview và xóa ảnh. |
| 2 | `ControlPanel.jsx` | 4 nhóm điều khiển (Bước 1: Denoise, Bước 2: Brightness + Auto-Gamma + Negative, Bước 3: Histogram/CLAHE, Bước 4: Laplacian) + nút **Reset mặc định**. Đảm bảo `stretch_r1 < stretch_r2`; hiển thị `applied_gamma` khi `applied_gamma !== null`. |
| 3 | `BeforeAfterSlider.jsx` | Chồng khít ảnh gốc & `processed_image` (`object-contain`), thanh kéo dùng `clip-path`, nhãn *Ảnh gốc (Before)* / *Sau xử lý (After)*, hiển thị trạng thái đang xử lý & `processing_time_ms`. |
| 4 | `HistogramChart.jsx` | Dùng **`recharts`** (`AreaChart` + `ResponsiveContainer`) vẽ 256 mức xám chồng 2 lớp (`hist_before` màu xám, `hist_after` màu indigo/sky). |
| 5 | `BatchProgressModal.jsx` | Polling `getBatchStatus(jobId)` mỗi `800ms`, luôn `clearInterval` khi xong/lỗi/unmount; nếu `failed_files.length > 0` hiện cảnh báo các file hỏng bị bỏ qua; khi `status === "done"` hiện nút tải `enhanced_photos.zip` qua `downloadBatchZip(jobId)`. |

- Sau đó ghép cả 5 component vào `frontend/src/App.jsx` với cơ chế **Debounce `280ms` + `AbortController`** cho `previewEnhance`, và hiện Banner lỗi thân thiện nếu Backend offline.
- Trước khi push: chạy `cd frontend && npm run build` đảm bảo 0 lỗi, rồi push lên `feat/frontend-ui` và tạo Pull Request vào `main`.

---

## PHẦN 2: HƯỚNG DẪN DÀNH CHO TV2 (DATASET, QA & BÁO CÁO)

### 2.1. Lấy code & chuyển sang nhánh `docs/dataset-report`
```powershell
git clone https://github.com/KHANG16705/ToolP.git
cd ToolP
git checkout docs/dataset-report
```

### 2.2. Chuẩn bị bộ ảnh test theo 4 nhóm lỗi chuẩn giáo trình
Tạo thư mục `sample_images/` (có thể chia 4 thư mục con) với tổng 15–25 ảnh thực tế (gồm đủ `.jpg`, `.png`, `.webp`) để vừa test QA vừa chụp hình minh họa Báo cáo:

1. **Nhóm 1 — Ảnh thiếu sáng / ngược sáng / quá tối (`01_low_light/`):**
   - Dùng để kiểm thử & so sánh **Gamma (`gamma < 1`)**, **Auto-Gamma (`auto_gamma: true`)**, và **Biến đổi Logarit (`log`)**.
2. **Nhóm 2 — Ảnh tương phản kém / mờ sương / dải xám hẹp (`02_low_contrast/`):**
   - Dùng để kiểm thử **Contrast Stretching**, **Histogram Equalization (`hist_eq`)**, và **CLAHE (`clahe`)**; chụp ảnh Histogram 256 mức xám trước & sau để đưa vào báo cáo.
3. **Nhóm 3 — Ảnh nhiễu hạt / nhiễu muối tiêu (`03_noisy/`):**
   - Ảnh có nhiễu Gaussian và ảnh có đốm đen/trắng Salt & Pepper để so sánh **Averaging (`average`)**, **Median (`median`)**, và **Morphology Opening + Closing (`morph_open_close`)** với `kernel_size` `3`, `5`, `7`.
4. **Nhóm 4 — Ảnh mờ cạnh & Bộ ảnh kiểm thử biên (`04_blurry_and_edge_cases/`):**
   - Ảnh hơi out-focus / chữ mờ để kiểm thử **Laplacian 4-láng giềng** vs **8-láng giềng** (`sharpen_alpha` từ `0.3` đến `1.0`).
   - Thêm test case biên cho QA: 2 ảnh **trùng tên file** (kiểm tra tự đổi thành `_1`), 1 file ảnh **cố tình bị hỏng** (tạo file `.jpg` chứa chữ rác để xác minh `failed_files` hoạt động đúng), và 1 file sai định dạng `.txt` (xác minh lỗi `400`).

### 2.3. Cách test nhanh toàn bộ API trên Swagger UI
1. **Click đúp `run_backend.bat`** ở thư mục gốc.
2. Mở trình duyệt truy cập **`http://127.0.0.1:8000/docs`**.
3. Test lần lượt 5 endpoint trực tiếp bằng nút **Try it out $\rightarrow$ Execute**:
   - **`GET /health`:** Xác nhận trả `200 OK` với `{"status": "ok"}`.
   - **`POST /api/preview`:** Chọn 1 file ảnh bất kỳ ở trường `file`, dán chuỗi JSON sau vào trường `params`:
     ```json
     {"denoise_mode":"median","kernel_size":3,"brightness_mode":"gamma","gamma":1.0,"auto_gamma":true,"log_c":1.0,"negative":false,"stretch_r1":30,"stretch_s1":10,"stretch_r2":225,"stretch_s2":245,"contrast_mode":"clahe","clahe_clip_limit":2.0,"sharpen_mode":"laplacian_4","sharpen_alpha":0.5}
     ```
     *Kiểm tra:* Response `200`, có `processed_image`, `hist_before` & `hist_after` đủ 256 số, `applied_gamma` là số thực (đổi `brightness_mode` sang `"log"` sẽ trả `null`), `processing_time_ms < 200`.
   - **`POST /api/batch-process`:** Chọn nhiều file ở trường `files` (thử gồm cả ảnh trùng tên và 1 ảnh hỏng) + dán `params` như trên $\rightarrow$ xác nhận trả `202 Accepted` và copy `job_id`.
   - **`GET /api/batch-status/{job_id}`:** Dán `job_id` $\rightarrow$ xác nhận `status` chuyển sang `"done"`, kiểm tra `processed == total` và tên ảnh hỏng nằm trong `failed_files`.
   - **`GET /api/batch-download/{job_id}`:** Dán `job_id` $\rightarrow$ bấm **Download file** để tải `enhanced_photos.zip`, giải nén kiểm tra ảnh giữ nguyên đuôi gốc và file trùng tên đã có hậu tố `_1`.
4. **Test các ca lỗi bắt buộc (Negative Testing):**
   - Upload file `.txt` $\rightarrow$ phải trả **`400 Bad Request`**.
   - Truyền `stretch_r1: 200, stretch_r2: 100` $\rightarrow$ phải trả **`422 Unprocessable Content`**.
   - Gọi `/api/batch-status/khong-ton-tai` $\rightarrow$ phải trả **`404 Not Found`**.
