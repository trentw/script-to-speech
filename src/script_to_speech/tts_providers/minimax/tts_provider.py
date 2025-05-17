import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Set

import requests

from ..base.exceptions import TTSError, TTSRateLimitError
from ..base.stateless_tts_provider import StatelessTTSProviderBase


class MinimaxTTSProvider(StatelessTTSProviderBase):
    """
    TTS Provider implementation for Minimax's Text-to-Speech API.
    """

    PROVIDER_IDENTIFIER: str = "minimax"
    MIME_TYPE: str = "audio/mp3"
    API_URL: str = "https://api.minimaxi.chat/v1/t2a_v2"
    MODEL_ID: str = "speech-02-hd"

    # Valid voice IDs from Minimax API
    VALID_VOICE_IDS: Set[str] = {
        "English_expressive_narrator",
        "English_radiant_girl",
        "English_magnetic_voiced_man",
        "English_compelling_lady1",
        "English_Aussie_Bloke",
        "English_captivating_female1",
        "English_Upbeat_Woman",
        "English_Trustworth_Man",
        "English_CalmWoman",
        "English_UpsetGirl",
        "English_Gentle-voiced_man",
        "English_Whispering_girl_v3",
        "English_Diligent_Man",
        "English_Graceful_Lady",
        "English_ReservedYoungMan",
        "English_PlayfulGirl",
        "English_ManWithDeepVoice",
        "English_GentleTeacher",
        "English_MaturePartner",
        "English_FriendlyPerson",
        "English_MatureBoss",
        "English_Debator",
        "English_Abbess",
        "English_LovelyGirl",
        "English_Steadymentor",
        "English_Deep-VoicedGentleman",
        "English_DeterminedMan",
        "English_Wiselady",
        "English_CaptivatingStoryteller",
        "English_AttractiveGirl",
        "English_DecentYoungMan",
        "English_SentimentalLady",
        "English_ImposingManner",
        "English_SadTeen",
        "English_ThoughtfulMan",
        "English_PassionateWarrior",
        "English_DecentBoy",
        "English_WiseScholar",
        "English_Soft-spokenGirl",
        "English_SereneWoman",
        "English_ConfidentWoman",
        "English_patient_man_v1",
        "English_Comedian",
        "English_GorgeousLady",
        "English_BossyLeader",
        "English_LovelyLady",
        "English_Strong-WilledBoy",
        "English_Deep-tonedMan",
        "English_StressedLady",
        "English_AssertiveQueen",
        "English_AnimeCharacter",
        "English_Jovialman",
        "English_WhimsicalGirl",
        "English_CharmingQueen",
        "English_Kind-heartedGirl",
        "English_FriendlyNeighbor",
        "English_Sweet_Female_4",
        "English_Magnetic_Male_2",
        "English_Lively_Male_11",
        "English_Friendly_Female_3",
        "English_Steady_Female_1",
        "English_Lively_Male_10",
        "English_Magnetic_Male_12",
        "English_Steady_Female_5",
    }

    # Valid emotions from API docs
    VALID_EMOTIONS: Set[str] = {
        "happy",
        "sad",
        "angry",
        "fear",
        "disgust",
        "neutral",
        "surprise",
    }

    # Valid language boosts from API docs
    VALID_LANGUAGE_BOOSTS: Set[str] = {
        "Chinese",
        "English",
        "Japanese",
        "Korean",
        "French",
        "Spanish",
        "German",
    }

    # Audio settings
    AUDIO_SAMPLE_RATE: int = 44100
    AUDIO_BITRATE: int = 256000
    AUDIO_FORMAT: str = "mp3"
    AUDIO_CHANNELS: int = 2
    OUTPUT_FORMAT_API: str = "hex"

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return cls.PROVIDER_IDENTIFIER

    @classmethod
    def instantiate_client(cls) -> None:
        """
        Minimax doesn't require a client instantiation, API key/group ID handled in generate_audio.
        """
        return None

    @classmethod
    def generate_audio(
        cls, client: None, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """
        Generate audio for the given speaker and text using Minimax API.

        Args:
            client: Not used for Minimax
            speaker_config: Configuration for the speaker
            text: Text to convert to speech

        Returns:
            bytes: Audio data

        Raises:
            TTSError: If there's an error with the API request
            TTSRateLimitError: If the API rate limit is exceeded
        """
        # Get API key and group ID from environment variables
        api_key = os.environ.get("MINIMAX_API_KEY")
        group_id = os.environ.get("MINIMAX_GROUP_ID")

        if not api_key:
            raise TTSError("MINIMAX_API_KEY environment variable is not set")
        if not group_id:
            raise TTSError("MINIMAX_GROUP_ID environment variable is not set")

        # Construct URL with group ID
        url = f"{cls.API_URL}?GroupId={group_id}"

        # Construct the main payload with common parameters
        payload = {
            "model": cls.MODEL_ID,
            "text": text,  # API handles pauses like <#x#>
            "stream": False,
            "audio_setting": {
                "sample_rate": cls.AUDIO_SAMPLE_RATE,
                "bitrate": cls.AUDIO_BITRATE,
                "format": cls.AUDIO_FORMAT,
                "channel": cls.AUDIO_CHANNELS,
            },
            "output_format": cls.OUTPUT_FORMAT_API,
        }

        # Voice Definition Logic - Either use timber_weights or voice_setting, but not both
        if "voice_mix" in speaker_config:
            # Use timber_weights directly in the main payload
            payload["timber_weights"] = speaker_config["voice_mix"]
        else:
            # Initialize voice settings payload
            voice_setting_payload = {"voice_id": speaker_config["voice_id"]}

            # Add optional parameters if they exist in speaker_config
            for param, api_param in [
                ("speed", "speed"),
                ("volume", "vol"),
                ("pitch", "pitch"),
                ("emotion", "emotion"),
            ]:
                if param in speaker_config:
                    voice_setting_payload[api_param] = speaker_config[param]

            # Handle english_normalization with default=true
            english_norm = speaker_config.get("english_normalization", True)
            voice_setting_payload["english_normalization"] = english_norm

            # Add voice_setting to payload
            payload["voice_setting"] = voice_setting_payload

        # Handle language_boost with default="English"
        language_boost = speaker_config.get("language_boost", "English")
        payload["language_boost"] = language_boost

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            # Make the API request
            response = requests.post(url, headers=headers, json=payload)

            # Check HTTP status code
            if response.status_code != 200:
                raise TTSError(
                    f"Minimax API HTTP error: {response.status_code} - {response.text}"
                )

            # Parse the JSON response
            parsed_json = response.json()

            # Check API response status
            base_resp = parsed_json.get("base_resp", {})
            status_code = base_resp.get("status_code")

            if status_code != 0:  # 0 indicates success
                status_msg = base_resp.get("status_msg", "Unknown error")

                # Status code 1039 is Minimax's "Trigger TPM flow restriction"
                # Also check for "rate limit" in the message for any other cases
                if (
                    status_code == 429
                    or status_code == 1039
                    or (status_msg and "rate limit" in status_msg.lower())
                ):
                    raise TTSRateLimitError(
                        f"Minimax API rate limit exceeded: {status_code} - {status_msg}"
                    )

                # Handle other specific error codes
                error_message = f"Minimax API error: {status_code} - {status_msg}"
                if status_code == 1000:
                    error_message = f"Minimax API unknown error: {status_msg}"
                elif status_code == 1001:
                    error_message = f"Minimax API timeout: {status_msg}"
                elif status_code == 1002:
                    error_message = (
                        f"Minimax API flow restriction triggered: {status_msg}"
                    )
                elif status_code == 1004:
                    error_message = f"Minimax API authentication failure: {status_msg}"
                elif status_code == 1042:
                    error_message = (
                        f"Minimax API illegal characters exceeded maximum: {status_msg}"
                    )
                elif status_code == 2013:
                    error_message = f"Minimax API invalid input format: {status_msg}"

                raise TTSError(error_message)

            # Extract audio data
            if "data" not in parsed_json or "audio" not in parsed_json["data"]:
                raise TTSError("Minimax API returned invalid response format")

            # Convert hex string to bytes
            audio_hex = parsed_json["data"]["audio"]
            return bytes.fromhex(audio_hex)

        except requests.RequestException as e:
            raise TTSError(f"Request to Minimax API failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise TTSError(f"Failed to parse Minimax API response: {str(e)}") from e
        except TTSRateLimitError:
            # Re-raise TTSRateLimitError directly without wrapping it
            raise
        except Exception as e:
            raise TTSError(
                f"Unexpected error generating audio with Minimax: {str(e)}"
            ) from e

    @classmethod
    def get_max_download_threads(cls) -> int:
        """
        Get the max number of concurrent download threads for Minimax provider.

        Returns:
            int: Returns 5 concurrent threads (default assumption)
        """
        return 5

    @classmethod
    def get_speaker_identifier(cls, speaker_config: Dict[str, Any]) -> str:
        """
        Get the voice identifier that changes if any generation parameter changes.

        Args:
            speaker_config: Configuration for the speaker

        Returns:
            str: A unique identifier based on the speaker configuration

        Raises:
            TTSError: If required fields are missing
        """
        # Initialize with fixed settings
        params_to_hash = {
            "model_id": cls.MODEL_ID,
            "audio_sample_rate": cls.AUDIO_SAMPLE_RATE,
            "audio_bitrate": cls.AUDIO_BITRATE,
            "audio_format": cls.AUDIO_FORMAT,
            "audio_channels": cls.AUDIO_CHANNELS,
            "output_format": cls.OUTPUT_FORMAT_API,
            "mime_type": cls.MIME_TYPE,
        }

        # Add voice definition (either voice_mix or voice_id)
        if "voice_mix" in speaker_config:
            params_to_hash["voice_mix"] = speaker_config["voice_mix"]
        elif "voice_id" in speaker_config:
            params_to_hash["voice_id"] = speaker_config["voice_id"]
        else:
            raise TTSError(
                "Either 'voice_id' or 'voice_mix' must be provided in speaker_config"
            )

        # Add optional parameters if present
        for param in [
            "speed",
            "volume",
            "pitch",
            "emotion",
            "english_normalization",
            "language_boost",
        ]:
            if param in speaker_config:
                params_to_hash[param] = speaker_config[param]

        # Generate hash
        params_str = json.dumps(params_to_hash, sort_keys=True)
        hash_val = hashlib.md5(params_str.encode()).hexdigest()[:12]
        return hash_val

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get required configuration fields."""
        return ["voice_id"]

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get optional configuration fields."""
        return [
            "voice_mix",
            "speed",
            "volume",
            "pitch",
            "emotion",
            "english_normalization",
            "language_boost",
        ]

    @classmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """
        Validate speaker configuration for Minimax.

        Args:
            speaker_config: Configuration for the speaker

        Raises:
            ValueError: If the configuration is invalid
        """
        has_voice_mix = "voice_mix" in speaker_config
        has_voice_id = (
            "voice_id" in speaker_config and speaker_config["voice_id"]
        )  # Non-empty voice_id

        # Check that at least one of voice_id or voice_mix is provided
        if not has_voice_mix and not has_voice_id:
            raise ValueError(
                f"Either 'voice_id' or 'voice_mix' must be provided in Minimax speaker configuration: {speaker_config}"
            )

        # Check that both voice_id and voice_mix are not provided
        if has_voice_mix and has_voice_id:
            raise ValueError(
                f"Cannot provide both 'voice_id' and 'voice_mix' in Minimax speaker configuration: {speaker_config}"
            )

        # Validate voice_id if present
        if has_voice_id:
            voice_id = speaker_config["voice_id"]
            if not isinstance(voice_id, str):
                raise ValueError("Field 'voice_id' for Minimax must be a string")

            if voice_id not in cls.VALID_VOICE_IDS:
                raise ValueError(
                    f"Invalid voice_id '{voice_id}' for Minimax. Must be one of: {', '.join(sorted(cls.VALID_VOICE_IDS))}"
                )

        # Validate voice_mix if present
        if has_voice_mix:
            voice_mix = speaker_config["voice_mix"]

            if not isinstance(voice_mix, list):
                raise ValueError("Field 'voice_mix' for Minimax must be a list")

            if not 1 <= len(voice_mix) <= 4:
                raise ValueError("Field 'voice_mix' for Minimax must contain 1-4 items")

            for i, item in enumerate(voice_mix):
                if not isinstance(item, dict):
                    raise ValueError(f"Item {i} in 'voice_mix' must be a dictionary")

                if "voice_id" not in item:
                    raise ValueError(f"Missing 'voice_id' in voice_mix item {i}")

                if "weight" not in item:
                    raise ValueError(f"Missing 'weight' in voice_mix item {i}")

                if not isinstance(item["voice_id"], str):
                    raise ValueError(
                        f"'voice_id' in voice_mix item {i} must be a string"
                    )

                if item["voice_id"] not in cls.VALID_VOICE_IDS:
                    raise ValueError(
                        f"Invalid voice_id '{item['voice_id']}' in voice_mix item {i}. "
                        f"Must be one of: {', '.join(sorted(cls.VALID_VOICE_IDS))}"
                    )

                if not isinstance(item["weight"], int):
                    raise ValueError(
                        f"'weight' in voice_mix item {i} must be an integer"
                    )

                if not 1 <= item["weight"] <= 100:
                    raise ValueError(
                        f"'weight' in voice_mix item {i} must be between 1 and 100"
                    )

        # Validate optional fields if present
        if "speed" in speaker_config:
            speed = speaker_config["speed"]
            if not isinstance(speed, (int, float)):
                raise ValueError("Field 'speed' for Minimax must be a number")
            if not 0.5 <= speed <= 2.0:
                raise ValueError(
                    f"Invalid speed '{speed}' for Minimax. Must be between 0.5 and 2.0"
                )

        if "volume" in speaker_config:
            volume = speaker_config["volume"]
            if not isinstance(volume, (int, float)):
                raise ValueError("Field 'volume' for Minimax must be a number")
            if not 0.0 < volume <= 10.0:
                raise ValueError(
                    f"Invalid volume '{volume}' for Minimax. Must be between >0.0 and 10.0"
                )

        if "pitch" in speaker_config:
            pitch = speaker_config["pitch"]
            if not isinstance(pitch, int):
                raise ValueError("Field 'pitch' for Minimax must be an integer")
            if not -12 <= pitch <= 12:
                raise ValueError(
                    f"Invalid pitch '{pitch}' for Minimax. Must be between -12 and 12"
                )

        if "emotion" in speaker_config:
            emotion = speaker_config["emotion"]
            if not isinstance(emotion, str):
                raise ValueError("Field 'emotion' for Minimax must be a string")
            if emotion not in cls.VALID_EMOTIONS:
                raise ValueError(
                    f"Invalid emotion '{emotion}' for Minimax. Must be one of: {', '.join(sorted(cls.VALID_EMOTIONS))}"
                )

        if "english_normalization" in speaker_config:
            english_norm = speaker_config["english_normalization"]
            if not isinstance(english_norm, bool):
                raise ValueError(
                    "Field 'english_normalization' for Minimax must be a boolean"
                )

        if "language_boost" in speaker_config:
            language_boost = speaker_config["language_boost"]
            if not isinstance(language_boost, str):
                raise ValueError("Field 'language_boost' for Minimax must be a string")
            if language_boost not in cls.VALID_LANGUAGE_BOOSTS:
                raise ValueError(
                    f"Invalid language_boost '{language_boost}' for Minimax. "
                    f"Must be one of: {', '.join(sorted(cls.VALID_LANGUAGE_BOOSTS))}"
                )

    @classmethod
    def get_yaml_instructions(cls) -> str:
        """Get configuration instructions for Minimax TTS."""
        # Format voice_ids with 10 per line
        sorted_voice_ids = sorted(cls.VALID_VOICE_IDS)
        voice_ids_chunks = [
            sorted_voice_ids[i : i + 7] for i in range(0, len(sorted_voice_ids), 7)
        ]
        voice_ids_formatted = "\n#   ".join(
            [", ".join(chunk) for chunk in voice_ids_chunks]
        )

        emotions_str = ", ".join(sorted(cls.VALID_EMOTIONS))
        language_boosts_str = ", ".join(sorted(cls.VALID_LANGUAGE_BOOSTS))

        return f"""# Minimax TTS Configuration
#
# Required Environment Variables:
#   MINIMAX_API_KEY: Your Minimax API key
#   MINIMAX_GROUP_ID: Your Minimax Group ID
#
# Provider Name for YAML: {cls.PROVIDER_IDENTIFIER}
#
# Valid voice_id: 
#   {voice_ids_formatted}
#
# Instructions:
#   - For each speaker using Minimax, specify EITHER:
#     Option 1: Single voice
#       voice_id: (string) One of valid voice_id
#
#     Option 2: Voice mix (cannot be used with voice_id)
#       voice_mix: (list) Each item must be a dict with:
#                  - voice_id: (string) One of valid voice_id
#                  - weight: (int) Between 1-100
#                  List can contain 1-4 items.
#
#     Optional fields:
#       speed: (float) Between 0.5-2.0 (defaults to 1)
#       volume: (float) Between 0.0-10.0 (defaults to 1)
#       pitch: (int) Between -12 to 12 (defaults to 0)
#       emotion: (string) One of [{emotions_str}]
#       english_normalization: (boolean) true or false (defaults to true if not specified)
#       language_boost: (string) One of [{language_boosts_str}] (defaults to "English" if not specified)
#
# Example (single voice):
#   JOHN:
#     provider: {cls.PROVIDER_IDENTIFIER}
#     voice_id: English_expressive_narrator
#
# Example (with voice_mix):
#   MARIA:
#     provider: {cls.PROVIDER_IDENTIFIER}
#     voice_mix:
#       - voice_id: English_ConfidentWoman
#         weight: 70
#       - voice_id: English_SereneWoman
#         weight: 30
#
# Example (with optional fields):
#   DAVID:
#     provider: {cls.PROVIDER_IDENTIFIER}
#     voice_id: Serious_Man
#     speed: 1.2
#     volume: 8.0
#     pitch: 2
#     emotion: happy
#     english_normalization: false  # Override default (true)
#     language_boost: Japanese  # Override default (English)
#
# Note: If optional fields are not provided, API defaults will apply.
"""
