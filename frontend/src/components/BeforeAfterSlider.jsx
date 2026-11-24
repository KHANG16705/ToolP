import React, { useState } from 'react';
import { ArrowLeftRight, Image as ImageIcon, LoaderCircle, ScanLine } from 'lucide-react';

export default function BeforeAfterSlider({
  beforeUrl,
  afterUrl,
  previewStatus = 'idle',
  processingTimeMs,
}) {
  const [position, setPosition] = useState(50);
  const isProcessing = previewStatus === 'processing';
  const isDebouncing = previewStatus === 'debouncing';

  return (
    <section className="overflow-hidden rounded-2xl border border-white/[0.08] bg-slate-900/75 shadow-xl shadow-black/10">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] px-4 py-3.5 sm:px-5">
        <div className="flex items-center gap-2">
          <ScanLine size={15} className="text-sky-300" aria-hidden="true" />
          <h3 className="text-xs font-semibold text-slate-200">Before / After</h3>
          <span className="rounded-md border border-white/[0.07] px-1.5 py-0.5 text-[8px] uppercase tracking-[0.12em] text-slate-500">Preview</span>
        </div>
        <div className="flex items-center gap-3 text-[9px] text-slate-500">
          <span className="inline-flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-slate-400" />Ảnh gốc</span>
          <span className="inline-flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-sky-400" />Sau xử lý</span>
          {isProcessing && (
            <span className="inline-flex items-center gap-1.5 text-sky-300" role="status" aria-live="polite">
              <LoaderCircle size={12} className="animate-spin" aria-hidden="true" />
              Đang xử lý
            </span>
          )}
          {isDebouncing && (
            <span className="inline-flex items-center gap-1.5 text-slate-400" role="status" aria-live="polite">
              <i className="h-1.5 w-1.5 rounded-full bg-slate-400" />
              Chờ cập nhật
            </span>
          )}
        </div>
      </div>

      <div className="relative mx-3 my-3 aspect-[16/10] overflow-hidden rounded-xl border border-white/[0.06] bg-[#090e18] sm:mx-4 sm:my-4">
        <div className="absolute inset-0 image-grid" />
        {beforeUrl ? (
          <img src={beforeUrl} alt="Ảnh gốc được chọn" className="absolute inset-0 h-full w-full object-contain" />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.03] text-slate-600">
              <ImageIcon size={21} aria-hidden="true" />
            </span>
            <p className="text-xs font-medium text-slate-400">Chưa có ảnh mẫu</p>
            <p className="mt-1 max-w-xs text-[10px] leading-5 text-slate-600">
              Chọn ảnh ở khu vực bên trái để xem ảnh gốc tại đây.
            </p>
          </div>
        )}

        {afterUrl && (
          <>
            <img
              src={afterUrl}
              alt="Ảnh sau xử lý"
              className="absolute inset-0 h-full w-full object-contain"
              style={{ clipPath: 'inset(0 0 0 ' + position + '%)' }}
            />
            <div className="absolute bottom-0 top-0 w-px bg-white shadow-[0_0_12px_rgba(255,255,255,0.8)]" style={{ left: position + '%' }} />
          </>
        )}

        {beforeUrl && !afterUrl && (
          <div className="absolute inset-x-3 bottom-3 flex justify-center">
            <div className="flex max-w-full items-center gap-2 rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-[10px] text-slate-300 shadow-lg backdrop-blur">
              {isProcessing ? (
                <LoaderCircle size={13} className="shrink-0 animate-spin text-sky-300" aria-hidden="true" />
              ) : (
                <ArrowLeftRight size={13} className="shrink-0 text-indigo-300" aria-hidden="true" />
              )}
              {isProcessing
                ? 'Đang thu nhỏ ảnh mẫu và gửi Preview API'
                : isDebouncing
                  ? 'Đang chờ thao tác điều chỉnh ổn định'
                  : previewStatus === 'error'
                    ? 'Xem thông báo lỗi phía trên để biết cách xử lý'
                    : 'Đang chờ kết quả Preview API'}
            </div>
          </div>
        )}

        <span className="absolute left-3 top-3 rounded-md border border-white/10 bg-slate-950/70 px-2 py-1 text-[9px] font-medium text-slate-200 backdrop-blur">
          Before
        </span>
        <span className="absolute right-3 top-3 rounded-md border border-white/10 bg-slate-950/70 px-2 py-1 text-[9px] font-medium text-slate-200 backdrop-blur">
          After
        </span>
      </div>

      {afterUrl ? (
        <div className="flex items-center gap-3 px-5 pb-4">
          <span className="text-[9px] text-slate-500">Before</span>
          <input
            type="range"
            min="0"
            max="100"
            value={position}
            onChange={(event) => setPosition(Number(event.target.value))}
            aria-label="Điều chỉnh thanh so sánh ảnh trước và sau"
            className="h-1.5 flex-1 cursor-ew-resize accent-sky-400"
          />
          <span className="text-[9px] text-slate-500">After</span>
          <span className="min-w-14 text-right text-[9px] tabular-nums text-slate-500">
            {Number.isFinite(processingTimeMs) ? processingTimeMs + ' ms' : ''}
          </span>
        </div>
      ) : (
        <div className="flex items-center justify-between px-5 pb-4 text-[9px] text-slate-600">
          <span>Thanh so sánh sẽ bật khi có kết quả xử lý</span>
          <span className="tabular-nums">
            {Number.isFinite(processingTimeMs) ? processingTimeMs + ' ms' : '— ms'}
          </span>
        </div>
      )}
    </section>
  );
}
