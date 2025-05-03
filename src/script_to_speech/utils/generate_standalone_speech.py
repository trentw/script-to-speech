import argparse
import importlib
import io
import os
import re
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
    provider_class: Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]],
    speaker_config: Dict[str, Any],
    text: str,
    variant_num: int = 1,
    output_dir: str = "standalone_speech",
    split_audio: bool = False,
    silence_threshold: int = -40,
    min_silence_len: int = 500,
    keep_silence: int = 100,
) -> None:
    """
    Generate speech using specified provider.

    Args:
        provider_class: TTS provider class (stateful or stateless)
        speaker_config: Configuration dictionary for the specific voice/speaker
        text: Text to convert to speech
        variant_num: Variant number when generating multiple versions
        output_dir: Directory for output files
        split_audio: Whether to split the audio after a constant sentence
        silence_threshold: Silence threshold in dBFS for splitting
        min_silence_len: Minimum silence length in ms for splitting
        keep_silence: Amount of silence to keep in ms after splitting
    """
    try:
        # Prepend constant sentence if split mode is enabled
        generation_text = f"{SPLIT_SENTENCE} {text}" if split_audio else text

        # Instantiate the client
        client = provider_class.instantiate_client()

        # Generate speech based on provider type
        if issubclass(provider_class, StatefulTTSProviderBase):
            # Create and use stateful provider instance
            provider_instance = provider_class()
            audio_data = provider_instance.generate_audio(
                client, speaker_config, generation_text
            )
        else:  # Stateless class
            # Call class method directly
            audio_data = provider_class.generate_audio(
                client, speaker_config, generation_text
            )

        # Create timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create base filename components
        text_preview = clean_filename(text[:30])
        variant_suffix = f"_variant{variant_num}" if variant_num > 1 else ""
        # Get provider and speaker identifiers (directly from class methods)
        provider_id = provider_class.get_provider_identifier()
        voice_id = provider_class.get_speaker_identifier(speaker_config)

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
        filename = f"{provider_id}--{voice_id}--{text_preview}{variant_suffix}--{timestamp}.mp3"
        output_path = os.path.join(output_dir, filename)

        # Save audio
        with open(output_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"Generated speech file: {output_path}")

    except Exception as e:
        logger.error(f"Error generating speech: {e}")


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

        # Build command with all configuration parameters
        config_params = []
        for param_name, param_value in config.items():
            if (
                param_name != "provider" and param_value is not None
            ):  # Filter out 'provider' key
                config_params.append(f"--{param_name} {param_value}")

        texts_quoted = [f'"{t}"' for t in texts]

        return f"python -m script_to_speech.utils.generate_standalone_speech {provider_name} {' '.join(config_params)} {' '.join(texts_quoted)}"
    except Exception as e:
        logger.error(f"Error generating command string: {e}")
        return ""


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

    # Get provider class to determine fields
    provider_class = get_provider_class(parser.parse_known_args()[0].provider)
    required_fields = provider_class.get_required_fields()
    optional_fields = provider_class.get_optional_fields()

    # Add arguments for each required field
    for field in required_fields:
        parser.add_argument(
            f"--{field}",
            required=True,
            help=f"Required {field} parameter for {parser.parse_known_args()[0].provider}",
        )

    # Add arguments for each optional field
    for field in optional_fields:
        parser.add_argument(
            f"--{field}",
            required=False,
            help=f"Optional {field} parameter for {parser.parse_known_args()[0].provider}",
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

    # Build the speaker configuration dictionary from arguments
    speaker_config: Dict[str, Any] = {}

    # Add required fields
    for field in required_fields:
        speaker_config[field] = getattr(args, field)

    # Add optional fields if provided
    for field in optional_fields:
        value = getattr(args, field, None)
        if value is not None:
            speaker_config[field] = value

    try:
        # Validate the constructed speaker config using the provider class
        provider_class.validate_speaker_config(speaker_config)

        # Store the provider class reference directly (no instantiation at this point)
        provider_ref = provider_class

        # Generate speech for each text string
        for text in args.texts:
            for variant in range(1, args.variants + 1):
                generate_standalone_speech(
                    provider_class=provider_ref,
                    speaker_config=speaker_config,
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
