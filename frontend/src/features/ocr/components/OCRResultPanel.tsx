import React from "react";
import { Copy, Check } from "lucide-react";
import { OCRResponse } from "../../../lib/types/ocr";

interface OCRResultPanelProps {
  data: OCRResponse | null;
}

export const OCRResultPanel: React.FC<OCRResultPanelProps> = ({ data }) => {
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = () => {
    if (data?.full_text) {
      navigator.clipboard.writeText(data.full_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!data) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-[32px] border border-dashed border-slate-300 bg-white/30 p-8 text-slate-400 dark:border-slate-700 dark:bg-slate-900/30">
        <p>No results yet. Upload an image to start OCR.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-[32px] border border-white/60 bg-white/50 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/50">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Extracted Text</h2>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          {copied ? (
            <>
              <Check size={14} className="text-green-500" />
              Copied
            </>
          ) : (
            <>
              <Copy size={14} />
              Copy All
            </>
          )}
        </button>
      </div>

      <div className="flex-1 overflow-auto rounded-2xl bg-white/50 p-4 dark:bg-slate-950/50">
        <pre className="whitespace-pre-wrap font-sans text-lg leading-relaxed text-slate-800 dark:text-slate-100">
          {data.full_text}
        </pre>
      </div>

      <div className="mt-6">
        <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-slate-400">Detailed Blocks</h3>
        <div className="space-y-2">
          {data.blocks.map((block, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50"
            >
              <span className="text-sm text-slate-700 dark:text-slate-300">{block.text}</span>
              <span className="text-xs font-mono text-slate-400">
                {(block.confidence * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
