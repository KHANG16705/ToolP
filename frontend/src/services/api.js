import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

/**
 * POST /api/preview
 * @param {Blob|File} imageBlob - Resized preview image (<= 800px)
 * @param {object} params - EnhanceParams object
 * @param {AbortSignal} [signal] - Optional AbortController signal
 */
export async function previewEnhance(imageBlob, params, signal) {
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
export async function getBatchStatus(jobId) {
  const response = await apiClient.get(`/api/batch-status/${encodeURIComponent(jobId)}`);
  return response.data;
}

/**
 * GET /api/batch-download/{job_id}
 * @param {string} jobId
 * @returns {Promise<Blob>} ZIP file blob
 */
export async function downloadBatchZip(jobId) {
  const response = await apiClient.get(`/api/batch-download/${encodeURIComponent(jobId)}`, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * GET /health
 */
export async function checkBackendHealth() {
  const response = await apiClient.get('/health', { timeout: 5000 });
  return response.data;
}
