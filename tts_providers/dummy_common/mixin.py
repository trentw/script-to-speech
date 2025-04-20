from typing import Any, Dict, List, cast

from dummy_tts_backend.backend import DummyTTSBackend


class DummyProviderMixin:
    """
    Common mixin class for dummy TTS providers.

    This mixin contains shared logic for both dummy providers, such as:
    - Configuration validation
    - Identifier generation
    - Client instantiation
    - Audio generation
    """

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get YAML configuration instructions."""
        return """# Dummy TTS Provider Configuration
#
# This provider is for testing purposes only and does not require any API keys.
#
# Optional fields:
#   dummy_id: A custom identifier for the voice
#   dummy_request_time: Override the base request time (seconds)
#   dummy_request_additional_delay: Add extra delay to requests (seconds)
#   dummy_generate_silent: Generate silent audio instead of dummy sound
#
# Example:
#   default:
#     provider: dummy_stateless
#
#   CHARACTER_A:
#     provider: dummy_stateful
#     id: custom_voice_id
#     dummy_request_time: 0.5
#     dummy_request_additional_delay: 0.2
#     dummy_generate_silent: false
"""

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get list of required config fields."""
        return []  # No required fields for dummy providers

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get list of optional config fields."""
        return [
            "dummy_id",
            "dummy_request_time",
            "dummy_request_additional_delay",
            "dummy_generate_silent",
        ]

    @classmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker configuration."""
        # Check id type if present
        if "dummy_id" in speaker_config and not isinstance(
            speaker_config["dummy_id"], str
        ):
            raise ValueError("Field 'dummy_id' must be a string")

        # Check dummy_request_time type if present
        if "dummy_request_time" in speaker_config and not isinstance(
            speaker_config["dummy_request_time"], (int, float)
        ):
            raise ValueError("Field 'dummy_request_time' must be a number")

        # Check dummy_request_additional_delay type if present
        if "dummy_request_additional_delay" in speaker_config and not isinstance(
            speaker_config["dummy_request_additional_delay"], (int, float)
        ):
            raise ValueError("Field 'dummy_request_additional_delay' must be a number")

        # Check dummy_generate_silent type if present
        if "dummy_generate_silent" in speaker_config and not isinstance(
            speaker_config["dummy_generate_silent"], bool
        ):
            raise ValueError("Field 'dummy_generate_silent' must be a boolean")

    @classmethod
    def get_speaker_identifier(cls, speaker_config: Dict[str, Any]) -> str:
        """
        Get unique voice identifier from config.

        If a dummy_id is provided in the config, use it to create a unique identifier.
        Otherwise, use a default identifier based on whether silent audio is requested.
        """
        speaker_id = speaker_config.get("dummy_id")

        if speaker_id and isinstance(speaker_id, str) and speaker_id.strip():
            return f"dummy_id_{speaker_id.strip()}"

        # No valid ID provided, use default based on silent flag
        is_silent = speaker_config.get("dummy_generate_silent", False)
        return "dummy_silent_voice" if is_silent else "dummy_standard_voice"

    @classmethod
    def get_max_download_threads(cls) -> int:
        """Get the max number of concurrent download threads."""
        return 5

    @classmethod
    def instantiate_client(cls) -> Any:
        """Instantiate and return the API client."""
        return DummyTTSBackend().create_client()

    @staticmethod
    def _generate_dummy_audio(
        client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """
        Generate dummy audio using the client and config.

        This is a helper method used by both stateless and stateful providers.
        """
        # Extract optional parameters from speaker_config
        request_time = speaker_config.get("dummy_request_time")
        additional_delay = speaker_config.get("dummy_request_additional_delay")
        generate_silent = speaker_config.get("dummy_generate_silent", False)

        # Call the client's generate_audio method with the extracted parameters
        return cast(
            bytes,
            client.generate_audio(
                text=text,
                request_time=request_time,
                additional_delay=additional_delay,
                generate_silent=generate_silent,
            ),
        )
