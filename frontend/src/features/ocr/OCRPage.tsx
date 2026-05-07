import React, { useState, useEffect } from "react";
import { Sparkles, Image as ImageIcon, Languages } from "lucide-react";
import { UploadPanel } from "./components/UploadPanel";
import { OCRResultPanel } from "./components/OCRResultPanel";

export interface TextBlock {
  text: string;
  confidence: number;
  box: number[][];
}

export interface OCRResponse {
  full_text: string;
  blocks: TextBlock[];
  image_url?: string;
}

const OCRPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [data, setData] = useState<OCRResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (selectedFile) {
      const url = URL.createObjectURL(selectedFile);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [selectedFile]);

  async function handleUpload() {
    if (!selectedFile) {
      setError("Choose an image file first.");
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`/api/ocr/process`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "OCR processing failed.");
      }

      const ocrData = (await response.json()) as OCRResponse;
      setData(ocrData);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not process this image.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8 flex flex-col gap-6 rounded-[36px] border border-white/60 bg-white/75 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/70 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900">
              <Sparkles size={16} />
              PaddleOCR Japanese Text Extraction
            </div>
            <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">Convert Japanese images to editable text instantly.</h1>
          </div>

          <div className="rounded-[28px] border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-950">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-sky-500/10 p-3 text-sky-500">
                <Languages size={22} />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Engine</p>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">PaddleOCR v2.7</p>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-6">
            <UploadPanel
              uploading={uploading}
              selectedFileName={selectedFile?.name ?? null}
              error={error}
              onFileChange={(file) => {
                setSelectedFile(file);
                setData(null);
              }}
              onUpload={handleUpload}
              disabled={uploading || !selectedFile}
            />

            {previewUrl && (
              <div className="overflow-hidden rounded-[32px] border border-white/60 bg-white/50 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/50">
                <div className="flex items-center gap-2 border-b border-slate-100 p-4 dark:border-slate-800">
                  <ImageIcon size={18} className="text-slate-400" />
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Image Preview</span>
                </div>
                <div className="p-6">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="h-auto max-w-full rounded-2xl shadow-lg"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="h-full">
            <OCRResultPanel data={data} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default OCRPage;
