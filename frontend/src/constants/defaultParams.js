/**
 * Locked frontend constants & EnhanceParams defaults matching README.md API Contract.
 */

export const PREVIEW_MAX_WIDTH = 800;
export const PREVIEW_JPEG_QUALITY = 0.9;
export const DEBOUNCE_MS = 280;
export const POLL_INTERVAL_MS = 800;
export const GRAY_LEVELS = 256;

export const MAX_BATCH_FILES = 50;
export const MAX_FILE_SIZE_MB = 15;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export const DEFAULT_ENHANCE_PARAMS = {
  denoise_mode: 'none',
  kernel_size: 3,
  brightness_mode: 'gamma',
  gamma: 1.0,
  auto_gamma: false,
  log_c: 1.0,
  negative: false,
  stretch_r1: 30,
  stretch_s1: 10,
  stretch_r2: 225,
  stretch_s2: 245,
  contrast_mode: 'none',
  clahe_clip_limit: 2.0,
  sharpen_mode: 'none',
  sharpen_alpha: 0.5,
};
