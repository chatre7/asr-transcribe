# Development Notes - ASR Transcribe API

## Docker Build Issues & Solutions

### ปัญหาที่เกิดขึ้นระหว่าง Development และวิธีแก้ไข

#### 1. Hatchling Package Configuration Error
**ปัญหา:**
```
ValueError: Unable to determine which files to ship inside the wheel
The most likely cause of this is that there is no directory that matches the name of your project (asr_transcribe).
```

**สาเหตุ:**
- โปรเจกต์ชื่อ `asr-transcribe` แต่โค้ดอยู่ใน directory `app/` ไม่ใช่ `asr_transcribe/`
- Hatchling build backend ไม่รู้ว่าจะ package ไฟล์อะไรเข้า wheel

**วิธีแก้:**
เพิ่มใน `pyproject.toml`:
```toml
[tool.hatch.build.targets.wheel]
packages = ["app"]
```

---

#### 2. README.md Missing in Docker Build Context
**ปัญหา:**
```
ERROR: Readme file does not exist: README.md
```

**สาเหตุ:**
- `.dockerignore` มีการ exclude `README.md`
- แต่ `pyproject.toml` ระบุ `readme = "README.md"` ซึ่ง hatchling ต้องการไฟล์นี้

**วิธีแก้:**
แก้ไข `.dockerignore` ให้อนุญาต README.md:
```
# Documentation (exclude all except README.md which is needed for pyproject.toml)
# README.md is required by hatchling build backend
*.md
!README.md
```

---

#### 3. PyAV Compilation Error with FFmpeg 6.x
**ปัญหา:**
```
src/av/option.c:6859:52: error: 'AV_OPT_TYPE_CHANNEL_LAYOUT' undeclared
(first use in this function); did you mean 'AV_OPT_TYPE_CHLAYOUT'?
```

**สาเหตุ:**
- `faster-whisper==0.10.0` ต้องการ `av==11.0.0`
- `av==11.0.0` ใช้ API เก่าของ FFmpeg (`AV_OPT_TYPE_CHANNEL_LAYOUT`)
- FFmpeg 6.x เปลี่ยนเป็น `AV_OPT_TYPE_CHLAYOUT`

**วิธีแก้:**
อัพเกรด faster-whisper ใน `pyproject.toml`:
```toml
"faster-whisper==1.1.0",  # Updated to newer version that supports av>=12
```

และ pre-install av ใน Dockerfile:
```dockerfile
RUN uv pip install --system --no-cache av>=12.0.0
```

---

#### 4. Missing C/C++ Compiler
**ปัญหา:**
```
error: command 'gcc' failed: No such file or directory
```

**สาเหตุ:**
- ขาด GCC และ build tools สำหรับ compile Python packages ที่มี C extensions

**วิธีแก้:**
เพิ่มใน Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
```

---

#### 5. Missing pkg-config and FFmpeg Development Libraries
**ปัญหา:**
```
pkg-config is required for building PyAV
```

**สาเหตุ:**
- PyAV package ต้องการ pkg-config และ FFmpeg development headers เพื่อ compile

**วิธีแก้:**
เพิ่มใน Dockerfile:
```dockerfile
pkg-config \
libavcodec-dev \
libavformat-dev \
libavutil-dev \
libavdevice-dev \
libavfilter-dev \
libswscale-dev \
libswresample-dev \
```

---

## สรุป Dockerfile Pattern ที่ใช้งานได้

### CPU Version (Dockerfile.cpu)
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 1. Install system dependencies (including build tools and FFmpeg dev libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    curl \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 3. Copy project files (including README.md required by hatchling)
COPY pyproject.toml ./
COPY README.md ./
COPY app/ ./app/

# 4. Pre-install av to avoid compilation issues
RUN uv pip install --system --no-cache av>=12.0.0

# 5. Install all other dependencies
RUN uv pip install --system --no-cache -e .

# 6. Create runtime directories
RUN mkdir -p temp logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### GPU Version (Dockerfile.gpu)
เหมือน CPU version แต่:
- ใช้ base image: `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`
- ต้องติดตั้ง Python 3.10 เอง
- ใช้ PyTorch CUDA index: `--extra-index-url https://download.pytorch.org/whl/cu118`

---

## Dependencies ที่สำคัญ

### pyproject.toml Configuration
```toml
[project]
name = "asr-transcribe"
version = "1.0.0"
readme = "README.md"  # Required by hatchling

dependencies = [
    "faster-whisper==1.1.0",  # MUST be 1.1.0+ to support av>=12.0.0
    # ... other dependencies
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]  # Tell hatchling to package app/ directory
```

---

## การ Build และ Deploy

### Build CPU Version
```bash
docker-compose -f docker-compose.cpu.yml up --build
```

### Build GPU Version (requires NVIDIA Docker)
```bash
docker-compose -f docker-compose.gpu.yml up --build
```

### ตรวจสอบ API
```bash
# Health check
curl http://localhost:8000/health

# Transcribe audio
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@audio.wav" \
  -F "model=pathumma"
```

---

## สิ่งที่ต้องระวัง

1. **อย่าลบ README.md** - hatchling ต้องการไฟล์นี้
2. **faster-whisper version** - ต้องใช้ 1.1.0+ เพื่อรองรับ av>=12.0.0
3. **Pre-install av** - ต้อง install av ก่อน dependencies อื่นเพื่อหลีกเลี่ยงการ compile av==11.0.0
4. **FFmpeg dev libraries** - จำเป็นสำหรับ compile PyAV
5. **.dockerignore pattern** - ใช้ `*.md` และ `!README.md` เพื่อ exclude md files อื่นแต่เก็บ README.md

---

## Package Versions ที่ใช้งานได้

| Package | Version | Note |
|---------|---------|------|
| faster-whisper | 1.1.0 | รองรับ av>=12.0.0 |
| av | 16.0.1 | ติดตั้งจาก pre-built wheel |
| torch | 2.1.1 | CPU: torch, GPU: torch+cu118 |
| transformers | 4.35.2 | |
| FastAPI | 0.104.1 | |
| uvicorn | 0.24.0 | |

---

## Model Information

### Pathumma Whisper
- Model ID: `nectec/Pathumma-whisper-th-large-v3`
- ใช้ faster-whisper library
- รองรับ word-level timestamps

### Typhoon ASR
- Model ID: `scb10x/typhoon-asr-realtime` ✅ (ใช้ตัวนี้)
- ~~Model ID: `scb10x/typhoon-audio-th-v1`~~ ❌ (model นี้ไม่มีอยู่จริง)
- ใช้ transformers pipeline
- Trained on 10,000 hours of Thai audio
- Real-time processing speed (4097x realtime)
- CER: 0.0984
- Hugging Face: https://huggingface.co/scb10x/typhoon-asr-realtime

**⚠️ สำคัญ**: ต้องใช้ `scb10x/typhoon-asr-realtime` เท่านั้น อย่าใช้ model name เดิม (`scb10x/typhoon-audio-th-v1`) เพราะจะเกิด error "not a valid model identifier"

---

## API Endpoints

### POST /api/v1/transcribe
**Request:**
- `file`: WAV file (stereo)
- `model`: "typhoon" หรือ "pathumma"

**Response:**
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
      "segments": [
        {
          "id": 0,
          "channel": "Caller",  // Left channel
          "start": 0.0,
          "end": 2.5,
          "text": "...",
          "words": [...]
        },
        {
          "id": 1,
          "channel": "Agent",  // Right channel
          "start": 2.6,
          "end": 5.0,
          "text": "...",
          "words": [...]
        }
      ]
    }
  }
}
```

### GET /health
**Response:**
```json
{
  "status": "healthy",
  "models_loaded": false
}
```

---

## Troubleshooting

### ถ้า Docker build fail
1. ตรวจสอบว่า README.md ถูก copy เข้า build context (ดูใน .dockerignore)
2. ตรวจสอบว่า pyproject.toml มี `[tool.hatch.build.targets.wheel]`
3. ตรวจสอบว่า faster-whisper version เป็น 1.1.0+
4. Clear Docker build cache: `docker builder prune -a`

### ถ้า API ไม่ทำงาน
1. ตรวจสอบ logs: `docker logs asr-transcribe-cpu`
2. ตรวจสอบว่า models โหลดสำเร็จ
3. ตรวจสอบว่า temp/ และ logs/ directories ถูกสร้าง

### ถ้า Typhoon model ไม่โหลดได้
**Error:** `scb10x/typhoon-audio-th-v1 is not a local folder and is not a valid model identifier`

**สาเหตุ:** ใช้ model identifier ผิด

**แก้ไข:**
1. เปิดไฟล์ `app/services/typhoon_service.py`
2. แก้บรรทัดที่ 11 จาก:
   ```python
   def __init__(self, model_name: str = "scb10x/typhoon-audio-th-v1"):
   ```
   เป็น:
   ```python
   def __init__(self, model_name: str = "scb10x/typhoon-asr-realtime"):
   ```
3. Rebuild Docker: `docker-compose -f docker-compose.cpu.yml up --build`

---

**Last Updated:** 2026-01-04
**Status:** ✅ Docker build สำเร็จ, API ทำงานได้
