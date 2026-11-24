import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowDownToLine,
  CheckCircle2,
  Clock3,
  Cpu,
  LoaderCircle,
  RefreshCw,
  X,
} from 'lucide-react';
import {
  downloadBatchZip,
  formatApiError,
  getBatchStatus,
  startBatchProcess,
} from '../services/api.js';
import { POLL_INTERVAL_MS } from '../constants/defaultParams.js';

const ALLOWED_JOB_STATUSES = ['queued', 'processing', 'done', 'failed'];
const ZIP_FILENAME = 'enhanced_photos.zip';

function createContractError(message) {
  const error = new Error(message);
  error.name = 'BatchContractError';
  return error;
}

function validateCreateResponse(response, expectedFileCount) {
  const problems = [];
  if (typeof response?.job_id !== 'string' || response.job_id.trim() === '') {
    problems.push('job_id (chuỗi không rỗng)');
  }
  if (!Number.isInteger(response?.total) || response.total <= 0) {
    problems.push('total (số nguyên dương)');
  } else if (response.total !== expectedFileCount) {
    problems.push('total phải khớp số ảnh đã gửi');
  }
  if (!ALLOWED_JOB_STATUSES.includes(response?.status)) {
    problems.push('status (queued, processing, done hoặc failed)');
  }

  if (problems.length > 0) {
    throw createContractError(
      'Response batch-process thiếu hoặc sai: ' +
        problems.join(', ') +
        '. Hãy xác nhận contract với Tech Lead.'
    );
  }
  return response;
}

function validateStatusResponse(response, expectedJobId, expectedTotal) {
  const problems = [];
  if (typeof response?.job_id !== 'string' || response.job_id !== expectedJobId) {
    problems.push('job_id phải khớp job đã tạo');
  }
  if (!Number.isInteger(response?.processed) || response.processed < 0) {
    problems.push('processed (số nguyên không âm)');
  }
  if (!Number.isInteger(response?.total) || response.total <= 0) {
    problems.push('total (số nguyên dương)');
  } else if (response.total !== expectedTotal) {
    problems.push('total phải khớp batch-process');
  }
  if (
    Number.isInteger(response?.processed) &&
    Number.isInteger(response?.total) &&
    response.processed > response.total
  ) {
    problems.push('processed không được lớn hơn total');
  }
  if (!ALLOWED_JOB_STATUSES.includes(response?.status)) {
    problems.push('status (queued, processing, done hoặc failed)');
  }
  if (!Array.isArray(response?.failed_files) || !response.failed_files.every((file) => typeof file === 'string')) {
    problems.push('failed_files (mảng tên file)');
  }
  if (response?.error !== null && typeof response?.error !== 'string') {
    problems.push('error (chuỗi hoặc null)');
  }

  if (problems.length > 0) {
    throw createContractError(
      'Response batch-status thiếu hoặc sai: ' +
        problems.join(', ') +
        '. Hãy xác nhận contract với Tech Lead.'
    );
  }
  return response;
}

function formatBlobDownloadError(error) {
  const responseData = error?.response?.data;
  if (!(responseData instanceof Blob)) {
    return formatApiError(error, 'Batch download API');
  }

  return responseData.text().then((body) => {
    let detail = '';
    try {
      detail = JSON.parse(body)?.detail || '';
    } catch {
      detail = body;
    }
    return (
      'Batch download API trả lỗi HTTP ' +
      error.response.status +
      (detail ? ': ' + detail : '.')
    );
  });
}

function saveZipFile(blob) {
  if (!(blob instanceof Blob) || blob.size === 0) {
    throw new Error('Backend trả về file ZIP rỗng hoặc không hợp lệ.');
  }

  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = ZIP_FILENAME;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export default function BatchProgressModal({ open, onClose, files, params }) {
  const [phase, setPhase] = useState('ready');
  const [job, setJob] = useState(null);
  const [statusRecord, setStatusRecord] = useState(null);
  const [error, setError] = useState('');
  const [failureAction, setFailureAction] = useState('new-job');
  const [downloadError, setDownloadError] = useState('');
  const [downloadStatus, setDownloadStatus] = useState('idle');
  const startLock = useRef(false);

  const isBusy = phase === 'uploading' || phase === 'processing';
  const fileCount = Array.isArray(files) ? files.length : 0;

  useEffect(() => {
    if (!open || phase !== 'processing' || !job?.job_id) return undefined;

    let active = true;
    let timeoutId;
    const controller = new AbortController();

    async function pollStatus() {
      try {
        const response = await getBatchStatus(job.job_id, controller.signal);
        if (!active || controller.signal.aborted) return;

        const validatedStatus = validateStatusResponse(response, job.job_id, job.total);
        setStatusRecord(validatedStatus);
        setJob((currentJob) => ({ ...currentJob, status: validatedStatus.status }));

        if (validatedStatus.status === 'done') {
          startLock.current = false;
          setPhase('done');
        } else if (validatedStatus.status === 'failed') {
          startLock.current = false;
          setFailureAction('new-job');
          setError(validatedStatus.error || 'Backend báo job xử lý thất bại.');
          setPhase('failed');
        } else {
          timeoutId = window.setTimeout(pollStatus, POLL_INTERVAL_MS);
        }
      } catch (pollError) {
        if (!active || controller.signal.aborted || pollError?.code === 'ERR_CANCELED') return;
        startLock.current = false;
        setFailureAction(pollError?.response?.status === 404 ? 'new-job' : 'resume-status');
        setError(formatApiError(pollError, 'Batch status API'));
        setPhase('failed');
      }
    }

    timeoutId = window.setTimeout(pollStatus, POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [open, phase, job?.job_id, job?.total]);

  useEffect(() => {
    if (!open || isBusy) return undefined;
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, isBusy, onClose]);

  async function handleStartBatch() {
    if (startLock.current || isBusy) return;
    if (fileCount === 0) {
      setError('Chọn ít nhất một ảnh trước khi bắt đầu xử lý hàng loạt.');
      setPhase('failed');
      return;
    }

    startLock.current = true;
    setPhase('uploading');
    setError('');
    setDownloadError('');
    setDownloadStatus('idle');
    setJob(null);
    setStatusRecord(null);

    try {
      const response = await startBatchProcess(files, params);
      const createdJob = validateCreateResponse(response, fileCount);
      setFailureAction('new-job');
      setJob(createdJob);
      setPhase('processing');
    } catch (startError) {
      startLock.current = false;
      setFailureAction('new-job');
      setError(formatApiError(startError, 'Batch process API'));
      setPhase('failed');
    }
  }

  async function handleDownload() {
    if (!job?.job_id || downloadStatus === 'downloading') return;

    setDownloadStatus('downloading');
    setDownloadError('');
    try {
      const zipBlob = await downloadBatchZip(job.job_id);
      saveZipFile(zipBlob);
      setDownloadStatus('downloaded');
    } catch (downloadFailure) {
      setDownloadStatus('failed');
      setDownloadError(await formatBlobDownloadError(downloadFailure));
    }
  }

  function handleRetryNewJob() {
    if (isBusy) return;
    startLock.current = false;
    handleStartBatch();
  }

  function handleRetryStatus() {
    if (isBusy || !job?.job_id) return;
    startLock.current = true;
    setError('');
    setFailureAction('new-job');
    setPhase('processing');
  }

  function handleRetry() {
    if (failureAction === 'resume-status' && job?.job_id) {
      handleRetryStatus();
    } else {
      handleRetryNewJob();
    }
  }

  function handleClose() {
    if (isBusy) return;
    onClose();
  }

  if (!open) return null;

  const progressAvailable = statusRecord && statusRecord.total > 0;
  const progressPercent = progressAvailable
    ? Math.round((statusRecord.processed / statusRecord.total) * 100)
    : null;
  const activeStatus = statusRecord?.status || job?.status;
  const statusLabel =
    phase === 'uploading'
      ? 'Đang gửi ảnh'
      : phase === 'processing'
        ? activeStatus === 'queued'
          ? 'Đang chờ xử lý'
          : 'Đang xử lý'
        : phase === 'done'
          ? 'Hoàn tất'
          : phase === 'failed'
            ? 'Thất bại'
            : 'Sẵn sàng';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) handleClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="batch-modal-title"
        className="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-5 shadow-2xl shadow-black/50"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-400/15 bg-indigo-400/10 text-indigo-300">
              <Cpu size={18} aria-hidden="true" />
            </span>
            <div>
              <h2 id="batch-modal-title" className="text-sm font-semibold text-white">Xử lý hàng loạt</h2>
              <p className="mt-1 text-[10px] text-slate-500">
                {fileCount} ảnh gốc · thông số hiện tại
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={isBusy}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Đóng"
            title={isBusy ? 'Không thể đóng khi job đang chạy' : 'Đóng'}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="mt-5 rounded-xl border border-white/[0.06] bg-slate-950/45 p-4">
          <div className="flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-2 text-[10px] text-slate-300">
              {phase === 'uploading' || phase === 'processing' ? (
                <LoaderCircle size={13} className="animate-spin text-indigo-300" aria-hidden="true" />
              ) : phase === 'done' ? (
                <CheckCircle2 size={13} className="text-emerald-300" aria-hidden="true" />
              ) : phase === 'failed' ? (
                <AlertCircle size={13} className="text-rose-300" aria-hidden="true" />
              ) : (
                <Clock3 size={13} className="text-slate-500" aria-hidden="true" />
              )}
              Trạng thái
            </span>
            <span className="rounded-md bg-slate-800 px-2 py-1 text-[10px] text-slate-300">{statusLabel}</span>
          </div>

          {progressPercent !== null ? (
            <>
              <div
                className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800"
                role="progressbar"
                aria-label="Tiến độ xử lý batch"
                aria-valuemin="0"
                aria-valuemax={statusRecord.total}
                aria-valuenow={statusRecord.processed}
              >
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-sky-400 transition-[width] duration-300"
                  style={{ width: progressPercent + '%' }}
                />
              </div>
              <div className="mt-2 flex justify-between text-[9px] text-slate-500">
                <span>{statusRecord.processed}/{statusRecord.total} ảnh</span>
                <span className="tabular-nums">{progressPercent}%</span>
              </div>
            </>
          ) : phase === 'uploading' ? (
            <div className="mt-3 flex items-center gap-2 text-[9px] text-slate-500" role="status" aria-live="polite">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-300" />
              Đang tải ảnh gốc và khởi tạo job…
            </div>
          ) : phase === 'processing' ? (
            <div className="mt-3 flex items-center gap-2 text-[9px] text-slate-500" role="status" aria-live="polite">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-300" />
              Đang chờ dữ liệu tiến độ từ backend…
            </div>
          ) : (
            <p className="mt-3 text-[9px] text-slate-500">
              Tiến độ chỉ hiển thị sau khi backend trả về processed và total.
            </p>
          )}
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-rose-400/15 bg-rose-400/[0.06] px-3.5 py-3" role="alert">
            <AlertCircle size={14} className="mt-0.5 shrink-0 text-rose-300" aria-hidden="true" />
            <p className="text-[10px] leading-5 text-rose-100/80">{error}</p>
          </div>
        )}

        {statusRecord?.error && phase !== 'failed' && (
          <p className="mt-3 text-[10px] text-amber-200" role="status">{statusRecord.error}</p>
        )}

        {Array.isArray(statusRecord?.failed_files) && statusRecord.failed_files.length > 0 && (
          <div className="mt-3 rounded-xl border border-amber-400/15 bg-amber-400/[0.05] px-3.5 py-3">
            <p className="text-[10px] font-medium text-amber-200">
              {statusRecord.failed_files.length} ảnh không xử lý được; ZIP có thể chứa các ảnh thành công.
            </p>
            <ul className="mt-2 max-h-20 space-y-1 overflow-y-auto text-[9px] text-amber-100/70">
              {statusRecord.failed_files.map((filename, index) => (
                <li key={filename + '-' + index} className="truncate">{filename}</li>
              ))}
            </ul>
          </div>
        )}

        {downloadError && (
          <div className="mt-3 rounded-xl border border-rose-400/15 bg-rose-400/[0.06] px-3.5 py-3 text-[10px] leading-5 text-rose-100/80" role="alert">
            {downloadError}
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] pt-4">
          <p className="max-w-[230px] text-[9px] leading-4 text-slate-500">
            {isBusy
              ? 'Modal sẽ mở đến khi job hoàn tất để tiếp tục theo dõi tiến độ.'
              : 'Ảnh gốc và bộ thông số sẽ được gửi theo API contract.'}
          </p>
          <div className="flex flex-wrap justify-end gap-2">
            {phase === 'ready' && (
              <button
                type="button"
                onClick={handleStartBatch}
                disabled={fileCount === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
              >
                <Cpu size={13} aria-hidden="true" />
                Bắt đầu xử lý
              </button>
            )}
            {phase === 'failed' && (
              <button
                type="button"
                onClick={handleRetry}
                disabled={fileCount === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
              >
                <RefreshCw size={13} aria-hidden="true" />
                {failureAction === 'resume-status' && job?.job_id
                  ? 'Thử kiểm tra trạng thái lại'
                  : 'Tạo job mới để thử lại'}
              </button>
            )}
            {phase === 'done' && (
              <>
                <button
                  type="button"
                  onClick={handleStartBatch}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-[10px] font-medium text-slate-300 hover:bg-white/[0.08]"
                >
                  <RefreshCw size={12} aria-hidden="true" />
                  Tạo job mới
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  disabled={downloadStatus === 'downloading'}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-emerald-400 disabled:cursor-wait disabled:opacity-60"
                >
                  {downloadStatus === 'downloading' ? (
                    <LoaderCircle size={13} className="animate-spin" aria-hidden="true" />
                  ) : (
                    <ArrowDownToLine size={13} aria-hidden="true" />
                  )}
                  {downloadStatus === 'downloading'
                    ? 'Đang tải ZIP'
                    : downloadStatus === 'downloaded'
                      ? 'Tải ZIP lại'
                      : downloadStatus === 'failed'
                        ? 'Thử tải ZIP lại'
                        : 'Tải enhanced_photos.zip'}
                </button>
              </>
            )}
            {!isBusy && (
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-[10px] font-medium text-slate-300 hover:bg-white/[0.08]"
              >
                Đóng
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
