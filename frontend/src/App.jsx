import React, { useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Image as ImageIcon,
  Layers3,
  Sparkles,
} from 'lucide-react';
import { checkBackendHealth, formatApiError, previewEnhance } from './services/api.js';
import {
  ALLOWED_MIME_TYPES,
  DEFAULT_ENHANCE_PARAMS,
  DEBOUNCE_MS,
  MAX_BATCH_FILES,
  MAX_FILE_SIZE_BYTES,
} from './constants/defaultParams.js';
import UploadDropzone from './components/UploadDropzone.jsx';
import ControlPanel from './components/ControlPanel.jsx';
import BeforeAfterSlider from './components/BeforeAfterSlider.jsx';
import HistogramChart from './components/HistogramChart.jsx';
import BatchProgressModal from './components/BatchProgressModal.jsx';
import { resizeImageForPreview } from './utils/imageResize.js';
import { validatePreviewResponse } from './utils/previewResponse.js';

function getFileKey(file) {
  return [file.name, file.size, file.lastModified].join('-');
}


function App() {
  const [files, setFiles] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [selectedPreviewUrl, setSelectedPreviewUrl] = useState('');
  const [previewResponse, setPreviewResponse] = useState(null);
  const [previewStatus, setPreviewStatus] = useState('idle');
  const [previewError, setPreviewError] = useState('');
  const [previewAttempt, setPreviewAttempt] = useState(0);
  const previewRequestSequence = useRef(0);
  const [params, setParams] = useState({ ...DEFAULT_ENHANCE_PARAMS });
  const [uploadError, setUploadError] = useState('');
  const [backendStatus, setBackendStatus] = useState('checking');
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  const selectedFile = files.find((file) => getFileKey(file) === selectedId) || null;

  useEffect(() => {
    if (!selectedFile) {
      setSelectedPreviewUrl('');
      return undefined;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setSelectedPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  useEffect(() => {
    const requestSequence = ++previewRequestSequence.current;
    const controller = new AbortController();

    if (!selectedFile) {
      setPreviewResponse(null);
      setPreviewError('');
      setPreviewStatus('idle');
      return () => controller.abort();
    }

    setPreviewResponse(null);
    setPreviewError('');
    setPreviewStatus('debouncing');

    const timeoutId = window.setTimeout(async () => {
      const isCurrentRequest = () =>
        !controller.signal.aborted && requestSequence === previewRequestSequence.current;

      setPreviewStatus('processing');

      let previewBlob;
      try {
        previewBlob = await resizeImageForPreview(selectedFile);
      } catch (error) {
        if (!isCurrentRequest()) return;
        setPreviewStatus('error');
        setPreviewError(
          'Không thể tạo ảnh preview từ file đã chọn: ' +
            (error?.message || 'định dạng ảnh không đọc được.')
        );
        return;
      }

      if (!isCurrentRequest()) return;

      try {
        const response = await previewEnhance(previewBlob, params, controller.signal);
        if (!isCurrentRequest()) return;

        const validatedResponse = validatePreviewResponse(response);
        setPreviewResponse(validatedResponse);
        setPreviewStatus('success');
      } catch (error) {
        if (!isCurrentRequest()) return;
        setPreviewStatus('error');
        setPreviewError(formatApiError(error, 'Preview API'));
      }
    }, DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [selectedFile, params, previewAttempt]);

  useEffect(() => {
    let active = true;
    checkBackendHealth()
      .then(() => {
        if (active) setBackendStatus('online');
      })
      .catch(() => {
        if (active) setBackendStatus('offline');
      });
    return () => {
      active = false;
    };
  }, []);

  function handleAddFiles(incomingFiles) {
    const nextFiles = [];
    const messages = [];
    const knownKeys = new Set(files.map(getFileKey));

    incomingFiles.forEach((file) => {
      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        messages.push(file.name + ': chỉ nhận JPEG, PNG hoặc WebP.');
      } else if (file.size > MAX_FILE_SIZE_BYTES) {
        messages.push(file.name + ': vượt giới hạn 15 MB.');
      } else if (files.length + nextFiles.length >= MAX_BATCH_FILES) {
        messages.push('Mỗi lượt chỉ hỗ trợ tối đa 50 ảnh.');
      } else if (!knownKeys.has(getFileKey(file))) {
        nextFiles.push(file);
        knownKeys.add(getFileKey(file));
      }
    });

    if (nextFiles.length > 0) {
      setFiles((currentFiles) => [...currentFiles, ...nextFiles]);
      setSelectedId((currentId) => currentId || getFileKey(nextFiles[0]));
    }
    setUploadError(messages.length > 0 ? messages.slice(0, 3).join(' ') : '');
  }

  function handleRemoveFile(fileToRemove) {
    const removedId = getFileKey(fileToRemove);
    const remainingFiles = files.filter((file) => getFileKey(file) !== removedId);
    setFiles(remainingFiles);
    if (selectedId === removedId) {
      setSelectedId(remainingFiles.length > 0 ? getFileKey(remainingFiles[0]) : '');
    }
  }

  function handleClearFiles() {
    setFiles([]);
    setSelectedId('');
    setUploadError('');
  }

  return (
    <div className="min-h-screen overflow-hidden bg-[#070b14] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(79,70,229,0.12),_transparent_45%)]" />
      <div className="relative">
        <header className="border-b border-white/[0.07] bg-slate-950/75 px-4 backdrop-blur-xl sm:px-6">
          <div className="mx-auto flex min-h-[76px] max-w-[1600px] items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-indigo-400/20 bg-indigo-500/10 text-indigo-300">
                <Sparkles size={19} aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h1 className="truncate text-sm font-semibold tracking-wide text-white sm:text-base">
                    Batch Photo Enhancer
                  </h1>
                  <span className="hidden rounded-full border border-white/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500 sm:inline-flex">
                    Studio
                  </span>
                </div>
                <p className="mt-0.5 truncate text-[11px] text-slate-500">
                  Spatial domain image processing
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="hidden items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.12em] text-slate-400 md:inline-flex">
                <Activity size={12} aria-hidden="true" />
                Local workspace
              </span>
              <BackendBadge status={backendStatus} />
            </div>
          </div>
        </header>

        <main className="mx-auto grid max-w-[1600px] grid-cols-1 gap-5 px-4 py-5 sm:px-6 lg:py-7 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="min-w-0 space-y-4">
            <UploadDropzone
              files={files}
              selectedFile={selectedFile}
              error={uploadError}
              onAddFiles={handleAddFiles}
              onRemoveFile={handleRemoveFile}
              onSelectFile={(file) => setSelectedId(getFileKey(file))}
              onClear={handleClearFiles}
            />
            <ControlPanel params={params} onChange={setParams} />
            <BatchActionCard
              fileCount={files.length}
              onOpen={() => setBatchModalOpen(true)}
            />
          </aside>

          <section className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3 px-1">
              <div>
                <p className="mb-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-indigo-300/80">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                  Live preview workspace
                </p>
                <h2 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
                  So sánh và tinh chỉnh
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  {selectedFile
                    ? 'Preview đang dùng thông số hiện hành; kết quả do backend trả về sẽ hiển thị bên dưới.'
                    : 'Tải ảnh lên để bắt đầu chuẩn bị bản xem trước.'}
                </p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2 text-[10px] font-medium text-slate-400">
                <ImageIcon size={13} aria-hidden="true" />
                {selectedFile ? selectedFile.name : 'Chưa chọn ảnh'}
              </div>
            </div>

            {previewError && (
              <div
                className="flex items-start justify-between gap-4 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] px-4 py-3"
                role="alert"
              >
                <div className="flex items-start gap-2.5">
                  <AlertCircle size={15} className="mt-0.5 shrink-0 text-rose-300" aria-hidden="true" />
                  <div>
                    <p className="text-[11px] font-semibold text-rose-200">Preview chưa hoàn tất</p>
                    <p className="mt-1 text-[10px] leading-5 text-rose-100/75">{previewError}</p>
                  </div>
                </div>
                {selectedFile && (
                  <button
                    type="button"
                    onClick={() => setPreviewAttempt((attempt) => attempt + 1)}
                    className="shrink-0 rounded-lg border border-rose-300/20 px-2.5 py-1.5 text-[10px] font-medium text-rose-100 transition hover:bg-rose-200/10"
                  >
                    Thử lại
                  </button>
                )}
              </div>
            )}

            <BeforeAfterSlider
              beforeUrl={selectedPreviewUrl}
              afterUrl={previewResponse?.processed_image || null}
              previewStatus={previewStatus}
              processingTimeMs={previewResponse?.processing_time_ms}
            />
            <HistogramChart
              histBefore={previewResponse?.hist_before || null}
              histAfter={previewResponse?.hist_after || null}
            />

            <div className="grid gap-3 sm:grid-cols-3">
              <InfoTile icon={<Layers3 size={15} />} label="Pipeline" value="5 bước xử lý" />
              <InfoTile icon={<ImageIcon size={15} />} label="Ảnh mẫu" value="Tối đa 800 px" />
              <InfoTile icon={<Cpu size={15} />} label="Batch" value="Tối đa 50 ảnh" />
            </div>
          </section>
        </main>

        <footer className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 pb-6 text-[10px] text-slate-600 sm:px-6">
          <span>Batch Photo Enhancer · Digital Image Processing</span>
          <span className="hidden sm:inline">Ảnh được xử lý trong phiên làm việc hiện tại</span>
        </footer>
      </div>

      <BatchProgressModal
        open={batchModalOpen}
        onClose={() => setBatchModalOpen(false)}
        files={files}
        params={params}
      />
    </div>
  );
}

function BackendBadge({ status }) {
  const online = status === 'online';
  const checking = status === 'checking';
  return (
    <span
      className={
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[10px] font-medium ' +
        (online
          ? 'border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-300'
          : checking
            ? 'border-slate-700 bg-slate-800/70 text-slate-400'
            : 'border-amber-400/20 bg-amber-400/[0.07] text-amber-200')
      }
      role="status"
      aria-live="polite"
    >
      {online ? (
        <CheckCircle2 size={13} aria-hidden="true" />
      ) : (
        <AlertCircle size={13} aria-hidden="true" />
      )}
      {online ? 'API sẵn sàng' : checking ? 'Đang kiểm tra' : 'API chưa kết nối'}
    </span>
  );
}

function BatchActionCard({ fileCount, onOpen }) {
  return (
    <section className="rounded-2xl border border-indigo-400/15 bg-gradient-to-br from-indigo-500/[0.09] to-slate-900/80 p-4 shadow-lg shadow-black/10">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-indigo-200/80">
            Batch processing
          </p>
          <h3 className="mt-1 text-sm font-semibold text-white">Xử lý hàng loạt</h3>
        </div>
        <span className="rounded-lg border border-white/10 bg-slate-950/40 px-2 py-1 text-[10px] text-slate-400">
          {fileCount}/50 ảnh
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-400">
        Áp dụng bộ thông số cho ảnh gốc và tải kết quả ZIP.
      </p>
      <button
        type="button"
        onClick={onOpen}
        disabled={fileCount === 0}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
      >
        <Layers3 size={15} aria-hidden="true" />
        Chuẩn bị batch
      </button>
      <p className="mt-2 text-center text-[10px] text-slate-500">
        {fileCount > 0
          ? 'Gửi ảnh gốc lên backend, theo dõi tiến độ và tải kết quả ZIP khi hoàn tất.'
          : 'Chọn ít nhất một ảnh trước khi bắt đầu batch.'}
      </p>
    </section>
  );
}

function InfoTile({ icon, label, value }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/[0.07] bg-slate-900/55 px-3.5 py-3">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.04] text-slate-400">
        {icon}
      </span>
      <div>
        <p className="text-[9px] font-medium uppercase tracking-[0.16em] text-slate-500">{label}</p>
        <p className="mt-0.5 text-xs font-medium text-slate-300">{value}</p>
      </div>
    </div>
  );
}

export default App;
