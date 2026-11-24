import React from 'react';
import { Activity, BarChart3 } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { GRAY_LEVELS } from '../constants/defaultParams.js';

function buildChartData(histBefore, histAfter) {
  return Array.from({ length: GRAY_LEVELS }, (_, index) => ({
    level: index,
    before: histBefore[index],
    after: histAfter[index],
  }));
}

export default function HistogramChart({ histBefore, histAfter }) {
  const hasData =
    Array.isArray(histBefore) &&
    Array.isArray(histAfter) &&
    histBefore.length === GRAY_LEVELS &&
    histAfter.length === GRAY_LEVELS;

  return (
    <section className="rounded-2xl border border-white/[0.08] bg-slate-900/75 p-4 shadow-xl shadow-black/10 sm:p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BarChart3 size={15} className="text-indigo-300" aria-hidden="true" />
          <h3 className="text-xs font-semibold text-slate-200">Phân bố mức xám</h3>
          <span className="text-[9px] text-slate-600">256 bins · kênh V</span>
        </div>
        <div className="flex items-center gap-3 text-[9px] text-slate-500">
          <span className="inline-flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-slate-400" />Trước</span>
          <span className="inline-flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-indigo-400" />Sau</span>
        </div>
      </div>

      {hasData ? (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={buildChartData(histBefore, histAfter)} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <defs>
                <linearGradient id="beforeFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#94a3b8" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="#94a3b8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="afterFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#818cf8" stopOpacity={0.34} />
                  <stop offset="100%" stopColor="#818cf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148,163,184,0.1)" vertical={false} />
              <XAxis dataKey="level" tick={{ fill: '#64748b', fontSize: 9 }} tickLine={false} axisLine={false} ticks={[0, 64, 128, 192, 255]} />
              <YAxis tick={{ fill: '#64748b', fontSize: 9 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,.1)', borderRadius: 10, fontSize: 10 }}
                labelStyle={{ color: '#cbd5e1' }}
              />
              <Area type="monotone" dataKey="before" stroke="#94a3b8" strokeWidth={1.5} fill="url(#beforeFill)" />
              <Area type="monotone" dataKey="after" stroke="#818cf8" strokeWidth={1.7} fill="url(#afterFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex h-48 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.07] bg-slate-950/35 px-6 text-center">
          <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-white/[0.035] text-slate-600">
            <Activity size={17} aria-hidden="true" />
          </span>
          <p className="text-[11px] font-medium text-slate-400">Chưa có dữ liệu Histogram</p>
          <p className="mt-1 max-w-xs text-[9px] leading-4 text-slate-600">
            Biểu đồ 256 mức xám sẽ được vẽ từ phản hồi Preview API. Không dùng dữ liệu mẫu.
          </p>
        </div>
      )}
      <div className="mt-2 flex justify-between px-1 text-[8px] uppercase tracking-[0.12em] text-slate-600">
        <span>Tối · 0</span>
        <span>Cường độ sáng</span>
        <span>255 · Sáng</span>
      </div>
    </section>
  );
}
