import os
import threading
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import yaml
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from ..base.tts_provider import TTSError, TTSProvider, VoiceNotFoundError
from .voice_registry_manager import ElevenLabsVoiceRegistryManager


class ElevenLabsTTSProvider(TTSProvider):
    """
    TTS Provider implementation for ElevenLabs API. Handles voice mapping and audio generation
    while abstracting away the complexity of ElevenLabs' voice registry system.
    """

    IS_STATEFUL = True

    @classmethod
    def instantiate_client(cls) -> ElevenLabs:
        """Instantiate and return the ElevenLabs API client."""
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise TTSError("ELEVEN_API_KEY environment variable is not set")
        try:
            return ElevenLabs(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize ElevenLabs client: {e}")

    def __init__(self) -> None:
        super().__init__()
        self.voice_registry_manager: Optional[ElevenLabsVoiceRegistryManager] = None
        self._init_lock = (
            threading.Lock()
        )  # Lock for thread-safe initialization of registry manager

    def initialize(self) -> None:
        """Initialize the stateful part of the provider (Voice Registry Manager)."""
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise TTSError("ELEVEN_API_KEY environment variable is not set")

        # Use lock to ensure registry manager is initialized only once if initialize
        # were ever called concurrently
        with self._init_lock:
            if self.voice_registry_manager is None:
                try:
                    self.voice_registry_manager = ElevenLabsVoiceRegistryManager(
                        api_key
                    )
                except Exception as e:
                    raise TTSError(
                        f"Failed to initialize ElevenLabsVoiceRegistryManager: {e}"
                    )

    def get_speaker_identifier(self, speaker_config: Dict[str, Any]) -> str:
        """
        Get the voice ID from configuration for a given speaker.
        This returns the public/config voice ID, not the registry ID.
        """
        voice_id = speaker_config.get("voice_id")
        if not voice_id or not isinstance(voice_id, str):
            raise TTSError(
                f"Missing or invalid 'voice_id' in speaker config: {speaker_config}"
            )
        return str(voice_id)

    def generate_audio(
        self, client: ElevenLabs, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio for the given speaker and text."""
        # Get the public voice ID first
        public_voice_id = self.get_speaker_identifier(speaker_config)

        # Then get the registry voice ID for actual generation
        try:
            if self.voice_registry_manager is None:
                # Attempt to initialize lazily if not done already
                self.initialize()
                if self.voice_registry_manager is None:  # Check again after trying init
                    raise TTSError("Voice registry manager could not be initialized")

            registry_voice_id = self.voice_registry_manager.get_library_voice_id(
                public_voice_id
            )
        except RuntimeError as e:
            raise TTSError(f"Failed to generate audio: Voice registry error - {str(e)}")

        try:
            if client is None:
                raise TTSError("ElevenLabs client is not initialized")

            response = client.text_to_speech.convert(
                voice_id=registry_voice_id,
                optimize_streaming_latency="0",
                output_format="mp3_44100_192",
                text=text,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True,
                ),
            )

            audio_data = b""
            for chunk in response:
                if chunk:
                    audio_data += chunk

            return audio_data

        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "elevenlabs"

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions."""
        return """# ElevenLabs TTS Configuration
#
# Required Environment Variable:
#   ELEVEN_API_KEY: Your ElevenLabs API key
#
# For each speaker, specify:
#   voice_id: The ElevenLabs voice ID to use
#
# Instructions:
#   - For each speaker, specify:
#       voice_id: The ElevenLabs voice ID to use
#
# Example:
#   default:
#     voice_id: i4CzbCVWoqvD0P1QJCUL
#   DAVID:
#     voice_id: XA2bIQ92TabjGbpO2xRr
"""

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ["voice_id"]

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get optional configuration fields."""
        return []

    @classmethod
    def get_metadata_fields(cls) -> List[str]:
        """Get metadata fields."""
        return []

    @classmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        if "voice_id" not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice_id' in speaker configuration: {speaker_config}"
            )

        if not isinstance(speaker_config["voice_id"], str):
            raise ValueError("Field 'voice_id' must be a string")
