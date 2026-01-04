# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ASR (Automatic Speech Recognition) transcription service for Thai language audio processing. The service accepts stereo WAV files, splits them into separate channels (Left=Caller, Right=Agent), transcribes each channel using Thai ASR models, and returns unified JSON results with word-level timestamps and channel labels.

**Tech Stack**: FastAPI, faster-whisper (Pathumma model), HuggingFace Transformers (Typhoon model), PyTorch

## Common Commands

### Running the Application

**Development server (local):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production server:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Docker (CPU):**
```bash
docker build -f Dockerfile.cpu -t asr-transcribe:cpu .
docker run -p 8000:8000 -v $(pwd)/temp:/app/temp -v $(pwd)/logs:/app/logs asr-transcribe:cpu
```

**Docker (GPU):**
```bash
docker build -f Dockerfile.gpu -t asr-transcribe:gpu .
docker run --gpus all -p 8000:8000 -v $(pwd)/temp:/app/temp -v $(pwd)/logs:/app/logs asr-transcribe:gpu
```

### Dependencies

**CPU version:**
```bash
pip install -r requirements.txt
```

**GPU version (CUDA 11.8):**
```bash
pip install -r requirements-gpu.txt
```

### API Documentation

Once running, access:
- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Architecture

### Request Flow

```
POST /api/v1/transcribe
    ↓
[1] Upload stereo WAV file + model selection (form data)
    ↓
[2] AudioService splits stereo → Left (Caller) + Right (Agent) channels
    ↓
[3] Save temporary mono WAV files to temp/
    ↓
[4] ASR Model Selection (Pathumma or Typhoon)
    ↓
[5] Parallel transcription: transcribe(caller_audio) + transcribe(agent_audio)
    ↓
[6] Formatter merges results, adds channel labels, sorts by timestamp
    ↓
[7] Return unified JSON response (matches example_response.json structure)
    ↓
[8] Cleanup temporary files
```

### Module Architecture

**app/main.py** - FastAPI application entry point
- CORS middleware configured (allow all origins)
- Global exception handler logs errors and returns 500
- Startup event logs configuration
- Includes API router from routes.py

**app/api/routes.py** - API endpoints
- `POST /api/v1/transcribe` - Main transcription endpoint (file upload + model selection)
- `GET /health` - Health check (returns model loaded status)
- Route validates: file type (.wav), file size (max 100MB), model selection (typhoon/pathumma)
- Always cleans up temp files in finally block

**app/services/audio_service.py** - Stereo channel processing
- `AudioService.load_wav_file()` - Validates stereo format (must have 2 channels)
- `AudioService.split_stereo_channels()` - Separates left/right channels
- `AudioService.save_mono_channel()` - Writes mono WAV files to temp/
- `AudioService.process_stereo_file()` - Complete workflow: load → split → save
- `AudioService.cleanup_temp_files()` - Removes temporary files

**app/services/pathumma_service.py** - Pathumma-Whisper ASR (default)
- Model: `pathumma/whisper-th-large-v3` (faster-whisper)
- Lazy loads on first transcription call
- Returns word-level timestamps with actual confidence scores from model
- Uses VAD filter, beam_size=5
- Global instance: `pathumma_asr`

**app/services/typhoon_service.py** - Typhoon ASR
- Model: `scb10x/typhoon-audio-th-v1` (HuggingFace Transformers)
- Lazy loads on first transcription call
- Auto-detects CUDA/CPU device
- Groups words into segments using 2s time gaps or 200 char length thresholds
- Returns default confidence 0.95 (model doesn't provide confidence)
- Global instance: `typhoon_asr`

**app/utils/formatter.py** - Response formatting
- `format_transcription_response()` - Merges caller/agent results
- Adds channel labels ("Caller"/"Agent") to all segments and words
- Sorts segments chronologically by start timestamp
- Re-indexes segments sequentially
- Output structure matches `example_response.json` schema

**app/utils/logger.py** - Centralized logging
- Dual output: console + file (logs/app.log)
- Log level from settings (default: INFO)
- Global instance: `logger`

**app/models/schemas.py** - Pydantic validation models
- `TranscribeResponse` - Top-level API response
- `Segment`, `Word` - Transcription data structures
- `HealthResponse`, `ErrorResponse` - Endpoint responses

**app/config.py** - Configuration management
- `Settings` class uses pydantic-settings
- Reads from .env file (use .env.example as template)
- Key settings: temp_path, max_file_size, supported_models, default_model, hf_home
- Global instance: `settings`

### Key Design Patterns

**Lazy Model Loading**: ASR models are only loaded into memory on first transcription request, not at startup. Check `model is not None` or `pipe is not None` to see if loaded.

**Channel Labeling**: All transcription segments and words include a `channel` field ("Caller" or "Agent"). Left audio channel = Caller, Right audio channel = Agent.

**Temporary File Management**: Each request generates unique temp files (UUID-based). Always cleaned up in route's finally block, even on errors.

**Global Singletons**: Services use module-level instances (pathumma_asr, typhoon_asr, settings, logger) to share state across requests.

## Configuration

Copy `.env.example` to `.env` and configure:

**Critical settings:**
- `HF_HOME` - HuggingFace model cache directory (models are ~1-3GB each)
- `TEMP_PATH` - Temporary audio storage (ensure sufficient disk space)
- `DEFAULT_MODEL` - "pathumma" (recommended, more accurate) or "typhoon" (faster)
- `MAX_FILE_SIZE_MB` - Upload size limit (default: 100MB)

**Model differences:**
- **Pathumma**: Higher accuracy, slower, returns real confidence scores, uses faster-whisper
- **Typhoon**: Faster inference, uses Transformers pipeline, fixed confidence 0.95

## Audio Requirements

- **Format**: WAV files only
- **Channels**: Must be stereo (2 channels)
- **Sample Rate**: 16kHz recommended (configurable in settings)
- **Size**: Default limit 100MB (configurable)
- **Channel Assignment**: Left=Caller, Right=Agent (hard-coded convention)

## Response Format

The API returns JSON matching `example_response.json` structure:
```json
{
  "message": "Successfully processed {filename}",
  "processing_status": "completed",
  "results": {
    "action": "unified_stereo_processed",
    "filename": "example.wav",
    "status": "completed",
    "model_selection": {
      "chosen_model": "pathumma",
      "reasoning": "Model selection skipped - using default"
    },
    "transcription": {
      "segments": [
        {
          "id": 0,
          "seek": 0,
          "start": 3.296,
          "end": 4.356,
          "text": "...",
          "channel": "Caller",
          "words": [
            {
              "word": "...",
              "start": 3.296,
              "end": 4.356,
              "confidence": 0.95,
              "channel": "Caller"
            }
          ]
        }
      ]
    }
  }
}
```

Segments are sorted by timestamp and include both Caller and Agent utterances in chronological order.

## Testing

Currently no test suite exists. When adding tests:
- Use pytest framework
- Mock model inference (models are large and slow)
- Use small test audio fixtures (< 1 second)
- Test key paths: channel splitting, model selection, response formatting, error handling
