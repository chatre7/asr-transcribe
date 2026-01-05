"""Typhoon ASR service"""
from typing import Dict, List
import torch

# Try to import typhoon-asr (may fail on Windows due to nemo-toolkit signal.SIGKILL issue)
TYPHOON_ASR_AVAILABLE = False
typhoon_transcribe = None
TYPHOON_IMPORT_ERROR = None

try:
    from typhoon_asr import transcribe as typhoon_transcribe
    TYPHOON_ASR_AVAILABLE = True
except (ImportError, AttributeError) as e:
    TYPHOON_ASR_AVAILABLE = False
    TYPHOON_IMPORT_ERROR = str(e)

from app.utils.logger import logger


class TyphoonASR:
    """Typhoon ASR service for Thai transcription using typhoon-asr package"""

    def __init__(self, model_name: str = "scb10x/typhoon-asr-realtime"):
        """Initialize Typhoon ASR model

        Args:
            model_name: Model name (not used with typhoon-asr package, kept for compatibility)
        """
        self.model_name = model_name
        self.loaded = False

        if not TYPHOON_ASR_AVAILABLE:
            if TYPHOON_IMPORT_ERROR and "SIGKILL" in TYPHOON_IMPORT_ERROR:
                logger.warning(f"Typhoon ASR not available on Windows: nemo-toolkit requires Linux/Unix. Error: {TYPHOON_IMPORT_ERROR}")
            else:
                logger.error(f"typhoon-asr package is not available. Error: {TYPHOON_IMPORT_ERROR or 'Not installed'}")
        else:
            logger.info(f"Initializing Typhoon ASR model: {self.model_name}")
            self.loaded = True

    def load_model(self, device: str = "auto"):
        """Load the Typhoon ASR model (no-op for typhoon-asr package)

        Args:
            device: Device to use ('cpu', 'cuda', or 'auto')
        """
        if not TYPHOON_ASR_AVAILABLE:
            raise ImportError("typhoon-asr package is not installed")

        # typhoon-asr handles model loading internally
        logger.info("Typhoon ASR is ready (uses typhoon-asr package)")
        self.loaded = True

    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio file using Typhoon ASR

        Args:
            audio_path: Path to audio file

        Returns:
            Dict containing segments with word-level timestamps and confidence
        """
        if not self.loaded:
            self.load_model()

        if not TYPHOON_ASR_AVAILABLE:
            raise ImportError("typhoon-asr package is not installed")

        try:
            logger.info(f"Transcribing audio with Typhoon ASR: {audio_path}")

            # Use typhoon-asr package with timestamps
            device = "cuda:1" if torch.cuda.device_count() > 1 else ("cuda" if torch.cuda.is_available() else "cpu")
            result = typhoon_transcribe(
                audio_path,
                with_timestamps=False,
                device=device
            )

            # Format results to match Pathumma format
            result_segments = []

            raw_text = result.get("text") or ""
            if isinstance(raw_text, list):
                raw_text = " ".join([str(item) for item in raw_text if item is not None])
            text = str(raw_text).strip()
            audio_duration = float(result.get("audio_duration", 0) or 0)

            # Create a single segment; approximate word timestamps if text is available.
            words = []
            if text:
                raw_words = text.split()
                if raw_words and audio_duration > 0:
                    avg_duration = audio_duration / len(raw_words)
                    for idx, word in enumerate(raw_words):
                        words.append({
                            "word": word,
                            "start": round(idx * avg_duration, 3),
                            "end": round((idx + 1) * avg_duration, 3),
                            "confidence": 0.95
                        })
            else:
                logger.warning("Typhoon ASR returned empty text")

            result_segments.append({
                "id": 0,
                "seek": 0,
                "start": 0,
                "end": audio_duration,
                "text": text,
                "words": words
            })

            logger.info(f"Transcription complete: {len(result_segments)} segments, {len(result_segments[0]['words']) if result_segments else 0} words")

            return {
                "segments": result_segments,
                "language": "th",
                "language_probability": 1.0
            }

        except Exception as e:
            logger.error(f"Error during Typhoon transcription: {str(e)}")
            raise


# Global instance
typhoon_asr = TyphoonASR()
