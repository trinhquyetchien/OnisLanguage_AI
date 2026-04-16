# 🎌 Kanji Recognition Demo App

A complete local web application for **handwritten Kanji character recognition** using your trained PyTorch ResNet18 model.

## 🌟 Features

✨ **Real-time Recognition** - Predictions update automatically after brief pause  
✨ **Beautiful UI** - Modern, responsive design with dual panels  
✨ **Grid Guidance** - Optional grid lines to help center characters  
✨ **Top 5 Predictions** - See confidence scores for all top candidates  
✨ **Preprocessing Preview** - View the exact 128×128 image sent to model  
✨ **Fast Local Mode** - Everything runs on your machine, no cloud needed  
✨ **API Testing** - Swagger UI for testing backend independently  
✨ **Production Ready** - Error handling, CORS, proper logging  

## 📋 Prerequisites

- Python 3.8+ (for backend)
- Node.js 16+ (for frontend)
- Your trained model files:
  - `best_etl9g_resnet18.pth`
  - `label_map.csv`

## 🏗️ Project Structure

```
kanji-recognition-demo/
├── backend/
│   ├── app.py                          # FastAPI server
│   ├── requirements.txt                # Python dependencies
│   └── models/                         # Place model files here
│       ├── best_etl9g_resnet18.pth     # (Copy from ETL9G/)
│       └── label_map.csv               # (Copy from ETL9G/)
│
├── frontend/
│   ├── index.html                      # HTML entry point
│   ├── vite.config.js                  # Vite configuration
│   ├── package.json                    # Node dependencies
│   └── src/
│       ├── main.jsx                    # React entry point
│       ├── App.jsx                     # Main component
│       └── App.css                     # Styling
│
├── README.md                           # This file
├── QUICK_START.md                      # Quick usage guide
├── UI_IMPROVEMENTS.md                  # UI/UX features
└── API_TESTING.md                      # Backend testing guide
```

## 🚀 Installation

### 1. Prepare Model Files

Copy your trained model to backend:
```bash
cp /path/to/best_etl9g_resnet18.pth kanji-recognition-demo/backend/models/
cp /path/to/label_map.csv kanji-recognition-demo/backend/models/
```

### 2. Backend Setup

```bash
cd kanji-recognition-demo/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

## ▶️ Running the App

### Terminal 1: Start Backend

```bash
cd backend
venv\Scripts\activate  # Windows
python app.py
```

Output should show:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

Output should show:
```
  ➜  Local:   http://127.0.0.1:5173/
  ➜  press h to show help
```

### 3. Open in Browser

- **Frontend**: http://127.0.0.1:5173
- **API Docs**: http://127.0.0.1:8000/docs
- **Backend Health**: http://127.0.0.1:8000/

## 📖 Usage

1. **Open** frontend at http://127.0.0.1:5173
2. **Enable Grid** (optional) - Toggle "Show Grid Lines" checkbox
3. **Draw** a single Kanji character in the canvas
4. **Wait** ~500ms - System automatically sends to model
5. **View Results**:
   - **Top Prediction**: Large purple card with main result
   - **Top 5**: Grid of 5 candidate characters
   - **Preview**: Processed 128×128 image
6. **Refine** - Use eraser or clear to adjust

## 📐 Writing Tips

| Tip | Benefit |
|-----|---------|
| Center on red cross | Better model accuracy |
| Write large | Preserves character details |
| Use smooth strokes | Smooth features help model |
| Keep consistent thickness | Even strokes = better recognition |
| Complete all strokes | Incomplete characters get lower confidence |
| Use grid as guide | Maintains proper proportions |

## 🔧 Configuration

### Backend (app.py)

```python
# Model paths
MODEL_PATH = "models/best_etl9g_resnet18.pth"
LABEL_MAP_PATH = "models/label_map.csv"

# API settings
HOST = "127.0.0.1"
PORT = 8000
RELOAD = True  # Hot reload on file changes

# CORS settings
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# Model settings
DEVICE = "cpu"  # Change to "cuda" for GPU
INPUT_SIZE = 128
NUM_CLASSES = 3036
DEBOUNCE_MS = 500
```

### Frontend (vite.config.js)

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1'
  }
})
```

## 🔌 API Reference

### POST /predict

Send a canvas image for Kanji recognition.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (PNG image)

**Response (200 OK):**
```json
{
  "top1": {
    "label_id": 123,
    "kanji": "漢",
    "confidence": 0.9847
  },
  "top5": [
    {"label_id": 123, "kanji": "漢", "confidence": 0.9847},
    {"label_id": 555, "kanji": "字", "confidence": 0.0089},
    ...
  ]
}
```

**Errors:**
- `400`: Invalid image or empty canvas
- `500`: Model not loaded

### GET /

Health check endpoint.

**Response:**
```json
{"message": "Kanji Recognition API is running"}
```

## 🧪 Testing

### Swagger UI
Visit http://127.0.0.1:8000/docs to test API interactively.

### Command Line Test
```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -F "file=@path/to/image.png"
```

### Python Test
```python
import requests

with open("path/to/image.png", "rb") as f:
    response = requests.post(
        "http://127.0.0.1:8000/predict",
        files={"file": f}
    )
    print(response.json())
```

See [API_TESTING.md](API_TESTING.md) for detailed testing guide.

## 🎯 Understanding Predictions

**Confidence Score**
- 0.0 - 0.50: Low confidence (uncertain)
- 0.50 - 0.80: Medium confidence (likely)
- 0.80 - 1.00: High confidence (very likely)

**Top 1 vs Top 5**
- If top 1 is wrong, correct answer usually in top 5
- Compare confidence scores to understand model uncertainty
- Very low top 1 with scattered top 5 = difficult character

## 📊 How It Works

```
User Input → Canvas
    ↓
Debounce (500ms pause)
    ↓
Crop bounding box
    ↓
Pad to square
    ↓
Resize to 128×128
    ↓
Normalize (mean=0.5, std=0.5)
    ↓
ResNet18 Inference (3036 classes)
    ↓
Softmax (probabilities)
    ↓
Get top 1 & top 5
    ↓
Display Results
```

## 🛠️ Troubleshooting

### Backend Issues

**Model not found:**
```
FileNotFoundError: Model file not found at models/best_etl9g_resnet18.pth
```
→ Copy model files to `backend/models/`

**Port already in use:**
```
Address already in use
```
→ Kill process on port 8000: `lsof -ti:8000 | xargs kill -9`

**Import errors:**
```
ModuleNotFoundError: No module named 'torch'
```
→ Activate venv and run `pip install -r requirements.txt`

### Frontend Issues

**Cannot connect to backend:**
```
CORS error or fetch error
```
→ Check backend is running at http://127.0.0.1:8000

**Dependencies missing:**
```
Error: Cannot find module
```
→ Run `npm install` in frontend directory

**Port 5173 in use:**
```
EADDRINUSE: address already in use :::5173
```
→ Kill process on port 5173 or change port in vite.config.js

## 📱 Browser Compatibility

| Browser | Status |
|---------|--------|
| Chrome/Chromium | ✅ Full support |
| Firefox | ✅ Full support |
| Safari | ✅ Full support |
| Edge | ✅ Full support |
| Mobile Chrome | ✅ Full support |
| Mobile Safari | ✅ Full support |

## 🚀 Performance

| Metric | Value |
|--------|-------|
| Inference Time | 50-200ms (CPU) |
| Debounce Delay | 500ms |
| Model Load Time | 2-5s |
| Memory Usage | ~500MB |
| Canvas Resolution | 400×400px |
| Model Input Size | 128×128px |

## 💡 Enhancement Ideas

**UI/UX**
- [ ] Dark mode toggle
- [ ] Stroke animation
- [ ] Undo/redo functionality
- [ ] Favorite predictions history

**Features**
- [ ] Stroke order visualization
- [ ] Character decomposition
- [ ] Pronunciation/meanings
- [ ] Similar character suggestions

**Performance**
- [ ] Model quantization
- [ ] Batch processing
- [ ] WebGL rendering
- [ ] Service worker for offline

**Accessibility**
- [ ] Keyboard shortcuts
- [ ] Screen reader support
- [ ] High contrast mode
- [ ] Text-to-speech results

## 📚 Additional Resources

- [QUICK_START.md](QUICK_START.md) - Quick usage guide
- [UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md) - Detailed UI features
- [API_TESTING.md](API_TESTING.md) - Testing guide

## 📝 Model Information

- **Architecture**: ResNet18
- **Input**: 1 channel (grayscale), 128×128px
- **Output**: 3036 Kanji classes
- **Normalization**: mean=[0.5], std=[0.5]
- **Training Dataset**: ETL9G
- **File**: best_etl9g_resnet18.pth

## 🤝 Contributing

Issues or improvements? Feel free to modify and experiment!

## 📄 License

This demo is for personal/educational use.

## ✨ Enjoy!

Draw some Kanji and watch the model recognize in real-time! 🎨✨

---

**Questions?** Check the documentation files or test the API at http://127.0.0.1:8000/docs
