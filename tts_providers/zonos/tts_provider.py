import hashlib
import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

from zyphra import ZyphraClient, ZyphraError

from tts_providers.base.exceptions import TTSError, VoiceNotFoundError
from tts_providers.base.stateless_tts_provider import StatelessTTSProviderBase


class ZonosTTSProvider(StatelessTTSProviderBase):
    """
    TTS Provider implementation for Zonos's Text-to-Speech API using Zyphra client.
    """

    MIME_TYPE = "audio/mp3"
    MIN_SPEAKING_RATE = 5
    MAX_SPEAKING_RATE = 35
    MIN_SEED = -1
    MAX_SEED = 2147483647
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
    def generate_audio(
        cls, client: ZyphraClient, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio for the given speaker and text."""

        try:
            voice_seed = speaker_config.get("voice_seed")
            speaking_rate = speaker_config.get("speaking_rate")
            language_code = speaker_config.get("language_iso_code")

            if voice_seed is None:  # Should be caught by validation
                raise TTSError(
                    f"Missing 'voice_seed' in speaker config: {speaker_config}"
                )

            params = {
                "text": text,
                "seed": int(voice_seed),
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
        voice_seed = speaker_config.get("voice_seed")
        speaking_rate = speaker_config.get("speaking_rate")
        language_code = speaker_config.get("language_iso_code")

        if voice_seed is None:  # Should be caught by validation
            raise TTSError(f"Missing 'voice_seed' in speaker config: {speaker_config}")

        params = {"seed": voice_seed, "mime_type": cls.MIME_TYPE}

        # Only include optional parameters if they have non-empty values
        if speaking_rate:
            params["speaking_rate"] = speaking_rate
        if language_code:
            params["language_iso_code"] = language_code

        # Create a hash of the parameters
        params_str = json.dumps(params, sort_keys=True)
        return f"s{voice_seed}_{hashlib.md5(params_str.encode()).hexdigest()[:12]}"

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
#     Required fields:
#       voice_seed: Integer between -1 and 2147483647
#     Optional fields:
#       speaking_rate: Float between 5 and 35
#       language_iso_code: One of [en-us, fr-fr, de, ja, ko, cmn]
#
# Example (minimal):
#   default:
#     voice_seed: 12345
#
# Example (with optional fields):
#   MARIA:
#     voice_seed: 67890
#     speaking_rate: 20
#     language_iso_code: fr-fr
#
# Note: Optional fields can be omitted entirely if not needed.
"""

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ["voice_seed"]

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get optional configuration fields."""
        return ["speaking_rate", "language_iso_code"]

    @classmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        if "voice_seed" not in speaker_config:
            raise ValueError(
                f"Missing required field 'voice_seed' in speaker configuration: {speaker_config}"
            )

        voice_seed = int(speaker_config["voice_seed"])
        if not isinstance(speaker_config["voice_seed"], int):
            raise ValueError("Field 'voice_seed' must be an integer")

        if not cls.MIN_SEED <= voice_seed <= cls.MAX_SEED:
            raise ValueError(
                f"Invalid voice_seed '{voice_seed}'. Must be between "
                f"{cls.MIN_SEED} and {cls.MAX_SEED}"
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
