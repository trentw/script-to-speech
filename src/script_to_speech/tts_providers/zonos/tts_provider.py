import hashlib
import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional, Set, Union

from zyphra import ZyphraClient, ZyphraError

from ..base.exceptions import TTSError, VoiceNotFoundError
from ..base.stateless_tts_provider import StatelessTTSProviderBase

# Define valid voice literals - these are the default voices supported by the Zonos API
DefaultVoiceType = Literal[
    "american_female",
    "american_male",
    "anime_girl",
    "british_female",
    "british_male",
    "energetic_boy",
    "energetic_girl",
    "japanese_female",
    "japanese_male",
]


class ZonosTTSProvider(StatelessTTSProviderBase):
    """
    TTS Provider implementation for Zonos's Text-to-Speech API using Zyphra client.
    """

    MIME_TYPE = "audio/mp3"
    MIN_SPEAKING_RATE = 5
    MAX_SPEAKING_RATE = 35
    VALID_LANGUAGES = {"en-us", "fr-fr", "de", "ja", "ko", "cmn"}

    @classmethod
    def instantiate_client(cls) -> ZyphraClient:
        """Instantiate and return the Zyphra API client."""
        api_key = os.environ.get("ZONOS_API_KEY")
        if not api_key:
            raise TTSError("ZONOS_API_KEY environment variable is not set")

        try:
            return ZyphraClient(api_key=api_key)
        except Exception as e:
            raise TTSError(f"Failed to initialize Zyphra client: {e}")

    @classmethod
    def get_valid_voices(cls) -> Set[str]:
        """Get the set of valid default voice names from DefaultVoiceType."""
        import typing

        # Get the arguments from the Literal type
        args = typing.get_args(DefaultVoiceType)
        return set(args)

    @classmethod
    def generate_audio(
        cls, client: ZyphraClient, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio for the given speaker and text."""

        try:
            default_voice_name = speaker_config.get("default_voice_name")
            speaking_rate = speaker_config.get("speaking_rate")
            language_code = speaker_config.get("language_iso_code")

            if default_voice_name is None:  # Should be caught by validation
                raise TTSError(
                    f"Missing 'default_voice_name' in speaker config: {speaker_config}"
                )

            params = {
                "text": text,
                "default_voice_name": default_voice_name,
                "mime_type": cls.MIME_TYPE,
            }

            # Add optional parameters only if they have non-empty values
            if speaking_rate:
                params["speaking_rate"] = speaking_rate
            if language_code:
                params["language_iso_code"] = language_code

            if client is None:
                raise TTSError("Zyphra client is not initialized")

            response = client.audio.speech.create(**params)
            if response is None:
                raise TTSError("Received None response from Zyphra API")

            return bytes(response)

        except ZyphraError as e:
            raise TTSError(f"Zyphra API error: {e}")
        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    @classmethod
    def get_speaker_identifier(cls, speaker_config: Dict[str, Any]) -> str:
        """Get the voice identifier that changes if any generation parameter changes."""
        # Create a dictionary of all non-empty parameters that affect voice generation
        default_voice_name = speaker_config.get("default_voice_name")
        speaking_rate = speaker_config.get("speaking_rate")
        language_code = speaker_config.get("language_iso_code")

        if default_voice_name is None:  # Should be caught by validation
            raise TTSError(
                f"Missing 'default_voice_name' in speaker config: {speaker_config}"
            )

        params = {"default_voice_name": default_voice_name, "mime_type": cls.MIME_TYPE}

        # Only include optional parameters if they have non-empty values
        if speaking_rate:
            params["speaking_rate"] = speaking_rate
        if language_code:
            params["language_iso_code"] = language_code

        # Create a hash of the parameters
        params_str = json.dumps(params, sort_keys=True)
        return (
            f"{default_voice_name}_{hashlib.md5(params_str.encode()).hexdigest()[:12]}"
        )

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "zonos"

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions."""
        valid_voices = cls.get_valid_voices()
        voices_str = ", ".join(sorted(valid_voices))

        return f"""# Zonos TTS Configuration
#
# Required Environment Variable:
#   ZONOS_API_KEY: Your Zonos API key
#
# Instructions:
#   - For each speaker, specify:
#     Required fields:
#       default_voice_name: One of [{voices_str}]
#     Optional fields:
#       speaking_rate: Float between {cls.MIN_SPEAKING_RATE} and {cls.MAX_SPEAKING_RATE}
#       language_iso_code: One of [{", ".join(sorted(cls.VALID_LANGUAGES))}]
#
# Example (minimal):
#   default:
#     default_voice_name: american_female
#
# Example (with optional fields):
#   MARIA:
#     default_voice_name: british_female
#     speaking_rate: 20
#     language_iso_code: fr-fr
#
# Note: Optional fields can be omitted entirely if not needed.
"""

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ["default_voice_name"]

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get optional configuration fields."""
        return ["speaking_rate", "language_iso_code"]

    @classmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        if "default_voice_name" not in speaker_config:
            raise ValueError(
                f"Missing required field 'default_voice_name' in speaker configuration: {speaker_config}"
            )

        default_voice_name = speaker_config["default_voice_name"]
        if not isinstance(default_voice_name, str):
            raise ValueError("Field 'default_voice_name' must be a string")

        valid_voices = cls.get_valid_voices()
        if default_voice_name not in valid_voices:
            raise VoiceNotFoundError(
                f"Invalid default_voice_name '{default_voice_name}'. Must be one of: {', '.join(sorted(valid_voices))}"
            )

        # Validate optional fields if present and non-empty
        speaking_rate = speaker_config.get("speaking_rate")
        if speaking_rate:
            if not isinstance(speaking_rate, (int, float)):
                raise ValueError("Field 'speaking_rate' must be a number")
            if not cls.MIN_SPEAKING_RATE <= speaking_rate <= cls.MAX_SPEAKING_RATE:
                raise ValueError(
                    f"Invalid speaking_rate '{speaking_rate}'. Must be between "
                    f"{cls.MIN_SPEAKING_RATE} and {cls.MAX_SPEAKING_RATE}"
                )

        language_code = speaker_config.get("language_iso_code")
        if language_code:
            if not isinstance(language_code, str):
                raise ValueError("Field 'language_iso_code' must be a string")
            if language_code not in cls.VALID_LANGUAGES:
                raise ValueError(
                    f"Invalid language_iso_code '{language_code}'. Must be one of: {', '.join(sorted(cls.VALID_LANGUAGES))}"
                )
