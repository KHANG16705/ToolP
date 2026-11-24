import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL?.trim();
const API_TIMEOUT_MS = 60000;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
});

function ensureApiBaseUrl() {
  if (API_BASE_URL) return;
  const error = new Error('Thiếu VITE_API_URL. Hãy cấu hình địa chỉ backend trong frontend/.env.');
  error.code = 'MISSING_API_URL';
  throw error;
}

function formatErrorDetail(detail) {
  if (typeof detail === 'string') return detail;
  if (!Array.isArray(detail)) {
    return detail && typeof detail === 'object' ? JSON.stringify(detail) : '';
  }

  return detail
    .map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.slice(-1).join('.') : '';
      const message = item.msg || '';
      return [field, message].filter(Boolean).join(': ');
    })
    .filter(Boolean)
    .join('; ');
}

export function formatApiError(error, operation = 'API') {
  if (error?.code === 'MISSING_API_URL') return error.message;
  if (error?.name?.endsWith('ContractError')) return error.message;

  if (error?.response) {
    const detail = formatErrorDetail(error.response.data?.detail);
    const suffix = detail ? ': ' + detail : '.';
    return operation + ' trả lỗi HTTP ' + error.response.status + suffix;
  }

  if (error?.request) {
    return (
      'Không thể kết nối backend tại VITE_API_URL (' +
      (API_BASE_URL || 'chưa cấu hình') +
      '). Hãy kiểm tra server FastAPI và cấu hình frontend/.env.'
    );
  }

  return error?.message || operation + ' gặp lỗi không xác định.';
}

/**
 * POST /api/preview
 * @param {Blob|File} imageBlob - Resized preview image (<= 800px)
 * @param {object} params - EnhanceParams object
 * @param {AbortSignal} [signal] - Optional AbortController signal
 */
export async function previewEnhance(imageBlob, params, signal) {
  ensureApiBaseUrl();
  const formData = new FormData();
  formData.append('file', imageBlob, 'preview.jpg');
  formData.append('params', JSON.stringify(params));

  const response = await apiClient.post('/api/preview', formData, { signal });
  return response.data;
}

/**
 * POST /api/batch-process
 * @param {File[]} files - Original full-resolution image files (1..50)
 * @param {object} params - EnhanceParams object
 */
export async function startBatchProcess(files, params) {
  ensureApiBaseUrl();
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });
  formData.append('params', JSON.stringify(params));

  const response = await apiClient.post('/api/batch-process', formData);
  return response.data;
}

/**
 * GET /api/batch-status/{job_id}
 * @param {string} jobId
 */
export async function getBatchStatus(jobId, signal) {
  ensureApiBaseUrl();
  const response = await apiClient.get(
    '/api/batch-status/' + encodeURIComponent(jobId),
    { signal }
  );
  return response.data;
}

/**
 * GET /api/batch-download/{job_id}
 * @param {string} jobId
 * @returns {Promise<Blob>} ZIP file blob
 */
export async function downloadBatchZip(jobId) {
  ensureApiBaseUrl();
  const response = await apiClient.get('/api/batch-download/' + encodeURIComponent(jobId), {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * GET /health
 */
export async function checkBackendHealth() {
  ensureApiBaseUrl();
  const response = await apiClient.get('/health', { timeout: 5000 });
  return response.data;
}
