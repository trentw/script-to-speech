import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Set

from cartesia import Cartesia
from cartesia.core.api_error import ApiError  # For specific Cartesia errors
from cartesia.tts.requests.output_format import OutputFormatParams
from cartesia.tts.requests.tts_request_voice_specifier import (
    TtsRequestVoiceSpecifierParams,
)

from ..base.exceptions import TTSError, TTSRateLimitError
from ..base.stateless_tts_provider import StatelessTTSProviderBase


class CartesiaTTSProvider(StatelessTTSProviderBase):
    """
    TTS Provider implementation for Cartesia's Text-to-Speech API using the official Python SDK.
    """

    PROVIDER_IDENTIFIER: str = "cartesia"
    MIME_TYPE: str = "audio/mp3"

    # Based on user-provided list
    VALID_LANGUAGES: Set[str] = {
        "en",
        "fr",
        "de",
        "es",
        "pt",
        "zh",
        "ja",
        "hi",
        "it",
        "ko",
        "nl",
        "pl",
        "ru",
        "sv",
        "tr",
    }
    VALID_SPEEDS: Set[str] = {"slow", "normal", "fast"}

    DEFAULT_LANGUAGE: str = "en"
    DEFAULT_SPEED: str = "normal"
    MODEL_ID: str = "sonic-2"

    OUTPUT_BIT_RATE: int = 192000
    OUTPUT_SAMPLE_RATE: int = 44100

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return cls.PROVIDER_IDENTIFIER

    @classmethod
    def instantiate_client(cls) -> Cartesia:
        """Instantiate and return the Cartesia API client."""
        api_key = os.environ.get("CARTESIA_API_KEY")
        if not api_key:
            raise TTSError("CARTESIA_API_KEY environment variable is not set")

        try:
            return Cartesia(api_key=api_key)
        except Exception as e:
            # The Cartesia SDK might raise its own specific errors on init
            raise TTSError(f"Failed to initialize Cartesia client: {e}") from e

    @classmethod
    def generate_audio(
        cls, client: Cartesia, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio for the given speaker and text using Cartesia SDK."""

        voice_id = speaker_config.get("voice_id")
        if not voice_id:  # Should be caught by validation, but good to double check
            raise TTSError(
                f"Missing 'voice_id' in speaker config for Cartesia: {speaker_config}"
            )

        language = speaker_config.get("language", cls.DEFAULT_LANGUAGE)
        speed = speaker_config.get("speed", cls.DEFAULT_SPEED)

        # Create voice payload with the correct type
        voice_payload: TtsRequestVoiceSpecifierParams = {"mode": "id", "id": voice_id}

        # Add experimental_controls for speed if specified or non-default
        if speed != cls.DEFAULT_SPEED or "speed" in speaker_config:
            voice_payload["experimental_controls"] = {"speed": speed, "emotion": []}

        output_format_payload: OutputFormatParams = {
            "container": "mp3",
            "bit_rate": cls.OUTPUT_BIT_RATE,
            "sample_rate": cls.OUTPUT_SAMPLE_RATE,
        }

        try:
            # The Cartesia SDK's tts.bytes() method returns an iterator of bytes chunks
            response_iterator = client.tts.bytes(
                model_id=cls.MODEL_ID,
                transcript=text,
                voice=voice_payload,
                language=language,
                output_format=output_format_payload,
            )

            # Concatenate all chunks into a single bytes object
            audio_chunks = []
            for chunk in response_iterator:
                audio_chunks.append(chunk)

            if not audio_chunks:
                raise TTSError("Cartesia SDK returned empty response")

            return b"".join(audio_chunks)
        except ApiError as e:
            if e.status_code == 429:  # Too Many Requests
                raise TTSRateLimitError(
                    f"Cartesia API rate limit exceeded: {e.status_code} - {str(e.body)}"
                ) from e
            # Handle other specific Cartesia errors
            raise TTSError(
                f"Cartesia API error ({e.status_code}): {str(e.body)}"
            ) from e
        except Exception as e:  # Catch any other unexpected errors during SDK call
            raise TTSError(f"Failed to generate audio with Cartesia SDK: {e}") from e

    @classmethod
    def get_max_download_threads(cls) -> int:
        """
        Get the max number of concurrent download threads for OpenAI provider.

        Returns:
            int: Returns 2 concurrent threads
        """
        return 2

    @classmethod
    def get_speaker_identifier(cls, speaker_config: Dict[str, Any]) -> str:
        """Get the voice identifier that changes if any generation parameter changes."""
        voice_id = speaker_config.get("voice_id")
        if voice_id is None:
            raise TTSError(
                "Missing 'voice_id' in speaker_config for get_speaker_identifier"
            )

        params_to_hash = {
            "voice_id": voice_id,
            "language": speaker_config.get("language", cls.DEFAULT_LANGUAGE),
            "speed": speaker_config.get("speed", cls.DEFAULT_SPEED),
            "model_id": cls.MODEL_ID,
            "output_container": "mp3",
            "output_bit_rate": cls.OUTPUT_BIT_RATE,
            "output_sample_rate": cls.OUTPUT_SAMPLE_RATE,
            "mime_type": cls.MIME_TYPE,
        }

        params_str = json.dumps(params_to_hash, sort_keys=True)
        hash_val = hashlib.md5(params_str.encode()).hexdigest()[:12]
        return f"{hash_val}"

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ["voice_id"]

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get optional configuration fields."""
        return ["language", "speed"]

    @classmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration for Cartesia."""
        if "voice_id" not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice_id' in Cartesia speaker configuration: {speaker_config}"
            )
        if not isinstance(speaker_config["voice_id"], str):
            raise ValueError("Field 'voice_id' for Cartesia must be a string")

        if "language" in speaker_config:
            language = speaker_config["language"]
            if not isinstance(language, str):
                raise ValueError("Field 'language' for Cartesia must be a string")
            if language not in cls.VALID_LANGUAGES:
                raise ValueError(
                    f"Invalid language '{language}' for Cartesia. Must be one of: {', '.join(sorted(cls.VALID_LANGUAGES))}"
                )

        if "speed" in speaker_config:
            speed = speaker_config["speed"]
            if not isinstance(speed, str):
                raise ValueError("Field 'speed' for Cartesia must be a string")
            if speed not in cls.VALID_SPEEDS:
                raise ValueError(
                    f"Invalid speed '{speed}' for Cartesia. Must be one of: {', '.join(sorted(cls.VALID_SPEEDS))}"
                )

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions for Cartesia TTS."""
        languages_str = ", ".join(sorted(cls.VALID_LANGUAGES))
        speeds_str = ", ".join(sorted(cls.VALID_SPEEDS))
        return f"""# Cartesia TTS Configuration
#
# Required Environment Variable:
#   CARTESIA_API_KEY: Your Cartesia API key
#
# Provider Name for YAML: {cls.PROVIDER_IDENTIFIER}
#
# Instructions:
#   - For each speaker using Cartesia, specify:
#     Required fields:
#       voice_id: (string) The ID of the Cartesia voice to use.
#     Optional fields:
#       language: (string) One of [{languages_str}]. Defaults to '{cls.DEFAULT_LANGUAGE}'.
#       speed: (string) One of [{speeds_str}]. Defaults to '{cls.DEFAULT_SPEED}'.
#
# Example (minimal):
#   TOM:
#     provider: {cls.PROVIDER_IDENTIFIER}
#     voice_id: 4df027cb-2920-4a1f-8c34-f21529d5c3fe
#
# Example (with optional fields):
#   CANDICE:
#     provider: {cls.PROVIDER_IDENTIFIER}
#     voice_id: bf0a246a-8642-498a-9950-80c35e9276b5
#     language: fr
#     speed: fast
"""
