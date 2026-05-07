import React, { useState } from "react";
import { Sparkles, PenTool } from "lucide-react";
import { DrawingCanvas } from "./components/DrawingCanvas";
import { KanjiResultPanel, KanjiResponse } from "./components/KanjiResultPanel";

const KanjiPage: React.FC = () => {
  const [data, setData] = useState<KanjiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brushSize, setBrushSize] = useState(8);

  async function handlePredict(blob: Blob) {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", blob, "kanji.png");

    try {
      const response = await fetch(`/api/kanji/predict`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Recognition failed.");
      }

      const res = (await response.json()) as KanjiResponse;
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process drawing.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8 flex flex-col gap-6 rounded-[36px] border border-white/60 bg-white/75 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/70 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900">
              <Sparkles size={16} />
              AI Handwritten Kanji Recognition
            </div>
            <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">Draw any Kanji to recognize and learn its details.</h1>
          </div>

          <div className="rounded-[28px] border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-950">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-rose-500/10 p-3 text-rose-500">
                <PenTool size={22} />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Engine</p>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">ResNet18 / PyTorch</p>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
          <DrawingCanvas 
            onPredict={handlePredict} 
            onClear={() => { setData(null); setError(null); }}
            brushSize={brushSize}
            setBrushSize={setBrushSize}
          />
          <div className="h-full">
            <KanjiResultPanel data={data} error={error} />
          </div>
        </div>
      </div>
      
      {loading && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/20 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-4 p-8 rounded-3xl bg-white shadow-soft dark:bg-slate-900">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-sky-500 border-t-transparent" />
            <p className="font-medium">Analyzing drawing...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default KanjiPage;
