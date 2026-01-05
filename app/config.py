"""Application configuration"""
import os
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Paths
    temp_path: str = "./temp"
    log_level: str = "INFO"

    # File upload limits
    max_file_size_mb: int = 100
    max_file_size: int = 100 * 1024 * 1024  # Derived from max_file_size_mb

    # Supported models
    supported_models: List[str] = ["typhoon", "pathumma"]
    default_model: str = "pathumma"
    enable_pathumma: bool = True
    enable_typhoon: bool = True

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Hugging Face
    hf_home: str = os.getenv("HF_HOME", "/root/.cache/huggingface")
    hf_local_files_only: bool = False
    hf_hub_offline: bool = False
    transformers_offline: bool = False
    huggingfacehub_api_token: str = ""

    # Model IDs
    pathumma_model_id: str = "nectec/Pathumma-whisper-th-large-v3"

    # Audio processing
    sample_rate: int = 16000

    # Chunking (seconds)
    chunk_duration_sec: float = 30.0
    chunk_overlap_sec: float = 3.0

    class Config:
        env_file = ".env"
        case_sensitive = False

    @model_validator(mode="after")
    def _apply_max_file_size(self):
        self.max_file_size = int(self.max_file_size_mb) * 1024 * 1024
        enabled = []
        if self.enable_pathumma:
            enabled.append("pathumma")
        if self.enable_typhoon:
            enabled.append("typhoon")
        if enabled:
            self.supported_models = enabled
        return self


# Global settings instance
settings = Settings()

# Ensure Hugging Face envs are set before any model download attempts.
os.environ["HF_HUB_OFFLINE"] = "1" if settings.hf_hub_offline else "0"
os.environ["TRANSFORMERS_OFFLINE"] = "1" if settings.transformers_offline else "0"
if settings.huggingfacehub_api_token:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = settings.huggingfacehub_api_token
