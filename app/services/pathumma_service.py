"""Pathumma-Whisper ASR service"""
from typing import Dict, List
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from app.config import settings
from app.utils.logger import logger


class PathummaASR:
    """Pathumma-Whisper ASR service for Thai transcription"""

    def __init__(self, model_size: str = "large-v3"):
        """Initialize Pathumma-Whisper model

        Args:
            model_size: Model size (default: large-v3)
        """
        # Prefer explicit model ID from settings; fall back to legacy size-based naming.
        self.model_name = settings.pathumma_model_id or f"nectec/Pathumma-whisper-th-{model_size}"
        self.model = None
        self.processor = None
        self.pipe = None
        logger.info(f"Initializing Pathumma ASR model: {self.model_name}")

    def load_model(self, device: str = "auto", compute_type: str = "auto"):
        """Load the Whisper model

        Args:
            device: Device to use ('cpu', 'cuda', or 'auto')
            compute_type: Computation type ('int8', 'float16', or 'auto')
        """
        try:
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"

            torch_dtype = torch.float16 if device == "cuda" else torch.float32
            logger.info(f"Loading Pathumma model on device: {device}, dtype: {torch_dtype}")

            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                cache_dir=settings.hf_home,
                local_files_only=settings.hf_local_files_only
            )
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                cache_dir=settings.hf_home,
                local_files_only=settings.hf_local_files_only
            )

            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                device=0 if device == "cuda" else -1
            )

            logger.info("Pathumma model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Pathumma model: {str(e)}")
            raise

    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio file using Pathumma-Whisper

        Args:
            audio_path: Path to audio file

        Returns:
            Dict containing segments with word-level timestamps and confidence
            Format: {
                'segments': [
                    {
                        'id': int,
                        'start': float,
                        'end': float,
                        'text': str,
                        'words': [
                            {
                                'word': str,
                                'start': float,
                                'end': float,
                                'confidence': float
                            }
                        ]
                    }
                ]
            }
        """
        if self.pipe is None:
            self.load_model()

        try:
            logger.info(f"Transcribing audio: {audio_path}")

            result = self.pipe(
                audio_path,
                return_timestamps="word",
                generate_kwargs={"language": "th"}
            )

            text = (result.get("text") or "").strip()
            chunks = result.get("chunks") or []

            words = []
            for chunk in chunks:
                word_text = (chunk.get("text") or "").strip()
                start, end = chunk.get("timestamp", (None, None))
                if word_text:
                    words.append({
                        "word": word_text,
                        "start": round(start or 0.0, 3),
                        "end": round(end or 0.0, 3),
                        "confidence": 0.95
                    })

            start_ts = words[0]["start"] if words else 0.0
            end_ts = words[-1]["end"] if words else 0.0

            result_segments = [{
                "id": 0,
                "seek": 0,
                "start": start_ts,
                "end": end_ts,
                "text": text,
                "words": words
            }]

            logger.info(f"Transcription complete: {len(words)} words")

            return {
                "segments": result_segments,
                "language": "th",
                "language_probability": 1.0
            }

        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise


# Global instance
pathumma_asr = PathummaASR()
