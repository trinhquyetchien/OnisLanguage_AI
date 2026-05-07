import React, { useRef, useEffect, useState, useCallback } from "react";
import { Eraser, Pen, Trash2, Grid } from "lucide-react";
import { clsx } from "clsx";

interface DrawingCanvasProps {
  onPredict: (blob: Blob) => void;
  onClear: () => void;
  brushSize: number;
  setBrushSize: (size: number) => void;
}

export const DrawingCanvas: React.FC<DrawingCanvasProps> = ({
  onPredict,
  onClear,
  brushSize,
  setBrushSize
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gridCanvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isEraser, setIsEraser] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const pointerActiveRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  useEffect(() => {
    const gridCanvas = gridCanvasRef.current;
    if (!gridCanvas) return;
    const ctx = gridCanvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);

    if (!showGrid) return;

    ctx.strokeStyle = "rgba(203, 213, 225, 0.5)"; // slate-300 with alpha
    ctx.lineWidth = 1;

    const gridSize = 40;
    for (let x = gridSize; x < gridCanvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, gridCanvas.height);
      ctx.stroke();
    }
    for (let y = gridSize; y < gridCanvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(gridCanvas.width, y);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(244, 63, 94, 0.3)"; // rose-500 with alpha
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    const cx = gridCanvas.width / 2;
    const cy = gridCanvas.height / 2;
    ctx.beginPath(); ctx.moveTo(cx - 40, cy); ctx.lineTo(cx + 40, cy); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy - 40); ctx.lineTo(cx, cy + 40); ctx.stroke();
    ctx.setLineDash([]);
  }, [showGrid]);

  const getCanvasPoint = (e: React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(canvas.width, e.clientX - rect.left)),
      y: Math.max(0, Math.min(canvas.height, e.clientY - rect.top)),
    };
  };

  const startDrawing = (e: React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { x, y } = getCanvasPoint(e);

    pointerActiveRef.current = true;
    setIsDrawing(true);
    ctx.globalCompositeOperation = isEraser ? "destination-out" : "source-over";
    ctx.beginPath();
    ctx.moveTo(x, y);
  };

  const draw = (e: React.PointerEvent) => {
    if (!pointerActiveRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { x, y } = getCanvasPoint(e);

    ctx.lineWidth = brushSize;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = isEraser ? "rgba(0,0,0,1)" : "black";
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    pointerActiveRef.current = false;
    setIsDrawing(false);
  };

  const clear = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    onClear();
  };

  const handlePredict = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Simplification: directly send blob of content
    canvas.toBlob((blob) => {
      if (blob) onPredict(blob);
    }, "image/png");
  };

  return (
    <div className="space-y-6">
      <div className="relative aspect-square w-full max-w-[400px] overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900/50 mx-auto">
        <canvas
          ref={gridCanvasRef}
          width={400}
          height={400}
          className="absolute inset-0 pointer-events-none"
        />
        <canvas
          ref={canvasRef}
          width={400}
          height={400}
          onPointerDown={startDrawing}
          onPointerMove={draw}
          onPointerUp={stopDrawing}
          onPointerCancel={stopDrawing}
          onPointerLeave={stopDrawing}
          className="absolute inset-0 cursor-crosshair touch-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-4 p-6 rounded-3xl border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Brush Settings</span>
            <span className="text-xs font-mono bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">{brushSize}px</span>
          </div>
          <input
            type="range"
            min="1"
            max="20"
            value={brushSize}
            onChange={(e) => setBrushSize(parseInt(e.target.value))}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => setIsEraser(false)}
              className={clsx(
                "flex-1 flex items-center justify-center gap-2 py-2 rounded-xl border transition-all",
                !isEraser ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900" : "border-slate-200 dark:border-slate-800"
              )}
            >
              <Pen size={16} /> <span className="text-sm">Pen</span>
            </button>
            <button
              onClick={() => setIsEraser(true)}
              className={clsx(
                "flex-1 flex items-center justify-center gap-2 py-2 rounded-xl border transition-all",
                isEraser ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900" : "border-slate-200 dark:border-slate-800"
              )}
            >
              <Eraser size={16} /> <span className="text-sm">Eraser</span>
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-3 justify-center">
          <button
            onClick={clear}
            className="flex items-center justify-center gap-2 py-4 rounded-2xl border border-slate-200 bg-white hover:bg-slate-50 transition-all dark:border-slate-800 dark:bg-slate-900/50"
          >
            <Trash2 size={18} /> Clear
          </button>
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={clsx(
              "flex items-center justify-center gap-2 py-4 rounded-2xl border transition-all",
              showGrid ? "bg-sky-500/10 text-sky-500 border-sky-500/50" : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50"
            )}
          >
            <Grid size={18} /> {showGrid ? "Hide Grid" : "Show Grid"}
          </button>
          <button
            onClick={handlePredict}
            className="flex items-center justify-center gap-2 py-4 rounded-2xl bg-slate-900 text-white font-semibold hover:bg-slate-800 transition-all dark:bg-white dark:text-slate-900"
          >
            Predict Kanji
          </button>
        </div>
      </div>
    </div>
  );
};
