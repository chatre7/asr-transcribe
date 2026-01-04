"""Audio processing service for stereo channel splitting"""
import os
from pathlib import Path
from typing import Tuple
import soundfile as sf
import numpy as np
from app.utils.logger import logger
from app.config import settings


class AudioService:
    """Service for handling audio file processing"""

    def __init__(self):
        """Initialize audio service"""
        self.temp_path = Path(settings.temp_path)
        self.temp_path.mkdir(parents=True, exist_ok=True)

    def load_wav_file(self, file_path: str) -> Tuple[np.ndarray, int]:
        """Load WAV file and validate it's stereo

        Args:
            file_path: Path to WAV file

        Returns:
            Tuple of (audio_data, sample_rate)

        Raises:
            ValueError: If file is not stereo or not WAV format
        """
        try:
            audio_data, sample_rate = sf.read(file_path)
            logger.info(f"Loaded audio file: {file_path}, shape: {audio_data.shape}, sr: {sample_rate}")

            # Check if stereo (2 channels)
            if len(audio_data.shape) != 2 or audio_data.shape[1] != 2:
                raise ValueError(
                    f"Audio file must be stereo (2 channels), got shape: {audio_data.shape}"
                )

            return audio_data, sample_rate

        except Exception as e:
            logger.error(f"Error loading WAV file {file_path}: {str(e)}")
            raise

    def split_stereo_channels(
        self, audio_data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Split stereo audio into left and right channels

        Args:
            audio_data: Stereo audio data (N, 2)

        Returns:
            Tuple of (left_channel, right_channel)
            - left_channel: Caller (mono)
            - right_channel: Agent (mono)
        """
        left_channel = audio_data[:, 0]  # Caller
        right_channel = audio_data[:, 1]  # Agent

        logger.info(f"Split stereo: Left (Caller) shape: {left_channel.shape}, Right (Agent) shape: {right_channel.shape}")

        return left_channel, right_channel

    def save_mono_channel(
        self,
        channel_data: np.ndarray,
        sample_rate: int,
        output_path: str
    ) -> str:
        """Save mono channel data to WAV file

        Args:
            channel_data: Mono audio data
            sample_rate: Sample rate
            output_path: Output file path

        Returns:
            Path to saved file
        """
        try:
            sf.write(output_path, channel_data, sample_rate)
            logger.info(f"Saved mono channel to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving mono channel to {output_path}: {str(e)}")
            raise

    def process_stereo_file(
        self, input_file: str, filename: str
    ) -> Tuple[str, str]:
        """Process stereo WAV file and split into Caller/Agent channels

        Args:
            input_file: Path to input stereo WAV file
            filename: Original filename (for naming output files)

        Returns:
            Tuple of (caller_file_path, agent_file_path)
        """
        # Load stereo file
        audio_data, sample_rate = self.load_wav_file(input_file)

        # Split channels
        left_channel, right_channel = self.split_stereo_channels(audio_data)

        # Generate output filenames
        base_name = Path(filename).stem
        caller_path = str(self.temp_path / f"{base_name}_caller.wav")
        agent_path = str(self.temp_path / f"{base_name}_agent.wav")

        # Save channels
        self.save_mono_channel(left_channel, sample_rate, caller_path)
        self.save_mono_channel(right_channel, sample_rate, agent_path)

        logger.info(f"Processed stereo file: Caller={caller_path}, Agent={agent_path}")

        return caller_path, agent_path

    def cleanup_temp_files(self, *file_paths: str) -> None:
        """Clean up temporary files

        Args:
            *file_paths: Variable number of file paths to delete
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_path}: {str(e)}")
