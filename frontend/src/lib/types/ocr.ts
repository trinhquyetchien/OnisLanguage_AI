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
