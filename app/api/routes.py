"""API routes"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.config import settings
from app.services.audio_service import AudioService
from app.services.pathumma_service import pathumma_asr
from app.services.typhoon_service import typhoon_asr
from app.utils.formatter import format_transcription_response
from app.utils.logger import logger
from app.models.schemas import TranscribeResponse, ErrorResponse, HealthResponse

router = APIRouter()
audio_service = AudioService()


@router.post("/api/v1/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Stereo WAV file"),
    model: str = Form(..., description="ASR model: typhoon or pathumma")
):
    """Transcribe stereo WAV file

    Args:
        file: Stereo WAV file upload
        model: Model selection (typhoon/pathumma)

    Returns:
        Transcription results matching example_response.json format
    """
    temp_files = []

    try:
        # Validate model selection
        if model.lower() not in settings.supported_models:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model. Supported models: {', '.join(settings.supported_models)}"
            )

        # Validate file type
        if not file.filename.lower().endswith('.wav'):
            raise HTTPException(
                status_code=400,
                detail="Only WAV files are supported"
            )

        # Check file size
        file_content = await file.read()
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_file_size / (1024*1024)}MB"
            )

        # Save uploaded file
        upload_id = str(uuid.uuid4())
        temp_upload_path = Path(settings.temp_path) / f"{upload_id}_{file.filename}"
        temp_files.append(str(temp_upload_path))

        with open(temp_upload_path, 'wb') as f:
            f.write(file_content)

        logger.info(f"Saved uploaded file: {temp_upload_path}")

        # Process stereo file - split into caller/agent channels
        caller_path, agent_path = audio_service.process_stereo_file(
            str(temp_upload_path),
            file.filename
        )
        temp_files.extend([caller_path, agent_path])

        # Select and use appropriate ASR model
        if model.lower() == "pathumma":
            logger.info("Using Pathumma ASR model")
            caller_result = pathumma_asr.transcribe(caller_path)
            agent_result = pathumma_asr.transcribe(agent_path)
        elif model.lower() == "typhoon":
            logger.info("Using Typhoon ASR model")
            caller_result = typhoon_asr.transcribe(caller_path)
            agent_result = typhoon_asr.transcribe(agent_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")

        # Format response
        response = format_transcription_response(
            filename=file.filename,
            model_name=model.lower(),
            caller_result=caller_result,
            agent_result=agent_result
        )

        logger.info(f"Transcription completed for {file.filename}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temporary files
        audio_service.cleanup_temp_files(*temp_files)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint

    Returns:
        Service health status
    """
    models_loaded = (
        pathumma_asr.model is not None or
        typhoon_asr.loaded
    )

    return {
        "status": "healthy",
        "models_loaded": models_loaded
    }
