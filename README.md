# ASR Stereo Transcription API

REST API สำหรับ Transcribe ไฟล์เสียง WAV แบบ Stereo โดยแยก Left/Right channels เป็น CALLER/AGENT และใช้ Thai ASR models (Typhoon ASR และ Pathumma-Whisper-TH-Large-V3)

## Features

- รับไฟล์ WAV Stereo และแยกเป็น 2 channels (Caller/Agent)
- รองรับ ASR models:
  - **Pathumma-Whisper-TH-Large-V3**: Thai Whisper model optimized
  - **Typhoon ASR**: Thai ASR model
- Word-level timestamps และ confidence scores
- Response format ตาม example_response.json
- รองรับทั้ง CPU และ GPU deployment
- Auto-download models จาก Hugging Face

## Prerequisites

### สำหรับ Docker Deployment
#### CPU Version
- Docker
- Docker Compose
- RAM อย่างน้อย 8GB

#### GPU Version
- Docker
- Docker Compose
- NVIDIA GPU (CUDA compatible)
- NVIDIA Docker runtime
- NVIDIA drivers installed

### สำหรับ Local Development
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- ffmpeg และ libsndfile1

## Installation

### 1. Clone หรือ Setup Project

```bash
cd asr-transcribe
```

### 2. เลือก Deployment Method

#### Option A: CPU Version (ช้ากว่า แต่ไม่ต้องการ GPU)

```bash
docker-compose -f docker-compose.cpu.yml up --build
```

#### Option B: GPU Version (เร็วกว่า ต้องการ GPU)

```bash
docker-compose -f docker-compose.gpu.yml up --build
```

### 3. รอ Models Download

ครั้งแรกที่รัน models จะ download อัตโนมัติจาก Hugging Face  
อาจใช้เวลา 5-15 นาทีขึ้นอยู่กับ internet speed

## API Usage

### API Endpoints

#### 1. Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "models_loaded": true
}
```

#### 2. Transcribe Audio

```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -F "file=@your-stereo-audio.wav" \
  -F "model=pathumma"
```

Parameters:
- `file`: Stereo WAV file
- `model`: เลือก model (`pathumma` หรือ `typhoon`)

Response Format (ตาม example_response.json):
```json
{
  "message": "Successfully processed your-stereo-audio.wav",
  "processing_status": "completed",
  "results": {
    "action": "unified_stereo_processed",
    "filename": "your-stereo-audio.wav",
    "status": "completed",
    "model_selection": {
      "chosen_model": "pathumma",
      "reasoning": "User selected model"
    },
    "transcription": {
      "segments": [
        {
          "id": 0,
          "seek": 0,
          "start": 3.296,
          "end": 4.356,
          "text": "สวัสดีครับ",
          "channel": "Caller",
          "words": [
            {
              "word": "สวัสดีครับ",
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

### Channel Mapping

- **Left Channel** = CALLER
- **Right Channel** = AGENT

## API Documentation

เมื่อ API ทำงาน สามารถเข้าถึง interactive API docs ที่:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

สามารถปรับแต่ง configuration ผ่าน environment variables:

```bash
# .env file
TEMP_PATH=./temp
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=100
HF_HOME=/root/.cache/huggingface
HF_LOCAL_FILES_ONLY=false
HF_HUB_OFFLINE=false
TRANSFORMERS_OFFLINE=false
PATHUMMA_MODEL_ID=nectec/Pathumma-whisper-th-large-v3
```

## Project Structure

```
asr-transcribe/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── services/
│   │   ├── audio_service.py    # Audio processing
│   │   ├── pathumma_service.py # Pathumma ASR
│   │   └── typhoon_service.py  # Typhoon ASR
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   └── utils/
│       ├── logger.py        # Logging
│       └── formatter.py     # Response formatting
├── temp/                    # Temporary files
├── logs/                    # Application logs
├── Dockerfile.cpu           # CPU Docker image
├── Dockerfile.gpu           # GPU Docker image
├── docker-compose.cpu.yml   # CPU deployment
├── docker-compose.gpu.yml   # GPU deployment
└── requirements.txt         # Python dependencies
```

## Development

### Run Locally (Without Docker)

#### ใช้ uv (แนะนำ - เร็วกว่า pip มาก)

```bash
# Install uv (ถ้ายังไม่มี)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e .

# หรือติดตั้งพร้อม dev dependencies
uv pip install -e ".[dev]"

# Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### ใช้ pip แบบปกติ

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from pyproject.toml
pip install -e .

# Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
# ถ้าใช้ uv
uv pip install -e ".[dev]"
pytest tests/

# ถ้าใช้ pip
pip install -e ".[dev]"
pytest tests/
```

## Troubleshooting

### Models ไม่ Download

ตรวจสอบ Hugging Face cache directory:
```bash
ls ~/.cache/huggingface
```

ถ้า run แบบ offline ให้ตั้ง:
```bash
HF_LOCAL_FILES_ONLY=true
HF_HUB_OFFLINE=true
TRANSFORMERS_OFFLINE=true
```

ถ้า model อยู่ local หรือชื่อ repo เปลี่ยน ให้ตั้ง:
```bash
PATHUMMA_MODEL_ID=nectec/Pathumma-whisper-th-large-v3
```

ลอง download manual:
```python
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
model = AutoModelForSpeechSeq2Seq.from_pretrained("nectec/Pathumma-whisper-th-large-v3")
processor = AutoProcessor.from_pretrained("nectec/Pathumma-whisper-th-large-v3")
```

### GPU ไม่ทำงาน

ตรวจสอบ NVIDIA Docker runtime:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Out of Memory

ลด model size หรือเพิ่ม RAM/VRAM  
ปรับให้ใช้ dtype ที่เบากว่าใน pathumma_service.py:
```python
torch_dtype = torch.float16  # ใช้ memory น้อยกว่า (เมื่อมี GPU)
```

## Performance

### CPU Version
- Transcription speed: ~0.1x realtime
- RAM usage: ~4-6GB
- Recommended: 8GB+ RAM

### GPU Version
- Transcription speed: ~1-2x realtime  
- VRAM usage: ~2-4GB
- Recommended: GPU with 6GB+ VRAM

## Model Information

### Pathumma-Whisper-TH-Large-V3
- Model: `nectec/Pathumma-whisper-th-large-v3`
- Source: Hugging Face
- Language: Thai
- Features: Word timestamps, confidence scores

### Typhoon ASR
- Model: `scb10x/typhoon-audio-th-v1`
- Source: Hugging Face
- Language: Thai
- Features: Thai ASR optimized

## License

MIT License

## Support

For issues and questions, please create an issue in the repository.

## TODO

- [ ] Add async processing for large files
- [ ] Add batch processing endpoint
- [ ] Add WebSocket support for real-time updates
- [ ] Add model caching strategies
- [ ] Add metrics and monitoring
