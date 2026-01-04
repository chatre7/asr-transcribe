"""Pathumma-Whisper ASR service"""
from typing import Dict, List
from faster_whisper import WhisperModel
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
        self.model_name = settings.pathumma_model_id or f"pathumma/whisper-th-{model_size}"
        self.model = None
        logger.info(f"Initializing Pathumma ASR model: {self.model_name}")

    def load_model(self, device: str = "auto", compute_type: str = "auto"):
        """Load the Whisper model

        Args:
            device: Device to use ('cpu', 'cuda', or 'auto')
            compute_type: Computation type ('int8', 'float16', or 'auto')
        """
        try:
            logger.info(f"Loading Pathumma model on device: {device}, compute_type: {compute_type}")
            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
                local_files_only=settings.hf_local_files_only,
                download_root=settings.hf_home
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
        if self.model is None:
            self.load_model()

        try:
            logger.info(f"Transcribing audio: {audio_path}")

            # Transcribe with word timestamps
            segments, info = self.model.transcribe(
                audio_path,
                language="th",
                word_timestamps=True,
                vad_filter=True,  # Voice activity detection
                beam_size=5
            )

            # Format results
            result_segments = []
            for idx, segment in enumerate(segments):
                # Format words
                words = []
                if segment.words:
                    for word in segment.words:
                        words.append({
                            "word": word.word.strip(),
                            "start": round(word.start, 3),
                            "end": round(word.end, 3),
                            "confidence": round(word.probability, 2)
                        })

                # Create segment
                segment_dict = {
                    "id": idx,
                    "seek": 0,  # Not used in faster-whisper
                    "start": round(segment.start, 3),
                    "end": round(segment.end, 3),
                    "text": segment.text.strip(),
                    "words": words
                }
                result_segments.append(segment_dict)

            logger.info(f"Transcription complete: {len(result_segments)} segments")

            return {
                "segments": result_segments,
                "language": info.language,
                "language_probability": round(info.language_probability, 2)
            }

        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise


# Global instance
pathumma_asr = PathummaASR()
