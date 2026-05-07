import React, { useRef } from "react";
import { Upload, X, FileImage } from "lucide-react";

interface UploadPanelProps {
  uploading: boolean;
  selectedFileName: string | null;
  error: string | null;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
  disabled: boolean;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({
  uploading,
  selectedFileName,
  error,
  onFileChange,
  onUpload,
  disabled,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      onFileChange(file);
    }
  };

  return (
    <div className="rounded-[32px] border border-white/60 bg-white/50 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/50">
      <h2 className="mb-4 text-xl font-semibold">Upload Image</h2>
      
      <div
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`group relative flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed py-12 transition-all ${
          selectedFileName
            ? "border-sky-500/50 bg-sky-500/5"
            : "border-slate-300 bg-slate-50 hover:border-sky-400 hover:bg-sky-50/50 dark:border-slate-700 dark:bg-slate-950/50 dark:hover:border-sky-500/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
        />

        {selectedFileName ? (
          <div className="flex flex-col items-center gap-3">
            <div className="rounded-2xl bg-sky-500 p-4 text-white shadow-lg shadow-sky-500/20">
              <FileImage size={32} />
            </div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{selectedFileName}</p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFileChange(null);
              }}
              className="absolute right-4 top-4 rounded-full p-2 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-800"
            >
              <X size={20} />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="rounded-2xl bg-slate-200 p-4 text-slate-400 transition-colors group-hover:bg-sky-100 group-hover:text-sky-500 dark:bg-slate-800">
              <Upload size={32} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                Click or drag to upload an image
              </p>
              <p className="mt-1 text-xs text-slate-400">Supports PNG, JPG, BMP</p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
          {error}
        </div>
      )}

      <button
        onClick={onUpload}
        disabled={disabled || uploading}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 py-4 font-semibold text-white transition-all hover:bg-slate-800 disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
      >
        {uploading ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent dark:border-slate-900" />
            Extracting text...
          </>
        ) : (
          "Run OCR"
        )}
      </button>
    </div>
  );
};
