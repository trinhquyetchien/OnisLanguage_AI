import clsx from "clsx";
import { Captions, ChevronDown } from "lucide-react";
import { RefObject } from "react";

import { formatTime } from "../../../lib/time";
import { TranscriptSegment } from "../../../lib/types/transcribe";

type TranscriptPanelProps = {
  segments: TranscriptSegment[];
  activeSegmentId: number | null;
  autoScroll: boolean;
  transcriptRef: RefObject<HTMLDivElement>;
  onSegmentClick: (segment: TranscriptSegment) => void;
  onToggleAutoScroll: () => void;
};

export function TranscriptPanel({
  segments,
  activeSegmentId,
  autoScroll,
  transcriptRef,
  onSegmentClick,
  onToggleAutoScroll,
}: TranscriptPanelProps) {
  return (
    <section className="flex min-h-[520px] flex-col rounded-[32px] border border-slate-200/70 bg-white/80 p-6 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/80">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-emerald-500/10 p-3 text-emerald-600 dark:text-emerald-300">
            <Captions size={22} />
          </div>
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-400">Transcript</p>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Synced Japanese segments</h2>
          </div>
        </div>

        <button
          type="button"
          onClick={onToggleAutoScroll}
          className={clsx(
            "rounded-full px-4 py-2 text-sm font-medium transition",
            autoScroll
              ? "bg-slate-900 text-white dark:bg-sky-400 dark:text-slate-950"
              : "border border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300",
          )}
        >
          Auto-scroll {autoScroll ? "on" : "off"}
        </button>
      </div>

      <div ref={transcriptRef} className="space-y-3 overflow-y-auto pr-1">
        {segments.length === 0 ? (
          <div className="flex min-h-60 items-center justify-center rounded-[28px] border border-dashed border-slate-300 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
            Upload a file and the transcript timeline will appear here.
          </div>
        ) : null}

        {segments.map((segment) => {
          const active = segment.segment_id === activeSegmentId;
          return (
            <button
              key={segment.segment_id}
              type="button"
              data-segment-id={segment.segment_id}
              onClick={() => onSegmentClick(segment)}
              className={clsx(
                "group flex w-full items-start justify-between gap-4 rounded-[24px] border px-4 py-4 text-left transition",
                active
                  ? "border-sky-400 bg-sky-50 shadow-lg shadow-sky-500/10 dark:border-sky-500 dark:bg-slate-950"
                  : "border-transparent bg-slate-50 hover:border-slate-200 hover:bg-white dark:bg-slate-950/60 dark:hover:border-slate-700 dark:hover:bg-slate-950",
              )}
            >
              <div>
                <p className="text-base font-medium leading-7 text-slate-900 dark:text-white">{segment.text_ja}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.24em] text-slate-400">Segment {segment.segment_id + 1}</p>
              </div>
              <div className="flex items-center gap-3 whitespace-nowrap">
                <span className="text-sm font-medium text-slate-500 dark:text-slate-300">
                  {formatTime(segment.start)} - {formatTime(segment.end)}
                </span>
                <ChevronDown
                  size={16}
                  className={clsx("transition", active ? "-rotate-90 text-sky-500" : "rotate-90 text-slate-300")}
                />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
