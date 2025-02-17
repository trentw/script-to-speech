from typing import Dict, Optional, List, Any
from zyphra import ZyphraClient, ZyphraError
import os
from dataclasses import dataclass
import hashlib
import json

from ..base.tts_provider import TTSProvider, TTSError, VoiceNotFoundError


@dataclass
class SpeakerConfig:
    """Configuration for a speaker using Zonos TTS."""
    voice_seed: int
    speaking_rate: Optional[float] = None
    language_iso_code: Optional[str] = None


class ZonosTTSProvider(TTSProvider):
    """
    TTS Provider implementation for Zonos's Text-to-Speech API using Zyphra client.
    """

    MIME_TYPE = "audio/mp3"
    MIN_SPEAKING_RATE = 5
    MAX_SPEAKING_RATE = 35
    MIN_SEED = -1
    MAX_SEED = 2147483647
    VALID_LANGUAGES = {"en-us", "fr-fr", "de", "ja", "ko", "cmn"}

    def __init__(self):
        self.client = None
        # Maps speaker names to their configuration
        self.speaker_configs: Dict[str, SpeakerConfig] = {}
        self.default_config: Optional[SpeakerConfig] = None

    def initialize(self, speaker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize the Zonos TTS provider with speaker configurations."""
        api_key = os.environ.get("ZONOS_API_KEY")
        if not api_key:
            raise TTSError("ZONOS_API_KEY environment variable is not set")

        try:
            self.client = ZyphraClient(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize Zyphra client: {e}")

        # Validate and store voice configurations
        for speaker, config in speaker_configs.items():
            self.validate_speaker_config(config)
            
            # Extract optional fields if present
            optional_fields = config.get('optional_fields', {})
            speaker_config = SpeakerConfig(
                voice_seed=config['voice_seed'],
                speaking_rate=optional_fields.get('speaking_rate'),
                language_iso_code=optional_fields.get('language_iso_code')
            )

            if speaker == 'default':
                self.default_config = speaker_config
            self.speaker_configs[speaker] = speaker_config

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        try:
            config = self._get_speaker_config(speaker)
            params = {
                "text": text,
                "seed": config.voice_seed,
                "mime_type": self.MIME_TYPE
            }

            # Add optional parameters if configured
            if config.speaking_rate is not None:
                params["speaking_rate"] = config.speaking_rate
            if config.language_iso_code is not None:
                params["language_iso_code"] = config.language_iso_code

            response = self.client.audio.speech.create(**params)
            return response

        except ZyphraError as e:
            raise TTSError(f"Zyphra API error: {e}")
        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """Get the voice identifier that changes if any generation parameter changes."""
        config = self._get_speaker_config(speaker)
        
        # Create a dictionary of all parameters that affect voice generation
        params = {
            "seed": config.voice_seed,
            "speaking_rate": config.speaking_rate,
            "language_iso_code": config.language_iso_code,
            "mime_type": self.MIME_TYPE
        }
        
        # Create a hash of the parameters
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()[:12]

    def _get_speaker_config(self, speaker: Optional[str]) -> SpeakerConfig:
        """Get the speaker configuration."""
        if not speaker:
            if not self.default_config:
                raise VoiceNotFoundError("No default voice configured")
            return self.default_config

        config = self.speaker_configs.get(speaker)
        if not config:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )
        return config

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "zonos"

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions."""
        return """# Zonos TTS Configuration
# 
# Required Environment Variable:
#   ZONOS_API_KEY: Your Zonos API key
#
# Instructions:
#   - For each speaker, specify:
#       voice_seed: Integer between -1 and 2147483647 (required)
#       optional_fields:
#         speaking_rate: Float between 5 and 35
#         language_iso_code: One of [en-us, fr-fr, de, ja, ko, cmn]
#
# Example (minimal):
#   default:
#     voice_seed: 12345
#
# Example (with optional fields):
#   MARIA:
#     voice_seed: 67890
#     optional_fields:
#       speaking_rate: 20
#       language_iso_code: fr-fr
"""

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ['voice_seed']

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get optional configuration fields."""
        return ['speaking_rate', 'language_iso_code']

    @classmethod
    def get_metadata_fields(cls) -> List[str]:
        """Get metadata fields."""
        return []

    def validate_speaker_config(self, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        if 'voice_seed' not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice_seed' in speaker configuration: {speaker_config}")

        voice_seed = speaker_config['voice_seed']
        if not isinstance(voice_seed, int):
            raise ValueError("Field 'voice_seed' must be an integer")

        if not self.MIN_SEED <= voice_seed <= self.MAX_SEED:
            raise ValueError(
                f"Invalid voice_seed '{voice_seed}'. Must be between {self.MIN_SEED} and {self.MAX_SEED}")

        # Validate optional fields if present
        optional_fields = speaker_config.get('optional_fields', {})
        if not isinstance(optional_fields, dict):
            raise ValueError("optional_fields must be a dictionary")

        if 'speaking_rate' in optional_fields:
            speaking_rate = optional_fields['speaking_rate']
            if not isinstance(speaking_rate, (int, float)):
                raise ValueError("Field 'speaking_rate' must be a number")
            if not self.MIN_SPEAKING_RATE <= speaking_rate <= self.MAX_SPEAKING_RATE:
                raise ValueError(
                    f"Invalid speaking_rate '{speaking_rate}'. Must be between {self.MIN_SPEAKING_RATE} and {self.MAX_SPEAKING_RATE}")

        if 'language_iso_code' in optional_fields:
            language_code = optional_fields['language_iso_code']
            if not isinstance(language_code, str):
                raise ValueError("Field 'language_iso_code' must be a string")
            if language_code not in self.VALID_LANGUAGES:
                raise ValueError(
                    f"Invalid language_iso_code '{language_code}'. Must be one of: {', '.join(sorted(self.VALID_LANGUAGES))}")