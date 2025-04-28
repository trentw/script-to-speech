import os
import typing
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional, Set

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from ..base.exceptions import (
    TTSError,
    TTSRateLimitError,
    VoiceNotFoundError,
)
from ..base.stateless_tts_provider import StatelessTTSProviderBase

# Define valid voice literals - these are the voices supported by the OpenAI API
VoiceType = Literal[
    "alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"
]


class OpenAITTSProvider(StatelessTTSProviderBase):
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

    @classmethod
    def instantiate_client(cls) -> OpenAI:
        """Instantiate and return the OpenAI API client."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise TTSError("OPENAI_API_KEY environment variable is not set")

        try:
            return OpenAI(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize OpenAI client: {e}")

    @classmethod
    def get_max_download_threads(cls) -> int:
        """
        Get the max number of concurrent download threads for OpenAI provider.

        Returns:
            int: Returns 7 concurrent threads
        """
        return 7

    @classmethod
    def generate_audio(
        cls, client: OpenAI, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio for the given speaker and text."""

        try:
            if client is None:
                raise TTSError("OpenAI client is not initialized")

            voice = cls._get_voice_from_config(speaker_config)
            # Type ignore: The API actually accepts all voices in VoiceType, despite what the type hints suggest
            response = client.audio.speech.create(
                model=cls.MODEL, voice=voice, input=text  # type: ignore
            )
            # OpenAI returns a streamable response
            if response is None:
                raise TTSError("Received None response from OpenAI API")

            return bytes(response.content)

        except AuthenticationError as e:
            raise TTSError(f"Authentication failed: {e}")
        except RateLimitError as e:
            # Convert OpenAI rate limit errors to our common exception type
            raise TTSRateLimitError(f"OpenAI rate limit exceeded: {e}")
        except APIError as e:
            raise TTSError(f"OpenAI API error: {e}")
        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    @classmethod
    def get_speaker_identifier(cls, speaker_config: Dict[str, Any]) -> str:
        """Get the voice identifier with model information."""
        voice = cls._get_voice_from_config(speaker_config)
        return f"{voice}_{cls.MODEL}"

    @classmethod
    def _get_voice_from_config(cls, speaker_config: Dict[str, Any]) -> VoiceType:
        """Extract and validate the voice from the speaker config."""
        voice = speaker_config.get("voice")
        if not voice or not isinstance(voice, str):
            raise TTSError(
                f"Missing or invalid 'voice' in speaker config: {speaker_config}"
            )

        # Ensure we return a valid VoiceType
        valid_voices = cls.get_valid_voices()
        if voice not in valid_voices:
            raise VoiceNotFoundError(
                f"Invalid voice '{voice}'. Must be one of: {', '.join(sorted(valid_voices))}"
            )
        return voice  # type: ignore  # We've validated it's a valid VoiceType

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
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        if "voice" not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice' in speaker configuration: {speaker_config}"
            )

        voice = speaker_config["voice"]
        if not isinstance(voice, str):
            raise ValueError("Field 'voice' must be a string")

        valid_voices = cls.get_valid_voices()
        if voice not in valid_voices:
            raise ValueError(
                f"Invalid voice '{voice}'. Must be one of: {', '.join(sorted(valid_voices))}"
            )
