import os
import typing
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional, Set

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from ..base.tts_provider import TTSError, TTSProvider, VoiceNotFoundError

# Define valid voice literals - these are the voices supported by the OpenAI API
VoiceType = Literal[
    "alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"
]


@dataclass
class SpeakerConfig:
    """Configuration for a speaker using OpenAI TTS."""

    voice: str


class OpenAITTSProvider(TTSProvider):
    """
    TTS Provider implementation for OpenAI's Text-to-Speech API.
    """

    MODEL = "tts-1-hd"

    @classmethod
    def get_valid_voices(cls) -> Set[str]:
        """Get the set of valid voice names from VoiceType."""
        import typing

        # Get the arguments from the Literal type
        args = typing.get_args(VoiceType)
        return set(args)

    def __init__(self) -> None:
        self.client: Optional[OpenAI] = None
        # Maps speaker names to their configurations
        self.speaker_configs: Dict[str, SpeakerConfig] = {}

    def _initialize_api_client(self) -> None:
        """Initialize API client"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise TTSError("OPENAI_API_KEY environment variable is not set")

        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize OpenAI client: {e}")

    def initialize(self, speaker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize the OpenAI TTS provider with speaker configurations."""

        # Validate and store voice configurations
        for speaker, config in speaker_configs.items():
            self.validate_speaker_config(config)
            speaker_config = SpeakerConfig(voice=config["voice"])
            self.speaker_configs[speaker] = speaker_config

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client:
            # Wait to initialize client for API calls until it is necessary for audio generation
            self._initialize_api_client()

        try:
            if self.client is None:
                raise TTSError("OpenAI client is not initialized")

            voice = self._get_base_voice(speaker)
            # Type ignore: The API actually accepts all voices in VoiceType, despite what the type hints suggest
            response = self.client.audio.speech.create(
                model=self.MODEL, voice=voice, input=text  # type: ignore
            )
            # OpenAI returns a streamable response
            if response is None:
                raise TTSError("Received None response from OpenAI API")

            return bytes(response.content)

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

    def _get_base_voice(self, speaker: Optional[str]) -> VoiceType:
        """Get the base voice name for a speaker."""
        if not speaker:
            speaker = "default"

        config = self.speaker_configs.get(speaker)
        if not config:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )
        # Ensure we return a valid VoiceType
        voice = config.voice
        valid_voices = self.get_valid_voices()
        if voice not in valid_voices:
            raise VoiceNotFoundError(
                f"Invalid voice '{voice}'. Must be one of: {', '.join(sorted(valid_voices))}"
            )
        return voice  # type: ignore  # We've validated it's a valid VoiceType

    def get_speaker_configuration(self, speaker: Optional[str]) -> Dict[str, Any]:
        """Get the configuration parameters for a given speaker."""
        if not speaker:
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

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "openai"

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions."""
        valid_voices = cls.get_valid_voices()
        voices_str = ", ".join(sorted(valid_voices))

        return f"""# OpenAI TTS Configuration
#
# Required Environment Variable:
#   OPENAI_API_KEY: Your OpenAI API key
#
# Instructions:
#   - For each speaker, specify:
#       voice: One of [{voices_str}]
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
        return ["voice"]

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
        if "voice" not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice' in speaker configuration: {speaker_config}"
            )

        voice = speaker_config["voice"]
        if not isinstance(voice, str):
            raise ValueError("Field 'voice' must be a string")

        valid_voices = self.get_valid_voices()
        if voice not in valid_voices:
            raise ValueError(
                f"Invalid voice '{voice}'. Must be one of: {', '.join(sorted(valid_voices))}"
            )
