# OnisUnifiedAI - Japanese Language Learning Suite

A unified platform consolidating multiple AI-powered tools for Japanese language learners.

## Features
- **OCR (Image to Text)**: Extract Japanese text from images using PaddleOCR.
- **Transcription**: Convert audio and video files into timestamped Japanese transcripts using OpenAI Whisper.
- **Kanji Recognition**: Recognize handwritten Kanji characters using a custom ResNet18 model.

## Architecture
- **Backend**: FastAPI (Python) implementing Service and Facade patterns for AI inference.
- **Frontend**: React (TypeScript) SPA with Vite and TailwindCSS, featuring a unified dashboard.
- **Client-Server**: Communication via REST API with a shared storage system for media.

## Project Structure
- `backend/`: Unified Python backend with modular services.
- `frontend/`: Integrated React application with feature-based routing.
- `models/`: Shared storage for machine learning weights and metadata.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- CUDA (optional, for GPU acceleration)

### Backend Setup
1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## Development
This project was consolidated from several experimental demos:
- `audio-transcribe-demo`
- `kanji-recognition-demo`
- `ImageToTextAI`
- `whisperAI`
