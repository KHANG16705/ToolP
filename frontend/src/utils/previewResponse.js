import { GRAY_LEVELS } from '../constants/defaultParams.js';

function isHistogram(value) {
  return (
    Array.isArray(value) &&
    value.length === GRAY_LEVELS &&
    value.every((bin) => Number.isInteger(bin) && bin >= 0)
  );
}

export function validatePreviewResponse(response) {
  const invalidFields = [];

  if (
    typeof response?.processed_image !== 'string' ||
    !response.processed_image.startsWith('data:image/jpeg;base64,')
  ) {
    invalidFields.push('processed_image (data:image/jpeg;base64)');
  }
  if (!isHistogram(response?.hist_before)) invalidFields.push('hist_before (256 số nguyên)');
  if (!isHistogram(response?.hist_after)) invalidFields.push('hist_after (256 số nguyên)');
  if (
    response?.applied_gamma !== null &&
    (typeof response?.applied_gamma !== 'number' || !Number.isFinite(response.applied_gamma))
  ) {
    invalidFields.push('applied_gamma (number hoặc null)');
  }
  if (
    typeof response?.processing_time_ms !== 'number' ||
    !Number.isFinite(response.processing_time_ms) ||
    response.processing_time_ms < 0
  ) {
    invalidFields.push('processing_time_ms (number không âm)');
  }

  if (invalidFields.length > 0) {
    const error = new Error(
      'Preview API thiếu hoặc trả sai trường theo contract README: ' +
        invalidFields.join(', ') +
        '. Hãy xác nhận response schema này với Tech Lead.'
    );
    error.name = 'PreviewContractError';
    throw error;
  }

  return response;
}
