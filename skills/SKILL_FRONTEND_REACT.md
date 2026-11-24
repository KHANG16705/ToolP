# AI SKILL: FRONTEND WEB APP (REACT + VITE + TAILWIND CSS)

> **Vai trò của AI Agent:** Bạn là Senior Frontend Engineer chuyên về React và UX cho các công cụ xử lý đồ họa/ảnh. Nhiệm vụ của bạn là xây dựng giao diện web trong thư mục `frontend/` sạch sẽ, trực quan, mượt mà, khớp tuyệt đối với **API Contract** trong `README.md`.

---

## 1. QUY TẮC CODE SẠCH & CẤU TRÚC KHOA HỌC

1. **Tách biệt tầng dữ liệu và giao diện:**
   * Toàn bộ lời gọi HTTP nằm tập trung trong `src/services/api.js` (dùng `axios` đọc `import.meta.env.VITE_API_URL`). Tuyệt đối không viết cứng URL `http://127.0.0.1:8000` trong component.
   * Toàn bộ giá trị mặc định của `EnhanceParams` nằm trong `src/constants/defaultParams.js`.
   * Logic resize ảnh trên Canvas nằm trong `src/utils/imageResize.js`.
2. **Component nhỏ gọn, dễ đọc:**
   * Chia rõ 5 component chuyên biệt trong `src/components/`: `UploadDropzone`, `ControlPanel`, `BeforeAfterSlider`, `HistogramChart`, `BatchProgressModal`.
   * Mỗi component chỉ nhận props cần thiết, tránh nhồi nhét logic phức tạp vào `App.jsx`.
3. **Phong cách giao diện (UI/UX):**
   * Dùng **Dark Mode Studio** nhẹ nhàng (nền `slate-950` / `slate-900`, chữ sáng, điểm nhấn màu `indigo-500` hoặc `sky-500`) giống các phần mềm chỉnh ảnh chuyên nghiệp để nổi bật màu sắc bức ảnh.
   * Bố cục 2 cột trên Desktop:
     * **Cột trái (320px–360px):** Upload danh sách ảnh + Bảng điều khiển thông số (ControlPanel) + Nút **"Xử lý hàng loạt & Tải ZIP"**.
     * **Cột phải (Chiếm phần còn lại):** Khung **Before-After Slider** lớn ở trên + Biểu đồ **Histogram Trước/Sau** ở dưới.

---

## 2. LUỒNG TƯƠNG TÁC & KỸ THUẬT TỐI ƯU BẮT BUỘC

### 2.1. Upload & Tự động tạo ảnh mẫu 800px (`utils/imageResize.js`)
* Khi người dùng kéo-thả nhiều ảnh (1 đến 50 ảnh):
  * Lưu danh sách `File` gốc vào state `files` (dùng cho Batch Processing).
  * Cho phép người dùng click chọn bất kỳ ảnh nào trong danh sách để làm **ảnh mẫu Preview** (mặc định là ảnh đầu tiên).
  * Trước khi gửi lên `POST /api/preview`, dùng HTML5 `<canvas>` thu nhỏ ảnh mẫu sao cho cạnh lớn nhất `<= 800px` (`PREVIEW_MAX_WIDTH = 800`) và xuất ra `Blob` JPEG chất lượng `0.9`. Cách này giảm dung lượng tải lên từ 5MB xuống ~80KB, giúp Preview phản hồi cực nhanh.

### 2.2. Debounce & AbortController chống spam API (Rất quan trọng)
* Khi người dùng kéo thanh trượt (`gamma`, `sharpen_alpha`, `clahe_clip_limit`, `stretch_r1/r2`), **KHÔNG** gọi API ngay lập tức theo từng pixel di chuột.
* **Bắt buộc kết hợp 2 cơ chế:**
  1. **Debounce `280ms`:** Chỉ gọi `POST /api/preview` sau khi người dùng dừng kéo chuột 280ms.
  2. **`AbortController`:** Nếu có request mới được phát đi khi request cũ chưa trả về, lập tức gọi `controller.abort()` để hủy request cũ, tránh tình trạng ảnh bị nhảy ngược (race condition).
* Hiển thị chỉ báo nhỏ `Đang xử lý...` và thời gian phản hồi (`processing_time_ms`) ở góc khung ảnh.

### 2.3. Before-After Slider (`components/BeforeAfterSlider.jsx`)
* Hiển thị ảnh gốc (bên trái) và ảnh sau xử lý `processed_image` (bên phải) chồng khít lên nhau cùng tỷ lệ `object-contain`.
* Dùng thanh kéo dọc (`input type="range"` ẩn hoặc sự kiện chuột/cảm ứng `pointermove`) điều chỉnh `clip-path: inset(0 ${100 - pos}% 0 0)` để người dùng gạt qua lại so sánh trực tiếp độ nét và độ sáng.
* Gắn nhãn nhỏ **"Ảnh gốc (Before)"** và **"Sau xử lý (After)"** ở 2 góc trên.

### 2.4. Biểu đồ Histogram 256 mức xám (`components/HistogramChart.jsx`)
* Dùng `chart.js` (`react-chartjs-2`) hoặc `recharts` vẽ 2 đường/vùng chồng lên nhau (Area Chart):
  * `hist_before`: Màu xám nhạt bán trong suốt.
  * `hist_after`: Màu xanh dương/indigo bán trong suốt.
* Trục hoành `0 -> 255` (mức cường độ sáng kênh V), ẩn bớt tick để biểu đồ thoáng đẹp.

### 2.5. Bảng điều khiển thông số bám sát giáo trình (`components/ControlPanel.jsx`)
Chia thành 4 nhóm rõ ràng tương ứng đúng 4 bước xử lý của Backend (kèm nút **Reset mặc định**):
1. **Bước 1 — Khử nhiễu (Denoising):**
   * Dropdown `denoise_mode`: Không (`none`), Lọc trung vị - Median (`median`), Lọc trung bình - Averaging (`average`), Hình thái học Mở + Đóng (`morph_open_close`).
   * Chọn kích thước cửa sổ `kernel_size`: `3x3`, `5x5`, `7x7` (chỉ hiện khi `denoise_mode !== "none"`).
2. **Bước 2 — Độ sáng & Điểm ảnh (Point Operations):**
   * Dropdown `brightness_mode`: Không (`none`), Hiệu chỉnh Gamma (`gamma`), Biến đổi Logarit (`log`), Kéo dãn tương phản (`contrast_stretch`).
   * Nếu `gamma`: Có nút toggle **"Tự động Gamma (Auto-Gamma)"** và thanh trượt `gamma` (`0.2` – `4.0`, bước `0.05`). Khi bật `auto_gamma`, khóa thanh trượt và hiển thị giá trị `applied_gamma` mà Backend tính được.
   * Nếu `log`: Thanh trượt `log_c` (`0.5` – `2.0`).
   * Nếu `contrast_stretch`: 4 thanh trượt `r1, s1, r2, s2` (đảm bảo ràng buộc `r1 < r2`).
   * Checkbox độc lập: **Ảnh âm bản (Negative)**.
3. **Bước 3 — Cân bằng tương phản (Histogram):**
   * Radio/Dropdown `contrast_mode`: Không (`none`), Cân bằng Histogram toàn cục (`hist_eq`), CLAHE cục bộ (`clahe`).
   * Nếu `clahe`: Hiện thanh trượt `clahe_clip_limit` (`1.0` – `8.0`, bước `0.5`).
4. **Bước 4 — Làm sắc nét (Laplacian Sharpening):**
   * Dropdown `sharpen_mode`: Không (`none`), Laplacian 4-láng giềng - Nhẹ (`laplacian_4`), Laplacian 8-láng giềng - Mạnh (`laplacian_8`).
   * Nếu bật: Hiện thanh trượt cường độ `sharpen_alpha` (`0.0` – `1.0`, bước `0.05`).

### 2.6. Luồng Xử lý hàng loạt & Polling tải ZIP (`components/BatchProgressModal.jsx`)
1. Khi bấm **"Xử lý tất cả (N ảnh)"**:
   * Đóng gói toàn bộ `files` gốc vào `FormData` (lặp `formData.append("files", file)`), kèm `formData.append("params", JSON.stringify(params))`.
   * Gọi `POST /api/batch-process` -> nhận `job_id`.
2. Mở Modal hiển thị thanh tiến độ `processed / total` (%):
   * Dùng `setInterval` gọi `GET /api/batch-status/{job_id}` mỗi `800ms`.
   * Luôn dọn dẹp `clearInterval` khi `status === "done"`, `status === "failed"` hoặc khi component unmount.
3. Khi `status === "done"`:
   * Hiển thị nút **"Tải xuống enhanced_photos.zip"** gọi `GET /api/batch-download/{job_id}` (dạng `blob` rồi kích hoạt tải file tự động qua `URL.createObjectURL`).

---

## 3. YÊU CẦU XỬ LÝ LỖI & TRẠNG THÁI TRỐNG

* Nếu Backend chưa bật hoặc mất kết nối: Hiện thông báo Toast/Banner rõ ràng *"Không thể kết nối Backend API. Hãy kiểm tra server FastAPI đang chạy ở cổng 8000."*
* Không cho bấm nút "Xử lý tất cả" khi chưa có ảnh nào được tải lên.
