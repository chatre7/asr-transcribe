# ASR Stereo Transcription API - Implementation Plan

## Project Overview
สร้าง REST API สำหรับ Transcribe ไฟล์ WAV แบบ Stereo โดยแยก Left/Right channels เป็น CALLER/AGENT และใช้ Thai ASR models (Typhoon ASR และ Pathumma-Whisper-TH-Large-V3)

## Requirements Summary
- **Input**: WAV file (Stereo)
- **Audio Processing**: Split Left channel = CALLER, Right channel = AGENT
- **ASR Models**: User selects per request (typhoon หรือ pathumma)
- **Output**: JSON format ตาม example_response.json
- **Deployment**: Docker รองรับทั้ง CPU และ GPU
- **Features**: Basic features only (no diarization, no async queue)

## Project Structure
```
asr-transcribe/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings & environment variables
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # API endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_service.py       # Stereo split logic
│   │   ├── typhoon_service.py     # Typhoon ASR wrapper
│   │   └── pathumma_service.py    # Pathumma-Whisper wrapper
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic request/response models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging configuration
│       └── formatter.py           # Response formatter
├── models/                        # Model weights directory (gitignored)
│   ├── typhoon/
│   └── pathumma/
├── temp/                          # Temporary audio files
├── tests/
│   ├── __init__.py
│   ├── test_audio_service.py
│   └── test_api.py
├── Dockerfile.cpu                 # CPU-only Docker image
├── Dockerfile.gpu                 # GPU-enabled Docker image
├── docker-compose.cpu.yml
├── docker-compose.gpu.yml
├── requirements.txt               # Python dependencies (CPU)
├── requirements-gpu.txt           # Python dependencies (GPU with CUDA)
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

## Implementation Steps

### Phase 1: Project Setup & Core Structure
1. **Create project directory structure**
   - สร้าง folders ทั้งหมดตาม structure ข้างบน
   - สร้าง `__init__.py` ในทุก Python packages

2. **Setup configuration files**
   - **config.py**: Settings class สำหรับ model paths, temp directory, logging level
   - **.env.example**: Template สำหรับ environment variables
   - **.gitignore**: Ignore models/, temp/, __pycache__, .env
   - **.dockerignore**: Ignore unnecessary files in Docker build

### Phase 2: Audio Processing Module
3. **Implement audio_service.py**
   - ฟังก์ชัน `load_stereo_wav(file_path)`: Load WAV file และตรวจสอบ stereo
   - ฟังก์ชัน `split_channels(audio)`: แยก Left (CALLER) และ Right (AGENT) channels
   - ฟังก์ชัน `save_mono_channel(channel_data, output_path)`: Save แต่ละ channel เป็น mono WAV
   - **Dependencies**: pydub, soundfile, numpy

### Phase 3: ASR Model Integration
4. **Implement pathumma_service.py**
   - Class `PathummaASR`:
     - `__init__()`: Load pathumma-whisper-th-large-v3 model
     - `transcribe(audio_path)`: Transcribe audio และคืน segments พร้อม word-level timestamps
   - Use `faster-whisper` สำหรับ performance
   - Return format: list of segments with words, timestamps, confidence

5. **Implement typhoon_service.py**
   - Class `TyphoonASR`:
     - `__init__()`: Load Typhoon ASR model
     - `transcribe(audio_path)`: Transcribe audio
   - ต้องตรวจสอบ Typhoon ASR API/SDK documentation
   - Return format เดียวกับ PathummaASR

### Phase 4: Response Formatter
6. **Implement formatter.py**
   - ฟังก์ชัน `format_transcription_response()`:
     - รับ filename, model_name, caller_segments, agent_segments
     - รวม segments จาก 2 channels และเรียงตาม timestamp
     - Format ตาม example_response.json structure:
       ```json
       {
         "message": "Successfully processed {filename}",
         "processing_status": "completed",
         "results": {
           "action": "unified_stereo_processed",
           "filename": "{filename}",
           "status": "completed",
           "model_selection": {
             "chosen_model": "{model}",
             "reasoning": "User selected model"
           },
           "transcription": {
             "segments": [...]
           }
         }
       }
       ```

### Phase 5: API Development
7. **Implement schemas.py**
   - `TranscribeRequest`: model selection (typhoon/pathumma)
   - `TranscribeResponse`: ตาม example_response.json
   - `ErrorResponse`: error message format

8. **Implement routes.py**
   - `POST /api/v1/transcribe`:
     - Accept file upload (WAV only)
     - Accept model parameter (typhoon/pathumma)
     - Validate file format (stereo WAV)
     - Process workflow:
       1. Save uploaded file to temp/
       2. Split stereo to 2 mono files
       3. Transcribe Left channel → CALLER segments
       4. Transcribe Right channel → AGENT segments
       5. Format response
       6. Cleanup temp files
     - Return JSON response
   - `GET /health`: Health check endpoint

9. **Implement main.py**
   - FastAPI application setup
   - CORS middleware
   - Exception handlers
   - Startup event: Load models
   - Include routers

### Phase 6: Utilities
10. **Implement logger.py**
    - Configure structured logging
    - Log levels: DEBUG, INFO, WARNING, ERROR
    - Log to console และ file (logs/app.log)

11. **Implement error handling**
    - Custom exceptions: InvalidAudioFormat, ModelNotFound, TranscriptionError
    - Global exception handler in main.py
    - Return proper HTTP status codes

### Phase 7: Docker Configuration
12. **Create requirements.txt (CPU version)**
    ```
    fastapi==0.104.1
    uvicorn[standard]==0.24.0
    python-multipart==0.0.6
    pydantic==2.5.0
    pydantic-settings==2.1.0

    # Audio processing
    pydub==0.25.1
    soundfile==0.12.1
    numpy==1.24.3

    # ASR models
    transformers==4.35.2
    torch==2.1.1
    faster-whisper==0.10.0

    # Thai NLP (optional)
    pythainlp==4.0.2
    ```

13. **Create requirements-gpu.txt**
    - เหมือน requirements.txt แต่ใช้ torch with CUDA:
    ```
    torch==2.1.1+cu118
    ```

14. **Create Dockerfile.cpu**
    ```dockerfile
    FROM python:3.10-slim

    WORKDIR /app

    # Install system dependencies
    RUN apt-get update && apt-get install -y \
        ffmpeg \
        libsndfile1 \
        && rm -rf /var/lib/apt/lists/*

    # Copy requirements and install
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy application code
    COPY app/ ./app/
    COPY example_response.json .

    # Create directories
    RUN mkdir -p models temp logs

    EXPOSE 8000

    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

15. **Create Dockerfile.gpu**
    ```dockerfile
    FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

    # Install Python 3.10
    RUN apt-get update && apt-get install -y \
        python3.10 \
        python3-pip \
        ffmpeg \
        libsndfile1 \
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /app

    # Copy requirements and install
    COPY requirements-gpu.txt .
    RUN pip3 install --no-cache-dir -r requirements-gpu.txt

    # Copy application code
    COPY app/ ./app/
    COPY example_response.json .

    # Create directories
    RUN mkdir -p models temp logs

    EXPOSE 8000

    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

16. **Create docker-compose.cpu.yml**
    ```yaml
    version: '3.8'

    services:
      asr-api-cpu:
        build:
          context: .
          dockerfile: Dockerfile.cpu
        container_name: asr-transcribe-cpu
        ports:
          - "8000:8000"
        volumes:
          - ./models:/app/models
          - ./temp:/app/temp
          - ./logs:/app/logs
        environment:
          - MODEL_PATH=/app/models
          - TEMP_PATH=/app/temp
          - LOG_LEVEL=INFO
        restart: unless-stopped
    ```

17. **Create docker-compose.gpu.yml**
    ```yaml
    version: '3.8'

    services:
      asr-api-gpu:
        build:
          context: .
          dockerfile: Dockerfile.gpu
        container_name: asr-transcribe-gpu
        ports:
          - "8000:8000"
        volumes:
          - ./models:/app/models
          - ./temp:/app/temp
          - ./logs:/app/logs
        environment:
          - MODEL_PATH=/app/models
          - TEMP_PATH=/app/temp
          - LOG_LEVEL=INFO
        deploy:
          resources:
            reservations:
              devices:
                - driver: nvidia
                  count: 1
                  capabilities: [gpu]
        restart: unless-stopped
    ```

### Phase 8: Documentation & Testing
18. **Create README.md**
    - Project description
    - Prerequisites (Docker, GPU drivers for GPU version)
    - Model download instructions
    - Installation steps:
      - CPU version: `docker-compose -f docker-compose.cpu.yml up --build`
      - GPU version: `docker-compose -f docker-compose.gpu.yml up --build`
    - API usage examples with curl
    - Configuration options
    - Troubleshooting

19. **Create basic tests**
    - `test_audio_service.py`: Test stereo split functionality
    - `test_api.py`: Test API endpoints with sample WAV file

## Critical Files to Create/Modify

### New Files (ทั้งหมด)
1. `app/main.py` - FastAPI application
2. `app/config.py` - Configuration settings
3. `app/api/routes.py` - API endpoints
4. `app/services/audio_service.py` - Audio processing
5. `app/services/pathumma_service.py` - Pathumma ASR
6. `app/services/typhoon_service.py` - Typhoon ASR
7. `app/models/schemas.py` - Pydantic models
8. `app/utils/formatter.py` - Response formatter
9. `app/utils/logger.py` - Logging setup
10. `Dockerfile.cpu` - CPU Docker image
11. `Dockerfile.gpu` - GPU Docker image
12. `docker-compose.cpu.yml` - CPU deployment
13. `docker-compose.gpu.yml` - GPU deployment
14. `requirements.txt` - Python dependencies (CPU)
15. `requirements-gpu.txt` - Python dependencies (GPU)
16. `.env.example` - Environment template
17. `.gitignore` - Git ignore rules
18. `.dockerignore` - Docker ignore rules
19. `README.md` - Documentation

## Technical Decisions

### Audio Processing
- **Library**: soundfile + numpy (lightweight, reliable)
- **Format**: Validate input is WAV stereo, resample if needed to 16kHz
- **Channel Mapping**: Left channel → CALLER, Right channel → AGENT (ตาม user requirement)

### ASR Models
- **Pathumma-Whisper**: Use faster-whisper library สำหรับ optimized inference
  - Model: `pathumma/whisper-th-large-v3` from Hugging Face
  - Auto-download on first use via transformers cache
- **Typhoon ASR**: Use from Hugging Face Hub
  - Model: `typhoon-audio/typhoon-asr` (ต้องตรวจสอบ exact model name)
  - Auto-download on first use via transformers cache
- **Model Loading**: Load models on startup (in memory) สำหรับ fast inference
- **Model Cache**: Use Hugging Face cache (~/.cache/huggingface) mounted to container
- **Fallback**: ถ้า user ไม่ระบุ model, ใช้ pathumma เป็น default

### API Design
- **Framework**: FastAPI (fast, async, auto docs)
- **File Upload**: Use UploadFile with size limit (max 100MB)
- **Model Selection**: Required parameter in request (typhoon/pathumma)
- **Response**: Follow example_response.json structure exactly
- **Error Handling**: Return appropriate HTTP status codes with error details
- **Authentication**: None (open API ตาม user requirement)
- **Rate Limiting**: None (basic version)

### Docker Strategy
- **Two Images**: แยก CPU และ GPU builds ชัดเจน
- **Base Images**:
  - CPU: python:3.10-slim (lightweight)
  - GPU: nvidia/cuda:11.8.0-cudnn8-runtime (CUDA support)
- **Volume Mounts**:
  - ~/.cache/huggingface → /root/.cache/huggingface (model cache)
  - ./temp → /app/temp (temporary files)
  - ./logs → /app/logs (application logs)
- **Model Downloads**: Auto-download on first use from Hugging Face

## Potential Challenges & Solutions

### 1. Typhoon ASR Model Name
**Challenge**: ต้องหา exact model name บน Hugging Face
**Solution**:
- ค้นหา "typhoon asr" บน huggingface.co
- ถ้าไม่เจอ ใช้ alternative Thai ASR model หรือ implement placeholder
- ตรวจสอบ model card สำหรับ usage instructions

### 2. Model Size & Memory
**Challenge**: Models ใหญ่ อาจเกิน container memory
**Solution**:
- ใช้ faster-whisper (quantized models)
- Set Docker memory limits
- Implement model lazy loading ถ้าจำเป็น

### 3. Word-level Timestamps
**Challenge**: ไม่ใช่ทุก ASR model ที่ให้ word-level timestamps
**Solution**:
- Whisper models รองรับ word timestamps (use `word_timestamps=True`)
- Typhoon อาจต้อง implement manual alignment

### 4. Performance
**Challenge**: Transcription อาจช้า especially on CPU
**Solution**:
- Use faster-whisper (optimized)
- GPU version สำหรับ production
- Consider async processing in future (out of scope for basic version)

## Next Steps After Implementation
1. Download model weights (Pathumma-Whisper และ Typhoon)
2. Test with sample stereo WAV files
3. Benchmark CPU vs GPU performance
4. Add monitoring/metrics (optional)
5. Consider adding features:
   - Batch processing
   - Async processing with job queue
   - WebSocket for real-time updates
   - Model caching strategies

## Estimated Task Breakdown
- Project setup: 5%
- Audio processing: 10%
- ASR integration: 30%
- Response formatting: 10%
- API development: 20%
- Docker configuration: 15%
- Documentation & testing: 10%
