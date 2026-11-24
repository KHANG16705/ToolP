import { PREVIEW_JPEG_QUALITY, PREVIEW_MAX_WIDTH } from '../constants/defaultParams.js';

/**
 * Resize an image File on an HTML5 canvas so its longest side is <= PREVIEW_MAX_WIDTH.
 * Returns a JPEG Blob ready for fast POST /api/preview uploads.
 * @param {File} file
 * @param {number} [maxDimension=PREVIEW_MAX_WIDTH]
 * @returns {Promise<Blob>}
 */
export async function resizeImageForPreview(file, maxDimension = PREVIEW_MAX_WIDTH) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`Unable to load image "${file.name}"`));
      image.src = objectUrl;
    });

    const longestSide = Math.max(img.naturalWidth, img.naturalHeight);
    const scale = longestSide > maxDimension ? maxDimension / longestSide : 1;
    const targetWidth = Math.max(1, Math.round(img.naturalWidth * scale));
    const targetHeight = Math.max(1, Math.round(img.naturalHeight * scale));

    const canvas = document.createElement('canvas');
    canvas.width = targetWidth;
    canvas.height = targetHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Canvas 2D context is unavailable');
    }

    ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

    return await new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to export resized JPEG blob'));
          }
        },
        'image/jpeg',
        PREVIEW_JPEG_QUALITY
      );
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
