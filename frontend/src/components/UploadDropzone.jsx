import React, { useRef, useState } from 'react';
import { FileImage, FilePlus2, Trash2, UploadCloud, X } from 'lucide-react';
import {
  ALLOWED_MIME_TYPES,
  MAX_BATCH_FILES,
  MAX_FILE_SIZE_BYTES,
} from '../constants/defaultParams.js';

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function UploadDropzone({
  files,
  selectedFile,
  error,
  onAddFiles,
  onRemoveFile,
  onSelectFile,
  onClear,
}) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function handleInputChange(event) {
    onAddFiles(Array.from(event.target.files || []));
    event.target.value = '';
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    onAddFiles(Array.from(event.dataTransfer.files || []));
  }

  function getFileKey(file) {
    return [file.name, file.size, file.lastModified].join('-');
  }

  return (
    <section className="rounded-2xl border border-white/[0.08] bg-slate-900/75 p-4 shadow-xl shadow-black/10">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">Ảnh đầu vào</h2>
          <p className="mt-0.5 text-[11px] text-slate-500">Chọn ảnh mẫu và lô cần xử lý</p>
        </div>
        {files.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-[10px] text-slate-400 transition hover:bg-white/[0.05] hover:text-white"
            aria-label="Xóa tất cả ảnh"
          >
            <Trash2 size={12} aria-hidden="true" />
            Xóa hết
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={
          'group flex min-h-[132px] w-full flex-col items-center justify-center rounded-xl border border-dashed px-4 py-5 text-center transition ' +
          (dragging
            ? 'border-indigo-300 bg-indigo-400/10'
            : 'border-slate-700 bg-slate-950/50 hover:border-indigo-400/60 hover:bg-indigo-400/[0.04]')
        }
        aria-label="Chọn hoặc thả ảnh vào đây"
      >
        <span className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-400/20 bg-indigo-400/10 text-indigo-300 transition group-hover:scale-105">
          {dragging ? <UploadCloud size={18} /> : <FilePlus2 size={18} />}
        </span>
        <span className="text-xs font-medium text-slate-200">
          {dragging ? 'Thả ảnh để thêm vào danh sách' : 'Kéo thả ảnh vào đây'}
        </span>
        <span className="mt-1 text-[10px] text-slate-500">hoặc nhấn để chọn từ thiết bị</span>
        <span className="mt-3 text-[9px] uppercase tracking-[0.13em] text-slate-600">
          JPEG · PNG · WebP · Tối đa 50 ảnh, 15 MB/ảnh
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_MIME_TYPES.join(',')}
        multiple
        className="sr-only"
        onChange={handleInputChange}
        aria-label="Chọn nhiều ảnh"
      />

      {error && (
        <p className="mt-3 rounded-lg border border-amber-400/15 bg-amber-400/[0.06] px-3 py-2 text-[10px] leading-4 text-amber-200" role="alert">
          {error}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between text-[10px] text-slate-500">
        <span>Danh sách ảnh</span>
        <span className="tabular-nums">{files.length}/{MAX_BATCH_FILES}</span>
      </div>

      {files.length === 0 ? (
        <div className="mt-2 flex items-center gap-2 rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-3 text-[11px] text-slate-500">
          <FileImage size={15} className="text-slate-600" aria-hidden="true" />
          Chưa có ảnh. Hãy chọn một hoặc nhiều ảnh để bắt đầu.
        </div>
      ) : (
        <ul className="mt-2 max-h-52 space-y-1.5 overflow-y-auto pr-1">
          {files.map((file) => {
            const selected = selectedFile && getFileKey(file) === getFileKey(selectedFile);
            return (
              <li key={getFileKey(file)}>
                <div
                  className={
                    'group flex items-center gap-2 rounded-xl border px-2.5 py-2 transition ' +
                    (selected
                      ? 'border-indigo-400/25 bg-indigo-400/[0.08]'
                      : 'border-transparent bg-slate-950/35 hover:border-white/[0.06]')
                  }
                >
                  <button
                    type="button"
                    onClick={() => onSelectFile(file)}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                    aria-pressed={Boolean(selected)}
                  >
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-400">
                      <FileImage size={14} aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[11px] font-medium text-slate-200">{file.name}</span>
                      <span className="mt-0.5 block text-[9px] text-slate-500">{formatSize(file.size)}</span>
                    </span>
                    {selected && <span className="mr-1 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-300" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemoveFile(file)}
                    className="rounded-md p-1 text-slate-600 opacity-100 transition hover:bg-white/[0.07] hover:text-rose-300 sm:opacity-0 sm:group-hover:opacity-100"
                    aria-label={'Xóa ' + file.name}
                  >
                    <X size={13} aria-hidden="true" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="mt-2 text-[9px] leading-4 text-slate-600">
        Ảnh gốc được giữ cho batch. Ảnh mẫu preview sẽ được thu nhỏ ở bước tích hợp API.
      </p>
    </section>
  );
}
