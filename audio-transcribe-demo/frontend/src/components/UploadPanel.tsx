import { Loader2, UploadCloud } from "lucide-react";

type UploadPanelProps = {
  uploading: boolean;
  selectedFileName: string | null;
  error: string | null;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
  disabled: boolean;
};

export function UploadPanel({
  uploading,
  selectedFileName,
  error,
  onFileChange,
  onUpload,
  disabled,
}: UploadPanelProps) {
  return (
    <section className="rounded-[32px] border border-white/60 bg-white/80 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/80">
      <div className="mb-5 flex items-center gap-3">
        <div className="rounded-2xl bg-sky-500/10 p-3 text-sky-600 dark:text-sky-300">
          <UploadCloud size={22} />
        </div>
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-400">Upload</p>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Japanese listening session</h2>
        </div>
      </div>

      <label className="flex cursor-pointer flex-col items-center justify-center rounded-[28px] border border-dashed border-slate-300 bg-slate-50/80 px-6 py-10 text-center transition hover:border-sky-400 hover:bg-sky-50 dark:border-slate-700 dark:bg-slate-950/50 dark:hover:border-sky-500/60 dark:hover:bg-slate-900">
        <input
          type="file"
          accept=".mp3,.wav,.m4a,.mp4,.flac,.ogg,.aac,.webm,.mov,.mkv"
          className="hidden"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
        />
        <p className="text-base font-semibold text-slate-900 dark:text-white">Drop an audio/video file or choose one</p>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Supported: mp3, wav, m4a, mp4, flac, ogg, aac, webm, mov, mkv</p>
        {selectedFileName ? (
          <div className="mt-4 rounded-full bg-slate-900 px-4 py-2 text-sm text-white dark:bg-slate-100 dark:text-slate-900">
            {selectedFileName}
          </div>
        ) : null}
      </label>

      <div className="mt-5 flex items-center justify-between gap-4">
        <p className="text-sm text-slate-500 dark:text-slate-400">Transcript is generated from your local model.</p>
        <button
          type="button"
          disabled={disabled}
          onClick={onUpload}
          className="inline-flex min-w-36 items-center justify-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300"
        >
          {uploading ? <Loader2 size={16} className="animate-spin" /> : null}
          {uploading ? "Transcribing..." : "Start analysis"}
        </button>
      </div>

      {error ? <p className="mt-4 text-sm text-rose-500">{error}</p> : null}
    </section>
  );
}
