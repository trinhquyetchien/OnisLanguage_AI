export type TranscriptSegment = {
  segment_id: number;
  start: number;
  end: number;
  text_ja: string;
};

export type TranscriptResponse = {
  audio_filename: string;
  duration: number;
  full_text_ja: string;
  segments: TranscriptSegment[];
  media_url: string;
  media_kind: "audio" | "video";
};
