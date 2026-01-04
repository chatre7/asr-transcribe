"""FastAPI main application"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import routes
from app.config import settings
from app.utils.logger import logger


# Create FastAPI app
app = FastAPI(
    title="ASR Stereo Transcription API",
    description="API for transcribing stereo WAV files with Thai ASR models",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    os.environ["HF_HUB_OFFLINE"] = "1" if settings.hf_hub_offline else "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "1" if settings.transformers_offline else "0"
    if settings.huggingfacehub_api_token:
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = settings.huggingfacehub_api_token
    logger.info("Starting ASR Transcription API")
    logger.info(f"Supported models: {settings.supported_models}")
    logger.info(f"Default model: {settings.default_model}")
    logger.info(f"Temp path: {settings.temp_path}")
    logger.info(f"Max file size: {settings.max_file_size / (1024*1024)}MB")
    logger.info(f"HF_HUB_OFFLINE: {os.environ['HF_HUB_OFFLINE']}")
    logger.info(f"TRANSFORMERS_OFFLINE: {os.environ['TRANSFORMERS_OFFLINE']}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down ASR Transcription API")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ASR Stereo Transcription API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
