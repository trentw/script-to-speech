from typing import Dict, Optional, List, Any
from openai import OpenAI, AuthenticationError, APIError, RateLimitError
import os
from dataclasses import dataclass, asdict

from ..base.tts_provider import TTSProvider, TTSError, VoiceNotFoundError


@dataclass
class SpeakerConfig:
    """Configuration for a speaker using OpenAI TTS."""
    voice: str


class OpenAITTSProvider(TTSProvider):
    """
    TTS Provider implementation for OpenAI's Text-to-Speech API.
    """

    MODEL = "tts-1-hd"
    VALID_VOICES = {"alloy", "ash", "coral", "echo",
                    "fable", "onyx", "nova", "sage", "shimmer"}

    def __init__(self):
        self.client = None
        # Maps speaker names to their configurations
        self.speaker_configs: Dict[str, SpeakerConfig] = {}

    def initialize(self, speaker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize the OpenAI TTS provider with speaker configurations."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise TTSError("OPENAI_API_KEY environment variable is not set")

        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize OpenAI client: {e}")

        # Validate and store voice configurations
        for speaker, config in speaker_configs.items():
            self.validate_speaker_config(config)
            speaker_config = SpeakerConfig(
                voice=config['voice']
            )
            self.speaker_configs[speaker] = speaker_config

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        try:
            voice = self._get_base_voice(speaker)
            response = self.client.audio.speech.create(
                model=self.MODEL,
                voice=voice,
                input=text
            )
            # OpenAI returns a streamable response
            return response.content

        except AuthenticationError as e:
            raise TTSError(f"Authentication failed: {e}")
        except RateLimitError as e:
            raise TTSError(f"Rate limit exceeded: {e}")
        except APIError as e:
            raise TTSError(f"OpenAI API error: {e}")
        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """Get the voice identifier with model information."""
        voice = self._get_base_voice(speaker)
        return f"{voice}_{self.MODEL}"

    def _get_base_voice(self, speaker: Optional[str]) -> str:
        """Get the base voice name for a speaker."""
        if not speaker:
            speaker = 'default'

        config = self.speaker_configs.get(speaker)
        if not config:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )
        return config.voice

    def get_speaker_configuration(self, speaker: Optional[str]) -> Dict[str, Any]:
        """Get the configuration parameters for a given speaker."""
        if not speaker:
            speaker = 'default'

        config = self.speaker_configs.get(speaker)
        if not config:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        # Convert dataclass to dict and filter out empty values
        speaker_config = {
            k: v for k, v in asdict(config).items()
            if not self._is_empty_value(v)
        }

        return speaker_config

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "openai"

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions."""
        return """# OpenAI TTS Configuration
# 
# Required Environment Variable:
#   OPENAI_API_KEY: Your OpenAI API key
#
# Instructions:
#   - For each speaker, specify:
#       voice: One of [alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer]
#
# Example:
#   default:
#     voice: onyx
#   DAVID:
#     voice: echo
"""

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ['voice']

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
        if 'voice' not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice' in speaker configuration: {speaker_config}")

        voice = speaker_config['voice']
        if not isinstance(voice, str):
            raise ValueError("Field 'voice' must be a string")

        if voice not in self.VALID_VOICES:
            raise ValueError(
                f"Invalid voice '{voice}'. Must be one of: {', '.join(sorted(self.VALID_VOICES))}"
            )
