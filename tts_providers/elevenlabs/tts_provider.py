from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import os
import yaml
from typing import Dict, Optional, List, Any

from ..base.tts_provider import TTSProvider, TTSError, VoiceNotFoundError
from .voice_registry_manager import ElevenLabsVoiceRegistryManager


class ElevenLabsTTSProvider(TTSProvider):
    """
    TTS Provider implementation for ElevenLabs API. Handles voice mapping and audio generation
    while abstracting away the complexity of ElevenLabs' voice registry system.
    """

    def __init__(self):
        self.client = None
        self.voice_registry_manager = None
        # Maps speaker names to public voice IDs
        self.voice_map: Dict[str, str] = {}
        self.default_voice_id: Optional[str] = None

    def initialize(self, speaker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize the provider with API key and voice configuration."""
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise TTSError("ELEVEN_API_KEY environment variable is not set")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_registry_manager = ElevenLabsVoiceRegistryManager(api_key)

        # Extract voice IDs from speaker configs
        for speaker, config in speaker_configs.items():
            self.validate_speaker_config(config)
            voice_id = config['voice_id']
            if speaker == 'default':
                self.default_voice_id = voice_id
            self.voice_map[speaker] = voice_id

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """
        Get the voice ID from configuration for a given speaker.
        This returns the public/config voice ID, not the registry ID.
        """
        if speaker is None:
            if not self.default_voice_id:
                raise VoiceNotFoundError("No default voice configured")
            return self.default_voice_id

        voice_id = self.voice_map.get(speaker)
        if not voice_id:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        return voice_id

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client or not self.voice_registry_manager:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        # Get the public voice ID first
        public_voice_id = self.get_speaker_identifier(speaker)

        # Then get the registry voice ID for actual generation
        registry_voice_id = self.voice_registry_manager.get_library_voice_id(
            public_voice_id)

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
                )
            )

            audio_data = b''
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
        return ['voice_id']

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
        if 'voice_id' not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice_id' in speaker configuration: {speaker_config}")

        if not isinstance(speaker_config['voice_id'], str):
            raise ValueError("Field 'voice_id' must be a string")
