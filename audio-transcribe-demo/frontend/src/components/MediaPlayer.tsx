import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { RefObject } from "react";

import { formatTime } from "../lib/time";

type MediaPlayerProps = {
  mediaRef: RefObject<HTMLAudioElement | HTMLVideoElement>;
  src: string | null;
  mediaKind: "audio" | "video" | null;
  title: string;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onSeek: (seconds: number) => void;
  onSkip: (delta: number) => void;
};

export function MediaPlayer({
  mediaRef,
  src,
  mediaKind,
  title,
  currentTime,
  duration,
  isPlaying,
  onTogglePlay,
  onSeek,
  onSkip,
}: MediaPlayerProps) {
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <section className="rounded-[32px] border border-slate-200/70 bg-white/80 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/80">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-400">Player</p>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">{title}</h2>
        </div>
        <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">
          {mediaKind === "video" ? "Video mode" : "Audio mode"}
        </div>
      </div>

      {mediaKind === "video" ? (
        <video ref={mediaRef as RefObject<HTMLVideoElement>} src={src ?? undefined} className="mb-5 aspect-video w-full rounded-[28px] bg-black" />
      ) : (
        <div className="mb-5 rounded-[28px] bg-[linear-gradient(135deg,rgba(14,165,233,0.18),rgba(249,115,22,0.16))] p-6">
          <audio ref={mediaRef as RefObject<HTMLAudioElement>} src={src ?? undefined} />
          <div className="flex h-40 items-end gap-2 overflow-hidden rounded-[24px] bg-slate-950/90 px-6 py-5">
            {Array.from({ length: 40 }).map((_, index) => (
              <div
                key={index}
                className="w-full rounded-full bg-gradient-to-t from-sky-400 to-cyan-200 opacity-80"
                style={{ height: `${30 + ((index * 17) % 70)}%` }}
              />
            ))}
          </div>
        </div>
      )}

      <div className="rounded-[28px] bg-slate-50 p-5 dark:bg-slate-950/70">
        <input
          type="range"
          min={0}
          max={duration || 0}
          value={Math.min(currentTime, duration || 0)}
          onChange={(event) => onSeek(Number(event.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-sky-500 dark:bg-slate-800"
          style={{
            background: `linear-gradient(to right, rgb(14 165 233) 0%, rgb(14 165 233) ${progress}%, rgba(148,163,184,0.25) ${progress}%, rgba(148,163,184,0.25) 100%)`,
          }}
        />

        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => onSkip(-5)} className="rounded-full border border-slate-200 p-3 transition hover:border-sky-400 hover:text-sky-500 dark:border-slate-700 dark:hover:border-sky-500">
              <SkipBack size={18} />
            </button>
            <button
              type="button"
              onClick={onTogglePlay}
              className="rounded-full bg-slate-900 p-4 text-white transition hover:bg-slate-700 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300"
            >
              {isPlaying ? <Pause size={20} /> : <Play size={20} />}
            </button>
            <button type="button" onClick={() => onSkip(5)} className="rounded-full border border-slate-200 p-3 transition hover:border-sky-400 hover:text-sky-500 dark:border-slate-700 dark:hover:border-sky-500">
              <SkipForward size={18} />
            </button>
          </div>

          <div className="text-sm font-medium text-slate-500 dark:text-slate-300">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
        </div>
      </div>
    </section>
  );
}
