import React from "react";
import { clsx } from "clsx";

export interface KanjiPrediction {
  kanji: string;
  confidence: number;
  label_id: number;
}

export interface KanjiResponse {
  top1: KanjiPrediction;
  top5: KanjiPrediction[];
}

interface KanjiResultPanelProps {
  data: KanjiResponse | null;
  error: string | null;
}

export const KanjiResultPanel: React.FC<KanjiResultPanelProps> = ({ data, error }) => {
  if (error) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-[32px] border border-rose-200 bg-rose-50 p-8 text-rose-600 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-400">
        <p>⚠️ {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-[32px] border border-dashed border-slate-300 bg-white/30 p-8 text-slate-400 dark:border-slate-700 dark:bg-slate-900/30">
        <p>Draw a Kanji character and click Predict to see results.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-[32px] border border-white/60 bg-white/50 p-8 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/50">
      <div className="mb-8 text-center">
        <h2 className="text-sm font-medium uppercase tracking-widest text-slate-400 mb-4">Top Prediction</h2>
        <div className="text-8xl font-bold text-slate-900 dark:text-white mb-4 drop-shadow-sm">
          {data.top1.kanji}
        </div>
        <div className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-4 py-1.5 text-sm font-bold text-white shadow-lg shadow-sky-500/20">
          {(data.top1.confidence * 100).toFixed(1)}% Confidence
        </div>
      </div>

      <div className="mt-auto">
        <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-slate-400">Candidates</h3>
        <div className="grid grid-cols-5 gap-3">
          {data.top5.map((item, i) => (
            <div
              key={i}
              className={clsx(
                "flex flex-col items-center justify-center p-3 rounded-2xl border transition-all",
                i === 0 
                  ? "border-sky-500 bg-sky-500/10 text-sky-600 dark:text-sky-400" 
                  : "border-slate-100 bg-white dark:border-slate-800 dark:bg-slate-950/50"
              )}
            >
              <span className="text-2xl font-bold mb-1">{item.kanji}</span>
              <span className="text-[10px] font-mono opacity-60">{(item.confidence * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
