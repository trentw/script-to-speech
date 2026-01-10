import argparse
import importlib
import io
import json
import os
import re
import shlex
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from ..tts_providers.base.exceptions import TTSError, VoiceNotFoundError
from ..tts_providers.base.stateful_tts_provider import StatefulTTSProviderBase
from ..tts_providers.base.stateless_tts_provider import StatelessTTSProviderBase
from ..tts_providers.tts_provider_manager import TTSProviderManager
from .audio_utils import configure_ffmpeg, split_audio_on_silence
from .logging import get_screenplay_logger

logger = get_screenplay_logger("utils.generate_standalone_speech")

# Constant sentence to prepend in split mode
SPLIT_SENTENCE = "this is a constant sentence. ... , ..."


def clean_filename(text: str) -> str:
    """Convert text to valid filename."""
    cleaned = re.sub(r"[^\w\s-]", "", text)
    return cleaned.replace(" ", "_")


def get_provider_class(
    provider_name: str,
) -> Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]]:
    """Get the provider class for a given provider name."""
    try:
        module = importlib.import_module(
            f"script_to_speech.tts_providers.{provider_name}.tts_provider"
        )

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(
                    attr, (StatelessTTSProviderBase, StatefulTTSProviderBase)
                )
                and attr not in (StatelessTTSProviderBase, StatefulTTSProviderBase)
                and attr.get_provider_identifier() == provider_name
            ):
                return attr

        raise ValueError(f"No valid provider class found for {provider_name}")
    except ImportError as e:
        raise ValueError(f"Provider '{provider_name}' not found: {e}")


def generate_standalone_speech(
    tts_manager: TTSProviderManager,
    text: str,
    variant_num: int = 1,
    output_dir: str = "standalone_speech",
    split_audio: bool = False,
    silence_threshold: int = -40,
    min_silence_len: int = 500,
    keep_silence: int = 100,
    output_filename: Optional[str] = None,
) -> None:
    """
    Generate speech using specified provider via TTSProviderManager.

    Args:
        tts_manager: TTSProviderManager instance to use for generation
        text: Text to convert to speech
        variant_num: Variant number when generating multiple versions
        output_dir: Directory for output files
        split_audio: Whether to split the audio after a constant sentence
        silence_threshold: Silence threshold in dBFS for splitting
        min_silence_len: Minimum silence length in ms for splitting
        keep_silence: Amount of silence to keep in ms after splitting
        output_filename: Optional custom filename (without extension)
    """
    try:
        # Prepend constant sentence if split mode is enabled
        generation_text = f"{SPLIT_SENTENCE} {text}" if split_audio else text

        # Generate audio using TTSProviderManager
        # "default" is the key used in _build_tts_provider_config_data
        audio_data = tts_manager.generate_audio("default", generation_text)

        # Create timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create base filename components
        text_preview = clean_filename(text[:30])
        variant_suffix = f"_variant{variant_num}" if variant_num > 1 else ""

        # Get provider and speaker identifiers from TTSProviderManager
        provider_id = tts_manager.get_provider_identifier("default")
        voice_id = tts_manager.get_speaker_identifier("default")

        if split_audio:
            # Process audio through splitter
            try:
                split_segment = split_audio_on_silence(
                    audio_data,
                    min_silence_len=min_silence_len,
                    silence_thresh=silence_threshold,
                    keep_silence=keep_silence,
                )

                if split_segment is None:
                    logger.error("Failed to detect silence for splitting audio")
                    return

                # Export split audio to bytes
                output_buffer = io.BytesIO()
                split_segment.export(output_buffer, format="mp3")
                audio_data = output_buffer.getvalue()

                # Add split indicator to filename
                text_preview = f"split_{text_preview}"

            except Exception as e:
                logger.error(f"Error splitting audio: {e}")
                return

        # Create final filename and path
        if output_filename:
            filename = f"{output_filename}{variant_suffix}.mp3"
        else:
            filename = f"{provider_id}--{voice_id}--{text_preview}{variant_suffix}--{timestamp}.mp3"
        output_path = os.path.join(output_dir, filename)

        # Save audio
        with open(output_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"Generated speech file: {output_path}")

    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise


def get_command_string(
    provider_manager: "TTSProviderManager", speaker: Optional[str], texts: List[str]
) -> str:
    """Generate command line string for standalone speech generation.

    Args:
        provider_manager: TTSProviderManager instance
        speaker: The speaker to get configuration for, or None for default speaker
        texts: List of text strings to convert

    Returns:
        Command line string that can be used to generate the audio
    """
    try:
        # Reconciling how default speaker is displayed vs. used in voice configuration
        if speaker == "(default)":
            speaker = "default"

        # Get provider name and configuration for the speaker
        provider_name = provider_manager.get_provider_for_speaker(speaker or "default")
        config = provider_manager.get_speaker_configuration(speaker)

        # Get the provider class to determine required fields
        provider_class = get_provider_class(provider_name)
        required_fields = provider_class.get_required_fields()

        # Build command with all configuration parameters
        config_params = []

        # First, add all parameters from the config
        for param_name, param_value in config.items():
            if (
                param_name != "provider" and param_value is not None
            ):  # Filter out 'provider' key
                # Handle complex types (lists, dicts) by serializing to JSON
                if isinstance(param_value, (list, dict)):
                    value_str = json.dumps(param_value)
                else:
                    value_str = str(param_value)

                # Quote the value for safe command-line usage
                config_params.append(f"--{param_name} {shlex.quote(value_str)}")

        # Then, ensure all required fields are included
        for field in required_fields:
            if field not in config:
                # Add the required field with an empty string value
                config_params.append(f"--{field} {shlex.quote('')}")

        texts_quoted = [f'"{t}"' for t in texts]

        return f"uv run sts-generate-standalone-speech {provider_name} {' '.join(config_params)} {' '.join(texts_quoted)}"
    except Exception as e:
        logger.error(f"Error generating command string: {e}")
        return ""


def json_or_str_type(value_str: str) -> Any:
    """
    Attempts to parse a string as JSON. If successful, returns the parsed object.
    Otherwise, returns the original string.

    Args:
        value_str: The string value to parse

    Returns:
        The parsed JSON object if valid, otherwise the original string
    """
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, TypeError):
        # If it's not valid JSON or not a string, return the original value
        return value_str


# Helper function to build config for TTSProviderManager
def _build_tts_provider_config_data(
    args: argparse.Namespace,
    provider_class: Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]],
) -> Dict[str, Any]:
    """Builds the TTS configuration data structure for TTSProviderManager, for a single 'default'."""
    speaker_specific_config: Dict[str, Any] = {}

    # Provider name must be part of the speaker_specific_config for validation and later use by TTSProviderManager
    speaker_specific_config["provider"] = args.provider

    required_fields = provider_class.get_required_fields()
    optional_fields = provider_class.get_optional_fields()

    # If sts_id is present, skip required fields and validation, just add sts_id and any overrides (required or optional)
    if getattr(args, "sts_id", None):
        speaker_specific_config["sts_id"] = args.sts_id
        # Add any supplied required or optional fields as overrides (except provider and sts_id)
        for field in required_fields + optional_fields:
            if field in ("provider", "sts_id"):
                continue
            value = getattr(args, field, None)
            if value is not None:
                speaker_specific_config[field] = value
        return {"default": speaker_specific_config}

    # Otherwise, require all required fields and validate
    for field in required_fields:
        if field == "provider":  # Already added
            continue
        speaker_specific_config[field] = getattr(args, field)

    for field in optional_fields:
        value = getattr(args, field, None)
        if value is not None:
            speaker_specific_config[field] = value

    # Validate the constructed speaker config
    try:
        provider_class.validate_speaker_config(speaker_specific_config)
    except Exception as e:
        raise ValueError(
            f"Generated speaker_config for provider '{args.provider}' is invalid: {e}"
        )

    # TTSProviderManager expects a dict of {speaker_name: speaker_config_dict}
    return {"default": speaker_specific_config}


def main() -> int:
    # Get available providers
    available_providers = []
    tts_providers_dir = os.path.join(os.path.dirname(__file__), "..", "tts_providers")
    for item in os.listdir(tts_providers_dir):
        if os.path.isdir(os.path.join(tts_providers_dir, item)) and item not in [
            "base",
            "__pycache__",
            "dummy_common",
        ]:
            try:
                get_provider_class(item)
                available_providers.append(item)
            except ValueError:
                continue

    parser = argparse.ArgumentParser(
        description="Generate speech files using TTS providers."
    )
    parser.add_argument(
        "provider", choices=available_providers, help="TTS provider to use"
    )
    parser.add_argument(
        "--sts_id",
        required=False,
        help="Voice library sts_id to expand into full voice_config",
    )

    # Check if --sts_id is present in sys.argv (before parsing)
    import sys

    sts_id_present = any(
        arg == "--sts_id" or arg.startswith("--sts_id=") for arg in sys.argv
    )

    # Temporarily parse known args to get the provider name for dynamic argument setup
    temp_args, _ = parser.parse_known_args()
    provider_name_for_args = temp_args.provider

    # Get provider class to determine fields
    provider_class = get_provider_class(provider_name_for_args)
    required_fields = provider_class.get_required_fields()
    optional_fields = provider_class.get_optional_fields()

    # Add arguments for each required field (excluding 'provider' as it's a positional arg)
    for field in required_fields:
        if field == "provider":
            continue
        parser.add_argument(
            f"--{field}",
            required=not sts_id_present,
            type=json_or_str_type,
            help=f"Required {field} parameter for {provider_name_for_args}{' (ignored if --sts_id is provided)' if sts_id_present else ''}",
        )

    # Add arguments for each optional field
    for field in optional_fields:
        parser.add_argument(
            f"--{field}",
            required=False,
            type=json_or_str_type,
            help=f"Optional {field} parameter for {provider_name_for_args}",
        )

    parser.add_argument("texts", nargs="+", help="Text strings to convert to speech")
    parser.add_argument(
        "--variants",
        "-v",
        type=int,
        default=1,
        help="Number of variants to generate for each text (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        default="standalone_speech",
        help="Directory for output files (default: standalone_speech)",
    )

    # Add split audio arguments
    parser.add_argument(
        "--split-audio",
        action="store_true",
        help="Enable split audio mode - splits after constant sentence",
    )
    parser.add_argument(
        "--silence-threshold",
        type=int,
        default=-40,
        help="Silence threshold in dBFS for splitting (default: -40)",
    )
    parser.add_argument(
        "--min-silence-len",
        type=int,
        default=500,
        help="Minimum silence length in ms for splitting (default: 500)",
    )
    parser.add_argument(
        "--keep-silence",
        type=int,
        default=100,
        help="Amount of silence to keep in ms after splitting (default: 100)",
    )

    args = parser.parse_args()

    # Configure ffmpeg if using split audio method
    if args.split_audio:
        try:
            configure_ffmpeg()
        except Exception as e:
            logger.error(f"Error configuring ffmpeg: {e}")
            return 1

    try:
        # Get the provider class again based on the final parsed args.provider
        # This is important because parse_known_args might not have all info if args are interleaved.
        final_provider_class = get_provider_class(args.provider)

        # Build the configuration data for TTSProviderManager
        tts_provider_config_data = _build_tts_provider_config_data(
            args, final_provider_class
        )

        # Instantiate TTSProviderManager
        tts_manager = TTSProviderManager(
            config_data=tts_provider_config_data,
            overall_provider=None,
            dummy_tts_provider_override=False,  # Standalone utility typically doesn't use dummy override
        )

        # Generate speech for each text string
        for text in args.texts:
            for variant in range(1, args.variants + 1):
                generate_standalone_speech(
                    tts_manager=tts_manager,
                    text=text,
                    variant_num=variant if args.variants > 1 else 1,
                    output_dir=args.output_dir,
                    split_audio=args.split_audio,
                    silence_threshold=args.silence_threshold,
                    min_silence_len=args.min_silence_len,
                    keep_silence=args.keep_silence,
                )

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
