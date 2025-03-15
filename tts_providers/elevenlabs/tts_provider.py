import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import yaml
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from ..base.tts_provider import TTSError, TTSProvider, VoiceNotFoundError
from .voice_registry_manager import ElevenLabsVoiceRegistryManager


@dataclass
class SpeakerConfig:
    """Configuration for a speaker using ElevenLabs TTS."""

    voice_id: str


class ElevenLabsTTSProvider(TTSProvider):
    """
    TTS Provider implementation for ElevenLabs API. Handles voice mapping and audio generation
    while abstracting away the complexity of ElevenLabs' voice registry system.
    """

    def __init__(self):
        self.client = None
        self.voice_registry_manager = None
        # Maps speaker names to their configurations
        self.speaker_configs: Dict[str, SpeakerConfig] = {}

    def _initialize_api_client(self):
        """Initialize API client"""
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise TTSError("ELEVEN_API_KEY environment variable is not set")

        try:
            self.client = ElevenLabs(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize ElevenLabs client: {e}")

        self.voice_registry_manager = ElevenLabsVoiceRegistryManager(api_key)

    def initialize(self, speaker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize the ElevenLabs TTS provider with speaker configurations."""

        # Extract voice IDs from speaker configs
        for speaker, config in speaker_configs.items():
            try:
                self.validate_speaker_config(config)
            except ValueError as e:
                raise TTSError(f"Failed validation for speaker {speaker}. Error: {e}")

            speaker_config = SpeakerConfig(voice_id=config["voice_id"])

            self.speaker_configs[speaker] = speaker_config

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """
        Get the voice ID from configuration for a given speaker.
        This returns the public/config voice ID, not the registry ID.
        """
        if speaker is None:
            speaker = "default"

        config = self.speaker_configs.get(speaker)
        if not config:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        return config.voice_id

    def get_speaker_configuration(self, speaker: Optional[str]) -> Dict[str, Any]:
        """Get the configuration parameters for a given speaker."""
        if speaker is None:
            speaker = "default"

        config = self.speaker_configs.get(speaker)
        if not config:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        # Convert dataclass to dict and filter out empty values
        speaker_config = {
            k: v for k, v in asdict(config).items() if not self._is_empty_value(v)
        }

        return speaker_config

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client:
            # Wait to initialize client for API calls until it is necessary for audio generation
            self._initialize_api_client()

        # Get the public voice ID first
        public_voice_id = self.get_speaker_identifier(speaker)

        # Then get the registry voice ID for actual generation
        try:
            registry_voice_id = self.voice_registry_manager.get_library_voice_id(
                public_voice_id
            )
        except RuntimeError as e:
            raise TTSError(f"Failed to generate audio: Voice registry error - {str(e)}")

        try:
            response = self.client.text_to_speech.convert(
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

    def validate_speaker_config(self, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        if "voice_id" not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice_id' in speaker configuration: {speaker_config}"
            )

        if not isinstance(speaker_config["voice_id"], str):
            raise ValueError("Field 'voice_id' must be a string")
