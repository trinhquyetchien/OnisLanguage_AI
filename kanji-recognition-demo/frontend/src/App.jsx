import React, { useState, useRef, useCallback, useEffect } from 'react';
import './App.css';

function App() {
  const [predictions, setPredictions] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [brushSize, setBrushSize] = useState(5);
  const [isEraser, setIsEraser] = useState(false);
  const [debugProcessed, setDebugProcessed] = useState(null);
  const [showGrid, setShowGrid] = useState(true);
  const [selectedLabel, setSelectedLabel] = useState(null);
  const [manualLabel, setManualLabel] = useState("");
  const [manualLabelId, setManualLabelId] = useState("");
  const [saveStatus, setSaveStatus] = useState("");
  const [saveError, setSaveError] = useState("");
  const [deviceType, setDeviceType] = useState("mouse");
  const [saving, setSaving] = useState(false);
  const canvasRef = useRef(null);
  const gridCanvasRef = useRef(null);
  const rawStrokesRef = useRef([]);
  const currentStrokeRef = useRef(null);
  const pointerActiveRef = useRef(false);
  const debounceRef = useRef(null);

  // Initialize drawing canvas as transparent on mount so stroke layer is isolated
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  // Draw grid lines on a separate canvas for guidance
  useEffect(() => {
    const gridCanvas = gridCanvasRef.current;
    if (!gridCanvas) return;

    const ctx = gridCanvas.getContext('2d');
    ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);

    if (!showGrid) return;

    const gridSize = 40; // Grid spacing in pixels
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;

    // Draw vertical lines
    for (let x = gridSize; x < gridCanvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, gridCanvas.height);
      ctx.stroke();
    }

    // Draw horizontal lines
    for (let y = gridSize; y < gridCanvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(gridCanvas.width, y);
      ctx.stroke();
    }

    // Draw center cross (guides for centering character)
    ctx.strokeStyle = '#ffb3ba';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    const centerX = gridCanvas.width / 2;
    const centerY = gridCanvas.height / 2;

    ctx.beginPath();
    ctx.moveTo(centerX - 40, centerY);
    ctx.lineTo(centerX + 40, centerY);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(centerX, centerY - 40);
    ctx.lineTo(centerX, centerY + 40);
    ctx.stroke();

    ctx.setLineDash([]);
  }, [showGrid]);

  const getCanvasBounds = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    let minX = canvas.width, minY = canvas.height, maxX = 0, maxY = 0;
    for (let y = 0; y < canvas.height; y++) {
      for (let x = 0; x < canvas.width; x++) {
        const index = (y * canvas.width + x) * 4;
        if (data[index + 3] > 0) { // Alpha > 0
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        }
      }
    }

    return { minX, minY, maxX, maxY };
  }, []);

  const processAndSendImage = useCallback(async () => {
    const canvas = canvasRef.current;
    const { minX, minY, maxX, maxY } = getCanvasBounds();

    if (maxX - minX === 0 || maxY - minY === 0) {
      // Empty canvas
      setPredictions(null);
      setDebugProcessed(null);
      return;
    }

    // Crop to content
    const croppedWidth = maxX - minX + 1;
    const croppedHeight = maxY - minY + 1;
    const size = Math.max(croppedWidth, croppedHeight);

    // Create a square canvas for the stroke-only layer
    const squareCanvas = document.createElement('canvas');
    squareCanvas.width = size;
    squareCanvas.height = size;
    const squareCtx = squareCanvas.getContext('2d');

    squareCtx.clearRect(0, 0, size, size);

    const offsetX = (size - croppedWidth) / 2;
    const offsetY = (size - croppedHeight) / 2;
    squareCtx.drawImage(
      canvas,
      minX,
      minY,
      croppedWidth,
      croppedHeight,
      offsetX,
      offsetY,
      croppedWidth,
      croppedHeight
    );

    // Convert to stroke-only binary layer with threshold
    const imageData = squareCtx.getImageData(0, 0, size, size);
    const data = imageData.data;
    const threshold = 160; // between 150 and 170
    for (let i = 0; i < data.length; i += 4) {
      const red = data[i];
      const green = data[i + 1];
      const blue = data[i + 2];
      const alpha = data[i + 3];
      const luma = 0.299 * red + 0.587 * green + 0.114 * blue;
      const isStroke = alpha > 10 && luma < threshold;
      const value = isStroke ? 0 : 255;
      data[i] = value;
      data[i + 1] = value;
      data[i + 2] = value;
      data[i + 3] = 255;
    }
    squareCtx.putImageData(imageData, 0, 0);

    // Resize using nearest neighbor to preserve stroke edges
    const finalCanvas = document.createElement('canvas');
    finalCanvas.width = 128;
    finalCanvas.height = 128;
    const finalCtx = finalCanvas.getContext('2d');
    finalCtx.imageSmoothingEnabled = false;
    finalCtx.imageSmoothingQuality = 'low';
    finalCtx.drawImage(squareCanvas, 0, 0, 128, 128);

    setDebugProcessed(finalCanvas.toDataURL());

    finalCanvas.toBlob(async (blob) => {
      if (!blob) {
        setPredictions({ error: 'Unable to serialize the processed canvas.' });
        return;
      }
      const formData = new FormData();
      formData.append('file', blob, 'kanji.png');

      try {
        const response = await fetch('http://127.0.0.1:8000/predict', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        setPredictions(result);
      } catch (error) {
        console.error('Prediction error:', error);
        setPredictions({ error: error.message });
      }
    }, 'image/png');
  }, [getCanvasBounds]);

  useEffect(() => {
    if (predictions && !predictions.error) {
      setSelectedLabel(predictions.top1);
      setManualLabel("");
      setManualLabelId("");
      setSaveStatus("");
      setSaveError("");
    }
  }, [predictions]);

  const getCanvasPoint = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(canvas.width, event.clientX - rect.left));
    const y = Math.max(0, Math.min(canvas.height, event.clientY - rect.top));
    return { x, y };
  };

  const dataUrlToBlob = async (dataUrl) => {
    const res = await fetch(dataUrl);
    return await res.blob();
  };

  const saveConfirmedDrawing = async () => {
    if (!predictions || predictions.error) {
      setSaveError('Please predict the drawing before saving.');
      return;
    }

    if (!rawStrokesRef.current.length) {
      setSaveError('No stroke data available. Draw before saving.');
      return;
    }

    const confirmedChar = manualLabel.trim() || selectedLabel?.kanji;
    const confirmedLabelIdValue = manualLabel.trim()
      ? parseInt(manualLabelId, 10) || 0
      : selectedLabel?.label_id || 0;

    if (!confirmedChar) {
      setSaveError('Please confirm or enter the correct Kanji label.');
      return;
    }

    if (!debugProcessed) {
      setSaveError('Processed image is not available. Predict first.');
      return;
    }

    setSaving(true);
    setSaveError("");
    setSaveStatus("");

    try {
      const processedBlob = await dataUrlToBlob(debugProcessed);
      const rawCanvasBlob = await new Promise((resolve) => {
        canvasRef.current.toBlob(resolve, 'image/png');
      });

      const formData = new FormData();
      formData.append('processed_image', processedBlob, 'processed.png');
      formData.append('raw_strokes', JSON.stringify({
        sample_width: 400,
        sample_height: 400,
        device: deviceType,
        source: 'user_app',
        strokes: rawStrokesRef.current,
      }));
      formData.append('confirmed_label', confirmedChar);
      formData.append('confirmed_label_id', confirmedLabelIdValue.toString());
      formData.append('top1_pred', JSON.stringify(predictions.top1));
      formData.append('top5_json', JSON.stringify(predictions.top5));
      formData.append('device', deviceType);
      formData.append('source', 'user_app');
      if (rawCanvasBlob) {
        formData.append('raw_canvas', rawCanvasBlob, 'raw_canvas.png');
      }

      const response = await fetch('http://127.0.0.1:8000/save-drawing', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errBody = await response.text();
        throw new Error(`Save failed: ${response.status} ${errBody}`);
      }

      const result = await response.json();
      setSaveStatus(`Saved sample ${result.sample_id}`);
      rawStrokesRef.current = [];
      setSelectedLabel(null);
      setManualLabel("");
      setManualLabelId("");
    } catch (error) {
      console.error('Save error:', error);
      setSaveError(error.message);
    } finally {
      setSaving(false);
    }
  };

  const handlePredict = useCallback(() => {
    processAndSendImage();
  }, [processAndSendImage]);

  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const { x, y } = getCanvasPoint(e);
    const device = e.pointerType || 'mouse';

    setDeviceType(device);
    pointerActiveRef.current = true;
    setIsDrawing(true);

    // Reset composite operation for fresh stroke
    if (isEraser) {
      ctx.globalCompositeOperation = 'destination-out';
    } else {
      ctx.globalCompositeOperation = 'source-over';
    }

    ctx.beginPath();
    ctx.moveTo(x, y);

    const newStroke = {
      pointerType: device,
      tool: isEraser ? 'eraser' : 'pen',
      points: [{ x, y }],
    };
    currentStrokeRef.current = newStroke;
    rawStrokesRef.current = [...rawStrokesRef.current, newStroke];
  };

  const draw = (e) => {
    if (!pointerActiveRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const { x, y } = getCanvasPoint(e);

    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (isEraser) {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.strokeStyle = 'rgba(0,0,0,1)';
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = 'black';
    }

    ctx.lineTo(x, y);
    ctx.stroke();

    if (currentStrokeRef.current) {
      currentStrokeRef.current.points.push({ x, y });
    }
  };

  const stopDrawing = () => {
    if (pointerActiveRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      ctx.globalCompositeOperation = 'source-over';
      pointerActiveRef.current = false;
      setIsDrawing(false);
    }
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    rawStrokesRef.current = [];
    setPredictions(null);
    setDebugProcessed(null);
    setSelectedLabel(null);
    setManualLabel("");
    setManualLabelId("");
    setSaveStatus("");
    setSaveError("");
  };

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <h1>🎨 Kanji Recognition Demo</h1>
        <p>Draw a single Kanji character to recognize it in real-time</p>
      </header>

      <div className="container">
        <div className="left-panel">
          <div className="canvas-section">
            <div className="canvas-label">Drawing Area</div>
            <div className="canvas-wrapper">
              {/* Grid overlay canvas */}
              <canvas
                ref={gridCanvasRef}
                width={400}
                height={400}
                className="grid-canvas"
              />
              {/* Main drawing canvas */}
              <canvas
                ref={canvasRef}
                width={400}
                height={400}
                onPointerDown={startDrawing}
                onPointerMove={draw}
                onPointerUp={stopDrawing}
                onPointerCancel={stopDrawing}
                onPointerLeave={stopDrawing}
                className="drawing-canvas"
                title="Draw a single Kanji character in the center"
              />
              {/* Brush preview circle */}
              {isDrawing && (
                <div
                  className="brush-preview"
                  style={{
                    width: `${brushSize * 2}px`,
                    height: `${brushSize * 2}px`,
                    backgroundColor: isEraser ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)',
                  }}
                />
              )}
            </div>
          </div>

          <div className="controls-section">
            <div className="control-group">
              <button onClick={clearCanvas} className="btn btn-clear">
                🗑️ Clear Canvas
              </button>
            </div>

            <div className="control-group">
              <button onClick={handlePredict} className="btn btn-predict">
                🔮 Predict
              </button>
            </div>

            <div className="control-group">
              <label className="control-label">
                <span>Brush Size: <strong>{brushSize}px</strong></span>
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={brushSize}
                  onChange={(e) => setBrushSize(parseInt(e.target.value))}
                  className="slider"
                />
              </label>
            </div>

            <div className="control-group">
              <label className="control-label checkbox">
                <input
                  type="checkbox"
                  checked={isEraser}
                  onChange={(e) => setIsEraser(e.target.checked)}
                />
                <span>✏️ {isEraser ? 'Eraser Mode' : 'Pen Mode'}</span>
              </label>
            </div>

            <div className="control-group">
              <label className="control-label checkbox">
                <input
                  type="checkbox"
                  checked={showGrid}
                  onChange={(e) => setShowGrid(e.target.checked)}
                />
                <span>📐 Show Grid Lines</span>
              </label>
            </div>
          </div>

          {debugProcessed && (
            <div className="preview-section">
              <div className="preview-label">debug_processed (128×128)</div>
              <img src={debugProcessed} alt="Debug Processed" className="preview-image" />
              <p className="preview-note">This is the stroke-only image sent to the model</p>
            </div>
          )}
        </div>

        <div className="right-panel">
          <div className="predictions-section">
            <div className="predictions-title">Recognition Result</div>

            {predictions ? (
              predictions.error ? (
                <div className="error-box">
                  <p>⚠️ {predictions.error}</p>
                </div>
              ) : (
                <>
                  <div className="top1-box">
                    <div className="top1-label">Primary Prediction</div>
                    <div className="top1-character">
                      {predictions.top1.kanji}
                    </div>
                    <div className="top1-confidence">
                      Confidence: <strong>{(predictions.top1.confidence * 100).toFixed(2)}%</strong>
                    </div>
                    <div className="top1-id">
                      (ID: {predictions.top1.label_id})
                    </div>
                  </div>

                  <div className="top5-section">
                    <div className="top5-title">Top 5 Candidates</div>
                    <div className="top5">
                      {predictions.top5.map((item, index) => (
                        <div
                          key={index}
                          className={`candidate ${index === 0 ? 'top' : ''} ${selectedLabel?.label_id === item.label_id ? 'selected' : ''}`}
                          onClick={() => setSelectedLabel(item)}
                        >
                          <div className="candidate-rank">#{index + 1}</div>
                          <div className="candidate-kanji">
                            {item.kanji}
                          </div>
                          <div className="candidate-confidence">
                            {(item.confidence * 100).toFixed(2)}%
                          </div>
                          <div className="candidate-id">
                            ID: {item.label_id}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="confirmation-section">
                    <div className="confirmation-title">Confirm or correct the label</div>
                    <div className="confirmation-row">
                      <button
                        className="btn btn-confirm"
                        type="button"
                        onClick={() => setSelectedLabel(predictions.top1)}
                      >
                        ✅ Confirm Top1
                      </button>
                    </div>
                    <div className="confirmation-row">
                      <label className="control-label">
                        <span>Manual Kanji</span>
                        <input
                          type="text"
                          value={manualLabel}
                          onChange={(e) => setManualLabel(e.target.value)}
                          placeholder="Enter Kanji manually"
                          className="text-input"
                        />
                      </label>
                    </div>
                    <div className="confirmation-row">
                      <label className="control-label">
                        <span>Label ID (optional)</span>
                        <input
                          type="text"
                          value={manualLabelId}
                          onChange={(e) => setManualLabelId(e.target.value)}
                          placeholder="Optional label_id"
                          className="text-input"
                        />
                      </label>
                    </div>
                    <div className="confirmation-row">
                      <button
                        className="btn btn-predict"
                        type="button"
                        onClick={saveConfirmedDrawing}
                        disabled={saving}
                      >
                        {saving ? 'Saving...' : 'Save Confirmed Drawing'}
                      </button>
                    </div>
                    {selectedLabel && !manualLabel && (
                      <div className="selected-label">
                        Selected label: {selectedLabel.kanji} (ID: {selectedLabel.label_id})
                      </div>
                    )}
                    {manualLabel && (
                      <div className="selected-label">
                        Manual label: {manualLabel} (ID: {manualLabelId || '0'})
                      </div>
                    )}
                    {saveStatus && <div className="save-status success">{saveStatus}</div>}
                    {saveError && <div className="save-status error">{saveError}</div>}
                  </div>
                </>
              )
            ) : (
              <div className="empty-state">
                <div className="empty-icon">🔮</div>
                <p>Draw a Kanji character then click Predict</p>
                <p className="empty-hint">Use the grid lines to center your character</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;