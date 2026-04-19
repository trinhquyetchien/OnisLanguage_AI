import { useEffect, useMemo, useRef, useState } from "react";
import { AudioLines, MoonStar, Sparkles, SunMedium } from "lucide-react";

import { MediaPlayer } from "./components/MediaPlayer";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { UploadPanel } from "./components/UploadPanel";
import type { TranscriptResponse, TranscriptSegment } from "./lib/types";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [data, setData] = useState<TranscriptResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  const mediaRef = useRef<HTMLAudioElement | HTMLVideoElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    const media = mediaRef.current;
    if (!media) {
      return;
    }

    const onTimeUpdate = () => setCurrentTime(media.currentTime);
    const onLoadedMetadata = () => setDuration(media.duration || data?.duration || 0);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onEnded = () => setIsPlaying(false);

    media.addEventListener("timeupdate", onTimeUpdate);
    media.addEventListener("loadedmetadata", onLoadedMetadata);
    media.addEventListener("play", onPlay);
    media.addEventListener("pause", onPause);
    media.addEventListener("ended", onEnded);

    return () => {
      media.removeEventListener("timeupdate", onTimeUpdate);
      media.removeEventListener("loadedmetadata", onLoadedMetadata);
      media.removeEventListener("play", onPlay);
      media.removeEventListener("pause", onPause);
      media.removeEventListener("ended", onEnded);
    };
  }, [data]);

  const activeSegment = useMemo(() => {
    if (!data) {
      return null;
    }

    return (
      data.segments.find(
        (segment) => currentTime >= segment.start && (currentTime < segment.end || Math.abs(currentTime - segment.end) < 0.15),
      ) ?? null
    );
  }, [currentTime, data]);

  useEffect(() => {
    if (!autoScroll || !activeSegment || !transcriptRef.current) {
      return;
    }

    const activeNode = transcriptRef.current.querySelector<HTMLElement>(`[data-segment-id="${activeSegment.segment_id}"]`);
    activeNode?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeSegment, autoScroll]);

  async function handleUpload() {
    if (!selectedFile) {
      setError("Choose an audio or video file first.");
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${API_BASE}/api/transcribe`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Transcription failed.");
      }

      const transcript = (await response.json()) as TranscriptResponse;
      setData(transcript);
      setCurrentTime(0);
      setDuration(transcript.duration);
      setIsPlaying(false);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not transcribe this file.");
    } finally {
      setUploading(false);
    }
  }

  function togglePlay() {
    const media = mediaRef.current;
    if (!media) {
      return;
    }

    if (media.paused) {
      void media.play();
    } else {
      media.pause();
    }
  }

  function seekTo(seconds: number) {
    const media = mediaRef.current;
    if (!media) {
      return;
    }

    media.currentTime = seconds;
    setCurrentTime(seconds);
  }

  function handleSegmentClick(segment: TranscriptSegment) {
    seekTo(segment.start);
    if (mediaRef.current?.paused) {
      void mediaRef.current.play();
    }
  }

  return (
    <main className="min-h-screen bg-ink-50 bg-halo px-4 py-6 text-slate-900 transition-colors dark:bg-slate-950 dark:text-white md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col gap-6 rounded-[36px] border border-white/60 bg-white/75 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/70 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900">
              <Sparkles size={16} />
              Local Japanese transcription studio
            </div>
            <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">Study Japanese from real audio and video with timestamped transcript sync.</h1>
            <p className="mt-4 max-w-xl text-sm leading-7 text-slate-600 dark:text-slate-300">
              Upload one file, transcribe it with your local model, then scrub through segments like a focused listening lab.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-[28px] border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-sky-500/10 p-3 text-sky-500">
                  <AudioLines size={22} />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Focus mode</p>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Segment-aware playback</p>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setTheme((value) => (value === "dark" ? "light" : "dark"))}
              className="rounded-full border border-slate-200 bg-white p-3 text-slate-700 transition hover:border-sky-400 hover:text-sky-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
            >
              {theme === "dark" ? <SunMedium size={18} /> : <MoonStar size={18} />}
            </button>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
          <div className="space-y-6">
            <UploadPanel
              uploading={uploading}
              selectedFileName={selectedFile?.name ?? null}
              error={error}
              onFileChange={setSelectedFile}
              onUpload={handleUpload}
              disabled={uploading || !selectedFile}
            />

            <MediaPlayer
              mediaRef={mediaRef}
              src={data ? `${API_BASE}${data.media_url}` : null}
              mediaKind={data?.media_kind ?? null}
              title={data?.audio_filename ?? "Waiting for media"}
              currentTime={currentTime}
              duration={duration}
              isPlaying={isPlaying}
              onTogglePlay={togglePlay}
              onSeek={seekTo}
              onSkip={(delta) => seekTo(Math.max(0, Math.min(duration || 0, currentTime + delta)))}
            />
          </div>

          <TranscriptPanel
            segments={data?.segments ?? []}
            activeSegmentId={activeSegment?.segment_id ?? null}
            autoScroll={autoScroll}
            transcriptRef={transcriptRef}
            onSegmentClick={handleSegmentClick}
            onToggleAutoScroll={() => setAutoScroll((value) => !value)}
          />
        </div>
      </div>
    </main>
  );
}

export default App;
