import React, { useEffect, useState } from 'react';
import { Sliders, Layers, Activity, CheckCircle2, AlertTriangle } from 'lucide-react';
import { checkBackendHealth } from './services/api.js';

/**
 * Starter Dark Mode Studio shell prepared by Lead for TV1 (feat/frontend-ui).
 * Locked contract modules ready to import:
 * - src/constants/defaultParams.js
 * - src/services/api.js
 * - src/utils/imageResize.js
 */
export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    let active = true;
    checkBackendHealth()
      .then(() => {
        if (active) setBackendStatus('online');
      })
      .catch(() => {
        if (active) setBackendStatus('offline');
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="h-14 border-b border-white/10 bg-slate-900/80 backdrop-blur px-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/40 text-indigo-400 flex items-center justify-center">
            <Sliders className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-slate-100">
              Batch Photo Enhancer
            </h1>
            <p className="text-[11px] text-slate-400">
              Spatial Domain Digital Image Processing Studio
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium">
          {backendStatus === 'online' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
              Backend API Ready (:8000)
            </span>
          ) : backendStatus === 'offline' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
              Backend Offline (:8000)
            </span>
          ) : (
            <span className="text-slate-400">Checking Backend...</span>
          )}
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-[350px_1fr] gap-4 p-4">
        <aside className="rounded-xl bg-slate-900 border border-white/10 p-4 flex flex-col gap-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Layers className="w-4 h-4 text-indigo-400" aria-hidden="true" />
            <span>Sidebar Slot (UploadDropzone + ControlPanel)</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Khung Dark Mode Studio, API Client và hằng số Contract đã sẵn sàng để TV1 triển khai 5
            component UI trên nhánh <code className="text-sky-400">feat/frontend-ui</code>.
          </p>
        </aside>

        <section className="rounded-xl bg-slate-900 border border-white/10 p-4 flex flex-col gap-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Activity className="w-4 h-4 text-sky-400" aria-hidden="true" />
            <span>Workspace Slot (BeforeAfterSlider + HistogramChart)</span>
          </div>
          <div className="flex-1 rounded-lg border border-dashed border-white/10 bg-slate-950/60 flex items-center justify-center text-sm text-slate-500">
            Ready for BeforeAfterSlider &amp; 256-bin Recharts Histogram
          </div>
        </section>
      </main>
    </div>
  );
}
