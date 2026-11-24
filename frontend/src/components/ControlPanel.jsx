import React from 'react';
import { RotateCcw, SlidersHorizontal } from 'lucide-react';
import { DEFAULT_ENHANCE_PARAMS } from '../constants/defaultParams.js';

const RANGE_LIMITS = {
  gamma: { min: 0.2, max: 4, step: 0.05 },
  log_c: { min: 0.5, max: 2, step: 0.05 },
  clahe_clip_limit: { min: 1, max: 8, step: 0.5 },
  sharpen_alpha: { min: 0, max: 1, step: 0.05 },
};

function SelectField({ label, value, options, onChange }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[10px] font-medium text-slate-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-white/[0.08] bg-slate-950 px-2.5 py-2 text-[11px] text-slate-200 outline-none transition focus:border-indigo-400/50"
      >
        {options.map((option) => (
          <option value={option.value} key={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

function RangeField({ label, value, min, max, step, onChange, disabled = false, suffix = '' }) {
  const shownValue = Number.isInteger(step) ? value : Number(value).toFixed(step < 1 ? 2 : 1);
  return (
    <label className="block">
      <span className="mb-1 flex items-center justify-between gap-3 text-[10px] text-slate-400">
        <span>{label}</span>
        <span className="tabular-nums text-slate-300">{shownValue}{suffix}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-1.5 w-full cursor-pointer accent-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
      />
    </label>
  );
}

function ToggleField({ label, checked, onChange, disabled = false }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-white/[0.06] bg-white/[0.025] px-3 py-2.5">
      <span className="text-[10px] font-medium text-slate-300">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-indigo-400 disabled:opacity-40"
      />
    </label>
  );
}

function Section({ number, title, children }) {
  return (
    <section className="border-t border-white/[0.06] pt-4">
      <h3 className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-300">
        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-white/[0.05] text-[9px] text-indigo-300">{number}</span>
        {title}
      </h3>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

export default function ControlPanel({ params, onChange }) {
  function setParam(name, value) {
    onChange((current) => ({ ...current, [name]: value }));
  }

  function resetParams() {
    onChange({ ...DEFAULT_ENHANCE_PARAMS });
  }

  return (
    <section className="rounded-2xl border border-white/[0.08] bg-slate-900/75 p-4 shadow-xl shadow-black/10">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={14} className="text-indigo-300" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-white">Thông số xử lý</h2>
          </div>
          <p className="mt-1 text-[10px] text-slate-500">Điều chỉnh cục bộ, chưa gửi lên backend</p>
        </div>
        <button
          type="button"
          onClick={resetParams}
          className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-[10px] text-slate-400 transition hover:bg-white/[0.05] hover:text-white"
        >
          <RotateCcw size={11} aria-hidden="true" />
          Mặc định
        </button>
      </div>

      <Section number="01" title="Khử nhiễu">
        <SelectField
          label="Bộ lọc"
          value={params.denoise_mode}
          onChange={(value) => setParam('denoise_mode', value)}
          options={[
            { value: 'none', label: 'Không khử nhiễu' },
            { value: 'median', label: 'Lọc trung vị · Median' },
            { value: 'average', label: 'Lọc trung bình · Average' },
            { value: 'morph_open_close', label: 'Hình thái học · Opening + Closing' },
          ]}
        />
        {params.denoise_mode !== 'none' && (
          <SelectField
            label="Kích thước kernel"
            value={String(params.kernel_size)}
            onChange={(value) => setParam('kernel_size', Number(value))}
            options={[
              { value: '3', label: '3 × 3' },
              { value: '5', label: '5 × 5' },
              { value: '7', label: '7 × 7' },
            ]}
          />
        )}
      </Section>

      <Section number="02" title="Độ sáng & điểm ảnh">
        <SelectField
          label="Phép biến đổi"
          value={params.brightness_mode}
          onChange={(value) => setParam('brightness_mode', value)}
          options={[
            { value: 'none', label: 'Không biến đổi' },
            { value: 'gamma', label: 'Hiệu chỉnh Gamma' },
            { value: 'log', label: 'Biến đổi Logarit' },
            { value: 'contrast_stretch', label: 'Kéo dãn tương phản' },
          ]}
        />
        {params.brightness_mode === 'gamma' && (
          <>
            <ToggleField label="Tự động tính Gamma" checked={params.auto_gamma} onChange={(value) => setParam('auto_gamma', value)} />
            <RangeField label="Gamma" value={params.gamma} {...RANGE_LIMITS.gamma} disabled={params.auto_gamma} onChange={(value) => setParam('gamma', value)} />
          </>
        )}
        {params.brightness_mode === 'log' && (
          <RangeField label="Hệ số Log · c" value={params.log_c} {...RANGE_LIMITS.log_c} onChange={(value) => setParam('log_c', value)} />
        )}
        {params.brightness_mode === 'contrast_stretch' && (
          <div className="grid grid-cols-2 gap-3">
            <RangeField label="Điểm r1" value={params.stretch_r1} min={0} max={params.stretch_r2 - 1} step={1} onChange={(value) => setParam('stretch_r1', value)} />
            <RangeField label="Điểm s1" value={params.stretch_s1} min={0} max={255} step={1} onChange={(value) => setParam('stretch_s1', value)} />
            <RangeField label="Điểm r2" value={params.stretch_r2} min={params.stretch_r1 + 1} max={255} step={1} onChange={(value) => setParam('stretch_r2', value)} />
            <RangeField label="Điểm s2" value={params.stretch_s2} min={0} max={255} step={1} onChange={(value) => setParam('stretch_s2', value)} />
          </div>
        )}
        <ToggleField label="Ảnh âm bản · Negative" checked={params.negative} onChange={(value) => setParam('negative', value)} />
      </Section>

      <Section number="03" title="Cân bằng Histogram">
        <SelectField
          label="Chế độ tương phản"
          value={params.contrast_mode}
          onChange={(value) => setParam('contrast_mode', value)}
          options={[
            { value: 'none', label: 'Không cân bằng' },
            { value: 'hist_eq', label: 'Histogram toàn cục' },
            { value: 'clahe', label: 'CLAHE cục bộ' },
          ]}
        />
        {params.contrast_mode === 'clahe' && (
          <RangeField label="CLAHE clip limit" value={params.clahe_clip_limit} {...RANGE_LIMITS.clahe_clip_limit} onChange={(value) => setParam('clahe_clip_limit', value)} />
        )}
      </Section>

      <Section number="04" title="Làm sắc nét">
        <SelectField
          label="Toán tử Laplacian"
          value={params.sharpen_mode}
          onChange={(value) => setParam('sharpen_mode', value)}
          options={[
            { value: 'none', label: 'Không làm nét' },
            { value: 'laplacian_4', label: 'Laplacian 4-láng giềng' },
            { value: 'laplacian_8', label: 'Laplacian 8-láng giềng' },
          ]}
        />
        {params.sharpen_mode !== 'none' && (
          <RangeField label="Cường độ" value={params.sharpen_alpha} {...RANGE_LIMITS.sharpen_alpha} onChange={(value) => setParam('sharpen_alpha', value)} />
        )}
      </Section>
    </section>
  );
}
